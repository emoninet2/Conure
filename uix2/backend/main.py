import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()

APP_ORIGIN = "http://localhost:5173"
STATE_FILE = Path(__file__).with_name("state.json")

DEFAULT_STATE: Dict[str, Any] = {
    "nav": {
        "page": "landing",   # "landing" | "home"
        "tab": "artgen",     # active tab inside home
    },
    "ui": {
        "home": {
            "tabs": {
                "artgen": {},
                "sim": {},
                "sweep": {},
                "model": {},
                "optimz": {},
            }
        }
    }
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[APP_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def read_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return DEFAULT_STATE
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_STATE


def write_state(state: Dict[str, Any]) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


REPLACE_PATHS = {
    ("artwork", "parameters"),
    ("artwork", "metadata"),
    ("artwork", "layers"),
    ("artwork", "vias"),
    ("artwork", "viaPadStack"),
    ("artwork", "bridges"),
    ("artwork", "ports"),
    ("artwork", "arms"),
    ("artwork", "segments"),
    ("artwork", "guardRing"),
}


def deep_merge(target: Dict[str, Any], patch: Dict[str, Any], path: Tuple[str, ...] = ()) -> None:
    for key, value in patch.items():
        new_path = path + (key,)

        # Optional: allow explicit deletes by sending null
        if value is None:
            target.pop(key, None)
            continue

        # Replace entire subtree for specific paths (so deletes work)
        if new_path in REPLACE_PATHS:
            target[key] = value
            continue

        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge(target[key], value, new_path)
        else:
            target[key] = value


@app.get("/api/state")
def get_state():
    return read_state()


@app.patch("/api/state")
def patch_state(partial: Dict[str, Any]):
    current = read_state()
    deep_merge(current, partial)
    write_state(current)
    return {"ok": True}


# ----------------------------
# Preview SVG + GDS generation
# ----------------------------

# Update this if your folder layout differs.
# This matches your example: '../../artwork_generator/artwork_generator.py'
GENERATOR_PY = (Path(__file__).resolve().parent / "../../artwork_generator/artwork_generator.py").resolve()

# Where generated previews live (token folders)
PREVIEW_ROOT = (Path(__file__).resolve().parent / ".previews").resolve()
PREVIEW_ROOT.mkdir(parents=True, exist_ok=True)


def _find_newest_file(root: Path, ext: str) -> Optional[Path]:
    files = list(root.rglob(f"*.{ext}"))
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def _cleanup_old_previews(max_age_seconds: int = 60 * 30) -> None:
    """Best-effort cleanup of preview folders older than max_age_seconds (default 30 min)."""
    now = time.time()
    for p in PREVIEW_ROOT.iterdir():
        try:
            if not p.is_dir():
                continue
            age = now - p.stat().st_mtime
            if age > max_age_seconds:
                shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass


@app.post("/api/preview/generate")
def generate_preview(payload: Dict[str, Any]):
    """
    Accepts either:
      - { "artwork": { ... } }
      - { ... }  (artwork object directly)

    Generates both .svg and .gds (as produced by your generator) and returns:
      - token (used for file download endpoints)
      - svgText (for inline render)
      - svgName / gdsName (filenames found)
    """
    _cleanup_old_previews()

    artwork = payload.get("artwork", payload)
    if not isinstance(artwork, dict):
        raise HTTPException(status_code=400, detail="Invalid payload: expected an artwork object (dict).")

    if not GENERATOR_PY.exists():
        raise HTTPException(status_code=500, detail=f"Generator script not found at: {str(GENERATOR_PY)}")

    token = uuid.uuid4().hex
    out_dir = PREVIEW_ROOT / token
    out_dir.mkdir(parents=True, exist_ok=True)

    in_json = out_dir / "artwork.json"
    in_json.write_text(json.dumps(artwork, ensure_ascii=False, indent=2), encoding="utf-8")

    cmd = [
        sys.executable,                 # use same python/venv as backend
        str(GENERATOR_PY),
        "-a", str(in_json),
        "-o", str(out_dir),
        "-n", "artwork",
        "--layout",
        "--svg",
    ]

    try:
        res = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(GENERATOR_PY.parent),
            env=os.environ.copy(),
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Preview generation failed",
                "returncode": e.returncode,
                "stdout": e.stdout[-8000:] if e.stdout else "",
                "stderr": e.stderr[-8000:] if e.stderr else "",
                "cmd": cmd,
            },
        )

    svg_path = _find_newest_file(out_dir, "svg")
    gds_path = _find_newest_file(out_dir, "gds")

    if not svg_path or not svg_path.exists():
        raise HTTPException(
            status_code=500,
            detail={
                "message": "No .svg produced by generator.",
                "out_dir": str(out_dir),
                "stdout": res.stdout[-8000:] if res.stdout else "",
                "stderr": res.stderr[-8000:] if res.stderr else "",
            },
        )

    svg_text = svg_path.read_text(encoding="utf-8", errors="replace")

    return {
        "token": token,
        "svgName": svg_path.name,
        "gdsName": gds_path.name if (gds_path and gds_path.exists()) else None,
        "svgText": svg_text,
    }


@app.get("/api/preview/{token}/svg")
def download_preview_svg(token: str):
    folder = (PREVIEW_ROOT / token).resolve()
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Preview not found")

    svg_path = _find_newest_file(folder, "svg")
    if not svg_path or not svg_path.exists():
        raise HTTPException(status_code=404, detail="SVG not found")

    return FileResponse(
        path=str(svg_path),
        media_type="image/svg+xml",
        filename=svg_path.name,
    )


@app.get("/api/preview/{token}/gds")
def download_preview_gds(token: str):
    folder = (PREVIEW_ROOT / token).resolve()
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Preview not found")

    gds_path = _find_newest_file(folder, "gds")
    if not gds_path or not gds_path.exists():
        raise HTTPException(status_code=404, detail="GDS not found")

    return FileResponse(
        path=str(gds_path),
        media_type="application/octet-stream",
        filename=gds_path.name,
    )
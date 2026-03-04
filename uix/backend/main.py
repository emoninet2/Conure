import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()

APP_ORIGIN = "http://localhost:5173"

BACKEND_DIR = Path(__file__).resolve().parent / "../../data"

# Workspace folder (inside backend folder)
WORKSPACE_ROOT = (BACKEND_DIR / "workspace").resolve()
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

ACTIVE_FILE = WORKSPACE_ROOT / ".active_project"  # contains project_id (folder name)

# Your default state/project content
DEFAULT_PROJECT: Dict[str, Any] = {
    "nav": {
        "page": "landing",
        "tab": "artgen",
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


# -------------------------
# Helpers
# -------------------------
def normalize_project_name(name: str) -> str:
    """
    Make a safe folder name from user input.
    - lowercase
    - spaces -> underscores
    - keep a-z 0-9 _ -
    """
    name = (name or "").strip().lower()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9_\-]", "", name)
    name = name.strip("_-")

    if not name:
        raise HTTPException(status_code=400, detail="Project name is invalid/empty after normalization.")

    if len(name) > 60:
        raise HTTPException(status_code=400, detail="Project name too long (max 60 after normalization).")

    return name


def _project_dir(project_id: str) -> Path:
    p = (WORKSPACE_ROOT / project_id).resolve()
    if WORKSPACE_ROOT not in p.parents:
        raise HTTPException(status_code=400, detail="Invalid project id.")
    return p


def _project_json_path(project_id: str) -> Path:
    return _project_dir(project_id) / "project.json"


def _meta_path(project_id: str) -> Path:
    return _project_dir(project_id) / "meta.json"


def _read_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_active_project_id() -> Optional[str]:
    if not ACTIVE_FILE.exists():
        return None
    pid = ACTIVE_FILE.read_text(encoding="utf-8").strip()
    if not pid:
        return None

    # if active folder no longer exists, clear it
    pdir = WORKSPACE_ROOT / pid
    if not pdir.exists():
        ACTIVE_FILE.write_text("", encoding="utf-8")
        return None

    return pid


def _set_active_project_id(project_id: str) -> None:
    ACTIVE_FILE.write_text(project_id, encoding="utf-8")


def deep_merge(target: Dict[str, Any], patch: Dict[str, Any], path: Tuple[str, ...] = ()) -> None:
    for key, value in patch.items():
        new_path = path + (key,)

        # allow explicit deletes by sending null
        if value is None:
            target.pop(key, None)
            continue

        # replace entire subtree for specific paths (so deletes work)
        if new_path in REPLACE_PATHS:
            target[key] = value
            continue

        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge(target[key], value, new_path)
        else:
            target[key] = value


# -------------------------
# Projects API
# -------------------------
@app.get("/api/projects")
def list_projects():
    active = _get_active_project_id()
    items = []

    for p in WORKSPACE_ROOT.iterdir():
        if not p.is_dir():
            continue
        if p.name.startswith("."):
            continue

        project_id = p.name
        meta = _read_json(p / "meta.json", {})
        pj = p / "project.json"

        mtime = pj.stat().st_mtime if pj.exists() else p.stat().st_mtime

        items.append(
            {
                "id": project_id,
                "name": meta.get("displayName", project_id),
                "created": meta.get("created"),
                "modified": mtime,
                "isActive": project_id == active,
            }
        )

    items.sort(key=lambda x: x["modified"] or 0, reverse=True)
    return {"activeProjectId": active, "projects": items}


@app.post("/api/projects")
def create_project(payload: Dict[str, Any]):
    raw_name = payload.get("name", "")
    project_id = normalize_project_name(raw_name)

    pdir = _project_dir(project_id)
    if pdir.exists():
        raise HTTPException(status_code=400, detail="Project already exists.")

    pdir.mkdir(parents=True, exist_ok=False)

    # create previews folder
    (pdir / "previews").mkdir(parents=True, exist_ok=True)

    # meta + project.json
    _write_json(_meta_path(project_id), {"displayName": raw_name.strip(), "created": time.time()})
    _write_json(_project_json_path(project_id), DEFAULT_PROJECT)

    # OPTIONAL: do NOT auto-open. (You can if you want)
    # _set_active_project_id(project_id)

    return {"id": project_id, "name": raw_name.strip()}


@app.post("/api/projects/{project_id}/open")
def open_project(project_id: str):
    pdir = _project_dir(project_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Project not found.")

    pj = _project_json_path(project_id)
    if not pj.exists():
        _write_json(pj, DEFAULT_PROJECT)

    (pdir / "previews").mkdir(parents=True, exist_ok=True)

    _set_active_project_id(project_id)
    return {"ok": True, "activeProjectId": project_id}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    pdir = _project_dir(project_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Project not found.")

    if _get_active_project_id() == project_id:
        ACTIVE_FILE.write_text("", encoding="utf-8")

    shutil.rmtree(pdir, ignore_errors=True)
    return {"ok": True}


@app.get("/api/projects/active")
def get_active_project():
    pid = _get_active_project_id()
    if not pid:
        return {"activeProjectId": None}

    meta = _read_json(_meta_path(pid), {})
    return {"activeProjectId": pid, "name": meta.get("displayName", pid)}


# -------------------------
# State API (project.json)
# -------------------------
@app.get("/api/state")
def get_state():
    """
    IMPORTANT FIX:
    If no project is open yet, return DEFAULT_PROJECT instead of error.
    This prevents your app's initial load() from failing.
    """
    pid = _get_active_project_id()
    if not pid:
        return DEFAULT_PROJECT
    return _read_json(_project_json_path(pid), DEFAULT_PROJECT)


@app.patch("/api/state")
def patch_state(partial: Dict[str, Any]):
    pid = _get_active_project_id()
    if not pid:
        raise HTTPException(status_code=400, detail="No project open. Open a project first.")

    current = _read_json(_project_json_path(pid), DEFAULT_PROJECT)
    deep_merge(current, partial)
    _write_json(_project_json_path(pid), current)
    return {"ok": True}


# ----------------------------
# Preview SVG + GDS generation
# ----------------------------
GENERATOR_PY = (BACKEND_DIR / "../artwork_generator/artwork_generator.py").resolve()


def _preview_root_for_active_project() -> Path:
    pid = _get_active_project_id()
    if not pid:
        raise HTTPException(status_code=400, detail="No project open. Open a project first.")
    root = (_project_dir(pid) / "previews").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _find_newest_file(root: Path, ext: str) -> Optional[Path]:
    files = list(root.rglob(f"*.{ext}"))
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def _cleanup_old_previews(preview_root: Path, max_age_seconds: int = 60 * 30) -> None:
    """
    Cleanup preview token folders older than max_age_seconds.
    Reliable method: each token folder has a ".created" file.
    """
    now = time.time()
    for p in preview_root.iterdir():
        try:
            if not p.is_dir():
                continue
            created_file = p / ".created"
            if created_file.exists():
                try:
                    created_ts = float(created_file.read_text(encoding="utf-8").strip())
                except Exception:
                    created_ts = p.stat().st_mtime
            else:
                created_ts = p.stat().st_mtime

            if (now - created_ts) > max_age_seconds:
                shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass


@app.post("/api/preview/generate")
def generate_preview(payload: Dict[str, Any]):
    preview_root = _preview_root_for_active_project()
    _cleanup_old_previews(preview_root)

    artwork = payload.get("artwork", payload)
    if not isinstance(artwork, dict):
        raise HTTPException(status_code=400, detail="Invalid payload: expected an artwork object (dict).")

    if not GENERATOR_PY.exists():
        raise HTTPException(status_code=500, detail=f"Generator script not found at: {str(GENERATOR_PY)}")

    token = uuid.uuid4().hex
    out_dir = (preview_root / token).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".created").write_text(str(time.time()), encoding="utf-8")

    in_json = out_dir / "artwork.json"
    in_json.write_text(json.dumps(artwork, ensure_ascii=False, indent=2), encoding="utf-8")

    cmd = [
        sys.executable,
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
                "stdout": (e.stdout or "")[-8000:],
                "stderr": (e.stderr or "")[-8000:],
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
                "stdout": (res.stdout or "")[-8000:],
                "stderr": (res.stderr or "")[-8000:],
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
    preview_root = _preview_root_for_active_project()
    folder = (preview_root / token).resolve()
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Preview not found")

    svg_path = _find_newest_file(folder, "svg")
    if not svg_path or not svg_path.exists():
        raise HTTPException(status_code=404, detail="SVG not found")

    return FileResponse(path=str(svg_path), media_type="image/svg+xml", filename=svg_path.name)


@app.get("/api/preview/{token}/gds")
def download_preview_gds(token: str):
    preview_root = _preview_root_for_active_project()
    folder = (preview_root / token).resolve()
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Preview not found")

    gds_path = _find_newest_file(folder, "gds")
    if not gds_path or not gds_path.exists():
        raise HTTPException(status_code=404, detail="GDS not found")

    return FileResponse(path=str(gds_path), media_type="application/octet-stream", filename=gds_path.name)
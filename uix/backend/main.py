import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse


app = FastAPI()

APP_ORIGIN = "http://localhost:5173"

BACKEND_DIR = Path(__file__).resolve().parent / "../../data"

WORKSPACE_ROOT = (BACKEND_DIR / "workspace").resolve()
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

ACTIVE_FILE = WORKSPACE_ROOT / ".active_project"

# IMPORTANT:
# This lock protects all read-modify-write operations on project.json.
PROJECT_STATE_LOCK = threading.RLock()
ACTIVE_FILE_LOCK = threading.RLock()

DEFAULT_PROJECT: Dict[str, Any] = {
    "project": {"id": None, "name": None},
    "nav": {"page": "landing", "tab": "artgen"},
    "ui": {
        "home": {
            "tabs": {
                "artgen": {},
                "sim": {},
                "sweep": {
                    "activeSweep": "",
                    "running": False,
                    "draftConfig": {
                        "enable_layout": True,
                        "enable_svg": True,
                        "enable_simulation": False,
                        "pack_sim": False,
                        "simulator": "emx",
                        "force_overwrite": False,
                        "parameters": [],
                    },
                },
                "model": {},
                "optimz": {},
            }
        }
    },
    "artwork": {},
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


# ------------------------------------------------------------
# General helpers
# ------------------------------------------------------------
def _deepcopy_jsonish(obj: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(obj))


def normalize_project_name(name: str) -> str:
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


def _read_json(path: Path, fallback: Dict[str, Any], *, strict: bool = False) -> Dict[str, Any]:
    if not path.exists():
        return _deepcopy_jsonish(fallback)

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        if strict:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read JSON file '{path.name}'. The file may be corrupted or partially written. Error: {e}",
            )
        return _deepcopy_jsonish(fallback)


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    """
    Atomic JSON write:
    write to temp file in same directory, then replace.
    This prevents readers from seeing partially written JSON.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _get_active_project_id() -> Optional[str]:
    with ACTIVE_FILE_LOCK:
        if not ACTIVE_FILE.exists():
            return None

        pid = ACTIVE_FILE.read_text(encoding="utf-8").strip()
        if not pid:
            return None

        pdir = WORKSPACE_ROOT / pid
        if not pdir.exists():
            ACTIVE_FILE.write_text("", encoding="utf-8")
            return None

        return pid


def _set_active_project_id(project_id: str) -> None:
    with ACTIVE_FILE_LOCK:
        ACTIVE_FILE.write_text(project_id, encoding="utf-8")


def deep_merge(target: Dict[str, Any], patch: Dict[str, Any], path: Tuple[str, ...] = ()) -> None:
    for key, value in patch.items():
        new_path = path + (key,)

        if value is None:
            target.pop(key, None)
            continue

        if new_path in REPLACE_PATHS:
            target[key] = value
            continue

        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge(target[key], value, new_path)
        else:
            target[key] = value


def _read_project_state() -> Dict[str, Any]:
    pid = _get_active_project_id()
    if not pid:
        raise HTTPException(status_code=400, detail="No project open.")

    with PROJECT_STATE_LOCK:
        return _read_json(_project_json_path(pid), _deepcopy_jsonish(DEFAULT_PROJECT), strict=True)


def _write_project_state(state: Dict[str, Any]) -> None:
    pid = _get_active_project_id()
    if not pid:
        raise HTTPException(status_code=400, detail="No project open.")

    with PROJECT_STATE_LOCK:
        _write_json(_project_json_path(pid), state)


# ------------------------------------------------------------
# Projects API
# ------------------------------------------------------------
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
    (pdir / "previews").mkdir(parents=True, exist_ok=True)

    _write_json(_meta_path(project_id), {"displayName": raw_name.strip(), "created": time.time()})
    _write_json(_project_json_path(project_id), _deepcopy_jsonish(DEFAULT_PROJECT))

    return {"id": project_id, "name": raw_name.strip()}


@app.post("/api/projects/{project_id}/open")
def open_project(project_id: str):
    pdir = _project_dir(project_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Project not found.")

    pj = _project_json_path(project_id)
    if not pj.exists():
        _write_json(pj, _deepcopy_jsonish(DEFAULT_PROJECT))

    (pdir / "previews").mkdir(parents=True, exist_ok=True)

    _set_active_project_id(project_id)
    return {"ok": True, "activeProjectId": project_id}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    pdir = _project_dir(project_id)
    if not pdir.exists():
        raise HTTPException(status_code=404, detail="Project not found.")

    if _get_active_project_id() == project_id:
        with ACTIVE_FILE_LOCK:
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


# ------------------------------------------------------------
# State API (project.json)
# ------------------------------------------------------------
@app.get("/api/state")
def get_state():
    pid = _get_active_project_id()
    if not pid:
        return _deepcopy_jsonish(DEFAULT_PROJECT)

    with PROJECT_STATE_LOCK:
        return _read_json(_project_json_path(pid), _deepcopy_jsonish(DEFAULT_PROJECT), strict=True)


@app.patch("/api/state")
def patch_state(partial: Dict[str, Any]):
    pid = _get_active_project_id()
    if not pid:
        raise HTTPException(status_code=400, detail="No project open. Open a project first.")

    project_path = _project_json_path(pid)

    with PROJECT_STATE_LOCK:
        current = _read_json(project_path, _deepcopy_jsonish(DEFAULT_PROJECT), strict=True)
        deep_merge(current, partial)
        _write_json(project_path, current)

    return {"ok": True}


# ------------------------------------------------------------
# Preview SVG + GDS generation
# ------------------------------------------------------------
GENERATOR_PY = (BACKEND_DIR / "../artwork_generator/artwork_generator.py").resolve()


def _preview_root_for_active_project() -> Path:
    pid = _get_active_project_id()
    if not pid:
        raise HTTPException(status_code=400, detail="No project open. Open a project first.")

    root = _project_dir(pid).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _find_newest_file(root: Path, ext: str) -> Optional[Path]:
    files = list(root.rglob(f"*.{ext}"))
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def _cleanup_old_previews(preview_root: Path, max_age_seconds: int = 60 * 30) -> None:
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

    out_dir = preview_root
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
        "svgName": svg_path.name,
        "gdsName": gds_path.name if (gds_path and gds_path.exists()) else None,
        "svgText": svg_text,
    }


@app.get("/api/preview/svg")
def download_preview_svg():
    preview_root = _preview_root_for_active_project()
    folder = preview_root.resolve()

    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Preview not found")

    svg_path = _find_newest_file(folder, "svg")
    if not svg_path or not svg_path.exists():
        raise HTTPException(status_code=404, detail="SVG not found")

    return FileResponse(path=str(svg_path), media_type="image/svg+xml", filename=svg_path.name)


@app.get("/api/preview/gds")
def download_preview_gds():
    preview_root = _preview_root_for_active_project()
    folder = preview_root.resolve()

    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Preview not found")

    gds_path = _find_newest_file(folder, "gds")
    if not gds_path or not gds_path.exists():
        raise HTTPException(status_code=404, detail="GDS not found")

    return FileResponse(path=str(gds_path), media_type="application/octet-stream", filename=gds_path.name)


# ------------------------------------------------------------
# Sweep API
# ------------------------------------------------------------
SWEEP_ACTIVE_RUN_KEY = "active"

SWEEP_RUNS: Dict[str, subprocess.Popen] = {}
SWEEP_RUN_META: Dict[str, Dict[str, Any]] = {}

SWEEP_RING: list[dict] = []
SWEEP_RING_MAX = 5000
SWEEP_RING_LOCK = threading.Lock()


def normalize_sweep_name(name: str) -> str:
    name = (name or "").strip().lower()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9_\-]", "", name)
    name = name.strip("_-")

    if not name:
        raise HTTPException(status_code=400, detail="Sweep name is invalid/empty after normalization.")
    if len(name) > 80:
        raise HTTPException(status_code=400, detail="Sweep name too long (max 80 after normalization).")

    return name


def _active_project_dir() -> Path:
    pid = _get_active_project_id()
    if not pid:
        raise HTTPException(status_code=400, detail="No project open. Open a project first.")
    return _project_dir(pid)


def _sweeps_root_for_active_project() -> Path:
    root = (_active_project_dir() / "sweep").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sweep_dir(sweep_name: str) -> Path:
    root = _sweeps_root_for_active_project()
    safe = normalize_sweep_name(sweep_name)
    p = (root / safe).resolve()
    if root not in p.parents and p != root:
        raise HTTPException(status_code=400, detail="Invalid sweep name.")
    return p


def _sweep_json_path(sweep_name: str) -> Path:
    return _sweep_dir(sweep_name) / "sweep.json"


def _default_sweep_file() -> Dict[str, Any]:
    return {"parameters": {}}


def _default_sweep_draft() -> Dict[str, Any]:
    return {
        "enable_layout": True,
        "enable_svg": True,
        "enable_simulation": False,
        "pack_sim": False,
        "simulator": "emx",
        "force_overwrite": False,
        "parameters": [],
    }


def _set_project_sweep_ui(active_sweep=None, running=None, draft_config=None) -> None:
    with PROJECT_STATE_LOCK:
        current = _read_project_state()
        ui = current.setdefault("ui", {}).setdefault("home", {}).setdefault("tabs", {}).setdefault("sweep", {})

        if active_sweep is not None:
            ui["activeSweep"] = active_sweep
        if running is not None:
            ui["running"] = running
        if draft_config is not None:
            ui["draftConfig"] = draft_config

        _write_project_state(current)


def _push_sweep_line(stream: str, line: str) -> None:
    item = {"t": time.time(), "stream": stream, "line": line}
    with SWEEP_RING_LOCK:
        SWEEP_RING.append(item)
        if len(SWEEP_RING) > SWEEP_RING_MAX:
            del SWEEP_RING[: len(SWEEP_RING) - SWEEP_RING_MAX]


def _sweep_reader_thread(pipe, stream_name: str):
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            _push_sweep_line(stream_name, line.rstrip("\n"))
    except Exception as e:
        _push_sweep_line("system", f"[reader:{stream_name}] exception: {e}")
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _validate_sweep_ui_config(config: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="config must be an object.")

    sweep_json = config.get("sweep_json")
    if not isinstance(sweep_json, dict):
        raise HTTPException(status_code=400, detail="config.sweep_json must be an object.")

    parameters = sweep_json.get("parameters")
    if not isinstance(parameters, dict):
        raise HTTPException(status_code=400, detail="sweep_json.parameters must be an object.")

    for pname, pvalue in parameters.items():
        if not isinstance(pname, str) or not pname.strip():
            raise HTTPException(status_code=400, detail="Invalid sweep parameter name.")

        if isinstance(pvalue, list):
            continue

        if isinstance(pvalue, dict):
            required = {"from", "to", "type", "value"}
            if not required.issubset(set(pvalue.keys())):
                raise HTTPException(
                    status_code=400,
                    detail=f"Parameter '{pname}' range object must contain from, to, type, value.",
                )
            if pvalue["type"] not in ("step", "npoints"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Parameter '{pname}' type must be 'step' or 'npoints'.",
                )
            continue

        raise HTTPException(
            status_code=400,
            detail=f"Parameter '{pname}' must be either a list or a range object.",
        )

    return config


def _sweep_file_to_rows(sweep_file: Dict[str, Any]) -> list:
    params = sweep_file.get("parameters", {})
    rows = []

    for name, value in params.items():
        if isinstance(value, list):
            rows.append(
                {
                    "name": name,
                    "mode": "list",
                    "list": value,
                    "listText": ", ".join(str(x) for x in value),
                    "from": "",
                    "to": "",
                    "rangeType": "step",
                    "value": "",
                }
            )
        else:
            rows.append(
                {
                    "name": name,
                    "mode": "range",
                    "list": [],
                    "listText": "",
                    "from": value.get("from", ""),
                    "to": value.get("to", ""),
                    "rangeType": value.get("type", "step"),
                    "value": value.get("value", ""),
                }
            )

    return rows


@app.get("/api/sweeps")
def list_sweeps():
    root = _sweeps_root_for_active_project()
    items = []

    for p in root.iterdir():
        if p.is_dir() and not p.name.startswith("."):
            items.append(p.name)

    items.sort()
    return {"sweeps": items}


@app.post("/api/sweeps/create")
def create_sweep(payload: Dict[str, Any] = Body(...)):
    sweep_name = normalize_sweep_name(payload.get("sweep_name", ""))
    sdir = _sweep_dir(sweep_name)

    if sdir.exists():
        raise HTTPException(status_code=400, detail="Sweep already exists.")

    sdir.mkdir(parents=True, exist_ok=False)
    _write_json(_sweep_json_path(sweep_name), _default_sweep_file())

    _set_project_sweep_ui(
        active_sweep=sweep_name,
        running=False,
        draft_config=_default_sweep_draft(),
    )

    return {"ok": True, "sweep_name": sweep_name}


@app.post("/api/sweeps/open")
def open_sweep(payload: Dict[str, Any] = Body(...)):
    sweep_name = normalize_sweep_name(payload.get("sweep_name", ""))
    sdir = _sweep_dir(sweep_name)

    if not sdir.exists():
        raise HTTPException(status_code=404, detail="Sweep not found.")

    sweep_file = _read_json(_sweep_json_path(sweep_name), _default_sweep_file())

    state = _read_project_state()
    sweep_ui = state.setdefault("ui", {}).setdefault("home", {}).setdefault("tabs", {}).setdefault("sweep", {})
    prev_draft = sweep_ui.get("draftConfig", {})

    draft_config = {
        "enable_layout": bool(prev_draft.get("enable_layout", True)),
        "enable_svg": bool(prev_draft.get("enable_svg", True)),
        "enable_simulation": bool(prev_draft.get("enable_simulation", False)),
        "pack_sim": bool(prev_draft.get("pack_sim", False)),
        "simulator": prev_draft.get("simulator", "emx"),
        "force_overwrite": bool(prev_draft.get("force_overwrite", False)),
        "parameters": _sweep_file_to_rows(sweep_file),
    }

    running = False
    proc = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)
    if proc and proc.poll() is None:
        running_name = SWEEP_RUN_META.get(SWEEP_ACTIVE_RUN_KEY, {}).get("sweep_name")
        running = running_name == sweep_name

    _set_project_sweep_ui(
        active_sweep=sweep_name,
        running=running,
        draft_config=draft_config,
    )

    return {
        "ok": True,
        "sweep_name": sweep_name,
        "running": running,
        "config": {
            "enable_layout": draft_config["enable_layout"],
            "enable_svg": draft_config["enable_svg"],
            "enable_simulation": draft_config["enable_simulation"],
            "pack_sim": draft_config["pack_sim"],
            "simulator": draft_config["simulator"],
            "force_overwrite": draft_config["force_overwrite"],
            "sweep_json": sweep_file,
        },
    }


@app.post("/api/sweeps/save")
def save_sweep(payload: Dict[str, Any] = Body(...)):
    sweep_name = normalize_sweep_name(payload.get("sweep_name", ""))
    config = _validate_sweep_ui_config(payload.get("config"))

    sdir = _sweep_dir(sweep_name)
    sdir.mkdir(parents=True, exist_ok=True)

    sweep_file = config["sweep_json"]
    _write_json(_sweep_json_path(sweep_name), sweep_file)

    draft_config = {
        "enable_layout": bool(config.get("enable_layout", True)),
        "enable_svg": bool(config.get("enable_svg", True)),
        "enable_simulation": bool(config.get("enable_simulation", False)),
        "pack_sim": bool(config.get("pack_sim", False)),
        "simulator": config.get("simulator", "emx"),
        "force_overwrite": bool(config.get("force_overwrite", False)),
        "parameters": _sweep_file_to_rows(sweep_file),
    }

    _set_project_sweep_ui(
        active_sweep=sweep_name,
        draft_config=draft_config,
    )

    return {"ok": True, "sweep_name": sweep_name}


@app.get("/api/sweeps/summary")
def sweep_summary(sweep_name: str):
    sweep_name = normalize_sweep_name(sweep_name)
    summary_path = _sweep_dir(sweep_name) / "summary.json"

    if not summary_path.exists():
        return {
            "state": "idle",
            "total_permutations": 0,
            "completed_runs": 0,
            "remaining_runs": 0,
            "current_run_index": None,
            "current_run": None,
            "current_run_name": None,
            "current_permutation": None,
            "current_task": None,
            "progress_percentage": 0.0,
            "counts": {
                "layout": {"completed": 0, "failed": 0, "pending": 0},
                "svg": {"completed": 0, "failed": 0, "pending": 0},
                "simulation": {"completed": 0, "failed": 0, "pending": 0},
            },
            "started_at": None,
            "finished_at": None,
            "last_updated": None,
        }

    return _read_json(summary_path, {}, strict=False)


@app.delete("/api/sweeps/{sweep_name}")
def delete_sweep(sweep_name: str):
    sweep_name = normalize_sweep_name(sweep_name)
    sdir = _sweep_dir(sweep_name)

    if not sdir.exists():
        raise HTTPException(status_code=404, detail="Sweep not found.")

    proc = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)
    if proc and proc.poll() is None:
        running_name = SWEEP_RUN_META.get(SWEEP_ACTIVE_RUN_KEY, {}).get("sweep_name")
        if running_name == sweep_name:
            raise HTTPException(status_code=400, detail="Cannot delete a running sweep.")

    shutil.rmtree(sdir, ignore_errors=True)

    with PROJECT_STATE_LOCK:
        current = _read_project_state()
        sweep_ui = current.setdefault("ui", {}).setdefault("home", {}).setdefault("tabs", {}).setdefault("sweep", {})
        if sweep_ui.get("activeSweep") == sweep_name:
            sweep_ui["activeSweep"] = ""
            sweep_ui["running"] = False
            sweep_ui["draftConfig"] = _default_sweep_draft()
            _write_project_state(current)

    return {"ok": True, "deleted": True, "sweep_name": sweep_name}


@app.post("/api/sweeps/start")
def start_sweep(payload: Dict[str, Any] = Body(...)):
    proc_existing = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)
    if proc_existing and proc_existing.poll() is None:
        raise HTTPException(status_code=400, detail="A sweep is already running.")

    sweep_name = normalize_sweep_name(payload.get("sweep_name", ""))
    config = _validate_sweep_ui_config(payload.get("config"))

    project_dir = _active_project_dir()
    sweep_folder = _sweep_dir(sweep_name)
    sweep_folder.mkdir(parents=True, exist_ok=True)

    artwork_path = project_dir / "artwork.json"
    if not artwork_path.exists():
        raise HTTPException(status_code=400, detail="artwork.json not found in project folder.")

    enable_layout = bool(config.get("enable_layout"))
    enable_svg = bool(config.get("enable_svg"))
    enable_simulation = bool(config.get("enable_simulation"))
    pack_sim = bool(config.get("pack_sim"))
    simulator = (config.get("simulator") or "emx").lower()
    force_overwrite = bool(config.get("force_overwrite"))

    if enable_simulation:
        sim_config_path = project_dir / "simConfig.json"
        if not sim_config_path.exists():
            state = _read_project_state()
            sim_config = state.get("sim_config")
            if sim_config is None:
                raise HTTPException(
                    status_code=400,
                    detail="Simulation enabled, but simConfig.json was not found and project.json is missing sim_config.",
                )
            _write_json(sim_config_path, sim_config)

    sweep_file = config["sweep_json"]
    _write_json(_sweep_json_path(sweep_name), sweep_file)

    base_dir = Path(__file__).resolve().parent
    sweep_script = os.path.abspath(os.path.join(str(base_dir), "../../sweep/sweep.py"))

    command = [
        sys.executable,
        sweep_script,
        "-a",
        str(project_dir / "artwork.json"),
        "--sweep",
        str(sweep_folder / "sweep.json"),
        "--output",
        str(sweep_folder),
    ]

    if enable_layout:
        command.append("--layout")
    if enable_svg:
        command.append("--svg")
    if enable_simulation:
        config_path = project_dir / "simConfig.json"
        command.extend(["--simulate", "-c", str(config_path)])
        if simulator:
            command.extend(["--sim", simulator])
    if pack_sim:
        command.append("--pack_sim")
    if force_overwrite:
        command.append("--force")

    command.append("--verbose")

    with SWEEP_RING_LOCK:
        SWEEP_RING.clear()

    _push_sweep_line("system", f"Launching sweep process: {' '.join(command)}")

    try:
        proc = subprocess.Popen(
            command,
            cwd=str(project_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start sweep: {e}")

    if proc.stdout:
        threading.Thread(target=_sweep_reader_thread, args=(proc.stdout, "stdout"), daemon=True).start()
    if proc.stderr:
        threading.Thread(target=_sweep_reader_thread, args=(proc.stderr, "stderr"), daemon=True).start()

    SWEEP_RUNS[SWEEP_ACTIVE_RUN_KEY] = proc
    SWEEP_RUN_META[SWEEP_ACTIVE_RUN_KEY] = {
        "sweep_name": sweep_name,
        "cmd": command,
        "started": time.time(),
        "projectId": _get_active_project_id(),
    }

    draft_config = {
        "enable_layout": enable_layout,
        "enable_svg": enable_svg,
        "enable_simulation": enable_simulation,
        "pack_sim": pack_sim,
        "simulator": simulator,
        "force_overwrite": force_overwrite,
        "parameters": _sweep_file_to_rows(sweep_file),
    }

    _set_project_sweep_ui(
        active_sweep=sweep_name,
        running=True,
        draft_config=draft_config,
    )

    return {"ok": True, "sweep_name": sweep_name}


@app.post("/api/sweeps/stop")
def stop_sweep(payload: Dict[str, Any] = Body(default={})):
    proc = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)
    if not proc:
        _set_project_sweep_ui(running=False)
        return {"ok": True, "stopped": False, "message": "No active sweep."}

    if proc.poll() is not None:
        SWEEP_RUNS.pop(SWEEP_ACTIVE_RUN_KEY, None)
        SWEEP_RUN_META.pop(SWEEP_ACTIVE_RUN_KEY, None)
        _set_project_sweep_ui(running=False)
        _push_sweep_line("system", "Sweep already finished.")
        return {"ok": True, "stopped": False, "message": "Sweep already finished."}

    _push_sweep_line("system", "Stopping sweep…")

    try:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except Exception:
            os.killpg(proc.pid, signal.SIGKILL)
    finally:
        SWEEP_RUNS.pop(SWEEP_ACTIVE_RUN_KEY, None)
        SWEEP_RUN_META.pop(SWEEP_ACTIVE_RUN_KEY, None)
        _set_project_sweep_ui(running=False)

    _push_sweep_line("system", "Sweep stopped by user.")
    return {"ok": True, "stopped": True}


@app.get("/api/sweeps/status")
def sweep_status():
    proc = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)

    if not proc:
        _set_project_sweep_ui(running=False)
        return {"running": False, "returncode": None, "sweep_name": None}

    rc = proc.poll()
    if rc is None:
        sweep_name = SWEEP_RUN_META.get(SWEEP_ACTIVE_RUN_KEY, {}).get("sweep_name")
        return {"running": True, "returncode": None, "sweep_name": sweep_name}

    SWEEP_RUNS.pop(SWEEP_ACTIVE_RUN_KEY, None)
    finished_name = SWEEP_RUN_META.pop(SWEEP_ACTIVE_RUN_KEY, {}).get("sweep_name")
    _set_project_sweep_ui(running=False)
    _push_sweep_line("system", f"Sweep finished. returncode={rc}")
    return {"running": False, "returncode": rc, "sweep_name": finished_name}


@app.get("/api/sweeps/stream")
def sweep_stream(request: Request, sweep_name: str):
    sweep_name = normalize_sweep_name(sweep_name)

    def event_gen():
        with SWEEP_RING_LOCK:
            start_idx = max(0, len(SWEEP_RING) - 300)
            backlog = SWEEP_RING[start_idx:]

        for item in backlog:
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

        last_idx = start_idx + len(backlog)

        while True:
            if request.client is None:
                break

            try:
                with SWEEP_RING_LOCK:
                    if last_idx < len(SWEEP_RING):
                        new_items = SWEEP_RING[last_idx:]
                        last_idx = len(SWEEP_RING)
                    else:
                        new_items = []

                for item in new_items:
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

                proc = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)
                if proc:
                    rc = proc.poll()
                    if rc is not None:
                        done_msg = {
                            "t": time.time(),
                            "stream": "system",
                            "line": f"[done] returncode={rc}",
                        }
                        yield f"data: {json.dumps(done_msg, ensure_ascii=False)}\n\n"
                        break

                yield ": ping\n\n"
                time.sleep(0.35)

            except GeneratorExit:
                break
            except Exception:
                break

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ------------------------------------------------------------
# Simulation (EMX) API
# ------------------------------------------------------------
ACTIVE_RUN_KEY = "active"

SIM_RUNS: Dict[str, subprocess.Popen] = {}
SIM_RUN_META: Dict[str, Dict[str, Any]] = {}

SIM_RING: list[dict] = []
SIM_RING_MAX = 5000
SIM_RING_LOCK = threading.Lock()


def _push_sim_line(stream: str, line: str) -> None:
    item = {"t": time.time(), "stream": stream, "line": line}
    with SIM_RING_LOCK:
        SIM_RING.append(item)
        if len(SIM_RING) > SIM_RING_MAX:
            del SIM_RING[: len(SIM_RING) - SIM_RING_MAX]


def _reader_thread(pipe, stream_name: str):
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            _push_sim_line(stream_name, line.rstrip("\n"))
    except Exception as e:
        _push_sim_line("system", f"[reader:{stream_name}] exception: {e}")
    finally:
        try:
            pipe.close()
        except Exception:
            pass


@app.post("/api/sim/start")
def sim_start(payload: Dict[str, Any] = Body(default={})):
    simulator = (payload.get("simulator") or "emx").lower()
    if simulator != "emx":
        raise HTTPException(status_code=400, detail=f"Unsupported simulator: {simulator}")

    proc_existing = SIM_RUNS.get(ACTIVE_RUN_KEY)
    if proc_existing and proc_existing.poll() is None:
        raise HTTPException(status_code=400, detail="A simulation is already running.")

    pid = _get_active_project_id()
    if not pid:
        raise HTTPException(status_code=400, detail="No project open. Open a project first.")
    root = _project_dir(pid).resolve()

    with PROJECT_STATE_LOCK:
        project_data = _read_json(root / "project.json", _deepcopy_jsonish(DEFAULT_PROJECT), strict=True)

    sim_config = project_data.get("sim_config")
    if sim_config is None:
        raise HTTPException(status_code=400, detail="project.json is missing 'sim_config'.")

    config_file_path = root / "simConfig.json"
    try:
        with open(config_file_path, "w", encoding="utf-8") as json_file:
            json.dump(sim_config, json_file, indent=4)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write simConfig.json: {e}")

    simulate_script = os.path.abspath(os.path.join(str(root), "../../../simulator/simulator.py"))

    gds_path = os.path.join(str(root), "artwork.gds")
    artwork_path = os.path.join(str(root), "artwork.json")

    command = [
        sys.executable,
        simulate_script,
        "-f",
        gds_path,
        "--sim",
        "emx",
        "-c",
        str(config_file_path),
        "-a",
        artwork_path,
        "-o",
        str(root),
        "-n",
        "artwork",
        "--verbose",
    ]

    with SIM_RING_LOCK:
        SIM_RING.clear()
    _push_sim_line("system", f"Starting simulation for project '{pid}' …")
    _push_sim_line("system", f"Command: {' '.join(command)}")

    try:
        proc = subprocess.Popen(
            command,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start simulation: {e}")

    if proc.stdout:
        threading.Thread(target=_reader_thread, args=(proc.stdout, "stdout"), daemon=True).start()
    if proc.stderr:
        threading.Thread(target=_reader_thread, args=(proc.stderr, "stderr"), daemon=True).start()

    SIM_RUNS[ACTIVE_RUN_KEY] = proc
    SIM_RUN_META[ACTIVE_RUN_KEY] = {
        "simulator": simulator,
        "cmd": command,
        "started": time.time(),
        "projectId": pid,
    }

    return {"ok": True}


@app.post("/api/sim/stop")
def sim_stop(payload: Dict[str, Any] = Body(default={})):
    proc = SIM_RUNS.get(ACTIVE_RUN_KEY)
    if not proc:
        return {"ok": True, "stopped": False, "message": "No active simulation."}

    if proc.poll() is not None:
        SIM_RUNS.pop(ACTIVE_RUN_KEY, None)
        _push_sim_line("system", "Simulation already finished.")
        return {"ok": True, "stopped": False, "message": "Simulation already finished."}

    _push_sim_line("system", "Stopping simulation…")

    try:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except Exception:
            os.killpg(proc.pid, signal.SIGKILL)
    finally:
        SIM_RUNS.pop(ACTIVE_RUN_KEY, None)

    _push_sim_line("system", "Simulation stopped by user.")
    return {"ok": True, "stopped": True}


@app.get("/api/sim/status")
def sim_status():
    proc = SIM_RUNS.get(ACTIVE_RUN_KEY)

    if not proc:
        return {"running": False, "returncode": None}

    rc = proc.poll()
    if rc is None:
        return {"running": True, "returncode": None}

    SIM_RUNS.pop(ACTIVE_RUN_KEY, None)
    _push_sim_line("system", f"Simulation finished. returncode={rc}")
    return {"running": False, "returncode": rc}


@app.get("/api/sim/stream")
def sim_stream(request: Request):
    def event_gen():
        with SIM_RING_LOCK:
            start_idx = max(0, len(SIM_RING) - 300)
            backlog = SIM_RING[start_idx:]

        for item in backlog:
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

        last_idx = start_idx + len(backlog)

        while True:
            if request.client is None:
                break

            try:
                with SIM_RING_LOCK:
                    if last_idx < len(SIM_RING):
                        new_items = SIM_RING[last_idx:]
                        last_idx = len(SIM_RING)
                    else:
                        new_items = []

                for item in new_items:
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

                proc = SIM_RUNS.get(ACTIVE_RUN_KEY)
                if proc:
                    rc = proc.poll()
                    if rc is not None:
                        done_msg = {"t": time.time(), "stream": "system", "line": f"[done] returncode={rc}"}
                        yield f"data: {json.dumps(done_msg, ensure_ascii=False)}\n\n"
                        break

                yield ": ping\n\n"
                time.sleep(0.35)

            except GeneratorExit:
                break
            except Exception:
                break

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


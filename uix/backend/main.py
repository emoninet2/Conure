
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

from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from model import train


app = FastAPI()

load_dotenv()

FRONTEND_HOST = os.getenv("FRONTEND_HOST", "http://localhost")
FRONTEND_PORT = os.getenv("FRONTEND_PORT", "5173")
APP_ORIGIN = f"{FRONTEND_HOST}:{FRONTEND_PORT}"

print("APP ORIGIN IS : ", APP_ORIGIN)

BACKEND_DIR = Path(__file__).resolve().parent
print(BACKEND_DIR)

WORKSPACE_ROOT = (BACKEND_DIR / "../../data" / "workspace").resolve()
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

ACTIVE_FILE = WORKSPACE_ROOT / ".active_project"

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
                "model": {
                    "activeModel": "",
                    "running": False,
                    "draftConfig": {
                        "sweep_name": "",
                        "model_type": "ANN",
                        "translate_config": {
                            "translation_type": "FFD",
                            "translation_params": {},
                            "selection": {"x_names": [], "y_names": []},
                        },
                        "model_config": {
                            "model_name": "",
                            "normalization": {
                                "feature_method": "standard",
                                "target_method": "standard",
                            },
                            "training": {
                                "epochs": 100,
                                "batch_size": 32,
                                "loss": "mse",
                                "metrics": ["mae"],
                                "validation_split": 0.2,
                                "optimizer": {
                                    "type": "Adam",
                                    "learning_rate": 0.001,
                                    "momentum": 0.9,
                                },
                            },
                            "early_stopping": {
                                "monitor": "val_loss",
                                "patience": 15,
                                "restore_best_weights": True,
                            },
                            "architecture": [
                                {"type": "Dense", "units": 128, "activation": "relu"},
                                {"type": "Dense", "units": "AUTO", "activation": "linear"},
                            ],
                        },
                    },
                },
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
    name = (name or "").strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9_\-]", "", name)
    name = name.strip("_-")

    if not name:
        raise HTTPException(status_code=400, detail="Project name is invalid/empty after normalization.")
    if len(name) > 60:
        raise HTTPException(status_code=400, detail="Project name too long (max 60 after normalization).")

    return name


def _project_dir(project_id: str) -> Path:
    if not isinstance(project_id, str) or not project_id.strip():
        raise HTTPException(status_code=400, detail="Project id is required.")

    p = (WORKSPACE_ROOT / project_id.strip()).resolve()

    try:
        p.relative_to(WORKSPACE_ROOT)
    except ValueError:
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
# Process helpers
# ------------------------------------------------------------
def _terminate_process_group(proc: Optional[subprocess.Popen], label: str = "process", timeout: float = 5.0) -> bool:
    if not proc:
        return False

    try:
        if proc.poll() is not None:
            return False

        if os.name == "nt":
            try:
                proc.terminate()
                proc.wait(timeout=timeout)
            except Exception:
                proc.kill()
        else:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=timeout)
            except Exception:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    pass
        return True
    except Exception:
        return False


def _cleanup_run_dicts(run_dict: Dict[str, subprocess.Popen], meta_dict: Dict[str, Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
    proc = run_dict.pop(key, None)
    meta = meta_dict.pop(key, None)
    if proc:
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass
        try:
            if proc.stderr:
                proc.stderr.close()
        except Exception:
            pass
    return meta


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
    artwork_path = _project_dir(pid) / "artwork.json"

    with PROJECT_STATE_LOCK:
        current = _read_json(project_path, _deepcopy_jsonish(DEFAULT_PROJECT), strict=True)
        deep_merge(current, partial)
        _write_json(project_path, current)

        # also write standalone artwork.json whenever artwork exists
        if "artwork" in current and isinstance(current["artwork"], dict):
            _write_json(artwork_path, current["artwork"])

    return {"ok": True}


# ------------------------------------------------------------
# Preview SVG + GDS generation
# ------------------------------------------------------------
GENERATOR_PY = (BACKEND_DIR / "../../artwork_generator/artwork_generator.py").resolve()
SIMULATOR_PY = (BACKEND_DIR / "../../simulator/simulator.py").resolve()


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
        "-a",
        str(in_json),
        "-o",
        str(out_dir),
        "-n",
        "artwork",
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
    name = (name or "").strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9_\-]", "", name)
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


def _safe_sweep_child_path(child_name: str) -> Path:
    root = _sweeps_root_for_active_project()
    if not isinstance(child_name, str):
        raise HTTPException(status_code=400, detail="Invalid sweep name.")

    child_name = child_name.strip()
    if not child_name:
        raise HTTPException(status_code=400, detail="Sweep name is required.")

    p = (root / child_name).resolve()
    if p != root and root not in p.parents:
        raise HTTPException(status_code=400, detail="Invalid sweep name.")
    return p


def _sweep_dir_for_create(sweep_name: str) -> Path:
    safe = normalize_sweep_name(sweep_name)
    return _safe_sweep_child_path(safe)


def _resolve_existing_sweep_dir(sweep_name: str) -> tuple[str, Path]:
    raw_name = str(sweep_name or "").strip()
    if not raw_name:
        raise HTTPException(status_code=400, detail="Sweep name is required.")

    raw_dir = _safe_sweep_child_path(raw_name)
    if raw_dir.exists() and raw_dir.is_dir():
        return raw_dir.name, raw_dir

    try:
        normalized = normalize_sweep_name(raw_name)
    except HTTPException:
        normalized = None

    if normalized:
        norm_dir = _safe_sweep_child_path(normalized)
        if norm_dir.exists() and norm_dir.is_dir():
            return norm_dir.name, norm_dir

    raise HTTPException(status_code=404, detail="Sweep not found.")


def _sweep_json_path_from_dir(sdir: Path) -> Path:
    return sdir / "sweep.json"


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
        if not p.is_dir():
            continue
        if p.name.startswith("."):
            continue
        if not (p / "sweep.json").exists():
            continue

        items.append(p.name)

    items.sort()
    return {"sweeps": items}


@app.post("/api/sweeps/create")
def create_sweep(payload: Dict[str, Any] = Body(...)):
    requested_name = str(payload.get("sweep_name", ""))
    sdir = _sweep_dir_for_create(requested_name)
    sweep_name = sdir.name

    if sdir.exists():
        raise HTTPException(status_code=400, detail="Sweep already exists.")

    sdir.mkdir(parents=True, exist_ok=False)
    _write_json(_sweep_json_path_from_dir(sdir), _default_sweep_file())

    _set_project_sweep_ui(
        active_sweep=sweep_name,
        running=False,
        draft_config=_default_sweep_draft(),
    )

    return {"ok": True, "sweep_name": sweep_name}


@app.post("/api/sweeps/open")
def open_sweep(payload: Dict[str, Any] = Body(...)):
    requested_name = str(payload.get("sweep_name", ""))
    sweep_name, sdir = _resolve_existing_sweep_dir(requested_name)

    sweep_json_path = _sweep_json_path_from_dir(sdir)
    if not sweep_json_path.exists():
        raise HTTPException(status_code=400, detail="Sweep folder is missing sweep.json.")

    sweep_file = _read_json(sweep_json_path, _default_sweep_file(), strict=True)

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
    requested_name = str(payload.get("sweep_name", ""))
    config = _validate_sweep_ui_config(payload.get("config"))

    try:
        sweep_name, sdir = _resolve_existing_sweep_dir(requested_name)
    except HTTPException as e:
        if e.status_code != 404:
            raise
        sdir = _sweep_dir_for_create(requested_name)
        sweep_name = sdir.name
        sdir.mkdir(parents=True, exist_ok=True)

    sweep_file = config["sweep_json"]
    _write_json(_sweep_json_path_from_dir(sdir), sweep_file)

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
    actual_name, sdir = _resolve_existing_sweep_dir(sweep_name)
    summary_path = sdir / "summary.json"

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
            "sweep_name": actual_name,
        }

    data = _read_json(summary_path, {}, strict=False)
    if isinstance(data, dict):
        data.setdefault("sweep_name", actual_name)
    return data


@app.delete("/api/sweeps/{sweep_name}")
def delete_sweep(sweep_name: str):
    actual_name, sdir = _resolve_existing_sweep_dir(sweep_name)

    proc = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)
    if proc and proc.poll() is None:
        running_name = SWEEP_RUN_META.get(SWEEP_ACTIVE_RUN_KEY, {}).get("sweep_name")
        if running_name == actual_name:
            raise HTTPException(status_code=400, detail="Cannot delete a running sweep.")

    shutil.rmtree(sdir, ignore_errors=True)

    with PROJECT_STATE_LOCK:
        current = _read_project_state()
        sweep_ui = current.setdefault("ui", {}).setdefault("home", {}).setdefault("tabs", {}).setdefault("sweep", {})
        if sweep_ui.get("activeSweep") == actual_name:
            sweep_ui["activeSweep"] = ""
            sweep_ui["running"] = False
            sweep_ui["draftConfig"] = _default_sweep_draft()
            _write_project_state(current)

    return {"ok": True, "deleted": True, "sweep_name": actual_name}


def _patch_sweep_name_in_tree(sweep_root: Path, from_name: str, to_name: str) -> None:
    """Update sweep_name fields in JSON files after a sweep folder rename."""
    if not sweep_root.is_dir():
        return
    for p in sweep_root.rglob("*.json"):
        if not p.is_file():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        if raw.get("sweep_name") == from_name:
            raw["sweep_name"] = to_name
            _write_json(p, raw)


@app.post("/api/sweeps/rename")
def rename_sweep(payload: Dict[str, Any] = Body(...)):
    raw_from = str(payload.get("from_name") or payload.get("sweep_name") or "").strip()
    raw_to = str(payload.get("to_name") or payload.get("new_name") or "").strip()

    actual_from, old_dir = _resolve_existing_sweep_dir(raw_from)
    new_dir = _sweep_dir_for_create(raw_to)
    to_name = new_dir.name

    if actual_from == to_name:
        raise HTTPException(status_code=400, detail="New name must differ from the current name.")

    if new_dir.exists():
        raise HTTPException(status_code=400, detail="A sweep with that name already exists.")

    proc = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)
    if proc and proc.poll() is None:
        running_name = SWEEP_RUN_META.get(SWEEP_ACTIVE_RUN_KEY, {}).get("sweep_name")
        if running_name == actual_from:
            raise HTTPException(
                status_code=400,
                detail="Cannot rename while this sweep's job is running.",
            )

    try:
        old_dir.rename(new_dir)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Rename failed: {e}") from e

    _patch_sweep_name_in_tree(new_dir, actual_from, to_name)

    with PROJECT_STATE_LOCK:
        current = _read_project_state()
        sweep_ui = (
            current.setdefault("ui", {})
            .setdefault("home", {})
            .setdefault("tabs", {})
            .setdefault("sweep", {})
        )
        if sweep_ui.get("activeSweep") == actual_from:
            sweep_ui["activeSweep"] = to_name
            _write_project_state(current)

    return {"ok": True, "from_name": actual_from, "sweep_name": to_name}


@app.post("/api/sweeps/start")
def start_sweep(payload: Dict[str, Any] = Body(...)):
    proc_existing = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)
    if proc_existing and proc_existing.poll() is None:
        raise HTTPException(status_code=400, detail="A sweep is already running.")

    requested_name = str(payload.get("sweep_name", ""))
    config = _validate_sweep_ui_config(payload.get("config"))

    project_dir = _active_project_dir()

    try:
        sweep_name, sweep_folder = _resolve_existing_sweep_dir(requested_name)
    except HTTPException as e:
        if e.status_code != 404:
            raise
        sweep_folder = _sweep_dir_for_create(requested_name)
        sweep_name = sweep_folder.name
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
    _write_json(_sweep_json_path_from_dir(sweep_folder), sweep_file)

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
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
            close_fds=True,
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
        finished_name = SWEEP_RUN_META.get(SWEEP_ACTIVE_RUN_KEY, {}).get("sweep_name")
        _cleanup_run_dicts(SWEEP_RUNS, SWEEP_RUN_META, SWEEP_ACTIVE_RUN_KEY)
        _set_project_sweep_ui(running=False)
        _push_sweep_line("system", "Sweep already finished.")
        return {"ok": True, "stopped": False, "message": "Sweep already finished.", "sweep_name": finished_name}

    _push_sweep_line("system", "Stopping sweep…")

    try:
        _terminate_process_group(proc, "sweep")
    finally:
        stopped_name = (SWEEP_RUN_META.get(SWEEP_ACTIVE_RUN_KEY) or {}).get("sweep_name")
        _cleanup_run_dicts(SWEEP_RUNS, SWEEP_RUN_META, SWEEP_ACTIVE_RUN_KEY)
        _set_project_sweep_ui(running=False)

    _push_sweep_line("system", "Sweep stopped by user.")
    return {"ok": True, "stopped": True, "sweep_name": stopped_name}


@app.get("/api/sweeps/status")
def sweep_status():
    proc = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)

    if not proc:
        _set_project_sweep_ui(running=False)
        return {"running": False, "returncode": None, "sweep_name": None}

    rc = proc.poll()
    if rc is None:
        sweep_name = (SWEEP_RUN_META.get(SWEEP_ACTIVE_RUN_KEY) or {}).get("sweep_name")
        return {"running": True, "returncode": None, "sweep_name": sweep_name}

    finished_name = (SWEEP_RUN_META.get(SWEEP_ACTIVE_RUN_KEY) or {}).get("sweep_name")
    _cleanup_run_dicts(SWEEP_RUNS, SWEEP_RUN_META, SWEEP_ACTIVE_RUN_KEY)
    _set_project_sweep_ui(running=False)
    _push_sweep_line("system", f"Sweep finished. returncode={rc}")
    return {"running": False, "returncode": rc, "sweep_name": finished_name}


@app.get("/api/sweeps/stream")
def sweep_stream(request: Request, sweep_name: str):
    actual_name, _ = _resolve_existing_sweep_dir(sweep_name)

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
                    running_name = (SWEEP_RUN_META.get(SWEEP_ACTIVE_RUN_KEY) or {}).get("sweep_name")
                    if rc is not None and running_name == actual_name:
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
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ------------------------------------------------------------
# Model training / prediction API
# ------------------------------------------------------------
MODEL_ACTIVE_RUN_KEY = "active"

MODEL_RUNS: Dict[str, subprocess.Popen] = {}
MODEL_RUN_META: Dict[str, Dict[str, Any]] = {}

MODEL_RING: list[dict] = []
MODEL_RING_MAX = 5000
MODEL_RING_LOCK = threading.Lock()


def normalize_model_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^A-Za-z0-9_\-]", "", name)
    name = name.strip("_-")

    if not name:
        raise HTTPException(status_code=400, detail="Model name is invalid/empty after normalization.")
    if len(name) > 80:
        raise HTTPException(status_code=400, detail="Model name too long (max 80 after normalization).")

    return name


def _models_root_for_active_project() -> Path:
    root = (_active_project_dir() / "model").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _model_dir(model_name: str) -> Path:
    root = _models_root_for_active_project()
    safe = normalize_model_name(model_name)
    p = (root / safe).resolve()
    if root not in p.parents and p != root:
        raise HTTPException(status_code=400, detail="Invalid model name.")
    return p


def _resolve_model_artifact_dir(model_name: str) -> Path:
    base_dir = _model_dir(model_name)
    nested_dir = (base_dir / model_name).resolve()

    if nested_dir.exists() and nested_dir.is_dir():
        return nested_dir
    return base_dir


def _model_translate_config_path(model_name: str) -> Path:
    return _model_dir(model_name) / "data_translate.json"


def _model_config_path(model_name: str) -> Path:
    return _model_dir(model_name) / "model_config.json"


def _model_report_path(model_name: str) -> Path:
    return _model_dir(model_name) / "summary.json"


def _model_report_fallback_path(model_name: str) -> Path:
    return _model_dir(model_name) / "report.json"


def _find_model_report_file(model_name: str) -> Optional[Path]:
    model_root = _model_dir(model_name)
    artifact_root = _resolve_model_artifact_dir(model_name)

    candidates = [
        _model_report_path(model_name),
        _model_report_fallback_path(model_name),
        artifact_root / "summary.json",
        artifact_root / "report.json",
        model_root / model_name / "summary.json",
        model_root / model_name / "report.json",
    ]

    for path in candidates:
        if path.exists() and path.is_file():
            return path

    recursive_candidates = []
    try:
        recursive_candidates.extend(model_root.rglob("summary.json"))
        recursive_candidates.extend(model_root.rglob("report.json"))
    except Exception:
        pass

    recursive_candidates = [p for p in recursive_candidates if p.is_file()]
    if not recursive_candidates:
        return None

    recursive_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return recursive_candidates[0]


def _load_model_report(model_name: str) -> Optional[Dict[str, Any]]:
    report_path = _find_model_report_file(model_name)
    if not report_path:
        return None

    data = _read_json(report_path, {}, strict=False)
    return data if isinstance(data, dict) and data else None


def _default_model_draft(model_name: str = "", model_type: str = "ANN") -> Dict[str, Any]:
    model_type = (model_type or "ANN").upper()

    if model_type == "CATBOOST":
        model_type = "CAT"
    elif model_type == "RANDOMFOREST":
        model_type = "RF"

    base = {
        "sweep_name": "",
        "model_type": model_type,
        "translate_config": {
            "translation_type": "FFI",
            "translation_params": {},
            "selection": {"x_names": [], "y_names": []},
        },
    }

    MODEL_DEFAULTS = {
        "ANN": {
            "model_config": {
                "model_name": model_name,
                "data_split": {"test_size": 0.2, "random_state": 42},
                "normalization": {
                    "feature_method": "standard",
                    "target_method": "standard",
                    "feature_methods": {},
                    "target_methods": {},
                },
                "training": {
                    "epochs": 100,
                    "batch_size": 32,
                    "loss": "mse",
                    "metrics": ["mae"],
                    "validation_split": 0.2,
                    "optimizer": {"type": "Adam", "learning_rate": 0.001, "momentum": 0.9},
                },
                "early_stopping": {"monitor": "val_loss", "patience": 15, "restore_best_weights": True},
                "architecture": [
                    {"type": "Dense", "units": 128, "activation": "relu"},
                    {"type": "Dense", "units": "AUTO", "activation": "linear"},
                ],
            }
        },
        "CAT": {
            "model_config": {
                "model_name": model_name,
                "normalization": {"feature_method": "none", "target_method": "none"},
                "data_split": {"test_size": 0.2, "random_state": 42},
                "cat_params": {
                    "iterations": 1000,
                    "learning_rate": 0.05,
                    "depth": 6,
                    "l2_leaf_reg": 3,
                    "random_seed": 42,
                    "task_type": "GPU",
                    "devices": "0",
                },
            }
        },
        "GPR": {
            "model_config": {
                "model_name": model_name,
                "data_split": {"test_size": 0.2, "random_state": 42},
                "normalization": {"feature_method": "standard", "target_method": "standard"},
                "max_cpu_threads": 8,
                "gpr_params": {
                    "kernel": "RBF",
                    "n_restarts_optimizer": 3,
                    "normalize_y": True,
                    "alpha": 1e-8,
                },
            }
        },
        "LGBM": {
            "model_config": {
                "model_name": model_name,
                "normalization": {"feature_method": "none", "target_method": "none"},
                "data_split": {"test_size": 0.2, "random_state": 42},
                "lgb_params": {
                    "n_estimators": 500,
                    "learning_rate": 0.05,
                    "max_depth": 6,
                    "num_leaves": 31,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "random_state": 42,
                    "n_jobs": -1,
                    "verbose": -1,
                },
            }
        },
        "PCE": {
            "model_config": {
                "model_name": model_name,
                "degree": 3,
                "normalization": {"feature_method": "none", "target_method": "none"},
                "data_split": {"test_size": 0.2, "random_state": 42},
            }
        },
        "PR": {
            "model_config": {
                "model_name": model_name,
                "data_split": {"test_size": 0.2, "random_state": 42},
                "normalization": {"feature_method": "none", "target_method": "none"},
                "pr_params": {"degree": 2, "include_bias": False},
            }
        },
        "RF": {
            "model_config": {
                "model_name": model_name,
                "data_split": {"test_size": 0.2, "random_state": 42},
                "normalization": {"feature_method": "none", "target_method": "none"},
                "rf_params": {
                    "n_estimators": 200,
                    "max_depth": 20,
                    "min_samples_split": 5,
                    "min_samples_leaf": 5,
                    "max_features": "sqrt",
                    "bootstrap": True,
                    "random_state": 42,
                    "n_jobs": -1,
                },
            }
        },
        "SVR": {
            "model_config": {
                "model_name": model_name,
                "data_split": {"test_size": 0.2, "random_state": 42},
                "normalization": {"feature_method": "standard", "target_method": "standard"},
                "svr_params": {"kernel": "rbf", "C": 100.0, "epsilon": 0.001, "gamma": "scale"},
            }
        },
        "XGB": {
            "model_config": {
                "model_name": model_name,
                "data_split": {"test_size": 0.2, "random_state": 42},
                "normalization": {"feature_method": "none", "target_method": "none"},
                "xgb_params": {
                    "n_estimators": 1,
                    "max_depth": 1,
                    "learning_rate": 1.0,
                    "eval_metric": "rmse",
                    "subsample": 0.2,
                    "colsample_bytree": 0.2,
                    "gamma": 0.0,
                    "reg_alpha": 0.0,
                    "reg_lambda": 1.0,
                    "random_state": 42,
                    "tree_method": "hist",
                    "device": "cpu",
                },
            }
        },
    }

    selected = MODEL_DEFAULTS.get(model_type, MODEL_DEFAULTS["ANN"])
    return {**base, **selected}


def _set_project_model_ui(active_model=None, running=None, draft_config=None) -> None:
    with PROJECT_STATE_LOCK:
        current = _read_project_state()
        ui = current.setdefault("ui", {}).setdefault("home", {}).setdefault("tabs", {}).setdefault("model", {})

        if active_model is not None:
            ui["activeModel"] = active_model
        if running is not None:
            ui["running"] = running
        if draft_config is not None:
            ui["draftConfig"] = draft_config

        _write_project_state(current)


def _push_model_line(stream: str, line: str, model_name: Optional[str] = None) -> None:
    item = {"t": time.time(), "stream": stream, "line": line, "model_name": model_name}
    with MODEL_RING_LOCK:
        MODEL_RING.append(item)
        if len(MODEL_RING) > MODEL_RING_MAX:
            del MODEL_RING[: len(MODEL_RING) - MODEL_RING_MAX]


def _model_reader_thread(pipe, stream_name: str, model_name: Optional[str] = None):
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            _push_model_line(stream_name, line.rstrip("\n"), model_name=model_name)
    except Exception as e:
        _push_model_line("system", f"[reader:{stream_name}] exception: {e}", model_name=model_name)
    finally:
        try:
            pipe.close()
        except Exception:
            pass


def _normalize_model_type(model_type: str) -> str:
    mt = str(model_type or "").strip().upper()
    if mt == "CATBOOST":
        return "CAT"
    if mt == "RANDOMFOREST":
        return "RF"
    return mt


def _validate_model_ui_config(config: Dict[str, Any], model_name: str = "") -> Dict[str, Any]:
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="config must be an object.")

    model_type = _normalize_model_type(config.get("model_type", ""))
    if model_type not in {"ANN", "GPR", "PCE", "CAT", "XGB", "RF", "PR", "SVR", "LGBM"}:
        raise HTTPException(status_code=400, detail="Unsupported model_type.")

    translate_config = config.get("translate_config")
    if not isinstance(translate_config, dict):
        raise HTTPException(status_code=400, detail="translate_config must be an object.")
    if not str(translate_config.get("translation_type", "")).strip():
        raise HTTPException(status_code=400, detail="translate_config.translation_type is required.")
    if "translation_params" in translate_config and not isinstance(translate_config.get("translation_params"), dict):
        raise HTTPException(status_code=400, detail="translate_config.translation_params must be an object.")
    if "selection" in translate_config and not isinstance(translate_config.get("selection"), dict):
        raise HTTPException(status_code=400, detail="translate_config.selection must be an object.")
    selection = translate_config.get("selection") or {}
    for key in ("x_names", "y_names"):
        value = selection.get(key, [])
        if value is None:
            value = []
        if not isinstance(value, list) or any(not str(item).strip() for item in value):
            raise HTTPException(status_code=400, detail=f"translate_config.selection.{key} must be a list of non-empty strings.")

    model_config = config.get("model_config")
    if not isinstance(model_config, dict):
        raise HTTPException(status_code=400, detail="model_config must be an object.")

    next_config = _deepcopy_jsonish(config)
    next_config["model_type"] = model_type
    next_config["sweep_name"] = str(next_config.get("sweep_name") or "").strip()
    next_config.setdefault("translate_config", {}).setdefault("translation_params", {})
    next_config.setdefault("translate_config", {}).setdefault("selection", {"x_names": [], "y_names": []})
    next_config.setdefault("model_config", {})
    if model_name:
        next_config["model_config"]["model_name"] = model_name
    elif not str(next_config["model_config"].get("model_name", "")).strip():
        raise HTTPException(status_code=400, detail="model_config.model_name is required.")

    return next_config


def _load_model_saved_config(model_name: str) -> Dict[str, Any]:
    translate_config = _read_json(
        _model_translate_config_path(model_name),
        {"translation_type": "FFD", "translation_params": {}, "selection": {"x_names": [], "y_names": []}},
        strict=False,
    )
    model_config = _read_json(_model_config_path(model_name), {"model_name": model_name}, strict=False)

    state = _read_project_state()
    model_ui = state.setdefault("ui", {}).setdefault("home", {}).setdefault("tabs", {}).setdefault("model", {})
    prev_draft = model_ui.get("draftConfig", {}) if isinstance(model_ui.get("draftConfig"), dict) else {}

    draft = {
        "sweep_name": str(model_config.get("sweep_name") or prev_draft.get("sweep_name") or "").strip(),
        "model_type": _normalize_model_type(model_config.get("model_type") or prev_draft.get("model_type") or "ANN"),
        "translate_config": translate_config,
        "model_config": model_config,
    }
    draft["model_config"]["model_name"] = model_name
    draft["model_type"] = _normalize_model_type(draft["model_type"])
    return _validate_model_ui_config(draft, model_name=model_name)


@app.get("/api/models/sweep-options")
def list_model_sweep_options():
    root = _sweeps_root_for_active_project()
    items = []

    for p in root.iterdir():
        if not p.is_dir() or p.name.startswith("."):
            continue

        npz_files = sorted([x.name for x in p.glob("*.npz") if x.is_file()])
        if not npz_files:
            continue

        items.append({"sweep_name": p.name, "npz_files": npz_files})

    items.sort(key=lambda x: x["sweep_name"])
    return {"sweeps": items}


@app.get("/api/models")
def list_models():
    root = _models_root_for_active_project()
    items = []

    for p in root.iterdir():
        if p.is_dir() and not p.name.startswith("."):
            items.append(p.name)

    items.sort()
    return {"models": items}


@app.post("/api/models/default-config")
def get_default_model_config(payload: Dict[str, Any] = Body(...)):
    model_type = payload.get("model_type", "ANN")
    model_name = payload.get("model_name", "")
    draft = _default_model_draft(model_name, model_type)
    return draft


@app.post("/api/models/create")
def create_model(payload: Dict[str, Any] = Body(...)):
    model_name = normalize_model_name(payload.get("model_name", ""))
    mdir = _model_dir(model_name)

    if mdir.exists():
        raise HTTPException(status_code=400, detail="Model already exists.")

    mdir.mkdir(parents=True, exist_ok=False)

    model_type = payload.get("model_type", "ANN")
    draft = _default_model_draft(model_name, model_type)

    _write_json(_model_translate_config_path(model_name), draft["translate_config"])
    model_config = _deepcopy_jsonish(draft["model_config"])
    model_config["model_type"] = draft["model_type"]
    model_config["sweep_name"] = draft.get("sweep_name", "")
    _write_json(_model_config_path(model_name), model_config)

    _set_project_model_ui(active_model=model_name, running=False, draft_config=draft)
    return {"ok": True, "model_name": model_name}


@app.post("/api/models/open")
def open_model(payload: Dict[str, Any] = Body(...)):
    model_name = normalize_model_name(payload.get("model_name", ""))
    mdir = _model_dir(model_name)

    if not mdir.exists():
        raise HTTPException(status_code=404, detail="Model not found.")

    draft = _load_model_saved_config(model_name)
    running = False
    proc = MODEL_RUNS.get(MODEL_ACTIVE_RUN_KEY)
    if proc and proc.poll() is None:
        running_name = (MODEL_RUN_META.get(MODEL_ACTIVE_RUN_KEY) or {}).get("model_name")
        running = running_name == model_name

    report = _load_model_report(model_name)

    _set_project_model_ui(active_model=model_name, running=running, draft_config=draft)
    return {"ok": True, "model_name": model_name, "running": running, "config": draft, "report": report}


@app.post("/api/models/save")
def save_model(payload: Dict[str, Any] = Body(...)):
    model_name = normalize_model_name(payload.get("model_name", ""))
    config = _validate_model_ui_config(payload.get("config"), model_name=model_name)

    mdir = _model_dir(model_name)
    mdir.mkdir(parents=True, exist_ok=True)

    _write_json(_model_translate_config_path(model_name), config["translate_config"])
    model_cfg = _deepcopy_jsonish(config["model_config"])
    model_cfg["model_type"] = config["model_type"]
    model_cfg["sweep_name"] = config.get("sweep_name", "")
    _write_json(_model_config_path(model_name), model_cfg)

    _set_project_model_ui(active_model=model_name, draft_config=config)
    return {"ok": True, "model_name": model_name}


@app.get("/api/models/report")
def get_model_report(model_name: str):
    model_name = normalize_model_name(model_name)
    report_path = _find_model_report_file(model_name)
    report = _load_model_report(model_name)
    if not report:
        return {"exists": False, "report": None, "report_path": None}
    return {"exists": True, "report": report, "report_path": str(report_path) if report_path else None}


@app.delete("/api/models/{model_name}")
def delete_model(model_name: str):
    model_name = normalize_model_name(model_name)
    mdir = _model_dir(model_name)

    if not mdir.exists():
        raise HTTPException(status_code=404, detail="Model not found.")

    proc = MODEL_RUNS.get(MODEL_ACTIVE_RUN_KEY)
    if proc and proc.poll() is None:
        running_name = (MODEL_RUN_META.get(MODEL_ACTIVE_RUN_KEY) or {}).get("model_name")
        if running_name == model_name:
            raise HTTPException(status_code=400, detail="Cannot delete a running model training job.")

    shutil.rmtree(mdir, ignore_errors=True)

    with PROJECT_STATE_LOCK:
        current = _read_project_state()
        model_ui = current.setdefault("ui", {}).setdefault("home", {}).setdefault("tabs", {}).setdefault("model", {})
        if model_ui.get("activeModel") == model_name:
            model_ui["activeModel"] = ""
            model_ui["running"] = False
            model_ui["draftConfig"] = _default_model_draft("")
            _write_project_state(current)

    return {"ok": True, "deleted": True, "model_name": model_name}


def _patch_model_name_in_tree(model_root: Path, from_name: str, to_name: str) -> None:
    """Update stored model_name fields after a on-disk rename (configs + reports)."""
    if not model_root.is_dir():
        return
    for p in model_root.rglob("*.json"):
        if not p.is_file():
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        changed = False
        if raw.get("model_name") == from_name:
            raw["model_name"] = to_name
            changed = True
        mi = raw.get("model_info")
        if isinstance(mi, dict) and mi.get("model_name") == from_name:
            mi["model_name"] = to_name
            changed = True
        cfg = raw.get("configuration")
        if isinstance(cfg, dict):
            mc = cfg.get("model_config")
            if isinstance(mc, dict) and mc.get("model_name") == from_name:
                mc["model_name"] = to_name
                changed = True
        if changed:
            _write_json(p, raw)


@app.post("/api/models/rename")
def rename_model(payload: Dict[str, Any] = Body(...)):
    from_name = normalize_model_name(
        str(payload.get("from_name") or payload.get("model_name") or "").strip()
    )
    to_name = normalize_model_name(str(payload.get("to_name") or payload.get("new_name") or "").strip())

    if from_name == to_name:
        raise HTTPException(status_code=400, detail="New name must differ from the current name.")

    old_dir = _model_dir(from_name)
    new_dir = _model_dir(to_name)

    if not old_dir.is_dir():
        raise HTTPException(status_code=404, detail="Model not found.")
    if new_dir.exists():
        raise HTTPException(status_code=400, detail="A model with that name already exists.")

    proc = MODEL_RUNS.get(MODEL_ACTIVE_RUN_KEY)
    if proc and proc.poll() is None:
        running_name = (MODEL_RUN_META.get(MODEL_ACTIVE_RUN_KEY) or {}).get("model_name")
        if running_name == from_name:
            raise HTTPException(
                status_code=400,
                detail="Cannot rename while this model's training job is running.",
            )

    try:
        old_dir.rename(new_dir)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Rename failed: {e}") from e

    nested_old = new_dir / from_name
    nested_new = new_dir / to_name
    if nested_old.is_dir():
        if nested_new.exists():
            try:
                new_dir.rename(old_dir)
            except OSError:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Rename blocked: '{nested_new}' already exists.",
            )
        try:
            nested_old.rename(nested_new)
        except OSError as e:
            try:
                new_dir.rename(old_dir)
            except OSError:
                pass
            raise HTTPException(status_code=500, detail=f"Could not rename artifact folder: {e}") from e

    _patch_model_name_in_tree(new_dir, from_name, to_name)

    with PROJECT_STATE_LOCK:
        current = _read_project_state()
        model_ui = (
            current.setdefault("ui", {})
            .setdefault("home", {})
            .setdefault("tabs", {})
            .setdefault("model", {})
        )
        if model_ui.get("activeModel") == from_name:
            model_ui["activeModel"] = to_name
            draft = model_ui.get("draftConfig")
            if isinstance(draft, dict):
                mc = draft.get("model_config")
                if isinstance(mc, dict):
                    mc["model_name"] = to_name
            _write_project_state(current)

    return {"ok": True, "from_name": from_name, "model_name": to_name}


@app.post("/api/models/translate-preview")
def preview_model_translation(payload: Dict[str, Any] = Body(...)):
    preview_model_name = str(payload.get("model_name") or "__preview__").strip() or "__preview__"
    config = _validate_model_ui_config(payload.get("config"), model_name=preview_model_name)

    npz_file = payload.get("npz_file")
    sweep_name = str(payload.get("sweep_name") or config.get("sweep_name") or "").strip()

    if npz_file:
        npz_path = Path(npz_file)
    elif sweep_name:
        actual_sweep_name, sweep_dir = _resolve_existing_sweep_dir(sweep_name)
        npz_matches = sorted([p for p in sweep_dir.glob("*.npz") if p.is_file()])
        if not npz_matches:
            raise HTTPException(status_code=400, detail=f"No .npz file found inside sweep '{actual_sweep_name}'.")
        npz_path = npz_matches[0]
    else:
        raise HTTPException(status_code=400, detail="Select a sweep containing an .npz file.")

    if not npz_path.exists():
        raise HTTPException(status_code=400, detail=f"NPZ file not found: {npz_path}")

    try:
        preview = train.build_translation_preview(str(npz_path), config["translate_config"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to preview translated data: {e}")

    return {"ok": True, "npz_file": str(npz_path), "preview": preview}


@app.post("/api/models/start")
def start_model_training(payload: Dict[str, Any] = Body(...)):
    print("OOOOOOOOOOOOOOLLLLLLLLAALALALLALALLALALLALLLALLALALLALLALALLALALLALAL")
    proc_existing = MODEL_RUNS.get(MODEL_ACTIVE_RUN_KEY)
    if proc_existing and proc_existing.poll() is None:
        raise HTTPException(status_code=400, detail="A model training process is already running.")

    model_name = normalize_model_name(payload.get("model_name", ""))
    config = _validate_model_ui_config(payload.get("config"), model_name=model_name)

    project_dir = _active_project_dir()
    model_folder = _model_dir(model_name)
    model_folder.mkdir(parents=True, exist_ok=True)

    npz_file = payload.get("npz_file")
    sweep_name = str(payload.get("sweep_name") or config.get("sweep_name") or "").strip()

    if npz_file:
        npz_path = Path(npz_file)
    elif sweep_name:
        actual_sweep_name, sweep_dir = _resolve_existing_sweep_dir(sweep_name)
        npz_matches = sorted([p for p in sweep_dir.glob("*.npz") if p.is_file()])
        if not npz_matches:
            raise HTTPException(status_code=400, detail=f"No .npz file found inside sweep '{actual_sweep_name}'.")
        npz_path = npz_matches[0]
        sweep_name = actual_sweep_name
    else:
        raise HTTPException(status_code=400, detail="Select a sweep containing an .npz file.")

    if not npz_path.exists():
        raise HTTPException(status_code=400, detail=f"NPZ file not found: {npz_path}")

    _write_json(_model_translate_config_path(model_name), config["translate_config"])
    model_cfg = _deepcopy_jsonish(config["model_config"])
    model_cfg["model_name"] = model_name
    model_cfg["model_type"] = config["model_type"]
    model_cfg["sweep_name"] = config.get("sweep_name", "")
    _write_json(_model_config_path(model_name), model_cfg)

    base_dir = Path(__file__).resolve().parent
    train_script = os.path.abspath(os.path.join(str(base_dir), "../../model/train.py"))

    command = [
        sys.executable,
        train_script,
        "-d",
        str(npz_path),
        "-t",
        config["model_type"],
        "-a",
        str(_model_translate_config_path(model_name)),
        "-m",
        str(_model_config_path(model_name)),
        "-o",
        str(_models_root_for_active_project()),
    ]

    with MODEL_RING_LOCK:
        MODEL_RING.clear()

    _push_model_line("system", f"Launching model training: {' '.join(command)}", model_name=model_name)

    try:
        proc = subprocess.Popen(
            command,
            cwd=str(project_dir),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
            close_fds=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start model training: {e}")

    if proc.stdout:
        threading.Thread(target=_model_reader_thread, args=(proc.stdout, "stdout", model_name), daemon=True).start()
    if proc.stderr:
        threading.Thread(target=_model_reader_thread, args=(proc.stderr, "stderr", model_name), daemon=True).start()

    MODEL_RUNS[MODEL_ACTIVE_RUN_KEY] = proc
    MODEL_RUN_META[MODEL_ACTIVE_RUN_KEY] = {
        "model_name": model_name,
        "cmd": command,
        "started": time.time(),
        "projectId": _get_active_project_id(),
    }

    _set_project_model_ui(active_model=model_name, running=True, draft_config=config)
    return {"ok": True, "model_name": model_name, "npz_file": str(npz_path)}


@app.post("/api/models/stop")
def stop_model_training(payload: Dict[str, Any] = Body(default={})):
    proc = MODEL_RUNS.get(MODEL_ACTIVE_RUN_KEY)
    if not proc:
        _set_project_model_ui(running=False)
        return {"ok": True, "stopped": False, "message": "No active model training."}

    if proc.poll() is not None:
        finished_model_name = (MODEL_RUN_META.get(MODEL_ACTIVE_RUN_KEY) or {}).get("model_name")
        _cleanup_run_dicts(MODEL_RUNS, MODEL_RUN_META, MODEL_ACTIVE_RUN_KEY)
        _set_project_model_ui(running=False)
        _push_model_line("system", "Model training already finished.", model_name=finished_model_name)
        return {"ok": True, "stopped": False, "message": "Model training already finished."}

    stopping_model_name = (MODEL_RUN_META.get(MODEL_ACTIVE_RUN_KEY) or {}).get("model_name")
    _push_model_line("system", "Stopping model training…", model_name=stopping_model_name)

    try:
        _terminate_process_group(proc, "model training")
    finally:
        _cleanup_run_dicts(MODEL_RUNS, MODEL_RUN_META, MODEL_ACTIVE_RUN_KEY)
        _set_project_model_ui(running=False)

    _push_model_line("system", "Model training stopped by user.", model_name=stopping_model_name)
    return {"ok": True, "stopped": True}


@app.get("/api/models/status")
def model_status():
    proc = MODEL_RUNS.get(MODEL_ACTIVE_RUN_KEY)

    if not proc:
        _set_project_model_ui(running=False)
        return {"running": False, "returncode": None, "model_name": None}

    rc = proc.poll()
    if rc is None:
        model_name = (MODEL_RUN_META.get(MODEL_ACTIVE_RUN_KEY) or {}).get("model_name")
        return {"running": True, "returncode": None, "model_name": model_name}

    finished_name = (MODEL_RUN_META.get(MODEL_ACTIVE_RUN_KEY) or {}).get("model_name")
    _cleanup_run_dicts(MODEL_RUNS, MODEL_RUN_META, MODEL_ACTIVE_RUN_KEY)
    _set_project_model_ui(running=False)
    _push_model_line("system", f"Model training finished. returncode={rc}", model_name=finished_name)
    return {"running": False, "returncode": rc, "model_name": finished_name}


@app.get("/api/models/stream")
def model_stream(request: Request, model_name: str):
    model_name = normalize_model_name(model_name)

    def event_gen():
        with MODEL_RING_LOCK:
            backlog = [item for item in MODEL_RING[-300:] if item.get("model_name") == model_name]

        for item in backlog:
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

        last_seen_ts = backlog[-1]["t"] if backlog else 0.0

        while True:
            if request.client is None:
                break

            try:
                with MODEL_RING_LOCK:
                    new_items = [
                        item for item in MODEL_RING
                        if item.get("model_name") == model_name and item.get("t", 0) > last_seen_ts
                    ]

                for item in new_items:
                    last_seen_ts = max(last_seen_ts, item.get("t", 0))
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

                proc = MODEL_RUNS.get(MODEL_ACTIVE_RUN_KEY)
                active_name = (MODEL_RUN_META.get(MODEL_ACTIVE_RUN_KEY) or {}).get("model_name")
                if proc and active_name == model_name:
                    rc = proc.poll()
                    if rc is not None:
                        done_msg = {
                            "t": time.time(),
                            "stream": "system",
                            "line": f"[done] returncode={rc}",
                            "model_name": model_name,
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
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.post("/api/models/predict")
def model_predict(payload: Dict[str, Any] = Body(...)):
    model_name = normalize_model_name(payload.get("model_name", ""))
    model_folder = _resolve_model_artifact_dir(model_name)
    if not model_folder.exists():
        raise HTTPException(status_code=404, detail="Model artifacts not found.")

    config = _load_model_saved_config(model_name)
    model_type = _normalize_model_type(payload.get("model_type") or config.get("model_type") or "ANN")
    x_input = payload.get("x_input")
    if x_input is None:
        raise HTTPException(status_code=400, detail="x_input is required.")

    base_dir = Path(__file__).resolve().parent
    predict_script = os.path.abspath(os.path.join(str(base_dir), "../../model/predict.py"))

    command = [
        sys.executable,
        predict_script,
        "-m",
        str(model_folder),
        "-x",
        json.dumps(x_input),
    ]

    try:
        res = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(_active_project_dir()),
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Prediction failed",
                "returncode": e.returncode,
                "stdout": (e.stdout or "")[-8000:],
                "stderr": (e.stderr or "")[-8000:],
                "cmd": command,
            },
        )

    try:
        prediction = json.loads((res.stdout or "").strip())
    except Exception:
        prediction = (res.stdout or "").strip()

    return {
        "ok": True,
        "model_name": model_name,
        "model_type": model_type,
        "prediction": prediction,
        "stdout": (res.stdout or "").strip(),
        "stderr": (res.stderr or "").strip(),
    }



@app.post("/api/models/ann/preview-architecture")
def preview_ann_architecture(payload: Dict[str, Any] = Body(...)):
    import io
    import numpy as np
    from model import ANN


    model_config = payload.get("model_config", {})
    input_dim = int(payload.get("input_dim", 1))
    output_dim = int(payload.get("output_dim", 1))

    dummy_x = np.zeros((4, input_dim), dtype=np.float32)
    dummy_y = np.zeros((4, output_dim), dtype=np.float32)

    config = ANN._prepare_config_for_training(dummy_x, dummy_y, model_config)

    arch_type = str(config.get("architecture_type", "sequential")).lower()
    if arch_type == "graph":
        model = ANN._build_graph_model(input_dim=input_dim, output_dim=output_dim, config=config)
    else:
        model = ANN._build_sequential_model(input_dim=input_dim, output_dim=output_dim, config=config)

    buf = io.StringIO()
    # Do not pass line_length — same as interactive terminal: Keras sizes the Rich table from
    # shutil.get_terminal_size() (see keras.utils.summary_utils.print_summary).
    model.summary(
        print_fn=lambda line: buf.write(line + "\n"),
        expand_nested=True,
    )

    return {
        "ok": True,
        "summary_text": buf.getvalue(),
        "input_dim": input_dim,
        "output_dim": output_dim,
    }





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

    gds_path = os.path.join(str(root), "artwork.gds")
    artwork_path = os.path.join(str(root), "artwork.json")

    command = [
        sys.executable,
        str(SIMULATOR_PY),
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
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
            close_fds=True,
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
        _cleanup_run_dicts(SIM_RUNS, SIM_RUN_META, ACTIVE_RUN_KEY)
        _push_sim_line("system", "Simulation already finished.")
        return {"ok": True, "stopped": False, "message": "Simulation already finished."}

    _push_sim_line("system", "Stopping simulation…")

    try:
        _terminate_process_group(proc, "simulation")
    finally:
        _cleanup_run_dicts(SIM_RUNS, SIM_RUN_META, ACTIVE_RUN_KEY)

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

    _cleanup_run_dicts(SIM_RUNS, SIM_RUN_META, ACTIVE_RUN_KEY)
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
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ------------------------------------------------------------
# App shutdown cleanup
# ------------------------------------------------------------
@app.on_event("shutdown")
def _shutdown_cleanup():
    sweep_proc = SWEEP_RUNS.get(SWEEP_ACTIVE_RUN_KEY)
    if sweep_proc and sweep_proc.poll() is None:
        _push_sweep_line("system", "Backend shutdown: stopping active sweep process.")
        _terminate_process_group(sweep_proc, "sweep")
    _cleanup_run_dicts(SWEEP_RUNS, SWEEP_RUN_META, SWEEP_ACTIVE_RUN_KEY)

    model_proc = MODEL_RUNS.get(MODEL_ACTIVE_RUN_KEY)
    if model_proc and model_proc.poll() is None:
        model_name = (MODEL_RUN_META.get(MODEL_ACTIVE_RUN_KEY) or {}).get("model_name")
        _push_model_line("system", "Backend shutdown: stopping active model training process.", model_name=model_name)
        _terminate_process_group(model_proc, "model training")
    _cleanup_run_dicts(MODEL_RUNS, MODEL_RUN_META, MODEL_ACTIVE_RUN_KEY)

    sim_proc = SIM_RUNS.get(ACTIVE_RUN_KEY)
    if sim_proc and sim_proc.poll() is None:
        _push_sim_line("system", "Backend shutdown: stopping active simulation process.")
        _terminate_process_group(sim_proc, "simulation")
    _cleanup_run_dicts(SIM_RUNS, SIM_RUN_META, ACTIVE_RUN_KEY)

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
from fastapi.responses import StreamingResponse
import threading
import queue
import signal 


app = FastAPI()

APP_ORIGIN = "http://localhost:5173"

BACKEND_DIR = Path(__file__).resolve().parent / "../../data"

# Workspace folder (inside backend folder)
WORKSPACE_ROOT = (BACKEND_DIR / "workspace").resolve()
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

ACTIVE_FILE = WORKSPACE_ROOT / ".active_project"  # contains project_id (folder name)

# Your default state/project content
# DEFAULT_PROJECT: Dict[str, Any] = {
#     "nav": {
#         "page": "landing",
#         "tab": "artgen",
#     },
#     "ui": {
#         "home": {
#             "tabs": {
#                 "artgen": {},
#                 "sim": {},
#                 "sweep": {},
#                 "model": {},
#                 "optimz": {},
#             }
#         }
#     }
# }

DEFAULT_PROJECT: Dict[str, Any] = {
    "project": { "id": None, "name": None },   # (optional but recommended)
    "nav": {"page": "landing", "tab": "artgen"},
    "ui": {"home": {"tabs": {"artgen": {}, "sim": {}, "sweep": {}, "model": {}, "optimz": {}}}},
    "artwork": {},   # ✅ IMPORTANT: so a new project overwrites old artwork in the UI
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
    #_write_json(_project_json_path(project_id), DEFAULT_PROJECT)
    _write_json(_project_json_path(project_id), json.loads(json.dumps(DEFAULT_PROJECT)))

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


# def _preview_root_for_active_project() -> Path:
#     pid = _get_active_project_id()
#     if not pid:
#         raise HTTPException(status_code=400, detail="No project open. Open a project first.")
#     root = (_project_dir(pid) / "previews").resolve()
#     root.mkdir(parents=True, exist_ok=True)
#     return root


def _preview_root_for_active_project() -> Path:
    pid = _get_active_project_id()
    if not pid:
        raise HTTPException(status_code=400, detail="No project open. Open a project first.")

    # generate directly inside project folder
    root = (_project_dir(pid)).resolve()
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

    # token = uuid.uuid4().hex
    # out_dir = (preview_root / token).resolve()
    # out_dir.mkdir(parents=True, exist_ok=True)
    # (out_dir / ".created").write_text(str(time.time()), encoding="utf-8")

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
        #"token": token,
        "svgName": svg_path.name,
        "gdsName": gds_path.name if (gds_path and gds_path.exists()) else None,
        "svgText": svg_text,
    }


#@app.get("/api/preview/{token}/svg")
@app.get("/api/preview/svg")
def download_preview_svg():
    preview_root = _preview_root_for_active_project()
    folder = (preview_root).resolve()
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Preview not found")

    svg_path = _find_newest_file(folder, "svg")
    if not svg_path or not svg_path.exists():
        raise HTTPException(status_code=404, detail="SVG not found")

    return FileResponse(path=str(svg_path), media_type="image/svg+xml", filename=svg_path.name)


#@app.get("/api/preview/{token}/gds")
@app.get("/api/preview/gds")
def download_preview_gds():
    preview_root = _preview_root_for_active_project()
    folder = (preview_root).resolve()
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Preview not found")

    gds_path = _find_newest_file(folder, "gds")
    if not gds_path or not gds_path.exists():
        raise HTTPException(status_code=404, detail="GDS not found")

    return FileResponse(path=str(gds_path), media_type="application/octet-stream", filename=gds_path.name)


# -------------------------
# Simulation (EMX) API (REAL-TIME STREAMING via SSE, NO LOG FILES)
# -------------------------
from fastapi import Body, Request
from fastapi.responses import StreamingResponse
import threading

ACTIVE_RUN_KEY = "active"

SIM_RUNS: Dict[str, subprocess.Popen] = {}
SIM_RUN_META: Dict[str, Dict[str, Any]] = {}

# Ring buffer of recent output lines (shared across clients)
SIM_RING: list[dict] = []  # items: {t, stream, line}
SIM_RING_MAX = 5000
SIM_RING_LOCK = threading.Lock()


def _push_sim_line(stream: str, line: str) -> None:
    item = {"t": time.time(), "stream": stream, "line": line}
    with SIM_RING_LOCK:
        SIM_RING.append(item)
        if len(SIM_RING) > SIM_RING_MAX:
            # keep last SIM_RING_MAX
            del SIM_RING[: len(SIM_RING) - SIM_RING_MAX]


def _reader_thread(pipe, stream_name: str):
    """
    Reads lines from a subprocess pipe and pushes them into SIM_RING.
    """
    try:
        # iter(readline, "") works for text mode pipes
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

    # Only one at a time
    proc_existing = SIM_RUNS.get(ACTIVE_RUN_KEY)
    if proc_existing and proc_existing.poll() is None:
        raise HTTPException(status_code=400, detail="A simulation is already running.")

    pid = _get_active_project_id()
    if not pid:
        raise HTTPException(status_code=400, detail="No project open. Open a project first.")
    root = (_project_dir(pid)).resolve()

    # Load project.json
    try:
        with open(str(root) + "/project.json", "r", encoding="utf-8") as file:
            project_data = json.load(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read project.json: {e}")

    # Write simConfig.json into project root
    sim_config = project_data.get("sim_config")
    if sim_config is None:
        raise HTTPException(status_code=400, detail="project.json is missing 'sim_config'.")

    config_file_path = os.path.join(str(root), "simConfig.json")
    try:
        with open(config_file_path, "w", encoding="utf-8") as json_file:
            json.dump(sim_config, json_file, indent=4)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write simConfig.json: {e}")

    simulate_script = os.path.abspath(os.path.join(str(root), "../../../simulator/simulator.py"))

    gds_path = os.path.join(str(root), "artwork.gds")
    artwork_path = os.path.join(str(root), "artwork.json")

    # IMPORTANT: Use python -u for unbuffered output so you get real-time lines
    command = [
        "python",
        "-u",
        simulate_script,
        "-f",
        gds_path,
        "--sim",
        "emx",
        "-c",
        config_file_path,
        "-a",
        artwork_path,
        "-o",
        str(root),
        "-n",
        "artwork",
    ]

    print("[sim_start] cwd:", str(root))
    print("[sim_start] cmd:", command)

    # Clear ring buffer for fresh run (optional; remove if you want history)
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
            bufsize=1,  # line buffered (best-effort)
            start_new_session=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start simulation: {e}")

    # Start reader threads
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
        # Kill entire process group (kills simulator + ssh + scp, etc.)
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

    # finished
    SIM_RUNS.pop(ACTIVE_RUN_KEY, None)
    _push_sim_line("system", f"Simulation finished. returncode={rc}")
    return {"running": False, "returncode": rc}


@app.get("/api/sim/stream")
def sim_stream(request: Request):
    """
    Server-Sent Events stream of simulation output.
    Frontend uses EventSource() to show real-time stdout/stderr/system lines.
    """

    def event_gen():
        # Send a backlog immediately
        with SIM_RING_LOCK:
            start_idx = max(0, len(SIM_RING) - 300)
            backlog = SIM_RING[start_idx:]
        for item in backlog:
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

        last_idx = start_idx + len(backlog)

        while True:
            # Client disconnected?
            if request.client is None:
                break

            # If the client closes the connection, FastAPI raises on send; we just exit.
            try:
                # Send any new items
                with SIM_RING_LOCK:
                    if last_idx < len(SIM_RING):
                        new_items = SIM_RING[last_idx:]
                        last_idx = len(SIM_RING)
                    else:
                        new_items = []

                for item in new_items:
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

                # If process ended, emit a "done" event and end stream
                proc = SIM_RUNS.get(ACTIVE_RUN_KEY)
                if proc:
                    rc = proc.poll()
                    if rc is not None:
                        done_msg = {"t": time.time(), "stream": "system", "line": f"[done] returncode={rc}"}
                        yield f"data: {json.dumps(done_msg, ensure_ascii=False)}\n\n"
                        break

                # Keep-alive heartbeat (prevents some proxies from buffering/closing)
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
            # If you're behind nginx, you often also want:
            # "X-Accel-Buffering": "no",
        },
    )

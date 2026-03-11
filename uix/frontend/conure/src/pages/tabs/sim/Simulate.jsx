import { useEffect, useRef, useState } from "react";
import { useUiStore } from "../../../state/uiStore";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const SIM_ROOT = ["ui", "home", "tabs", "sim", "simulate"];
const SIMULATOR_PATH = [...SIM_ROOT, "simulator"];
const RUNNING_PATH = [...SIM_ROOT, "running"];
const LINES_PATH = [...SIM_ROOT, "lines"];
const AUTOSCROLL_PATH = [...SIM_ROOT, "autoScroll"];

const ANSI_REGEX = /\x1B\[[0-?]*[ -/]*[@-~]/g;
function stripAnsi(s) {
  return typeof s === "string" ? s.replace(ANSI_REGEX, "") : s;
}

export default function Simulate() {
  const setValue = useUiStore((s) => s.setValue);

  // Keep the important UI state locally, but initialize from store.
  const [simulator, setSimulatorLocal] = useState(() =>
    useUiStore.getState().getValue(SIMULATOR_PATH, "emx")
  );

  const [running, setRunningLocal] = useState(() =>
    !!useUiStore.getState().getValue(RUNNING_PATH, false)
  );

  const [lines, setLines] = useState(() =>
    useUiStore.getState().getValue(LINES_PATH, []) || []
  );

  const [autoScroll, setAutoScrollLocal] = useState(() => {
    const v = useUiStore.getState().getValue(AUTOSCROLL_PATH, true);
    return typeof v === "boolean" ? v : true;
  });

  const esRef = useRef(null);
  const scrollerRef = useRef(null);

  function setSimulator(next) {
    setSimulatorLocal(next);
    setValue(SIMULATOR_PATH, next);
  }

  function setRunning(next) {
    const b = !!next;
    setRunningLocal(b);
    setValue(RUNNING_PATH, b);
  }

  function setAutoScroll(next) {
    const b = !!next;
    setAutoScrollLocal(b);
    setValue(AUTOSCROLL_PATH, b);
  }

  function setConsoleLines(next) {
    setLines((prev) => {
      const resolved = typeof next === "function" ? next(prev) : next;
      setValue(LINES_PATH, resolved);
      return resolved;
    });
  }

  async function syncStatus() {
    try {
      const res = await fetch(`${API_BASE}/api/sim/status`);
      if (!res.ok) return;
      const data = await res.json();
      setRunning(!!data.running);
    } catch {
      //
    }
  }

  useEffect(() => {
    // restore from store on mount in case component remounted after tab switch
    const store = useUiStore.getState();
    setSimulatorLocal(store.getValue(SIMULATOR_PATH, "emx"));
    setRunningLocal(!!store.getValue(RUNNING_PATH, false));
    setLines(store.getValue(LINES_PATH, []) || []);
    const v = store.getValue(AUTOSCROLL_PATH, true);
    setAutoScrollLocal(typeof v === "boolean" ? v : true);

    syncStatus();
  }, []);

  useEffect(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    if (!running) return;

    const es = new EventSource(`${API_BASE}/api/sim/stream`);
    esRef.current = es;

    es.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);

        setConsoleLines((prev) => {
          const next = [...prev, msg];
          if (next.length > 3000) next.splice(0, next.length - 3000);
          return next;
        });

        if (typeof msg?.line === "string" && msg.line.startsWith("[done]")) {
          setRunning(false);
        }
      } catch {
        //
      }
    };

    es.onerror = async () => {
      es.close();
      esRef.current = null;
      await syncStatus();
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [running]);

  useEffect(() => {
    if (!autoScroll) return;
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [lines, autoScroll]);

  async function start() {
    try {
      setConsoleLines([]);
      setRunning(true);

      const res = await fetch(`${API_BASE}/api/sim/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ simulator }),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `Start failed (${res.status})`);
      }

      await syncStatus();
    } catch (err) {
      alert(err?.message || String(err));
      setRunning(false);
    }
  }

  async function stop() {
    try {
      const res = await fetch(`${API_BASE}/api/sim/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `Stop failed (${res.status})`);
      }
    } catch (err) {
      alert(err?.message || String(err));
    } finally {
      setRunning(false);
    }
  }

  function clearConsole() {
    setConsoleLines([]);
  }

  return (
    <div>
      <h4>Simulate</h4>

      <div style={{ padding: 12, border: "1px solid #ccc" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            Simulator:
            <select
              value={simulator}
              onChange={(e) => setSimulator(e.target.value)}
              disabled={running}
            >
              <option value="emx">EMX</option>
            </select>
          </label>

          <button onClick={start} disabled={running}>
            Start
          </button>

          <button onClick={stop} disabled={!running}>
            Stop
          </button>

          <button onClick={clearConsole} disabled={running && lines.length === 0}>
            Clear
          </button>

          <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>

          <div style={{ opacity: 0.75 }}>
            Status: {running ? "Running…" : "Idle"}
          </div>
        </div>

        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
            Simulation output
          </div>

          <div
            ref={scrollerRef}
            style={{
              height: 280,
              overflow: "auto",
              padding: 12,
              border: "1px solid #ddd",
              background: "#fafafa",
              whiteSpace: "pre-wrap",
              fontFamily:
                "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              fontSize: 12,
              lineHeight: 1.35,
            }}
            onScroll={() => {
              const el = scrollerRef.current;
              if (!el) return;
              const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 8;
              setAutoScroll(atBottom);
            }}
          >
            {lines.length === 0 ? (
              <span style={{ opacity: 0.6 }}>
                {running ? "Waiting for output…" : "No output yet. Press Start."}
              </span>
            ) : (
              lines.map((x, i) => (
                <div key={i}>{stripAnsi(x.line)}</div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
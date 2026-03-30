import { useEffect, useRef, useState } from "react";
import ProcessConsole from "../../../components/ProcessConsole";
import { appendCapped, maxLineTime } from "../../../components/consoleUtils";
import { useUiStore } from "../../../state/uiStore";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const SIMULATOR_PATH = ["ui", "home", "tabs", "sim", "simulate", "simulator"];
const RUNNING_PATH = ["ui", "home", "tabs", "sim", "simulate", "running"];

export default function Simulate() {
  const setValue = useUiStore((s) => s.setValue);

  const [simulator, setSimulatorLocal] = useState(() =>
    useUiStore.getState().getValue(SIMULATOR_PATH, "emx")
  );

  const [running, setRunningLocal] = useState(() =>
    !!useUiStore.getState().getValue(RUNNING_PATH, false)
  );

  const [lines, setLines] = useState([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [logsHydrated, setLogsHydrated] = useState(false);

  const esRef = useRef(null);
  const scrollerRef = useRef(null);
  const linesRef = useRef([]);

  linesRef.current = lines;

  function setSimulator(next) {
    setSimulatorLocal(next);
    setValue(SIMULATOR_PATH, next);
  }

  function setRunning(next) {
    const b = !!next;
    setRunningLocal(b);
    setValue(RUNNING_PATH, b);
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

  async function fetchLogs() {
    try {
      const res = await fetch(`${API_BASE}/api/sim/logs`);
      if (!res.ok) {
        setLines([]);
        return;
      }
      const data = await res.json();
      setLines(data.lines || []);
    } catch {
      setLines([]);
    } finally {
      setLogsHydrated(true);
    }
  }

  useEffect(() => {
    const store = useUiStore.getState();
    setSimulatorLocal(store.getValue(SIMULATOR_PATH, "emx"));
    setRunningLocal(!!store.getValue(RUNNING_PATH, false));
    fetchLogs();
    syncStatus();
  }, []);

  useEffect(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    if (!running || !logsHydrated) return;

    const since = maxLineTime(linesRef.current);
    const es = new EventSource(`${API_BASE}/api/sim/stream?since=${encodeURIComponent(since)}`);
    esRef.current = es;

    es.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);

        setLines((prev) => appendCapped(prev, msg));

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
  }, [running, logsHydrated]);

  useEffect(() => {
    if (!autoScroll) return;
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [lines, autoScroll]);

  async function start() {
    try {
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
      await fetchLogs();
    }
  }

  async function clearConsole() {
    if (running) return;
    try {
      const res = await fetch(`${API_BASE}/api/sim/logs`, { method: "DELETE" });
      if (!res.ok) return;
      setLines([]);
    } catch {
      //
    }
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

          <button type="button" onClick={start} disabled={running}>
            Start
          </button>

          <button type="button" onClick={stop} disabled={!running}>
            Stop
          </button>

          <div style={{ opacity: 0.75 }}>
            Status: {running ? "Running…" : "Idle"}
          </div>
        </div>

        <ProcessConsole
          title="Simulation output (stored on server)"
          lines={lines}
          running={running}
          emptyIdle="No output yet. Press Start — history is kept in the project logs folder."
          emptyRunning="Waiting for output…"
          autoScroll={autoScroll}
          onAutoScrollChange={setAutoScroll}
          scrollerRef={scrollerRef}
          onScrollContainer={() => {
            const el = scrollerRef.current;
            if (!el) return;
            const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 8;
            setAutoScroll(atBottom);
          }}
          onClear={clearConsole}
          clearDisabled={running}
          clearLabel="Clear log"
        />
      </div>
    </div>
  );
}

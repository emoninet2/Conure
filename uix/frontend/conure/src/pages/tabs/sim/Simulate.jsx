import { useEffect, useRef, useState } from "react";
import { useUiStore } from "../../../state/uiStore";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const SIMULATOR_PATH = ["ui", "home", "tabs", "sim", "simulate", "simulator"];
const RUNNING_PATH = ["ui", "home", "tabs", "sim", "simulate", "running"];

// put near the top of the file
const ANSI_REGEX = /\x1B\[[0-?]*[ -/]*[@-~]/g; // matches ANSI escape sequences
function stripAnsi(s) {
  return typeof s === "string" ? s.replace(ANSI_REGEX, "") : s;
}


export default function Simulate() {
  const setValue = useUiStore((s) => s.setValue);

  const simulator = useUiStore((s) => s.getValue(SIMULATOR_PATH, "emx"));
  const running = useUiStore((s) => s.getValue(RUNNING_PATH, false));

  // local console state (fast + simple)
  const [lines, setLines] = useState([]); // [{t, stream, line}]
  const esRef = useRef(null);
  const scrollerRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // sync on mount with backend status so UI never gets stuck
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/sim/status`);
        if (!res.ok) return;
        const data = await res.json();
        setValue(RUNNING_PATH, !!data.running);
      } catch {
        // ignore
      }
    })();
  }, [setValue]);

  // SSE live stream when running
  useEffect(() => {
    // close any previous stream
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
        setLines((prev) => {
          const next = [...prev, msg];
          // keep last N lines
          if (next.length > 3000) next.splice(0, next.length - 3000);
          return next;
        });

        // If backend sends "[done]" line, reflect running=false
        if (typeof msg?.line === "string" && msg.line.startsWith("[done]")) {
          setValue(RUNNING_PATH, false);
        }
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      // server ended stream or network issue
      // Don't force running=false here (backend may still be running).
      // But we can do a quick status check:
      (async () => {
        try {
          const res = await fetch(`${API_BASE}/api/sim/status`);
          if (!res.ok) return;
          const data = await res.json();
          setValue(RUNNING_PATH, !!data.running);
        } catch {
          // ignore
        }
      })();

      es.close();
      esRef.current = null;
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [running, setValue]);

  // autoscroll
  useEffect(() => {
    if (!autoScroll) return;
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [lines, autoScroll]);

  async function start() {
    try {
      setLines([]);
      setValue(RUNNING_PATH, true);

      const res = await fetch(`${API_BASE}/api/sim/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ simulator }),
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `Start failed (${res.status})`);
      }
    } catch (err) {
      alert(err?.message || String(err));
      setValue(RUNNING_PATH, false);
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
      setValue(RUNNING_PATH, false);
    }
  }

  function clearConsole() {
    setLines([]);
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
              onChange={(e) => setValue(SIMULATOR_PATH, e.target.value)}
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
          <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Simulation output</div>

          <div
            ref={scrollerRef}
            style={{
              height: 280,
              overflow: "auto",
              padding: 12,
              border: "1px solid #ddd",
              background: "#fafafa",
              whiteSpace: "pre-wrap",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              fontSize: 12,
              lineHeight: 1.35,
            }}
            onScroll={() => {
              // if user scrolls up, disable autoscroll; if at bottom, enable
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
              lines.map((x, i) => {
                // const prefix = x.stream ? `${x.stream}: ` : "";
                const prefix = "";
                return (
                  <div key={i}>
                    {stripAnsi(x.line)}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
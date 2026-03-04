import { useEffect } from "react";
import { useUiStore } from "../../../state/uiStore";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const SIMULATOR_PATH = ["ui", "home", "tabs", "sim", "simulate", "simulator"];
const RUNNING_PATH = ["ui", "home", "tabs", "sim", "simulate", "running"];

export default function Simulate() {
  const setValue = useUiStore((s) => s.setValue);

  const simulator = useUiStore((s) => s.getValue(SIMULATOR_PATH, "emx"));
  const running = useUiStore((s) => s.getValue(RUNNING_PATH, false));

  // optional: sync on mount with backend status so it never gets stuck
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

  async function start() {
    try {
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

          <div style={{ opacity: 0.75 }}>
            Status: {running ? "Running…" : "Idle"}
          </div>
        </div>
      </div>
    </div>
  );
}
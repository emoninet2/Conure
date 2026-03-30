import { useEffect, useMemo, useRef, useState } from "react";
import ProcessConsole from "../../components/ProcessConsole";
import { appendCapped, maxLineTime } from "../../components/consoleUtils";
import { IconPencil, IconTrash } from "../../icons/actionIcons";
import { useUiStore } from "../../state/uiStore";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const SWEEP_UI_PATH = ["ui", "home", "tabs", "sweep"];
const ACTIVE_SWEEP_PATH = [...SWEEP_UI_PATH, "activeSweep"];
const RUNNING_PATH = [...SWEEP_UI_PATH, "running"];
const ARTWORK_PARAMETERS_PATH = ["artwork", "parameters"];

const DEFAULT_DRAFT = {
  enable_layout: true,
  enable_svg: true,
  enable_simulation: false,
  pack_sim: false,
  simulator: "emx",
  force_overwrite: false,
  parameters: [],
};

const DEFAULT_SUMMARY = {
  state: "idle",
  total_permutations: 0,
  completed_runs: 0,
  remaining_runs: 0,
  current_run_index: null,
  current_run: null,
  current_run_name: null,
  current_permutation: null,
  current_task: null,
  progress_percentage: 0,
  counts: {
    layout: { completed: 0, failed: 0, pending: 0 },
    svg: { completed: 0, failed: 0, pending: 0 },
    simulation: { completed: 0, failed: 0, pending: 0 },
  },
  started_at: null,
  finished_at: null,
  last_updated: null,
};

function parseScalar(value) {
  const t = String(value ?? "").trim();
  if (t === "") return "";
  if (t === "true") return true;
  if (t === "false") return false;
  if (!Number.isNaN(Number(t))) return Number(t);

  try {
    return JSON.parse(t);
  } catch {
    return t;
  }
}

function parseListText(text) {
  return String(text || "")
    .split(",")
    .map((x) => x.trim())
    .filter((x) => x !== "")
    .map(parseScalar);
}

function toListText(arr) {
  if (!Array.isArray(arr)) return "";
  return arr.join(", ");
}

function draftToSweepJson(draft) {
  const out = { parameters: {} };

  for (const row of draft.parameters || []) {
    if (!row?.name) continue;

    if (row.mode === "list") {
      out.parameters[row.name] = Array.isArray(row.list) ? row.list : [];
    } else {
      out.parameters[row.name] = {
        from: parseScalar(row.from),
        to: parseScalar(row.to),
        type: row.rangeType || "step",
        value: parseScalar(row.value),
      };
    }
  }

  return out;
}

function sweepResponseToDraft(config) {
  const params = config?.sweep_json?.parameters || {};
  const rows = Object.entries(params).map(([name, value]) => {
    if (Array.isArray(value)) {
      return {
        name,
        mode: "list",
        list: value,
        listText: toListText(value),
        from: "",
        to: "",
        rangeType: "step",
        value: "",
      };
    }

    return {
      name,
      mode: "range",
      list: [],
      listText: "",
      from: value?.from ?? "",
      to: value?.to ?? "",
      rangeType: value?.type || "step",
      value: value?.value ?? "",
    };
  });

  return {
    enable_layout: !!config?.enable_layout,
    enable_svg: !!config?.enable_svg,
    enable_simulation: !!config?.enable_simulation,
    pack_sim: !!config?.pack_sim,
    simulator: config?.simulator || "emx",
    force_overwrite: !!config?.force_overwrite,
    parameters: rows,
  };
}

function draftToBackendConfig(draft) {
  return {
    enable_layout: !!draft.enable_layout,
    enable_svg: !!draft.enable_svg,
    enable_simulation: !!draft.enable_simulation,
    pack_sim: !!draft.pack_sim,
    simulator: draft.simulator || "emx",
    force_overwrite: !!draft.force_overwrite,
    sweep_json: draftToSweepJson(draft),
  };
}

function formatTimestamp(ts) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return String(ts);
  }
}

export default function Sweep() {
  const setValue = useUiStore((s) => s.setValue);

  const [activeSweep, setActiveSweepLocal] = useState("");
  const [running, setRunningLocal] = useState(false);
  const [artworkParameters, setArtworkParameters] = useState({});

  const [sweeps, setSweeps] = useState([]);
  const [newSweepName, setNewSweepName] = useState("");
  const [draft, setDraft] = useState(DEFAULT_DRAFT);
  const [savedSnapshot, setSavedSnapshot] = useState(DEFAULT_DRAFT);
  const [summary, setSummary] = useState(DEFAULT_SUMMARY);
  const [lines, setLines] = useState([]);
  const [logsHydrated, setLogsHydrated] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [apiError, setApiError] = useState("");

  const scrollerRef = useRef(null);
  const esRef = useRef(null);
  const linesRef = useRef([]);

  linesRef.current = lines;

  useEffect(() => {
    let cancelled = false;
    setLogsHydrated(false);
    if (!activeSweep) {
      setLines([]);
      setLogsHydrated(true);
      return () => {
        cancelled = true;
      };
    }
    (async () => {
      try {
        const res = await fetch(
          `${API_BASE}/api/sweeps/logs?sweep_name=${encodeURIComponent(activeSweep)}`
        );
        if (!res.ok || cancelled) return;
        const data = await res.json();
        if (!cancelled) setLines(data.lines || []);
      } catch {
        if (!cancelled) setLines([]);
      } finally {
        if (!cancelled) setLogsHydrated(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeSweep]);

  useEffect(() => {
    const store = useUiStore.getState();
    setActiveSweepLocal(store.getValue(ACTIVE_SWEEP_PATH, "") || "");
    setRunningLocal(!!store.getValue(RUNNING_PATH, false));
    setArtworkParameters(store.getValue(ARTWORK_PARAMETERS_PATH, {}) || {});
    refreshSweeps();
    syncStatus();
  }, []);

  const availableParamNames = useMemo(
    () => Object.keys(artworkParameters || {}).sort(),
    [artworkParameters]
  );

  const dirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(savedSnapshot),
    [draft, savedSnapshot]
  );

  const duplicateNames = useMemo(() => {
    const counts = {};
    for (const row of draft.parameters || []) {
      if (!row.name) continue;
      counts[row.name] = (counts[row.name] || 0) + 1;
    }
    return new Set(Object.keys(counts).filter((k) => counts[k] > 1));
  }, [draft.parameters]);

  const generatedSweepJson = useMemo(() => draftToSweepJson(draft), [draft]);

  useEffect(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    if (!running || !activeSweep || !logsHydrated) return;

    const since = maxLineTime(linesRef.current);
    const es = new EventSource(
      `${API_BASE}/api/sweeps/stream?sweep_name=${encodeURIComponent(activeSweep)}&since=${encodeURIComponent(since)}`
    );
    esRef.current = es;

    es.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        setLines((prev) => appendCapped(prev, msg));

        if (typeof msg?.line === "string" && msg.line.startsWith("[done]")) {
          setValue(RUNNING_PATH, false);
          setRunningLocal(false);
          fetchSummary(activeSweep);
        }
      } catch {
        //
      }
    };

    es.onerror = async () => {
      es.close();
      esRef.current = null;
      await syncStatus();
      await fetchSummary(activeSweep);
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [running, activeSweep, logsHydrated, setValue]);

  useEffect(() => {
    if (!activeSweep) {
      setSummary(DEFAULT_SUMMARY);
      return;
    }

    fetchSummary(activeSweep);

    if (!running) return;

    const id = setInterval(() => {
      fetchSummary(activeSweep);
    }, 700);

    return () => clearInterval(id);
  }, [activeSweep, running]);

  useEffect(() => {
    if (!autoScroll) return;
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines, autoScroll]);

  async function refreshSweeps() {
    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/sweeps`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSweeps(data.sweeps || []);
    } catch (err) {
      setApiError(err?.message || String(err));
    }
  }

  async function syncStatus() {
    try {
      const res = await fetch(`${API_BASE}/api/sweeps/status`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      const nextRunning = !!data.running;
      const nextSweep = data.sweep_name || "";

      setValue(RUNNING_PATH, nextRunning);
      setRunningLocal(nextRunning);

      if (nextSweep && nextSweep !== activeSweep) {
        setValue(ACTIVE_SWEEP_PATH, nextSweep);
        setActiveSweepLocal(nextSweep);
      }
    } catch (err) {
      setApiError(err?.message || String(err));
    }
  }

  async function fetchSummary(name = activeSweep) {
    if (!name) {
      setSummary(DEFAULT_SUMMARY);
      return;
    }

    try {
      const res = await fetch(
        `${API_BASE}/api/sweeps/summary?sweep_name=${encodeURIComponent(name)}`
      );
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setSummary({ ...DEFAULT_SUMMARY, ...data });
    } catch (err) {
      setApiError(err?.message || String(err));
    }
  }

  function updateTopField(key, value) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  function addParameterRow() {
    setDraft((prev) => ({
      ...prev,
      parameters: [
        ...(prev.parameters || []),
        {
          name: "",
          mode: "range",
          from: "",
          to: "",
          rangeType: "step",
          value: "",
          list: [],
          listText: "",
        },
      ],
    }));
  }

  function removeParameterRow(index) {
    setDraft((prev) => ({
      ...prev,
      parameters: prev.parameters.filter((_, i) => i !== index),
    }));
  }

  function updateParameterRow(index, patch) {
    setDraft((prev) => ({
      ...prev,
      parameters: prev.parameters.map((row, i) => {
        if (i !== index) return row;
        const next = { ...row, ...patch };
        if (patch.listText !== undefined) {
          next.list = parseListText(patch.listText);
        }
        return next;
      }),
    }));
  }

  async function createSweep() {
    const name = newSweepName.trim();
    if (!name) {
      alert("Enter a sweep name.");
      return;
    }

    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/sweeps/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sweep_name: name }),
      });

      if (!res.ok) throw new Error(await res.text());

      const data = await res.json();
      setNewSweepName("");
      await refreshSweeps();
      await openSweep(data.sweep_name || name);
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  async function openSweep(name) {
    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/sweeps/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sweep_name: name }),
      });

      if (!res.ok) throw new Error(await res.text());

      const data = await res.json();
      const nextDraft = sweepResponseToDraft(data.config);

      setValue(ACTIVE_SWEEP_PATH, data.sweep_name);
      setActiveSweepLocal(data.sweep_name);

      setValue(RUNNING_PATH, !!data.running);
      setRunningLocal(!!data.running);

      setDraft(nextDraft);
      setSavedSnapshot(JSON.parse(JSON.stringify(nextDraft)));
      await fetchSummary(data.sweep_name);
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  async function saveSweep() {
    if (!activeSweep) {
      alert("Open or create a sweep first.");
      return;
    }

    if (duplicateNames.size > 0) {
      alert("Duplicate parameter names are not allowed.");
      return;
    }

    const backendConfig = draftToBackendConfig(draft);

    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/sweeps/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sweep_name: activeSweep,
          config: backendConfig,
        }),
      });

      if (!res.ok) throw new Error(await res.text());

      setSavedSnapshot(JSON.parse(JSON.stringify(draft)));
      await refreshSweeps();
      await fetchSummary(activeSweep);
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  async function resetSweep() {
    if (!activeSweep) {
      setDraft(DEFAULT_DRAFT);
      setSavedSnapshot(DEFAULT_DRAFT);
      setSummary(DEFAULT_SUMMARY);
      return;
    }
    await openSweep(activeSweep);
  }

  async function startSweep() {
    if (!activeSweep) {
      alert("Open or create a sweep first.");
      return;
    }

    if (duplicateNames.size > 0) {
      alert("Duplicate parameter names are not allowed.");
      return;
    }

    const backendConfig = draftToBackendConfig(draft);

    try {
      setApiError("");
      setSummary((prev) => ({ ...prev, state: "running" }));

      setValue(RUNNING_PATH, true);
      setRunningLocal(true);

      const res = await fetch(`${API_BASE}/api/sweeps/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sweep_name: activeSweep,
          config: backendConfig,
        }),
      });

      if (!res.ok) throw new Error(await res.text());

      setSavedSnapshot(JSON.parse(JSON.stringify(draft)));
      await fetchSummary(activeSweep);
    } catch (err) {
      setValue(RUNNING_PATH, false);
      setRunningLocal(false);
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  async function stopSweep() {
    if (!activeSweep) return;

    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/sweeps/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sweep_name: activeSweep }),
      });

      if (!res.ok) throw new Error(await res.text());
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    } finally {
      setValue(RUNNING_PATH, false);
      setRunningLocal(false);
      await fetchSummary(activeSweep);
    }
  }

  async function clearSweepLog() {
    if (!activeSweep || running) return;
    try {
      const res = await fetch(
        `${API_BASE}/api/sweeps/logs?sweep_name=${encodeURIComponent(activeSweep)}`,
        { method: "DELETE" }
      );
      if (!res.ok) return;
      setLines([]);
    } catch {
      //
    }
  }

  async function deleteSweep(name) {
    if (!name) return;

    const ok = window.confirm(`Delete sweep "${name}"?`);
    if (!ok) return;

    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/sweeps/${encodeURIComponent(name)}`, {
        method: "DELETE",
      });

      if (!res.ok) throw new Error(await res.text());

      if (name === activeSweep) {
        setValue(ACTIVE_SWEEP_PATH, "");
        setActiveSweepLocal("");

        setValue(RUNNING_PATH, false);
        setRunningLocal(false);

        setDraft(DEFAULT_DRAFT);
        setSavedSnapshot(DEFAULT_DRAFT);
        setSummary(DEFAULT_SUMMARY);
        setLines([]);
      }

      await refreshSweeps();
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  async function renameSweep(name) {
    if (!name) return;

    const next = window.prompt(`Rename sweep "${name}" to:`, name);
    if (next == null) return;
    const trimmed = next.trim();
    if (!trimmed || trimmed === name) return;

    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/sweeps/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from_name: name, to_name: trimmed }),
      });
      if (!res.ok) throw new Error(await res.text());

      const data = await res.json();
      const newName = data.sweep_name || trimmed;

      if (name === activeSweep) {
        await openSweep(newName);
      }
      await refreshSweeps();
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  return (
    <div>
      <h3>Sweep</h3>

      {apiError ? (
        <div style={{ marginBottom: 12, color: "crimson" }}>
          API error: {apiError}
        </div>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 16, alignItems: "start" }}>
        <div
          style={{
            border: "1px solid #d9dee7",
            padding: 12,
            background: "#fbfcfe",
            borderRadius: 10,
          }}
        >
          <h4 style={{ marginTop: 0, marginBottom: 12 }}>Sweeps</h4>

          <div
            style={{
              display: "flex",
              gap: 8,
              marginBottom: 14,
              alignItems: "center",
            }}
          >
            <input
              value={newSweepName}
              onChange={(e) => setNewSweepName(e.target.value)}
              placeholder="New sweep name"
              style={{
                flex: 1,
                minWidth: 0,
                padding: "9px 10px",
                border: "1px solid #d0d7de",
                borderRadius: 8,
                background: "#fff",
              }}
            />
            <button
              onClick={createSweep}
              style={{
                padding: "9px 14px",
                borderRadius: 8,
                border: "1px solid #cfd6e4",
                background: "#fff",
                fontWeight: 600,
                whiteSpace: "nowrap",
              }}
            >
              Create
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {sweeps.length === 0 ? (
              <div style={{ opacity: 0.7 }}>No sweeps yet.</div>
            ) : (
              sweeps.map((name) => (
                <div
                  key={name}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(0, 1fr) auto auto",
                    gap: 6,
                    alignItems: "center",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => openSweep(name)}
                    style={{
                      flex: 1,
                      minWidth: 0,
                      textAlign: "left",
                      fontWeight: name === activeSweep ? 700 : 500,
                      padding: "10px 12px",
                      borderRadius: 8,
                      border: name === activeSweep ? "1px solid #b9c9ef" : "1px solid #e2e8f0",
                      background: name === activeSweep ? "#eef4ff" : "#fff",
                      color: "#1f2937",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={name}
                  >
                    {name}
                  </button>
                  <button
                    type="button"
                    onClick={() => renameSweep(name)}
                    disabled={running && activeSweep === name}
                    aria-label={`Rename sweep ${name}`}
                    title="Rename this sweep"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 36,
                      height: 36,
                      padding: 0,
                      borderRadius: 8,
                      border: "1px solid #e2e8f0",
                      background: "#fff",
                      color: "#334155",
                      flexShrink: 0,
                      opacity: running && activeSweep === name ? 0.6 : 1,
                    }}
                  >
                    <IconPencil />
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteSweep(name)}
                    disabled={running && activeSweep === name}
                    aria-label={`Delete sweep ${name}`}
                    title="Delete this sweep"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: 36,
                      height: 36,
                      padding: 0,
                      borderRadius: 8,
                      border: "1px solid #e2e8f0",
                      background: "#fff",
                      color: "#b42318",
                      flexShrink: 0,
                      opacity: running && activeSweep === name ? 0.6 : 1,
                    }}
                  >
                    <IconTrash />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div style={{ border: "1px solid #d9dee7", padding: 12, borderRadius: 10, background: "#fff" }}>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 12 }}>
            <div>
              Active sweep: <strong>{activeSweep || "None"}</strong>
            </div>
            <div>Status: {running ? "Running…" : "Idle"}</div>
            <div>State: {summary.state || "idle"}</div>
            <div>Unsaved: {dirty ? "Yes" : "No"}</div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <strong>Progress</strong>
              <span>{Number(summary.progress_percentage || 0).toFixed(1)}%</span>
            </div>

            <div
              style={{
                width: "100%",
                height: 14,
                border: "1px solid #ccc",
                background: "#f3f3f3",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${Math.max(0, Math.min(100, summary.progress_percentage || 0))}%`,
                  height: "100%",
                  background: "#4caf50",
                  transition: "width 0.2s ease",
                }}
              />
            </div>

            <div style={{ marginTop: 8, fontSize: 12, opacity: 0.8 }}>
              {summary.completed_runs || 0} / {summary.total_permutations || 0} runs completed
            </div>
          </div>

          <div style={{ marginBottom: 16, fontSize: 13 }}>
            {summary.current_run ? (
              <div>
                <strong>Current run:</strong> {summary.current_run}
              </div>
            ) : null}

            {summary.current_run_name ? (
              <div>
                <strong>Run name:</strong> {summary.current_run_name}
              </div>
            ) : null}

            <div>
              <strong>Started:</strong> {formatTimestamp(summary.started_at)}
            </div>

            <div>
              <strong>Finished:</strong> {formatTimestamp(summary.finished_at)}
            </div>

            {summary.current_permutation &&
            Object.keys(summary.current_permutation).length > 0 ? (
              <div style={{ marginTop: 8 }}>
                <strong>Current permutation:</strong>
                <pre
                  style={{
                    marginTop: 6,
                    padding: 8,
                    border: "1px solid #ddd",
                    background: "#fafafa",
                    fontSize: 12,
                    overflow: "auto",
                  }}
                >
                  {JSON.stringify(summary.current_permutation, null, 2)}
                </pre>
              </div>
            ) : null}
          </div>

          <div style={{ marginBottom: 16, fontSize: 13 }}>
            <strong>Counts</strong>
            <div>
              Layout: {summary.counts?.layout?.completed ?? 0} completed,{" "}
              {summary.counts?.layout?.failed ?? 0} failed,{" "}
              {summary.counts?.layout?.pending ?? 0} pending
            </div>
            <div>
              SVG: {summary.counts?.svg?.completed ?? 0} completed,{" "}
              {summary.counts?.svg?.failed ?? 0} failed,{" "}
              {summary.counts?.svg?.pending ?? 0} pending
            </div>
            <div>
              Simulation: {summary.counts?.simulation?.completed ?? 0} completed,{" "}
              {summary.counts?.simulation?.failed ?? 0} failed,{" "}
              {summary.counts?.simulation?.pending ?? 0} pending
            </div>
          </div>

          <div style={{ display: "grid", gap: 10, marginBottom: 14 }}>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={draft.enable_layout}
                onChange={(e) => updateTopField("enable_layout", e.target.checked)}
                disabled={running}
              />
              Enable layout
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={draft.enable_svg}
                onChange={(e) => updateTopField("enable_svg", e.target.checked)}
                disabled={running}
              />
              Enable SVG
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={draft.enable_simulation}
                onChange={(e) => updateTopField("enable_simulation", e.target.checked)}
                disabled={running}
              />
              Enable simulation
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={draft.pack_sim}
                onChange={(e) => updateTopField("pack_sim", e.target.checked)}
                disabled={running}
              />
              Pack simulation data
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              Simulator:
              <select
                value={draft.simulator}
                onChange={(e) => updateTopField("simulator", e.target.value)}
                disabled={running || !draft.enable_simulation}
              >
                <option value="emx">EMX</option>
              </select>
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={draft.force_overwrite}
                onChange={(e) => updateTopField("force_overwrite", e.target.checked)}
                disabled={running}
              />
              Force overwrite
            </label>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <strong>Sweep Parameters</strong>
              <button onClick={addParameterRow} disabled={running}>
                Add Parameter
              </button>
            </div>

            <div style={{ display: "grid", gap: 12 }}>
              {(draft.parameters || []).map((row, index) => {
                const isDuplicate = row.name && duplicateNames.has(row.name);

                return (
                  <div key={index} style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1.2fr 0.8fr auto",
                        gap: 8,
                        marginBottom: 10,
                      }}
                    >
                      <select
                        value={row.name}
                        onChange={(e) => updateParameterRow(index, { name: e.target.value })}
                        disabled={running}
                      >
                        <option value="">Select parameter</option>
                        {availableParamNames.map((name) => (
                          <option key={name} value={name}>
                            {name}
                          </option>
                        ))}
                      </select>

                      <select
                        value={row.mode}
                        onChange={(e) => updateParameterRow(index, { mode: e.target.value })}
                        disabled={running}
                      >
                        <option value="range">Range</option>
                        <option value="list">List</option>
                      </select>

                      <button onClick={() => removeParameterRow(index)} disabled={running}>
                        Remove
                      </button>
                    </div>

                    {isDuplicate ? (
                      <div style={{ color: "crimson", marginBottom: 8 }}>
                        Duplicate parameter name.
                      </div>
                    ) : null}

                    {row.mode === "list" ? (
                      <input
                        value={row.listText || ""}
                        onChange={(e) => updateParameterRow(index, { listText: e.target.value })}
                        disabled={running}
                        placeholder="2, 3, 4, 5"
                        style={{ width: "100%" }}
                      />
                    ) : (
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr 1fr 1fr",
                          gap: 8,
                        }}
                      >
                        <input
                          value={row.from}
                          onChange={(e) => updateParameterRow(index, { from: e.target.value })}
                          disabled={running}
                          placeholder="from"
                        />
                        <input
                          value={row.to}
                          onChange={(e) => updateParameterRow(index, { to: e.target.value })}
                          disabled={running}
                          placeholder="to"
                        />
                        <select
                          value={row.rangeType}
                          onChange={(e) =>
                            updateParameterRow(index, { rangeType: e.target.value })
                          }
                          disabled={running}
                        >
                          <option value="step">step</option>
                          <option value="npoints">npoints</option>
                        </select>
                        <input
                          value={row.value}
                          onChange={(e) => updateParameterRow(index, { value: e.target.value })}
                          disabled={running}
                          placeholder="value"
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 6, fontWeight: "bold" }}>Generated sweep.json</div>
            <pre
              style={{
                margin: 0,
                padding: 12,
                border: "1px solid #ddd",
                background: "#fafafa",
                overflow: "auto",
                fontSize: 12,
              }}
            >
              {JSON.stringify(generatedSweepJson, null, 2)}
            </pre>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            <button onClick={saveSweep} disabled={!activeSweep || running}>
              Save
            </button>
            <button onClick={resetSweep} disabled={running}>
              Reset
            </button>
            <button onClick={startSweep} disabled={!activeSweep || running}>
              Start
            </button>
            <button onClick={stopSweep} disabled={!running}>
              Stop
            </button>
          </div>

          <ProcessConsole
            title={activeSweep ? `Sweep output — ${activeSweep} (server log)` : "Sweep output"}
            lines={lines}
            running={running}
            emptyIdle={activeSweep ? "No output yet for this sweep." : "Open or create a sweep to view logs."}
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
            onClear={clearSweepLog}
            clearDisabled={running || !activeSweep}
            clearLabel="Clear log"
          />
        </div>
      </div>
    </div>
  );
}
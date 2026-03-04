import { useEffect, useMemo, useRef, useState } from "react";
import AddButton from "../../../components/AddButton";


function makeId() {
  return (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function safeObj(x) {
  return x && typeof x === "object" ? x : {};
}

function toPortRows(dataObj) {
  const obj = safeObj(dataObj);
  return Object.entries(obj).map(([name, v]) => ({
    id: makeId(),
    name: String(name),
    label: v?.label ?? "",
  }));
}

function toSimRows(simArray) {
  const arr = Array.isArray(simArray) ? simArray : [];
  return arr.map((p) => ({
    _rowId: makeId(), // internal stable id for React
    id: typeof p?.id === "number" ? p.id : 0,
    type: p?.type ?? "differential",
    plus: p?.plus ?? "",
    minus: p?.minus ?? "",
    enable: p?.enable ?? true,
  }));
}

function numOrZero(x) {
  const s = String(x).trim();
  if (s === "") return 0;
  const n = Number(s);
  return Number.isNaN(n) ? 0 : n;
}

export default function Ports({ draftArtwork, setDraftArtwork, markDirty, resetToken = 0 }) {
  const debounceRef = useRef(null);

  const ports = safeObj(draftArtwork?.ports);
  const portsData = safeObj(ports?.data);
  const simPorts = ports?.config?.simulatingPorts;

  const [portRows, setPortRows] = useState(() => toPortRows(portsData));
  const [simRows, setSimRows] = useState(() => toSimRows(simPorts));

  // Reset-only rehydrate
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    const freshPorts = safeObj(draftArtwork?.ports);
    setPortRows(toPortRows(safeObj(freshPorts?.data)));
    setSimRows(toSimRows(freshPorts?.config?.simulatingPorts));
  }, [resetToken]);

  // Dropdown options for plus/minus (port names)
  const portNameOptions = useMemo(() => {
    // use the current UI rows (so dropdown updates immediately if user adds a port row)
    return portRows
      .map((r) => r.name.trim())
      .filter(Boolean)
      .filter((v, i, a) => a.indexOf(v) === i)
      .sort();
  }, [portRows]);

  const duplicatePortNames = useMemo(() => {
    const counts = new Map();
    for (const r of portRows) {
      const k = r.name.trim();
      if (!k) continue;
      counts.set(k, (counts.get(k) || 0) + 1);
    }
    return new Set([...counts.entries()].filter(([, c]) => c > 1).map(([k]) => k));
  }, [portRows]);

  const duplicateSimIds = useMemo(() => {
    const counts = new Map();
    for (const r of simRows) {
      const k = r.id;
      counts.set(k, (counts.get(k) || 0) + 1);
    }
    return new Set([...counts.entries()].filter(([, c]) => c > 1).map(([k]) => k));
  }, [simRows]);

  function addPortRow() {
    markDirty?.();
    setPortRows((prev) => [...prev, { id: makeId(), name: "", label: "" }]);
  }

  function deletePortRow(rowId) {
    markDirty?.();
    setPortRows((prev) => prev.filter((r) => r.id !== rowId));
  }

  function updatePortRow(rowId, patch) {
    markDirty?.();
    setPortRows((prev) => prev.map((r) => (r.id === rowId ? { ...r, ...patch } : r)));
  }

  function addSimRow() {
    markDirty?.();
    const nextId =
      simRows.length === 0 ? 0 : Math.max(...simRows.map((r) => Number(r.id) || 0)) + 1;

    setSimRows((prev) => [
      ...prev,
      {
        _rowId: makeId(),
        id: nextId,
        type: "differential",
        plus: portNameOptions[0] ?? "",
        minus: portNameOptions[1] ?? portNameOptions[0] ?? "",
        enable: true,
      },
    ]);
  }

  function deleteSimRow(rowId) {
    markDirty?.();
    setSimRows((prev) => prev.filter((r) => r._rowId !== rowId));
  }

  function updateSimRow(rowId, patch) {
    markDirty?.();
    setSimRows((prev) => prev.map((r) => (r._rowId === rowId ? { ...r, ...patch } : r)));
  }

  // Push -> draftArtwork.ports (debounced)
  useEffect(() => {
    // avoid ambiguous saves
    if (duplicatePortNames.size > 0) return;
    if (duplicateSimIds.size > 0) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      // build ports.data
      const data = {};
      for (const r of portRows) {
        const name = r.name.trim();
        if (!name) continue;
        data[name] = { label: String(r.label ?? "") };
      }

      // build ports.config.simulatingPorts
      const simulatingPorts = simRows.map((r) => ({
        id: numOrZero(r.id),
        type: r.type || "differential",
        plus: (r.plus || "").trim(),
        minus: (r.minus || "").trim(),
        enable: !!r.enable,
      }));

      setDraftArtwork?.((prev) => ({
        ...(prev || {}),
        ports: {
          config: { simulatingPorts },
          data,
        },
      }));
    }, 150);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
    };
  }, [portRows, simRows, duplicatePortNames, duplicateSimIds, setDraftArtwork, resetToken]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      <h4>Ports</h4>

      {/* Ports table */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <h5 style={{ margin: 0 }}>Ports (data)</h5>

                <AddButton onClick={addPortRow}>
                  Add Port
                </AddButton>
        
        


      </div>

      {duplicatePortNames.size > 0 && (
        <div style={{ color: "crimson" }}>
          Duplicate port name(s): {[...duplicatePortNames].join(", ")}
        </div>
      )}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Name</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Label</th>
            <th style={{ padding: 6, borderBottom: "1px solid #ccc" }} />
          </tr>
        </thead>
        <tbody>
          {portRows.length === 0 && (
            <tr>
              <td colSpan={3} style={{ padding: 8, opacity: 0.7 }}>
                No ports defined
              </td>
            </tr>
          )}

          {portRows.map((r) => {
            const name = r.name.trim();
            const isDup = name && duplicatePortNames.has(name);

            return (
              <tr key={r.id}>
                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.name}
                    onChange={(e) => updatePortRow(r.id, { name: e.target.value })}
                    placeholder="e.g. PORT0"
                    style={{ width: "100%", borderColor: isDup ? "crimson" : undefined }}
                  />
                </td>
                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.label}
                    onChange={(e) => updatePortRow(r.id, { label: e.target.value })}
                    placeholder="e.g. P0"
                    style={{ width: "100%" }}
                  />
                </td>
                <td style={{ padding: 6, borderBottom: "1px solid #eee", textAlign: "right" }}>
                  <button onClick={() => deletePortRow(r.id)}>Delete</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Simulating ports table */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <h5 style={{ margin: 0 }}>Simulating Ports</h5>
                <AddButton onClick={addSimRow}>
                  Add Sim port
                </AddButton>
        
        
      </div>

      {portNameOptions.length === 0 && (
        <div style={{ opacity: 0.75 }}>
          Add at least one port in the Ports table to enable Plus/Minus selection.
        </div>
      )}

      {duplicateSimIds.size > 0 && (
        <div style={{ color: "crimson" }}>
          Duplicate sim port id(s): {[...duplicateSimIds].join(", ")}
        </div>
      )}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>ID</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Type</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Plus</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Minus</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Enable</th>
            <th style={{ padding: 6, borderBottom: "1px solid #ccc" }} />
          </tr>
        </thead>
        <tbody>
          {simRows.length === 0 && (
            <tr>
              <td colSpan={6} style={{ padding: 8, opacity: 0.7 }}>
                No simulating ports configured
              </td>
            </tr>
          )}

          {simRows.map((r) => {
            const isDupId = duplicateSimIds.has(r.id);

            return (
              <tr key={r._rowId}>
                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.id}
                    onChange={(e) => updateSimRow(r._rowId, { id: e.target.value })}
                    style={{ width: "100%" }}
                  />
                  {isDupId && <div style={{ color: "crimson", fontSize: 12 }}>Duplicate</div>}
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <select
                    value={r.type}
                    onChange={(e) => updateSimRow(r._rowId, { type: e.target.value })}
                    style={{ width: "100%" }}
                  >
                    <option value="differential">differential</option>
                    <option value="singleEnded">singleEnded</option>
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <select
                    value={r.plus}
                    onChange={(e) => updateSimRow(r._rowId, { plus: e.target.value })}
                    style={{ width: "100%" }}
                    disabled={portNameOptions.length === 0}
                  >
                    <option value="" disabled>
                      Select
                    </option>
                    {portNameOptions.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <select
                    value={r.minus}
                    onChange={(e) => updateSimRow(r._rowId, { minus: e.target.value })}
                    style={{ width: "100%" }}
                    disabled={portNameOptions.length === 0}
                  >
                    <option value="" disabled>
                      Select
                    </option>
                    {portNameOptions.map((p) => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    type="checkbox"
                    checked={!!r.enable}
                    onChange={(e) => updateSimRow(r._rowId, { enable: e.target.checked })}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", textAlign: "right" }}>
                  <button onClick={() => deleteSimRow(r._rowId)}>Delete</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
import { useEffect, useMemo, useRef, useState } from "react";

function makeId() {
  return (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function safeObj(x) {
  return x && typeof x === "object" ? x : {};
}

function toRows(bridgesObj) {
  const obj = safeObj(bridgesObj);

  return Object.entries(obj).map(([name, v]) => ({
    id: makeId(),
    name: String(name),

    layer: v?.layer ?? "",

    // nullable numeric
    viaWidth: v?.ViaWidth ?? null,

    // nullable strings
    viaStackCCW: v?.ViaStackCCW ?? null,
    viaStackCW: v?.ViaStackCW ?? null,
  }));
}

function numOrNull(x) {
  const s = String(x).trim();
  if (s === "") return null;
  const n = Number(s);
  return Number.isNaN(n) ? null : n;
}

export default function Bridges({ draftArtwork, setDraftArtwork, markDirty, resetToken = 0 }) {
  const debounceRef = useRef(null);

  const layerOptions = useMemo(
    () => Object.keys(safeObj(draftArtwork?.layers)).sort(),
    [draftArtwork?.layers]
  );

  const viaPadStackOptions = useMemo(
    () => Object.keys(safeObj(draftArtwork?.viaPadStack)).sort(),
    [draftArtwork?.viaPadStack]
  );

  const [rows, setRows] = useState(() => toRows(draftArtwork?.bridges));

  // Rehydrate ONLY on reset
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    setRows(toRows(draftArtwork?.bridges));
  }, [resetToken]);

  const duplicateNames = useMemo(() => {
    const counts = new Map();
    for (const r of rows) {
      const k = r.name.trim();
      if (!k) continue;
      counts.set(k, (counts.get(k) || 0) + 1);
    }
    return new Set([...counts.entries()].filter(([, c]) => c > 1).map(([k]) => k));
  }, [rows]);

  function addRow() {
    markDirty?.();
    setRows((prev) => [
      ...prev,
      {
        id: makeId(),
        name: "",
        layer: layerOptions[0] ?? "",
        viaWidth: null,
        viaStackCCW: null,
        viaStackCW: null,
      },
    ]);
  }

  function deleteRow(id) {
    markDirty?.();
    setRows((prev) => prev.filter((r) => r.id !== id));
  }

  function updateRow(id, patch) {
    markDirty?.();
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  // rows -> draftArtwork.bridges (debounced)
  useEffect(() => {
    if (duplicateNames.size > 0) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      const next = {};

      for (const r of rows) {
        const name = r.name.trim();
        if (!name) continue;

        next[name] = {
          layer: (r.layer || "").trim(),

          // numeric null when empty
          ViaWidth: r.viaWidth === null ? null : numOrNull(r.viaWidth),

          ViaStackCCW: r.viaStackCCW ? String(r.viaStackCCW) : null,
          ViaStackCW: r.viaStackCW ? String(r.viaStackCW) : null,
        };
      }

      setDraftArtwork?.((prev) => ({
        ...(prev || {}),
        bridges: next,
      }));
    }, 150);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
    };
  }, [rows, duplicateNames, setDraftArtwork, resetToken]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h4>Bridges</h4>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={addRow}>Add bridge</button>
        {layerOptions.length === 0 && (
          <div style={{ opacity: 0.75 }}>
            No layers found (define Layers first).
          </div>
        )}
      </div>

      {duplicateNames.size > 0 && (
        <div style={{ color: "crimson" }}>
          Duplicate bridge name(s): {[...duplicateNames].join(", ")}
        </div>
      )}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Name</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Layer</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>ViaWidth</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>ViaStackCCW</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>ViaStackCW</th>
            <th style={{ padding: 6, borderBottom: "1px solid #ccc" }} />
          </tr>
        </thead>

        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={6} style={{ padding: 8, opacity: 0.7 }}>
                No bridges defined
              </td>
            </tr>
          )}

          {rows.map((r) => {
            const name = r.name.trim();
            const isDup = name && duplicateNames.has(name);

            return (
              <tr key={r.id}>
                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <input
                    value={r.name}
                    onChange={(e) => updateRow(r.id, { name: e.target.value })}
                    placeholder="e.g. B0"
                    style={{ width: "100%", borderColor: isDup ? "crimson" : undefined }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <select
                    value={r.layer}
                    onChange={(e) => updateRow(r.id, { layer: e.target.value })}
                    style={{ width: "100%" }}
                    disabled={layerOptions.length === 0}
                  >
                    <option value="" disabled>
                      {layerOptions.length === 0 ? "No layers" : "Select"}
                    </option>
                    {layerOptions.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <input
                    value={r.viaWidth ?? ""}
                    onChange={(e) => updateRow(r.id, { viaWidth: e.target.value === "" ? null : e.target.value })}
                    placeholder="null"
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <select
                    value={r.viaStackCCW ?? ""}
                    onChange={(e) => updateRow(r.id, { viaStackCCW: e.target.value || null })}
                    style={{ width: "100%" }}
                  >
                    <option value="">None</option>
                    {viaPadStackOptions.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <select
                    value={r.viaStackCW ?? ""}
                    onChange={(e) => updateRow(r.id, { viaStackCW: e.target.value || null })}
                    style={{ width: "100%" }}
                  >
                    <option value="">None</option>
                    {viaPadStackOptions.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", textAlign: "right", verticalAlign: "top" }}>
                  <button onClick={() => deleteRow(r.id)}>Delete</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
import { useEffect, useMemo, useRef, useState } from "react";
import Select from "react-select";

function makeId() {
  return (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function safeObj(x) {
  return x && typeof x === "object" ? x : {};
}

function toRows(vpsObj) {
  const obj = safeObj(vpsObj);

  return Object.entries(obj).map(([name, v]) => ({
    id: makeId(),
    name: String(name),
    topLayer: v?.topLayer ?? "",
    bottomLayer: v?.bottomLayer ?? "",
    margin: v?.margin ?? 0,
    vias: Array.isArray(v?.vias) ? v.vias : [],
  }));
}

function numOrEmpty(x) {
  const s = String(x).trim();
  if (s === "") return "";
  const n = Number(s);
  return Number.isNaN(n) ? "" : n;
}

export default function ViaPadStack({ draftArtwork, setDraftArtwork, markDirty, resetToken = 0 }) {
  const debounceRef = useRef(null);

  const layerOptions = useMemo(
    () => Object.keys(safeObj(draftArtwork?.layers)).sort(),
    [draftArtwork?.layers]
  );

  // react-select options
  const viaOptions = useMemo(() => {
    return Object.keys(safeObj(draftArtwork?.via))
      .sort()
      .map((name) => ({ label: name, value: name }));
  }, [draftArtwork?.via]);

  const [rows, setRows] = useState(() => toRows(draftArtwork?.viaPadStack));

  // Rehydrate ONLY on reset
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    setRows(toRows(draftArtwork?.viaPadStack));
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
        topLayer: layerOptions[0] ?? "",
        bottomLayer: layerOptions[0] ?? "",
        margin: 0,
        vias: [],
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

  // rows -> draftArtwork.viaPadStack (debounced)
  useEffect(() => {
    if (duplicateNames.size > 0) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      const next = {};

      for (const r of rows) {
        const name = r.name.trim();
        if (!name) continue;

        const margin = numOrEmpty(r.margin);

        next[name] = {
          topLayer: (r.topLayer || "").trim(),
          bottomLayer: (r.bottomLayer || "").trim(),
          margin: margin === "" ? 0 : margin,
          vias: Array.isArray(r.vias) ? r.vias.filter(Boolean) : [],
        };
      }

      setDraftArtwork?.((prev) => ({
        ...(prev || {}),
        viaPadStack: next,
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
      <h4>Via Pad Stack</h4>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={addRow}>Add pad stack</button>

        {(layerOptions.length === 0 || viaOptions.length === 0) && (
          <div style={{ opacity: 0.75 }}>
            {layerOptions.length === 0 && "No layers found (define Layers first). "}
            {viaOptions.length === 0 && "No vias found (define Vias first)."}
          </div>
        )}
      </div>

      {duplicateNames.size > 0 && (
        <div style={{ color: "crimson" }}>
          Duplicate pad stack name(s): {[...duplicateNames].join(", ")}
        </div>
      )}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Name</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Top Layer</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Bottom Layer</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Margin</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Vias</th>
            <th style={{ padding: 6, borderBottom: "1px solid #ccc" }} />
          </tr>
        </thead>

        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={6} style={{ padding: 8, opacity: 0.7 }}>
                No via pad stacks defined
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
                    placeholder="e.g. VS_9_8"
                    style={{ width: "100%", borderColor: isDup ? "crimson" : undefined }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <select
                    value={r.topLayer}
                    onChange={(e) => updateRow(r.id, { topLayer: e.target.value })}
                    style={{ width: "100%" }}
                    disabled={layerOptions.length === 0}
                  >
                    <option value="" disabled>
                      {layerOptions.length === 0 ? "No layers" : "Select"}
                    </option>
                    {layerOptions.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <select
                    value={r.bottomLayer}
                    onChange={(e) => updateRow(r.id, { bottomLayer: e.target.value })}
                    style={{ width: "100%" }}
                    disabled={layerOptions.length === 0}
                  >
                    <option value="" disabled>
                      {layerOptions.length === 0 ? "No layers" : "Select"}
                    </option>
                    {layerOptions.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <input
                    value={r.margin}
                    onChange={(e) => updateRow(r.id, { margin: e.target.value })}
                    placeholder="0"
                    style={{ width: "100%" }}
                  />
                </td>

                {/* ✅ react-select multi picker */}
                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top", minWidth: 240 }}>
                  <Select
                    isMulti
                    options={viaOptions}
                    value={
                      Array.isArray(r.vias)
                        ? viaOptions.filter((opt) => r.vias.includes(opt.value))
                        : []
                    }
                    onChange={(selected) => {
                      markDirty?.();
                      const values = Array.isArray(selected)
                        ? selected.map((opt) => opt.value)
                        : [];
                      updateRow(r.id, { vias: values });
                    }}
                    classNamePrefix="select"
                    placeholder="Select vias..."
                  />
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
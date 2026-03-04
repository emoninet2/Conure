import { useEffect, useMemo, useRef, useState } from "react";

function makeId() {
  return (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function safeObj(x) {
  return x && typeof x === "object" ? x : {};
}

function toRows(viaObj) {
  const obj = safeObj(viaObj);

  return Object.entries(obj).map(([name, v]) => ({
    id: makeId(),
    name: String(name),
    length: v?.length ?? "",
    width: v?.width ?? "",
    spacing: v?.spacing ?? "",
    angle: v?.angle ?? "",
    layer: v?.layer ?? "",
  }));
}

function numOrEmpty(x) {
  const s = String(x).trim();
  if (s === "") return "";
  const n = Number(s);
  return Number.isNaN(n) ? "" : n;
}

export default function Vias({ draftArtwork, setDraftArtwork, markDirty, resetToken = 0 }) {
  const debounceRef = useRef(null);

  // dropdown options from artwork.layers (keys)
  const layerOptions = useMemo(() => {
    const layers = safeObj(draftArtwork?.layers);
    return Object.keys(layers).sort();
  }, [draftArtwork?.layers]);

  const [rows, setRows] = useState(() => toRows(draftArtwork?.via));

  // Rehydrate ONLY on reset
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    setRows(toRows(draftArtwork?.via));
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
        length: "",
        width: "",
        spacing: "",
        angle: "",
        layer: layerOptions[0] ?? "",
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

  // rows -> draftArtwork.via (debounced)
  useEffect(() => {
    if (duplicateNames.size > 0) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      const next = {};

      for (const r of rows) {
        const name = r.name.trim();
        if (!name) continue;

        // numbers
        const length = numOrEmpty(r.length);
        const width = numOrEmpty(r.width);
        const spacing = numOrEmpty(r.spacing);
        const angle = numOrEmpty(r.angle);

        // Build object; you can choose to default missing numbers to 0 or skip them.
        // Here we default missing to 0 to match typical schema stability.
        next[name] = {
          length: length === "" ? 0 : length,
          width: width === "" ? 0 : width,
          spacing: spacing === "" ? 0 : spacing,
          angle: angle === "" ? 0 : angle,
          layer: (r.layer || "").trim(),
        };
      }

      setDraftArtwork?.((prev) => ({
        ...(prev || {}),
        via: next,
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
      <h4>Vias</h4>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={addRow}>Add via</button>
        {layerOptions.length === 0 && (
          <div style={{ opacity: 0.75 }}>
            No layers found. Define layers first (Layers tab) to enable the dropdown.
          </div>
        )}
      </div>

      {duplicateNames.size > 0 && (
        <div style={{ color: "crimson" }}>
          Duplicate via name(s): {[...duplicateNames].join(", ")}
        </div>
      )}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Name</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Length</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Width</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Spacing</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Angle</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Layer</th>
            <th style={{ padding: 6, borderBottom: "1px solid #ccc" }} />
          </tr>
        </thead>

        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={7} style={{ padding: 8, opacity: 0.7 }}>
                No vias defined
              </td>
            </tr>
          )}

          {rows.map((r) => {
            const name = r.name.trim();
            const isDup = name && duplicateNames.has(name);

            return (
              <tr key={r.id}>
                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.name}
                    onChange={(e) => updateRow(r.id, { name: e.target.value })}
                    placeholder="e.g. Via8"
                    style={{ width: "100%", borderColor: isDup ? "crimson" : undefined }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.length}
                    onChange={(e) => updateRow(r.id, { length: e.target.value })}
                    placeholder="e.g. 1"
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.width}
                    onChange={(e) => updateRow(r.id, { width: e.target.value })}
                    placeholder="e.g. 1"
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.spacing}
                    onChange={(e) => updateRow(r.id, { spacing: e.target.value })}
                    placeholder="e.g. 0.5"
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.angle}
                    onChange={(e) => updateRow(r.id, { angle: e.target.value })}
                    placeholder="e.g. 0"
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <select
                    value={r.layer}
                    onChange={(e) => updateRow(r.id, { layer: e.target.value })}
                    style={{ width: "100%" }}
                    disabled={layerOptions.length === 0}
                  >
                    <option value="" disabled>
                      {layerOptions.length === 0 ? "No layers" : "Select layer"}
                    </option>
                    {layerOptions.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", textAlign: "right" }}>
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
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

function toRows(armsObj) {
  const obj = safeObj(armsObj);

  return Object.entries(obj).map(([name, v]) => ({
    id: makeId(),
    name: String(name),

    type: v?.type ?? "double",
    length: v?.length ?? "",
    width: v?.width ?? "",
    spacing: v?.spacing ?? "",

    layer: v?.layer ?? "",
    viaStack: v?.viaStack ?? null,

    port: Array.isArray(v?.port) ? v.port : [],
  }));
}

function maxPortsForType(type) {
  return type === "single" ? 1 : 2; // default to double behavior
}

export default function Arms({ draftArtwork, setDraftArtwork, markDirty, resetToken = 0 }) {
  const debounceRef = useRef(null);

  const layerOptions = useMemo(
    () => Object.keys(safeObj(draftArtwork?.layers)).sort(),
    [draftArtwork?.layers]
  );

  const viaStackOptions = useMemo(
    () => Object.keys(safeObj(draftArtwork?.viaPadStack)).sort(),
    [draftArtwork?.viaPadStack]
  );

  const portOptions = useMemo(() => {
    const portNames = Object.keys(safeObj(draftArtwork?.ports?.data)).sort();
    return portNames.map((p) => ({ label: p, value: p }));
  }, [draftArtwork?.ports]);

  const [rows, setRows] = useState(() => toRows(draftArtwork?.arms));

  // Rehydrate ONLY on reset
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    setRows(toRows(draftArtwork?.arms));
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
        type: "double",
        length: "",
        width: "",
        spacing: "",
        layer: layerOptions[0] ?? "",
        viaStack: viaStackOptions[0] ?? null,
        port: [],
      },
    ]);
  }

  function deleteRow(id) {
    markDirty?.();
    setRows((prev) => prev.filter((r) => r.id !== id));
  }

  function updateRow(id, patch) {
    markDirty?.();
    setRows((prev) =>
      prev.map((r) => {
        if (r.id !== id) return r;

        // If changing type, clamp ports immediately
        if (patch.type) {
          const nextType = patch.type;
          const max = maxPortsForType(nextType);
          const nextPorts = Array.isArray(r.port) ? r.port.slice(0, max) : [];
          return { ...r, ...patch, port: nextPorts };
        }

        // If updating port directly somewhere else, also clamp (safe)
        if (patch.port) {
          const max = maxPortsForType(r.type);
          const nextPorts = Array.isArray(patch.port) ? patch.port.slice(0, max) : [];
          return { ...r, ...patch, port: nextPorts };
        }

        return { ...r, ...patch };
      })
    );
  }

  // rows -> draftArtwork.arms (debounced)
  useEffect(() => {
    if (duplicateNames.size > 0) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      const next = {};

      for (const r of rows) {
        const name = r.name.trim();
        if (!name) continue;

        const max = maxPortsForType(r.type);
        const ports = Array.isArray(r.port) ? r.port.filter(Boolean).slice(0, max) : [];

        next[name] = {
          type: r.type || "double",
          length: String(r.length ?? ""),
          width: String(r.width ?? ""),
          spacing: String(r.spacing ?? ""),
          layer: (r.layer || "").trim(),
          viaStack: r.viaStack ? String(r.viaStack) : null,
          port: ports,
        };
      }

      setDraftArtwork?.((prev) => ({
        ...(prev || {}),
        arms: next,
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
      <h4>Arms</h4>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={addRow}>Add arm</button>

        {(layerOptions.length === 0 || portOptions.length === 0) && (
          <div style={{ opacity: 0.75 }}>
            {layerOptions.length === 0 && "No layers found (define Layers first). "}
            {portOptions.length === 0 && "No ports found (define Ports first)."}
          </div>
        )}
      </div>

      {duplicateNames.size > 0 && (
        <div style={{ color: "crimson" }}>
          Duplicate arm name(s): {[...duplicateNames].join(", ")}
        </div>
      )}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Name</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Type</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Length</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Width</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Spacing</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Layer</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>ViaStack</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Ports</th>
            <th style={{ padding: 6, borderBottom: "1px solid #ccc" }} />
          </tr>
        </thead>

        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={9} style={{ padding: 8, opacity: 0.7 }}>
                No arms defined
              </td>
            </tr>
          )}

          {rows.map((r) => {
            const nm = r.name.trim();
            const isDup = nm && duplicateNames.has(nm);
            const maxPorts = maxPortsForType(r.type);
            const selectedPorts = Array.isArray(r.port) ? r.port : [];

            return (
              <tr key={r.id}>
                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <input
                    value={r.name}
                    onChange={(e) => updateRow(r.id, { name: e.target.value })}
                    placeholder="e.g. A0"
                    style={{ width: "100%", borderColor: isDup ? "crimson" : undefined }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <select
                    value={r.type}
                    onChange={(e) => updateRow(r.id, { type: e.target.value })}
                    style={{ width: "100%" }}
                  >
                    <option value="double">double</option>
                    <option value="single">single</option>
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <input
                    value={r.length}
                    onChange={(e) => updateRow(r.id, { length: e.target.value })}
                    placeholder='e.g. guardRingDistance + 20'
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <input
                    value={r.width}
                    onChange={(e) => updateRow(r.id, { width: e.target.value })}
                    placeholder='e.g. width'
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <input
                    value={r.spacing}
                    onChange={(e) => updateRow(r.id, { spacing: e.target.value })}
                    placeholder='e.g. spacing'
                    style={{ width: "100%" }}
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
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <select
                    value={r.viaStack ?? ""}
                    onChange={(e) => updateRow(r.id, { viaStack: e.target.value || null })}
                    style={{ width: "100%" }}
                  >
                    <option value="">None</option>
                    {viaStackOptions.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </td>

                {/* Ports multi-select with max selection */}
                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top", minWidth: 220 }}>
                  <Select
                    isMulti
                    options={portOptions}
                    value={portOptions.filter((opt) => selectedPorts.includes(opt.value))}
                    onChange={(selected) => {
                      markDirty?.();
                      const values = Array.isArray(selected) ? selected.map((opt) => opt.value) : [];
                      updateRow(r.id, { port: values.slice(0, maxPorts) });
                    }}
                    // Disable selecting more once max reached (still allows removing)
                    isOptionDisabled={(opt) =>
                      selectedPorts.length >= maxPorts && !selectedPorts.includes(opt.value)
                    }
                    classNamePrefix="select"
                    placeholder={maxPorts === 1 ? "Select 1 port..." : "Select up to 2 ports..."}
                    isDisabled={portOptions.length === 0}
                  />
                  <div style={{ fontSize: 12, opacity: 0.7, marginTop: 4 }}>
                    Max {maxPorts} port{maxPorts === 1 ? "" : "s"} for type "{r.type}"
                  </div>
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
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

function toRows(layersObj) {
  const obj = safeObj(layersObj);

  return Object.entries(obj).map(([name, data]) => ({
    id: makeId(),
    name,
    layer: data?.gds?.layer ?? "",
    datatype: data?.gds?.datatype ?? "",
  }));
}

export default function Layers({ draftArtwork, setDraftArtwork, markDirty, resetToken = 0 }) {
  const debounceRef = useRef(null);

  const [rows, setRows] = useState(() => toRows(draftArtwork?.layers));

  // Rehydrate ONLY when parent resets
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }

    setRows(toRows(draftArtwork?.layers));
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
        layer: "",
        datatype: "",
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

  // rows -> draftArtwork.layers
  useEffect(() => {
    if (duplicateNames.size > 0) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      const next = {};

      for (const r of rows) {
        const name = r.name.trim();
        if (!name) continue;

        const layer = Number(r.layer);
        const datatype = Number(r.datatype);

        next[name] = {
          gds: {
            layer: Number.isNaN(layer) ? 0 : layer,
            datatype: Number.isNaN(datatype) ? 0 : datatype,
          },
        };
      }

      setDraftArtwork?.((prev) => ({
        ...(prev || {}),
        layers: next,
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
      <h4>Layers</h4>

      <div style={{ display: "flex", gap: 8 }}>
        <AddButton onClick={addRow}>
          Add Layer
        </AddButton>
      </div>

      {duplicateNames.size > 0 && (
        <div style={{ color: "crimson" }}>
          Duplicate layer name(s): {[...duplicateNames].join(", ")}
        </div>
      )}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>
              Name
            </th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>
              GDS Layer
            </th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>
              Datatype
            </th>
            <th style={{ padding: 6, borderBottom: "1px solid #ccc" }} />
          </tr>
        </thead>

        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} style={{ padding: 8, opacity: 0.7 }}>
                No layers defined
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
                    placeholder="e.g. M1"
                    style={{
                      width: "100%",
                      borderColor: isDup ? "crimson" : undefined,
                    }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.layer}
                    onChange={(e) => updateRow(r.id, { layer: e.target.value })}
                    placeholder="e.g. 31"
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.datatype}
                    onChange={(e) => updateRow(r.id, { datatype: e.target.value })}
                    placeholder="e.g. 0"
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
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
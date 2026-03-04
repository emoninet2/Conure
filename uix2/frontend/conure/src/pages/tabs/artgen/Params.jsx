import { useEffect, useMemo, useRef, useState } from "react";

/**
 * Props expected:
 * - draftArtwork: object
 * - setDraftArtwork: fn(updater)
 * - markDirty: fn()
 * - resetToken: number  (increment this in parent when you click Reset / Load)
 */

function makeId() {
  return (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function toRows(parametersObj) {
  const obj = parametersObj && typeof parametersObj === "object" ? parametersObj : {};
  return Object.entries(obj).map(([k, v]) => ({
    id: makeId(),
    key: String(k),
    value: v,
  }));
}

function parseValue(raw) {
  const s = String(raw).trim();
  if (s === "") return "";

  if (s.toLowerCase() === "true") return true;
  if (s.toLowerCase() === "false") return false;

  const n = Number(s);
  if (!Number.isNaN(n) && String(n) === s) return n;

  if ((s.startsWith("{") && s.endsWith("}")) || (s.startsWith("[") && s.endsWith("]"))) {
    try {
      return JSON.parse(s);
    } catch {
      // fall through
    }
  }

  return s;
}

export default function Params({ draftArtwork, setDraftArtwork, markDirty, resetToken = 0 }) {
  const parametersObj = draftArtwork?.parameters || {};

  // Local editable state is the source of truth for the UI
  const [rows, setRows] = useState(() => toRows(parametersObj));

  // Rehydrate ONLY when parent says "reset/reload" via resetToken
  useEffect(() => {
    setRows(toRows(draftArtwork?.parameters || {}));
  }, [resetToken]);

  const duplicateKeys = useMemo(() => {
    const counts = new Map();
    for (const r of rows) {
      const k = r.key.trim();
      if (!k) continue;
      counts.set(k, (counts.get(k) || 0) + 1);
    }
    return new Set([...counts.entries()].filter(([, c]) => c > 1).map(([k]) => k));
  }, [rows]);

  function addRow() {
    markDirty?.();
    setRows((prev) => [...prev, { id: makeId(), key: "", value: "" }]);
  }

  function deleteRow(id) {
    markDirty?.();
    setRows((prev) => prev.filter((r) => r.id !== id));
  }

  function updateRow(id, patch) {
    markDirty?.();
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  // Push rows -> parent draft (debounced) so parent Save always has latest values,
  // without causing focus loss (since we are NOT rehydrating rows on draft changes).
  const debounceRef = useRef(null);
  useEffect(() => {
    if (duplicateKeys.size > 0) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const next = {};
      for (const r of rows) {
        const k = r.key.trim();
        if (!k) continue;
        next[k] = parseValue(r.value);
      }

      setDraftArtwork?.((prev) => ({
        ...(prev || {}),
        parameters: next,
      }));
    }, 150);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [rows, duplicateKeys, setDraftArtwork]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h4>Parameters</h4>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={addRow}>Add row</button>

        {duplicateKeys.size > 0 && (
          <div style={{ color: "crimson" }}>
            Duplicate parameter name(s): {[...duplicateKeys].join(", ")}
          </div>
        )}
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 6 }}>
              Parameter
            </th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 6 }}>
              Value
            </th>
            <th style={{ borderBottom: "1px solid #ccc", padding: 6 }} />
          </tr>
        </thead>

        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={3} style={{ padding: 8, opacity: 0.7 }}>
                No parameters yet. Click “Add row”.
              </td>
            </tr>
          )}

          {rows.map((r) => {
            const k = r.key.trim();
            const isDup = k && duplicateKeys.has(k);

            return (
              <tr key={r.id}>
                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={r.key}
                    onChange={(e) => updateRow(r.id, { key: e.target.value })}
                    placeholder="e.g. corners"
                    style={{ width: "100%", borderColor: isDup ? "crimson" : undefined }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                  <input
                    value={typeof r.value === "string" ? r.value : JSON.stringify(r.value)}
                    onChange={(e) => updateRow(r.id, { value: e.target.value })}
                    placeholder="e.g. 8"
                    style={{ width: "100%" }}
                  />
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
import { useEffect, useMemo, useRef, useState } from "react";

const FIXED_KEYS = ["name", "author", "description", "tags", "version", "date"];

function makeId() {
  return (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function safeObj(x) {
  return x && typeof x === "object" && !Array.isArray(x) ? x : {};
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
    } catch {}
  }

  return s;
}

function toFixedState(metadataObj) {
  const md = safeObj(metadataObj);
  return {
    name: md.name ?? "",
    author: md.author ?? "",
    description: md.description ?? "",
    version: md.version ?? "",
    date: md.date ?? "",
    tagsText: Array.isArray(md.tags) ? md.tags.join(", ") : (md.tags ?? ""),
  };
}

function toCustomRows(metadataObj) {
  const md = safeObj(metadataObj);
  return Object.entries(md)
    .filter(([k]) => !FIXED_KEYS.includes(k))
    .map(([k, v]) => ({
      id: makeId(),
      key: String(k),
      value: v,
    }));
}

export default function Metadata({ draftArtwork, setDraftArtwork, markDirty, resetToken = 0 }) {
  const debounceRef = useRef(null);

  const [fixed, setFixed] = useState(() => toFixedState(draftArtwork?.metadata));
  const [customRows, setCustomRows] = useState(() => toCustomRows(draftArtwork?.metadata));

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    setFixed(toFixedState(draftArtwork?.metadata));
    setCustomRows(toCustomRows(draftArtwork?.metadata));
  }, [resetToken]);

  const duplicateCustomKeys = useMemo(() => {
    const counts = new Map();
    for (const r of customRows) {
      const k = r.key.trim();
      if (!k) continue;
      counts.set(k, (counts.get(k) || 0) + 1);
    }
    return new Set([...counts.entries()].filter(([, c]) => c > 1).map(([k]) => k));
  }, [customRows]);

  const reservedCollisions = useMemo(() => {
    const collisions = new Set();
    for (const r of customRows) {
      const k = r.key.trim();
      if (!k) continue;
      if (FIXED_KEYS.includes(k)) collisions.add(k);
    }
    return collisions;
  }, [customRows]);

  const nameMissing = fixed.name.trim() === "";

  function updateFixedField(key, value) {
    markDirty?.();
    setFixed((prev) => ({ ...prev, [key]: value }));
  }

  function addCustomRow() {
    markDirty?.();
    setCustomRows((prev) => [...prev, { id: makeId(), key: "", value: "" }]);
  }

  function deleteCustomRow(id) {
    markDirty?.();
    setCustomRows((prev) => prev.filter((r) => r.id !== id));
  }

  function updateCustomRow(id, patch) {
    markDirty?.();
    setCustomRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  useEffect(() => {
    if (nameMissing) return;
    if (duplicateCustomKeys.size > 0) return;
    if (reservedCollisions.size > 0) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      const md = {};

      md.name = fixed.name.trim();

      const author = fixed.author.trim();
      if (author) md.author = author;

      const version = fixed.version.trim();
      if (version) md.version = version;

      const date = fixed.date.trim();
      if (date) md.date = date;

      const description = fixed.description.trim();
      if (description) md.description = description;

      const tagsArr = String(fixed.tagsText || "")
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      if (tagsArr.length > 0) md.tags = tagsArr;

      for (const r of customRows) {
        const k = r.key.trim();
        if (!k) continue;

        const v = parseValue(r.value);
        if (v === "") continue;
        md[k] = v;
      }

      setDraftArtwork?.((prev) => ({
        ...(prev || {}),
        metadata: md,
      }));
    }, 150);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
    };
  }, [
    fixed,
    customRows,
    nameMissing,
    duplicateCustomKeys,
    reservedCollisions,
    setDraftArtwork,
    resetToken,
  ]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <h4>Metadata</h4>

      <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: 10, alignItems: "center" }}>
        <label>Name *</label>
        <input
          value={fixed.name}
          onChange={(e) => updateFixedField("name", e.target.value)}
          placeholder="Required"
          style={{ borderColor: nameMissing ? "crimson" : undefined }}
        />

        <label>Author</label>
        <input
          value={fixed.author}
          onChange={(e) => updateFixedField("author", e.target.value)}
          placeholder="Optional"
        />

        <label>Version</label>
        <input
          value={fixed.version}
          onChange={(e) => updateFixedField("version", e.target.value)}
          placeholder="Optional"
        />

        <label>Date</label>
        <input
          value={fixed.date}
          onChange={(e) => updateFixedField("date", e.target.value)}
          placeholder="Optional"
        />

        <label>Tags</label>
        <input
          value={fixed.tagsText}
          onChange={(e) => updateFixedField("tagsText", e.target.value)}
          placeholder="Optional (comma-separated)"
        />

        <label>Description</label>
        <textarea
          value={fixed.description}
          onChange={(e) => updateFixedField("description", e.target.value)}
          placeholder="Optional"
          rows={4}
          style={{ resize: "vertical" }}
        />
      </div>

      {nameMissing && <div style={{ color: "crimson" }}>Name is required.</div>}

      <div style={{ marginTop: 6 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <h5 style={{ margin: 0 }}>Custom metadata</h5>
          <button onClick={addCustomRow}>Add row</button>
        </div>

        {(duplicateCustomKeys.size > 0 || reservedCollisions.size > 0) && (
          <div style={{ color: "crimson", marginTop: 8 }}>
            {duplicateCustomKeys.size > 0 && <div>Duplicate key(s): {[...duplicateCustomKeys].join(", ")}</div>}
            {reservedCollisions.size > 0 && (
              <div>Reserved key(s): {[...reservedCollisions].join(", ")} (used by fixed fields)</div>
            )}
          </div>
        )}

        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 10 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 6 }}>Key</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 6 }}>Value</th>
              <th style={{ borderBottom: "1px solid #ccc", padding: 6 }} />
            </tr>
          </thead>

          <tbody>
            {customRows.length === 0 && (
              <tr>
                <td colSpan={3} style={{ padding: 8, opacity: 0.7 }}>
                  No custom metadata yet.
                </td>
              </tr>
            )}

            {customRows.map((r) => {
              const k = r.key.trim();
              const isDup = k && duplicateCustomKeys.has(k);
              const isReserved = k && reservedCollisions.has(k);

              return (
                <tr key={r.id}>
                  <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                    <input
                      value={r.key}
                      onChange={(e) => updateCustomRow(r.id, { key: e.target.value })}
                      placeholder="e.g. material"
                      style={{ width: "100%", borderColor: isDup || isReserved ? "crimson" : undefined }}
                    />
                  </td>

                  <td style={{ padding: 6, borderBottom: "1px solid #eee" }}>
                    <input
                      value={typeof r.value === "string" ? r.value : JSON.stringify(r.value)}
                      onChange={(e) => updateCustomRow(r.id, { value: e.target.value })}
                      placeholder='e.g. "copper" or 0.2 or true'
                      style={{ width: "100%" }}
                    />
                  </td>

                  <td style={{ padding: 6, borderBottom: "1px solid #eee", textAlign: "right" }}>
                    <button onClick={() => deleteCustomRow(r.id)}>Delete</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
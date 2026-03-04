import { useEffect, useMemo, useRef, useState } from "react";

function safeObj(x) {
  return x && typeof x === "object" ? x : {};
}

function clampInt(n, fallback) {
  const v = Number(n);
  if (!Number.isFinite(v)) return fallback;
  const i = Math.trunc(v);
  return i > 0 ? i : fallback;
}

const SEGMENT_KEYS = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"];
const SEGMENT_LABELS = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"];

function normalizeEntry(raw, defaultLayer) {
  const type = raw?.type ?? "DEFAULT";
  const data = raw?.data ?? {};

  return {
    type,
    layer: data?.layer ?? defaultLayer ?? "",
    arm: data?.arm ?? "",
    bridge: data?.bridge ?? "",
    jump: typeof data?.jump === "number" ? data.jump : (data?.jump ?? 0),
  };
}

function makeDefaultEntry(defaultLayer) {
  return { type: "DEFAULT", layer: defaultLayer ?? "", arm: "", bridge: "", jump: 0 };
}

function toStateFromSegments(segmentsObj, ringsCount, defaultLayer) {
  const seg = safeObj(segmentsObj);
  const data = safeObj(seg.data);

  const groups = SEGMENT_KEYS.map((k) => {
    const group = Array.isArray(data?.[k]?.group) ? data[k].group : [];
    const normalized = group.map((g) => normalizeEntry(g, defaultLayer));

    // resize to ringsCount
    if (normalized.length < ringsCount) {
      return normalized.concat(
        Array.from({ length: ringsCount - normalized.length }, () => makeDefaultEntry(defaultLayer))
      );
    }
    if (normalized.length > ringsCount) {
      return normalized.slice(0, ringsCount);
    }
    return normalized;
  });

  const bridge_extension_aligned =
    typeof seg?.config?.bridge_extension_aligned === "boolean"
      ? seg.config.bridge_extension_aligned
      : true;

  return { bridge_extension_aligned, groups };
}

function buildSegmentsJson({ bridge_extension_aligned, groups }) {
  const data = {};
  for (let i = 0; i < 8; i++) {
    const key = SEGMENT_KEYS[i];
    const groupArr = Array.isArray(groups?.[i]) ? groups[i] : [];

    data[key] = {
      id: i, // ✅ derived, not editable
      group: groupArr.map((e) => {
        const type = e.type || "DEFAULT";
        const layer = (e.layer || "").trim();

        if (type === "PORT") {
          return {
            type: "PORT",
            data: {
              layer,
              arm: (e.arm || "").trim(),
            },
          };
        }

        if (type === "BRIDGE") {
          const jumpNum = Number(e.jump);
          return {
            type: "BRIDGE",
            data: {
              layer,
              bridge: (e.bridge || "").trim(),
              jump: Number.isFinite(jumpNum) ? jumpNum : 0,
            },
          };
        }

        return {
          type: "DEFAULT",
          data: { layer },
        };
      }),
    };
  }

  return {
    config: { bridge_extension_aligned: !!bridge_extension_aligned },
    data,
  };
}

export default function Segments({ draftArtwork, setDraftArtwork, markDirty, resetToken = 0 }) {
  const debounceRef = useRef(null);

  const layerOptions = useMemo(
    () => Object.keys(safeObj(draftArtwork?.layers)).sort(),
    [draftArtwork?.layers]
  );
  const armOptions = useMemo(
    () => Object.keys(safeObj(draftArtwork?.arms)).sort(),
    [draftArtwork?.arms]
  );
  const bridgeOptions = useMemo(
    () => Object.keys(safeObj(draftArtwork?.bridges)).sort(),
    [draftArtwork?.bridges]
  );

  const defaultLayer = layerOptions[0] ?? "M9";

  // Rings count:
  // - prefer artwork.parameters.rings if present
  // - else infer from existing segments groups
  // - else default to 2
  const ringsFromParams = useMemo(() => {
    const r = draftArtwork?.parameters?.rings;
    return typeof r === "number" ? clampInt(r, 0) : 0;
  }, [draftArtwork?.parameters]);

  const ringsFromData = useMemo(() => {
    const seg = safeObj(draftArtwork?.segments);
    const data = safeObj(seg.data);
    let mx = 0;
    for (const k of SEGMENT_KEYS) {
      const g = data?.[k]?.group;
      if (Array.isArray(g)) mx = Math.max(mx, g.length);
    }
    return mx;
  }, [draftArtwork?.segments]);

  const initialRings = clampInt(ringsFromParams || ringsFromData || 2, 2);

  const [ringsCount, setRingsCount] = useState(initialRings);

  const [bridgeExtensionAligned, setBridgeExtensionAligned] = useState(true);
  const [groups, setGroups] = useState(() =>
    toStateFromSegments(draftArtwork?.segments, initialRings, defaultLayer).groups
  );

  // Rehydrate ONLY on reset
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }

    const nextRings = clampInt(ringsFromParams || ringsFromData || 2, 2);
    setRingsCount(nextRings);

    const state = toStateFromSegments(draftArtwork?.segments, nextRings, defaultLayer);
    setBridgeExtensionAligned(state.bridge_extension_aligned);
    setGroups(state.groups);
  }, [resetToken]); // important

  function resizeAllSegments(nextRings) {
    markDirty?.();
    setRingsCount(nextRings);

    setGroups((prev) => {
      const out = [];
      for (let s = 0; s < 8; s++) {
        const cur = Array.isArray(prev?.[s]) ? prev[s] : [];
        if (cur.length < nextRings) {
          out[s] = cur.concat(
            Array.from({ length: nextRings - cur.length }, () => makeDefaultEntry(defaultLayer))
          );
        } else if (cur.length > nextRings) {
          out[s] = cur.slice(0, nextRings);
        } else {
          out[s] = cur;
        }
      }
      return out;
    });
  }

  function updateEntry(segIndex, ringIndex, patch) {
    markDirty?.();
    setGroups((prev) => {
      const next = prev.map((g) => g.slice());
      const entry = { ...(next[segIndex]?.[ringIndex] ?? makeDefaultEntry(defaultLayer)) };

      // If switching type, clear irrelevant fields
      if (patch.type && patch.type !== entry.type) {
        if (patch.type === "DEFAULT") {
          entry.arm = "";
          entry.bridge = "";
          entry.jump = 0;
        } else if (patch.type === "PORT") {
          entry.bridge = "";
          entry.jump = 0;
        } else if (patch.type === "BRIDGE") {
          entry.arm = "";
        }
      }

      Object.assign(entry, patch);

      // ensure layer always present
      if (!entry.layer) entry.layer = defaultLayer;

      next[segIndex][ringIndex] = entry;
      return next;
    });
  }

  // Push -> draftArtwork.segments (debounced)
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      const nextSegments = buildSegmentsJson({
        bridge_extension_aligned: bridgeExtensionAligned,
        groups,
      });

      setDraftArtwork?.((prev) => ({
        ...(prev || {}),
        segments: nextSegments,
      }));
    }, 150);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
    };
  }, [bridgeExtensionAligned, groups, setDraftArtwork, resetToken]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <h4>Segments</h4>

      <div style={{ display: "flex", gap: 14, flexWrap: "wrap", alignItems: "center" }}>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={!!bridgeExtensionAligned}
            onChange={(e) => {
              markDirty?.();
              setBridgeExtensionAligned(e.target.checked);
            }}
          />
          bridge_extension_aligned
        </label>

        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          Rings per segment:
          <input
            value={ringsCount}
            onChange={(e) => resizeAllSegments(clampInt(e.target.value, ringsCount))}
            style={{ width: 70 }}
          />
        </label>

        <div style={{ opacity: 0.75 }}>
          (8 segments × {ringsCount} ring rows)
        </div>
      </div>

      {layerOptions.length === 0 && (
        <div style={{ opacity: 0.75 }}>
          No layers found (define Layers first) — layer dropdown will be empty.
        </div>
      )}

      {/* 8 segment tables */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 16 }}>
        {SEGMENT_KEYS.map((segKey, segIndex) => {
          const segLabel = SEGMENT_LABELS[segIndex];
          const segGroup = groups?.[segIndex] ?? [];

          return (
            <div key={segKey} style={{ border: "1px solid #ccc", padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                <div style={{ fontWeight: 600 }}>
                  {segKey} ({segLabel})
                </div>
                <div style={{ opacity: 0.7, fontSize: 12 }}>id = {segIndex}</div>
              </div>

              <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 10 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ddd" }}>
                      Ring
                    </th>
                    <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ddd" }}>
                      Type
                    </th>
                    <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ddd" }}>
                      Layer
                    </th>
                    <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ddd" }}>
                      Arm (PORT)
                    </th>
                    <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ddd" }}>
                      Bridge (BRIDGE)
                    </th>
                    <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ddd" }}>
                      Jump (BRIDGE)
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {Array.from({ length: ringsCount }).map((_, ringIndex) => {
                    const e = segGroup[ringIndex] ?? makeDefaultEntry(defaultLayer);
                    const isPort = e.type === "PORT";
                    const isBridge = e.type === "BRIDGE";

                    return (
                      <tr key={`${segKey}-r${ringIndex}`}>
                        <td style={{ padding: 6, borderBottom: "1px solid #eee", width: 70 }}>
                          {ringIndex + 1}
                        </td>

                        <td style={{ padding: 6, borderBottom: "1px solid #eee", width: 130 }}>
                          <select
                            value={e.type}
                            onChange={(ev) => updateEntry(segIndex, ringIndex, { type: ev.target.value })}
                            style={{ width: "100%" }}
                          >
                            <option value="DEFAULT">DEFAULT</option>
                            <option value="PORT">PORT</option>
                            <option value="BRIDGE">BRIDGE</option>
                          </select>
                        </td>

                        <td style={{ padding: 6, borderBottom: "1px solid #eee", width: 150 }}>
                          <select
                            value={e.layer}
                            onChange={(ev) => updateEntry(segIndex, ringIndex, { layer: ev.target.value })}
                            style={{ width: "100%" }}
                            disabled={layerOptions.length === 0}
                          >
                            {layerOptions.length === 0 ? (
                              <option value={e.layer}>{e.layer || "No layers"}</option>
                            ) : (
                              layerOptions.map((opt) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))
                            )}
                          </select>
                        </td>

                        <td style={{ padding: 6, borderBottom: "1px solid #eee", width: 160 }}>
                          <select
                            value={e.arm || ""}
                            onChange={(ev) => updateEntry(segIndex, ringIndex, { arm: ev.target.value })}
                            style={{ width: "100%" }}
                            disabled={!isPort || armOptions.length === 0}
                          >
                            <option value="">
                              {!isPort ? "—" : armOptions.length === 0 ? "No arms" : "Select"}
                            </option>
                            {isPort &&
                              armOptions.map((opt) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))}
                          </select>
                        </td>

                        <td style={{ padding: 6, borderBottom: "1px solid #eee", width: 160 }}>
                          <select
                            value={e.bridge || ""}
                            onChange={(ev) => updateEntry(segIndex, ringIndex, { bridge: ev.target.value })}
                            style={{ width: "100%" }}
                            disabled={!isBridge || bridgeOptions.length === 0}
                          >
                            <option value="">
                              {!isBridge ? "—" : bridgeOptions.length === 0 ? "No bridges" : "Select"}
                            </option>
                            {isBridge &&
                              bridgeOptions.map((opt) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))}
                          </select>
                        </td>

                        <td style={{ padding: 6, borderBottom: "1px solid #eee", width: 120 }}>
                          <input
                            value={isBridge ? String(e.jump ?? 0) : ""}
                            onChange={(ev) => updateEntry(segIndex, ringIndex, { jump: ev.target.value })}
                            placeholder={isBridge ? "e.g. 1" : "—"}
                            style={{ width: "100%" }}
                            disabled={!isBridge}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>
    </div>
  );
}
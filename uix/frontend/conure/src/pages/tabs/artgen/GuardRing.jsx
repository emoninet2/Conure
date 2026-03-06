import { useEffect, useMemo, useRef, useState } from "react";
import Select from "react-select";
import AddButton from "../../../components/AddButton";


function makeId() {
  return (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random()}`;
}

function safeObj(x) {
  return x && typeof x === "object" ? x : {};
}

function parseNumOrString(v) {
  const s = String(v ?? "").trim();
  if (s === "") return "";
  const n = Number(s);
  return Number.isNaN(n) ? s : n;
}

const SEGMENT_OPTIONS = [
  { value: "0", label: "0 (E)" },
  { value: "1", label: "1 (NE)" },
  { value: "2", label: "2 (N)" },
  { value: "3", label: "3 (NW)" },
  { value: "4", label: "4 (W)" },
  { value: "5", label: "5 (SW)" },
  { value: "6", label: "6 (S)" },
  { value: "7", label: "7 (SE)" },
];

function toGuardRingState(grObj) {
  const gr = safeObj(grObj);
  const config = safeObj(gr.config);
  const data = safeObj(gr.data);

  const segmentsObj = safeObj(data.segments);
  const segmentsRows = Object.entries(segmentsObj).map(([name, seg]) => ({
    id: makeId(),
    name: String(name),
    shape: seg?.shape ?? "octagon",
    offset: seg?.offset ?? 0,
    layer: seg?.layer ?? "",
    width: seg?.width ?? "",

    contactsUse: !!seg?.contacts?.use,
    contactsViaStack: seg?.contacts?.viaStack ?? "",

    partialUse: !!seg?.partialCut?.use,
    partialSegment: seg?.partialCut?.segment ?? "",
    partialSpacing: seg?.partialCut?.spacing ?? "",
  }));

  const dummy = safeObj(data.dummyFills);
  const dummyItemsObj = safeObj(dummy.items);
  const dummyItemRows = Object.entries(dummyItemsObj).map(([name, item]) => ({
    id: makeId(),
    name: String(name),
    shape: "rect",
    length: item?.length ?? "",
    height: item?.height ?? "",
    offsetX: item?.offsetX ?? "",
    offsetY: item?.offsetY ?? "",
    layers: Array.isArray(item?.layers) ? item.layers : [],
  }));

  return {
    useGuardRing: typeof config.useGuardRing === "boolean" ? config.useGuardRing : true,
    distance: data?.distance ?? "guardRingDistance",

    segmentsRows,

    dummyType: "checkered",
    dummyGroupSpacing: dummy?.groupSpacing ?? 2,
    dummyItemRows,
  };
}

export default function GuardRing({ draftArtwork, setDraftArtwork, markDirty, resetToken = 0 }) {
  const debounceRef = useRef(null);

  const layerOptions = useMemo(
    () => Object.keys(safeObj(draftArtwork?.layers)).sort(),
    [draftArtwork?.layers]
  );

  const layerSelectOptions = useMemo(
    () => layerOptions.map((l) => ({ label: l, value: l })),
    [layerOptions]
  );

  const viaStackOptions = useMemo(
    () => Object.keys(safeObj(draftArtwork?.viaPadStack)).sort(),
    [draftArtwork?.viaPadStack]
  );

  const [useGuardRing, setUseGuardRing] = useState(true);
  const [distance, setDistance] = useState("guardRingDistance");

  const [segmentsRows, setSegmentsRows] = useState([]);
  const [dummyGroupSpacing, setDummyGroupSpacing] = useState(2);
  const [dummyItemRows, setDummyItemRows] = useState([]);

  // Rehydrate ONLY on reset
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }

    const st = toGuardRingState(draftArtwork?.guardRing);

    setUseGuardRing(st.useGuardRing);
    setDistance(st.distance);

    setSegmentsRows(st.segmentsRows);
    setDummyGroupSpacing(st.dummyGroupSpacing ?? 2);

    // enforce dummy shape rect
    setDummyItemRows((st.dummyItemRows || []).map((r) => ({ ...r, shape: "rect" })));
  }, [resetToken]);

  // -------- Segments table handlers --------
  function addSegment() {
    markDirty?.();
    setSegmentsRows((prev) => [
      ...prev,
      {
        id: makeId(),
        name: "",
        shape: "octagon",
        offset: 0,
        layer: layerOptions[0] ?? "",
        width: "",
        contactsUse: false,
        contactsViaStack: viaStackOptions[0] ?? "",
        partialUse: false,
        partialSegment: "",
        partialSpacing: "",
      },
    ]);
  }

  function deleteSegment(id) {
    markDirty?.();
    setSegmentsRows((prev) => prev.filter((r) => r.id !== id));
  }

  function updateSegment(id, patch) {
    markDirty?.();
    setSegmentsRows((prev) =>
      prev.map((r) => {
        if (r.id !== id) return r;
        const next = { ...r, ...patch };

        // enforce allowed shapes
        if (next.shape !== "octagon" && next.shape !== "octagonRing") {
          next.shape = "octagon";
        }
        return next;
      })
    );
  }

  // -------- Dummy fills items handlers --------
  function addDummyItem() {
    markDirty?.();
    setDummyItemRows((prev) => [
      ...prev,
      {
        id: makeId(),
        name: "",
        shape: "rect",
        length: "",
        height: "",
        offsetX: "",
        offsetY: "",
        layers: [],
      },
    ]);
  }

  function deleteDummyItem(id) {
    markDirty?.();
    setDummyItemRows((prev) => prev.filter((r) => r.id !== id));
  }

  function updateDummyItem(id, patch) {
    markDirty?.();
    setDummyItemRows((prev) =>
      prev.map((r) => {
        if (r.id !== id) return r;
        const next = { ...r, ...patch };
        next.shape = "rect"; // enforce only option for now
        return next;
      })
    );
  }

  // -------- Push to draftArtwork.guardRing (debounced) --------
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(() => {
      const segments = {};
      for (const r of segmentsRows) {
        const name = r.name.trim();
        if (!name) continue;

        const seg = {
          shape: r.shape === "octagonRing" ? "octagonRing" : "octagon",
          offset: parseNumOrString(r.offset),
          layer: (r.layer || "").trim(),
        };

        if (String(r.width ?? "").trim() !== "") seg.width = parseNumOrString(r.width);

        if (r.contactsUse) {
          seg.contacts = {
            use: true,
            viaStack: (r.contactsViaStack || "").trim(),
          };
        }

        if (r.partialUse) {
          seg.partialCut = {
            use: true,
            segment: String(r.partialSegment ?? "").trim(), // "0".."7"
            spacing: String(r.partialSpacing ?? "").trim(),
          };
        }

        segments[name] = seg;
      }

      const items = {};
      for (const r of dummyItemRows) {
        const name = r.name.trim();
        if (!name) continue;

        items[name] = {
          shape: "rect",
          length: parseNumOrString(r.length),
          height: parseNumOrString(r.height),
          offsetX: parseNumOrString(r.offsetX),
          offsetY: parseNumOrString(r.offsetY),
          layers: Array.isArray(r.layers) ? r.layers.filter(Boolean) : [],
        };
      }

      const nextGuardRing = {
        config: { useGuardRing: !!useGuardRing },
        data: {
          distance: String(distance ?? "").trim(),
          segments,
          dummyFills: {
            type: "checkered",
            groupSpacing: parseNumOrString(dummyGroupSpacing),
            items,
          },
        },
      };

      setDraftArtwork?.((prev) => ({
        ...(prev || {}),
        guardRing: nextGuardRing,
      }));
    }, 150);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
    };
  }, [
    useGuardRing,
    distance,
    segmentsRows,
    dummyGroupSpacing,
    dummyItemRows,
    setDraftArtwork,
    resetToken,
  ]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <h4>Guard Ring</h4>

      {/* Config */}
      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={!!useGuardRing}
            onChange={(e) => {
              markDirty?.();
              setUseGuardRing(e.target.checked);
            }}
          />
          useGuardRing
        </label>

        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          distance:
          <input
            value={distance}
            onChange={(e) => {
              markDirty?.();
              setDistance(e.target.value);
            }}
            placeholder="guardRingDistance"
            style={{ minWidth: 240 }}
          />
        </label>
      </div>

      {/* Segments table */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <h5 style={{ margin: 0 }}>Segments (data.segments)</h5>

        <AddButton onClick={addSegment}>
          Add segment
        </AddButton>


      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Name</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Shape</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Offset</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Layer</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Width</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Contacts</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Partial Cut</th>
            <th style={{ padding: 6, borderBottom: "1px solid #ccc" }} />
          </tr>
        </thead>

        <tbody>
          {segmentsRows.length === 0 && (
            <tr>
              <td colSpan={8} style={{ padding: 8, opacity: 0.7 }}>
                No guard ring segments yet.
              </td>
            </tr>
          )}

          {segmentsRows.map((r) => {
            const isRing = r.shape === "octagonRing";

            return (
              <tr key={r.id}>
                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <input
                    value={r.name}
                    onChange={(e) => updateSegment(r.id, { name: e.target.value })}
                    placeholder="e.g. OD"
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <select
                    value={r.shape}
                    onChange={(e) => updateSegment(r.id, { shape: e.target.value })}
                    style={{ width: "100%" }}
                  >
                    <option value="octagon">octagon</option>
                    <option value="octagonRing">octagonRing</option>
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <input
                    value={r.offset}
                    onChange={(e) => updateSegment(r.id, { offset: e.target.value })}
                    placeholder="e.g. -0.5"
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                  <select
                    value={r.layer}
                    onChange={(e) => updateSegment(r.id, { layer: e.target.value })}
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
                    value={r.width}
                    onChange={(e) => updateSegment(r.id, { width: e.target.value })}
                    placeholder={isRing ? "e.g. 4" : "(optional)"}
                    style={{ width: "100%" }}
                  />
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top", minWidth: 220 }}>
                  <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="checkbox"
                      checked={!!r.contactsUse}
                      onChange={(e) => updateSegment(r.id, { contactsUse: e.target.checked })}
                    />
                    use
                  </label>

                  <select
                    value={r.contactsViaStack}
                    onChange={(e) => updateSegment(r.id, { contactsViaStack: e.target.value })}
                    style={{ width: "100%", marginTop: 6 }}
                    disabled={!r.contactsUse || viaStackOptions.length === 0}
                  >
                    <option value="">
                      {!r.contactsUse ? "—" : viaStackOptions.length === 0 ? "No via stacks" : "Select viaStack"}
                    </option>
                    {viaStackOptions.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top", minWidth: 220 }}>
                  <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="checkbox"
                      checked={!!r.partialUse}
                      onChange={(e) => updateSegment(r.id, { partialUse: e.target.checked })}
                    />
                    use
                  </label>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginTop: 6 }}>
                    <select
                      value={r.partialSegment}
                      onChange={(e) => updateSegment(r.id, { partialSegment: e.target.value })}
                      disabled={!r.partialUse}
                    >
                      <option value="">
                        {!r.partialUse ? "—" : "Select segment"}
                      </option>
                      {SEGMENT_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>

                    <input
                      value={r.partialSpacing}
                      onChange={(e) => updateSegment(r.id, { partialSpacing: e.target.value })}
                      placeholder="spacing (e.g. 10)"
                      disabled={!r.partialUse}
                    />
                  </div>
                </td>

                <td style={{ padding: 6, borderBottom: "1px solid #eee", textAlign: "right", verticalAlign: "top" }}>
                  <button onClick={() => deleteSegment(r.id)}>Delete</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Dummy fills */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <h5 style={{ margin: 0 }}>Dummy Fills (data.dummyFills)</h5>

      <AddButton onClick={addDummyItem}>
        Add dummy Element
      </AddButton>


      </div>

      <div style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          type:
          <select value="checkered" disabled onChange={() => {}}>
            <option value="checkered">checkered</option>
          </select>
        </label>

        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          groupSpacing:
          <input
            value={dummyGroupSpacing}
            onChange={(e) => {
              markDirty?.();
              setDummyGroupSpacing(e.target.value);
            }}
            placeholder="2"
            style={{ width: 90 }}
          />
        </label>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Name</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Shape</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Length</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Height</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>OffsetX</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>OffsetY</th>
            <th style={{ textAlign: "left", padding: 6, borderBottom: "1px solid #ccc" }}>Layers</th>
            <th style={{ padding: 6, borderBottom: "1px solid #ccc" }} />
          </tr>
        </thead>

        <tbody>
          {dummyItemRows.length === 0 && (
            <tr>
              <td colSpan={8} style={{ padding: 8, opacity: 0.7 }}>
                No dummy fill items yet.
              </td>
            </tr>
          )}

          {dummyItemRows.map((r) => (
            <tr key={r.id}>
              <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                <input
                  value={r.name}
                  onChange={(e) => updateDummyItem(r.id, { name: e.target.value })}
                  placeholder="e.g. rect0"
                  style={{ width: "100%" }}
                />
              </td>

              <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                <select value="rect" disabled style={{ width: "100%" }}>
                  <option value="rect">rect</option>
                </select>
              </td>

              <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                <input
                  value={r.length}
                  onChange={(e) => updateDummyItem(r.id, { length: e.target.value })}
                  placeholder="e.g. 3"
                  style={{ width: "100%" }}
                />
              </td>

              <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                <input
                  value={r.height}
                  onChange={(e) => updateDummyItem(r.id, { height: e.target.value })}
                  placeholder="e.g. 3"
                  style={{ width: "100%" }}
                />
              </td>

              <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                <input
                  value={r.offsetX}
                  onChange={(e) => updateDummyItem(r.id, { offsetX: e.target.value })}
                  placeholder="e.g. 0"
                  style={{ width: "100%" }}
                />
              </td>

              <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top" }}>
                <input
                  value={r.offsetY}
                  onChange={(e) => updateDummyItem(r.id, { offsetY: e.target.value })}
                  placeholder="e.g. -2"
                  style={{ width: "100%" }}
                />
              </td>

              <td style={{ padding: 6, borderBottom: "1px solid #eee", verticalAlign: "top", minWidth: 260 }}>
                <Select
                  isMulti
                  options={layerSelectOptions}
                  value={
                    Array.isArray(r.layers)
                      ? layerSelectOptions.filter((opt) => r.layers.includes(opt.value))
                      : []
                  }
                  onChange={(selected) => {
                    markDirty?.();
                    const values = Array.isArray(selected) ? selected.map((o) => o.value) : [];
                    updateDummyItem(r.id, { layers: values });
                  }}
                  classNamePrefix="select"
                  placeholder="Select layers..."
                  isDisabled={layerSelectOptions.length === 0}
                />
              </td>

              <td style={{ padding: 6, borderBottom: "1px solid #eee", textAlign: "right", verticalAlign: "top" }}>
                <button onClick={() => deleteDummyItem(r.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {layerOptions.length === 0 && (
        <div style={{ opacity: 0.75 }}>
          No layers found (define Layers first) — layer selection will be empty.
        </div>
      )}
    </div>
  );
}
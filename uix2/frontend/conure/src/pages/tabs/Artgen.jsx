import { useEffect, useMemo, useRef, useState } from "react";
import { useUiStore } from "../../state/uiStore";

import Metadata from "./artgen/Metadata";
import Params from "./artgen/Params";
import Seg from "./artgen/Seg";
import Arms from "./artgen/Arms";
import Ports from "./artgen/Ports";
import Bridges from "./artgen/Bridges";
import ViaPadStack from "./artgen/ViaPadStack";
import Vias from "./artgen/Vias";
import Layers from "./artgen/Layers";
import GuardRing from "./artgen/GuardRing";
import Preview from "./artgen/Preview";

const ARTGEN_TABS = [
  { key: "metadata", label: "Metadata" },
  { key: "params", label: "Parameters" },
  { key: "layers", label: "Layers" },
  { key: "vias", label: "Vias" },
  { key: "viaPadStack", label: "Via Pad Stack" },
  { key: "bridges", label: "Bridges" },
  { key: "ports", label: "Ports" },
  { key: "arms", label: "Arms" },
  { key: "seg", label: "Segments" },
  { key: "guardRing", label: "Guard Ring" },
  { key: "preview", label: "Preview" },
];

const ARTWORK_PATH = ["artwork"];

export default function Artgen() {
  const setValue = useUiStore((s) => s.setValue);

  const fileInputRef = useRef(null);

  // active artgen subtab stored in backend
  const active = useUiStore((s) =>
    s.getValue(["nav", "home", "artgen", "tab"], "metadata")
  );

  // ✅ last SAVED artwork from store (stable string)
  const savedArtworkJson = useUiStore((s) => {
    const obj = s.getValue(ARTWORK_PATH, null) || {};
    try {
      return JSON.stringify(obj);
    } catch {
      return "{}";
    }
  });

  const savedArtwork = useMemo(() => {
    try {
      return JSON.parse(savedArtworkJson);
    } catch {
      return {};
    }
  }, [savedArtworkJson]);

  const [draftArtwork, setDraftArtwork] = useState(() => savedArtwork);
  const [dirty, setDirty] = useState(false);
  const [resetToken, setResetToken] = useState(0);

  // If store reloads from backend and user isn't editing, refresh draft
  useEffect(() => {
    if (!dirty) {
      setDraftArtwork(savedArtwork);
      setResetToken((t) => t + 1);
    }
  }, [savedArtworkJson]); // stable dependency

  function saveAll() {
    setValue(ARTWORK_PATH, draftArtwork);
    setDirty(false);
  }

  function resetAll() {
    setDraftArtwork(savedArtwork);
    setDirty(false);
    setResetToken((t) => t + 1);
  }

  function downloadArtwork() {
    const pretty = JSON.stringify(savedArtwork, null, 2);
    const blob = new Blob([pretty], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;

    const ts = new Date().toISOString().replaceAll(":", "-");
    a.download = `artwork-${ts}.json`;

    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
  }

  function uploadArtworkClick() {
    fileInputRef.current?.click();
  }

  async function onUploadFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const parsed = JSON.parse(text);

      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        alert("Invalid file: expected a JSON object at the root.");
        return;
      }

      // Load into draft + persist to backend/store
      setDraftArtwork(parsed);
      setValue(ARTWORK_PATH, parsed);

      setDirty(false);
      setResetToken((t) => t + 1);
    } catch (err) {
      alert(`Upload failed: ${err?.message || String(err)}`);
    } finally {
      // allow uploading the same file again
      e.target.value = "";
    }
  }

  const commonTabProps = {
    draftArtwork,
    setDraftArtwork,
    markDirty: () => setDirty(true),
    resetToken,
  };

  return (
    <div>
      <h3>Artwork Generator</h3>

      {/* ✅ Shared controls */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <button onClick={saveAll} disabled={!dirty}>Save</button>
        <button onClick={resetAll} disabled={!dirty}>Reset</button>
        <button onClick={downloadArtwork}>Download</button>

        <button onClick={uploadArtworkClick}>Upload</button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/json"
          style={{ display: "none" }}
          onChange={onUploadFile}
        />
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        {ARTGEN_TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setValue(["nav", "home", "artgen", "tab"], t.key)}
            style={{ fontWeight: active === t.key ? "bold" : "normal" }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ padding: 12, border: "1px solid #ccc" }}>
        {active === "metadata" && <Metadata {...commonTabProps} />}
        {active === "params" && <Params {...commonTabProps} />}
        {active === "layers" && <Layers {...commonTabProps} />}
        {active === "vias" && <Vias {...commonTabProps} />}
        {active === "viaPadStack" && <ViaPadStack {...commonTabProps} />}
        {active === "bridges" && <Bridges {...commonTabProps} />}
        {active === "ports" && <Ports {...commonTabProps} />}
        {active === "arms" && <Arms {...commonTabProps} />}
        {active === "seg" && <Seg {...commonTabProps} />}
        {active === "guardRing" && <GuardRing {...commonTabProps} />}
        {active === "preview" && <Preview {...commonTabProps} />}
      </div>
    </div>
  );
}
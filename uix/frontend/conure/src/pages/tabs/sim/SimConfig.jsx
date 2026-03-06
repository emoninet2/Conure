import { useEffect, useMemo, useRef, useState } from "react";
import { useUiStore } from "../../../state/uiStore";

import EmxConfig from "./config/EmxConfig";

const CONFIG_TABS = [{ key: "emx", label: "EMX" }];

// ✅ manage the entire sim_config
const SIM_PATH = ["sim_config"];

function safeObj(x) {
  return x && typeof x === "object" && !Array.isArray(x) ? x : {};
}

function ensureSimConfigShape(obj) {
  const s = safeObj(obj);
  // ensure emx_config exists so the key is never missing
  if (!safeObj(s.emx_config)) return { ...s, emx_config: {} };
  return s;
}

export default function SimConfig() {
  const setValue = useUiStore((s) => s.setValue);
  const fileInputRef = useRef(null);

  const active = useUiStore((s) =>
    s.getValue(["nav", "home", "sim", "config", "tab"], "emx")
  );

  // ✅ last SAVED sim_config from store (stable string)
  const savedSimJson = useUiStore((s) => {
    const obj = s.getValue(SIM_PATH, null) || {};
    try {
      return JSON.stringify(obj);
    } catch {
      return "{}";
    }
  });

  const savedSimConfig = useMemo(() => {
    try {
      return ensureSimConfigShape(JSON.parse(savedSimJson));
    } catch {
      return ensureSimConfigShape({});
    }
  }, [savedSimJson]);

  const [draftSimConfig, setDraftSimConfig] = useState(() => savedSimConfig);
  const [dirty, setDirty] = useState(false);
  const [resetToken, setResetToken] = useState(0);

  // If store reloads from backend and user isn't editing, refresh draft
  useEffect(() => {
    if (!dirty) {
      setDraftSimConfig(savedSimConfig);
      setResetToken((t) => t + 1);
    }
  }, [savedSimJson]);

  function saveAll() {
    setValue(SIM_PATH, draftSimConfig);
    setDirty(false);
  }

  function resetAll() {
    setDraftSimConfig(savedSimConfig);
    setDirty(false);
    setResetToken((t) => t + 1);
  }

  // ✅ download ENTIRE sim_config (including emx_config key)
  function downloadSimConfig() {
    const pretty = JSON.stringify(savedSimConfig, null, 2);
    const blob = new Blob([pretty], { type: "application/json" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;

    const ts = new Date().toISOString().replaceAll(":", "-");
    a.download = `sim_config-${ts}.json`;

    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
  }

  function uploadClick() {
    fileInputRef.current?.click();
  }

  // ✅ upload ENTIRE sim_config (and ensure emx_config exists)
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

      const next = ensureSimConfigShape(parsed);

      setDraftSimConfig(next);
      setValue(SIM_PATH, next);

      setDirty(false);
      setResetToken((t) => t + 1);
    } catch (err) {
      alert(`Upload failed: ${err?.message || String(err)}`);
    } finally {
      e.target.value = "";
    }
  }

  const commonTabProps = {
    draftSimConfig,
    setDraftSimConfig: (updater) => {
      setDirty(true);
      setDraftSimConfig((prev) => {
        const base = ensureSimConfigShape(prev);
        const next = typeof updater === "function" ? updater(base) : updater;
        return ensureSimConfigShape(next);
      });
    },
    markDirty: () => setDirty(true),
    resetToken,
  };

  return (
    <div>
      <h4>Config</h4>

      {/* ✅ Shared controls */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          flexWrap: "wrap",
          marginBottom: 12,
        }}
      >
        <button
          onClick={uploadClick}
          style={{
            padding: "6px 12px",
            borderRadius: 6,
            border: "1px solid #ccc",
            background: "#f5f5f5",
            cursor: "pointer",
          }}
        >
          Upload
        </button>

        <button
          onClick={downloadSimConfig}
          style={{
            padding: "6px 12px",
            borderRadius: 6,
            border: "1px solid #ccc",
            background: "#f5f5f5",
            cursor: "pointer",
          }}
        >
          Download
        </button>

        <div style={{ width: 1, height: 24, background: "#ddd", margin: "0 6px" }} />

        <button
          onClick={saveAll}
          disabled={!dirty}
          style={{
            padding: "6px 14px",
            borderRadius: 6,
            border: "none",
            background: dirty ? "#2d6cdf" : "#c7d3f5",
            color: "white",
            cursor: dirty ? "pointer" : "default",
            fontWeight: 500,
          }}
        >
          Save
        </button>

        <button
          onClick={resetAll}
          disabled={!dirty}
          style={{
            padding: "6px 12px",
            borderRadius: 6,
            border: "1px solid #ccc",
            background: "#f2f2f2",
            cursor: dirty ? "pointer" : "default",
          }}
        >
          Reset
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="application/json"
          style={{ display: "none" }}
          onChange={onUploadFile}
        />
      </div>

      {/* Config tabs */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        {CONFIG_TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setValue(["nav", "home", "sim", "config", "tab"], t.key)}
            style={{ fontWeight: active === t.key ? "bold" : "normal" }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ padding: 12, border: "1px solid #ccc" }}>
        {active === "emx" && <EmxConfig {...commonTabProps} />}
      </div>
    </div>
  );
}
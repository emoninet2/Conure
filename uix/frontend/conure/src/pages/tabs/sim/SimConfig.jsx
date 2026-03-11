import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useUiStore } from "../../../state/uiStore";

import EmxConfig, { normalizeEmxConfig } from "./config/EmxConfig";

const CONFIG_TABS = [{ key: "emx", label: "EMX" }];

const SIM_PATH = ["sim_config"];

function safeObj(x) {
  return x && typeof x === "object" && !Array.isArray(x) ? x : {};
}

function ensureSimConfigShape(obj) {
  const s = safeObj(obj);
  if (!safeObj(s.emx_config)) return { ...s, emx_config: {} };
  return s;
}

function buildDefaultSimConfig() {
  return {
    emx_config: normalizeEmxConfig({}),
  };
}

function hasPersistedEmxConfig(obj) {
  const s = safeObj(obj);
  const emx = safeObj(s.emx_config);
  return Object.keys(emx).length > 0;
}

export default function SimConfig() {
  const setValue = useUiStore((s) => s.setValue);
  const fileInputRef = useRef(null);

  const active = useUiStore((s) =>
    s.getValue(["nav", "home", "sim", "config", "tab"], "emx")
  );

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

  const hasSavedEmx = useMemo(() => {
    return hasPersistedEmxConfig(savedSimConfig);
  }, [savedSimConfig]);

  const [draftSimConfig, setDraftSimConfigState] = useState(() => {
    return hasSavedEmx ? savedSimConfig : buildDefaultSimConfig();
  });

  const [dirty, setDirty] = useState(() => !hasSavedEmx);
  const [resetToken, setResetToken] = useState(0);

  useEffect(() => {
    if (!dirty) {
      const next = hasSavedEmx ? savedSimConfig : buildDefaultSimConfig();
      setDraftSimConfigState(next);
      setDirty(!hasSavedEmx);
      setResetToken((t) => t + 1);
    }
  }, [savedSimConfig, hasSavedEmx, dirty]);

  const updateDraftSimConfig = useCallback((updater) => {
    setDirty(true);
    setDraftSimConfigState((prev) => {
      const base = ensureSimConfigShape(prev);
      const next = typeof updater === "function" ? updater(base) : updater;
      return ensureSimConfigShape(next);
    });
  }, []);

  const markDirty = useCallback(() => {
    setDirty(true);
  }, []);

  function saveAll() {
    setValue(SIM_PATH, draftSimConfig);
    setDirty(false);
  }

  function resetAll() {
    const next = hasSavedEmx ? savedSimConfig : buildDefaultSimConfig();
    setDraftSimConfigState(next);
    setDirty(!hasSavedEmx);
    setResetToken((t) => t + 1);
  }

  function downloadSimConfig() {
    const pretty = JSON.stringify(draftSimConfig, null, 2);
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

      setDraftSimConfigState(next);
      setValue(SIM_PATH, next);

      setDirty(false);
      setResetToken((t) => t + 1);
    } catch (err) {
      alert(`Upload failed: ${err?.message || String(err)}`);
    } finally {
      e.target.value = "";
    }
  }

  const commonTabProps = useMemo(
    () => ({
      draftSimConfig,
      setDraftSimConfig: updateDraftSimConfig,
      markDirty,
      resetToken,
    }),
    [draftSimConfig, updateDraftSimConfig, markDirty, resetToken]
  );

  return (
    <div>
      <h4>Config</h4>

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

        {!hasSavedEmx && (
          <div style={{ fontSize: 12, opacity: 0.75 }}>
            Default EMX config is loaded but not saved yet.
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="application/json"
          style={{ display: "none" }}
          onChange={onUploadFile}
        />
      </div>

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

      <div style={{ padding: 12, border: "1px solid #ccc" }}>
        {active === "emx" && <EmxConfig {...commonTabProps} />}
      </div>
    </div>
  );
}
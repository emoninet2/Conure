import { useEffect, useMemo, useRef, useState } from "react";
import { useUiStore } from "../../state/uiStore";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const MODEL_UI_PATH = ["ui", "home", "tabs", "model"];
const ACTIVE_MODEL_PATH = [...MODEL_UI_PATH, "activeModel"];
const RUNNING_PATH = [...MODEL_UI_PATH, "running"];

const MODEL_TYPE_OPTIONS = [
  "ANN",
  "GPR",
  "PCE",
  "CAT",
  "XGB",
  "RF",
  "PR",
  "SVR",
];

const TRANSLATION_BASE_TYPES = ["FFD", "FFI", "IFD", "IFI"];

const DEFAULT_TRANSLATE_CONFIG = {
  translation_type: "FFD",
  translation_params: {},
};

const DEFAULT_DRAFT = {
  sweep_name: "",
  model_type: "ANN",
  translate_config: {
    translation_type: "FFD",
    translation_params: {},
  },
  model_config: {
    model_name: "",
    normalization: {
      feature_method: "standard",
      target_method: "standard",
    },
    training: {
      epochs: 100,
      batch_size: 32,
      loss: "mse",
      metrics: ["mae"],
      validation_split: 0.2,
      optimizer: {
        type: "Adam",
        learning_rate: 0.001,
        momentum: 0.9,
      },
    },
    early_stopping: {
      monitor: "val_loss",
      patience: 15,
      restore_best_weights: true,
    },
    architecture: [
      { type: "Dense", units: 128, activation: "relu" },
      { type: "Dense", units: "AUTO", activation: "linear" },
    ],
  },
};


async function fetchDefaultModelDraft(model_type, model_name = "") {
  const res = await fetch(`${API_BASE}/api/models/default-config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_type, model_name }),
  });

  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}



const DEFAULT_REPORT = null;
const ANSI_REGEX = /\x1B\[[0-?]*[ -/]*[@-~]/g;

function stripAnsi(s) {
  return typeof s === "string" ? s.replace(ANSI_REGEX, "") : s;
}

function safePretty(value) {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return "{}";
  }
}

function parseJsonText(text, label) {
  try {
    const parsed = JSON.parse(text);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error(`${label} must be a JSON object.`);
    }
    return parsed;
  } catch (err) {
    throw new Error(`${label} is invalid JSON. ${err?.message || String(err)}`);
  }
}

function formatNumber(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  return value.toFixed(6);
}

function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

function statusPillStyle(background, color = "#111") {
  return {
    display: "inline-flex",
    alignItems: "center",
    padding: "4px 10px",
    borderRadius: 999,
    background,
    color,
    fontSize: 12,
    fontWeight: 600,
  };
}

function cloneJson(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function normalizeTranslateConfig(config) {
  const input =
    config && typeof config === "object" && !Array.isArray(config)
      ? config
      : DEFAULT_TRANSLATE_CONFIG;

  const rawType = String(input.translation_type || "FFD").trim();
  const isAugmented = rawType.endsWith("_augmented");
  const baseType = isAugmented
    ? rawType.replace(/_augmented$/, "")
    : rawType;

  const safeBaseType = TRANSLATION_BASE_TYPES.includes(baseType)
    ? baseType
    : "FFD";

  const params =
    input.translation_params &&
      typeof input.translation_params === "object" &&
      !Array.isArray(input.translation_params)
      ? input.translation_params
      : {};

  return {
    baseType: safeBaseType,
    augmented: isAugmented,
    feature_noise_std:
      params.feature_noise_std === undefined ? 0.01 : Number(params.feature_noise_std),
    target_noise_std:
      params.target_noise_std === undefined ? 0.005 : Number(params.target_noise_std),
    n_augment:
      params.n_augment === undefined ? 3 : Number(params.n_augment),
    clip:
      params.clip === undefined ? true : Boolean(params.clip),
  };
}

function buildTranslateConfigFromForm(form) {
  const baseType = TRANSLATION_BASE_TYPES.includes(form.baseType)
    ? form.baseType
    : "FFD";

  const augmented = !!form.augmented;
  const translation_type = augmented ? `${baseType}_augmented` : baseType;

  if (!augmented) {
    return {
      translation_type,
      translation_params: {},
    };
  }

  return {
    translation_type,
    translation_params: {
      feature_noise_std: Number(form.feature_noise_std || 0),
      target_noise_std: Number(form.target_noise_std || 0),
      n_augment: Number(form.n_augment || 0),
      clip: !!form.clip,
    },
  };
}

function TranslationConfigForm({ value, onChange, disabled }) {
  return (
    <div
      style={{
        border: "1px solid #ddd",
        padding: 12,
        background: "#fafafa",
      }}
    >
      <div style={{ fontWeight: "bold", marginBottom: 10 }}>
        data_translate.json
      </div>

      <div style={{ display: "grid", gap: 12 }}>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          Translation type:
          <select
            value={value.baseType}
            onChange={(e) =>
              onChange((prev) => ({ ...prev, baseType: e.target.value }))
            }
            disabled={disabled}
          >
            {TRANSLATION_BASE_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={value.augmented}
            onChange={(e) =>
              onChange((prev) => ({ ...prev, augmented: e.target.checked }))
            }
            disabled={disabled}
          />
          Use augmented translation
        </label>

        {value.augmented ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
              padding: 12,
              border: "1px solid #e0e0e0",
              background: "#fff",
            }}
          >
            <label style={{ display: "grid", gap: 6 }}>
              <span>Feature noise std</span>
              <input
                type="number"
                step="any"
                value={value.feature_noise_std}
                onChange={(e) =>
                  onChange((prev) => ({
                    ...prev,
                    feature_noise_std: e.target.value,
                  }))
                }
                disabled={disabled}
              />
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              <span>Target noise std</span>
              <input
                type="number"
                step="any"
                value={value.target_noise_std}
                onChange={(e) =>
                  onChange((prev) => ({
                    ...prev,
                    target_noise_std: e.target.value,
                  }))
                }
                disabled={disabled}
              />
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              <span>Number of augmentations</span>
              <input
                type="number"
                min="1"
                step="1"
                value={value.n_augment}
                onChange={(e) =>
                  onChange((prev) => ({
                    ...prev,
                    n_augment: e.target.value,
                  }))
                }
                disabled={disabled}
              />
            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 24 }}>
              <input
                type="checkbox"
                checked={!!value.clip}
                onChange={(e) =>
                  onChange((prev) => ({
                    ...prev,
                    clip: e.target.checked,
                  }))
                }
                disabled={disabled}
              />
              Clip augmented values
            </label>
          </div>
        ) : null}

        <div>
          <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>
            Preview
          </div>
          <pre
            style={{
              margin: 0,
              padding: 12,
              border: "1px solid #ddd",
              background: "#fff",
              overflow: "auto",
              fontSize: 12,
            }}
          >
            {safePretty(buildTranslateConfigFromForm(value))}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default function Model() {
  const setValue = useUiStore((s) => s.setValue);

  const [activeModel, setActiveModelLocal] = useState("");
  const [running, setRunningLocal] = useState(false);

  const [models, setModels] = useState([]);
  const [newModelName, setNewModelName] = useState("");

  const [draft, setDraft] = useState(DEFAULT_DRAFT);
  const [savedSnapshot, setSavedSnapshot] = useState(DEFAULT_DRAFT);

  const [translateForm, setTranslateForm] = useState(
    normalizeTranslateConfig(DEFAULT_DRAFT.translate_config)
  );
  const [modelConfigText, setModelConfigText] = useState(
    safePretty(DEFAULT_DRAFT.model_config)
  );

  const [sweepOptions, setSweepOptions] = useState([]);
  const [report, setReport] = useState(DEFAULT_REPORT);
  const [lines, setLines] = useState([]);
  const [predictionInput, setPredictionInput] = useState("[[10, 5000000]]");
  const [predictionOutput, setPredictionOutput] = useState("");
  const [apiError, setApiError] = useState("");
  const [predicting, setPredicting] = useState(false);

  const esRef = useRef(null);
  const scrollerRef = useRef(null);

  useEffect(() => {
    refreshSweepOptions();
  }, []);

  async function refreshSweepOptions() {
    try {
      const res = await fetch(`${API_BASE}/api/models/sweep-options`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      const sweeps = (data.sweeps || []).filter((item) =>
        Array.isArray(item?.npz_files)
          ? item.npz_files.includes("simulation_data.npz")
          : true
      );
      setSweepOptions(sweeps);
    } catch (err) {
      setApiError(err?.message || String(err));
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function init() {
      const store = useUiStore.getState();
      setActiveModelLocal(store.getValue(ACTIVE_MODEL_PATH, "") || "");
      setRunningLocal(!!store.getValue(RUNNING_PATH, false));

      await refreshModels();
      const { nextActiveModel } = await hydrateFromProjectState();
      await syncStatus();

      if (!cancelled && nextActiveModel) {
        await openModel(nextActiveModel);
      }
    }

    init();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!activeModel) return;
    fetchReport(activeModel);
  }, [activeModel]);

  useEffect(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }

    if (!running || !activeModel) return;

    const es = new EventSource(
      `${API_BASE}/api/models/stream?model_name=${encodeURIComponent(activeModel)}`
    );
    esRef.current = es;

    es.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        setLines((prev) => {
          const next = [...prev, msg];
          if (next.length > 3000) next.splice(0, next.length - 3000);
          return next;
        });

        if (typeof msg?.line === "string" && msg.line.startsWith("[done]")) {
          setValue(RUNNING_PATH, false);
          setRunningLocal(false);
          setTimeout(() => {
            fetchReport(activeModel);
          }, 500);
        }
      } catch {
        //
      }
    };

    es.onerror = async () => {
      es.close();
      esRef.current = null;
      await syncStatus();
      setTimeout(() => {
        fetchReport(activeModel);
      }, 500);
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [running, activeModel, setValue]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines]);

  const dirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(savedSnapshot),
    [draft, savedSnapshot]
  );

  const isTrained = useMemo(() => !!report, [report]);

  const modelSummary = useMemo(() => {
    if (!report) return null;
    return {
      modelName: report?.model_info?.model_name ?? activeModel ?? "—",
      modelType: report?.model_info?.model_type ?? draft.model_type ?? "—",
      completedAt: report?.model_info?.completion_timestamp ?? null,
      framework: report?.model_info?.framework ?? "—",
      durationSec: report?.model_info?.training_duration_sec,
      r2: report?.performance?.metrics?.Aggregate?.R2,
      rmse: report?.performance?.metrics?.Aggregate?.RMSE,
      mae: report?.performance?.metrics?.Aggregate?.MAE,
    };
  }, [report, activeModel, draft.model_type]);

  function syncEditorsFromDraft(nextDraft) {
    setTranslateForm(normalizeTranslateConfig(nextDraft.translate_config));
    setModelConfigText(safePretty(nextDraft.model_config));
  }

  function buildDraftFromEditors() {
    const translate_config = buildTranslateConfigFromForm(translateForm);
    const model_config = parseJsonText(modelConfigText, "Model config");

    return {
      sweep_name: draft.sweep_name || "",
      model_type: String(draft.model_type || "ANN").toUpperCase(),
      translate_config,
      model_config,
    };
  }

  async function hydrateFromProjectState() {
    try {
      const res = await fetch(`${API_BASE}/api/state`);
      if (!res.ok) throw new Error(await res.text());
      const state = await res.json();

      const modelUi = state?.ui?.home?.tabs?.model || {};
      const nextActiveModel = modelUi?.activeModel || "";
      const nextRunning = !!modelUi?.running;
      const nextDraft = modelUi?.draftConfig || DEFAULT_DRAFT;

      setValue(ACTIVE_MODEL_PATH, nextActiveModel);
      setActiveModelLocal(nextActiveModel);
      setValue(RUNNING_PATH, nextRunning);
      setRunningLocal(nextRunning);

      setDraft(nextDraft);
      setSavedSnapshot(cloneJson(nextDraft));
      syncEditorsFromDraft(nextDraft);

      return { nextActiveModel, nextRunning, nextDraft };
    } catch (err) {
      setApiError(err?.message || String(err));
      return { nextActiveModel: "", nextRunning: false, nextDraft: DEFAULT_DRAFT };
    }
  }

  async function refreshModels() {
    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/models`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setModels(data.models || []);
    } catch (err) {
      setApiError(err?.message || String(err));
    }
  }

  async function syncStatus() {
    try {
      const res = await fetch(`${API_BASE}/api/models/status`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      const nextRunning = !!data.running;
      const nextModel = data.model_name || "";

      setValue(RUNNING_PATH, nextRunning);
      setRunningLocal(nextRunning);

      if (nextModel && nextModel !== activeModel) {
        setValue(ACTIVE_MODEL_PATH, nextModel);
        setActiveModelLocal(nextModel);
      }
    } catch (err) {
      setApiError(err?.message || String(err));
    }
  }

  async function fetchReport(name = activeModel) {
    if (!name) {
      setReport(null);
      return;
    }
    try {
      const res = await fetch(
        `${API_BASE}/api/models/report?model_name=${encodeURIComponent(name)}`
      );
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setReport(
        data.exists && data.report && Object.keys(data.report).length > 0
          ? data.report
          : null
      );
    } catch (err) {
      setApiError(err?.message || String(err));
    }
  }

  async function createModel() {
    const name = newModelName.trim();
    if (!name) {
      alert("Enter a model name.");
      return;
    }

    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/models/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_name: name }),
      });
      if (!res.ok) throw new Error(await res.text());

      const data = await res.json();
      setLines([]);
      setPredictionOutput("");
      setNewModelName("");
      await refreshModels();
      await openModel(data.model_name || name);
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  async function openModel(name) {
    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/models/open`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_name: name }),
      });
      if (!res.ok) throw new Error(await res.text());

      const data = await res.json();
      const nextDraft = data.config || DEFAULT_DRAFT;

      setValue(ACTIVE_MODEL_PATH, data.model_name);
      setActiveModelLocal(data.model_name);

      setValue(RUNNING_PATH, !!data.running);
      setRunningLocal(!!data.running);

      setDraft(nextDraft);
      setSavedSnapshot(cloneJson(nextDraft));
      syncEditorsFromDraft(nextDraft);
      setReport(data.report || null);
      setLines([]);
      setPredictionOutput("");
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  async function saveModel() {
    if (!activeModel) {
      alert("Open or create a model first.");
      return;
    }

    try {
      const nextDraft = buildDraftFromEditors();
      nextDraft.model_config.model_name = activeModel;
      nextDraft.sweep_name = draft.sweep_name || "";

      setApiError("");
      const res = await fetch(`${API_BASE}/api/models/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_name: activeModel, config: nextDraft }),
      });
      if (!res.ok) throw new Error(await res.text());

      setDraft(nextDraft);
      setSavedSnapshot(cloneJson(nextDraft));
      await fetchReport(activeModel);
      await refreshModels();
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  async function resetModel() {
    if (!activeModel) {
      setDraft(DEFAULT_DRAFT);
      setSavedSnapshot(DEFAULT_DRAFT);
      syncEditorsFromDraft(DEFAULT_DRAFT);
      setReport(null);
      return;
    }
    await openModel(activeModel);
  }

  async function startTraining() {
    if (!activeModel) {
      alert("Open or create a model first.");
      return;
    }

    try {
      const nextDraft = buildDraftFromEditors();
      nextDraft.model_config.model_name = activeModel;
      nextDraft.sweep_name = draft.sweep_name || "";

      setDraft(nextDraft);
      setSavedSnapshot(cloneJson(nextDraft));

      setApiError("");
      setLines([]);
      setReport(null);
      setPredictionOutput("");

      setValue(RUNNING_PATH, true);
      setRunningLocal(true);

      const body = {
        model_name: activeModel,
        config: nextDraft,
        sweep_name: nextDraft.sweep_name || "",
      };

      const res = await fetch(`${API_BASE}/api/models/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error(await res.text());
    } catch (err) {
      setValue(RUNNING_PATH, false);
      setRunningLocal(false);
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  async function stopTraining() {
    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/models/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error(await res.text());
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    } finally {
      setValue(RUNNING_PATH, false);
      setRunningLocal(false);
      await fetchReport(activeModel);
    }
  }

  async function deleteModel(name) {
    const ok = window.confirm(`Delete model "${name}"?`);
    if (!ok) return;

    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/models/${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(await res.text());

      if (name === activeModel) {
        setValue(ACTIVE_MODEL_PATH, "");
        setActiveModelLocal("");
        setValue(RUNNING_PATH, false);
        setRunningLocal(false);
        setDraft(DEFAULT_DRAFT);
        setSavedSnapshot(DEFAULT_DRAFT);
        syncEditorsFromDraft(DEFAULT_DRAFT);
        setReport(null);
        setLines([]);
        setPredictionOutput("");
      }

      await refreshModels();
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    }
  }

  async function runPrediction() {
    if (!activeModel) {
      alert("Open a model first.");
      return;
    }
    if (!report) {
      alert("Train the model first so prediction can use the saved model.");
      return;
    }

    try {
      setPredicting(true);
      setApiError("");
      const x_input = JSON.parse(predictionInput);

      const res = await fetch(`${API_BASE}/api/models/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_name: activeModel,
          model_type: draft.model_type,
          x_input,
        }),
      });
      if (!res.ok) throw new Error(await res.text());

      const data = await res.json();
      setPredictionOutput(safePretty(data.prediction));
    } catch (err) {
      setApiError(err?.message || String(err));
      alert(err?.message || String(err));
    } finally {
      setPredicting(false);
    }
  }

  return (
    <div>
      <h3>Model</h3>

      {apiError ? (
        <div style={{ marginBottom: 12, color: "crimson", whiteSpace: "pre-wrap" }}>
          API error: {apiError}
        </div>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16 }}>
        <div style={{ border: "1px solid #ccc", padding: 12 }}>
          <h4 style={{ marginTop: 0 }}>Models</h4>

          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input
              value={newModelName}
              onChange={(e) => setNewModelName(e.target.value)}
              placeholder="New model name"
              style={{ flex: 1 }}
            />
            <button onClick={createModel}>Create</button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {models.length === 0 ? (
              <div style={{ opacity: 0.7 }}>No models yet.</div>
            ) : (
              models.map((name) => (
                <div key={name} style={{ display: "flex", gap: 6 }}>
                  <button
                    onClick={() => openModel(name)}
                    style={{
                      flex: 1,
                      textAlign: "left",
                      fontWeight: name === activeModel ? "bold" : "normal",
                    }}
                  >
                    {name}
                  </button>
                  <button onClick={() => deleteModel(name)} disabled={running && activeModel === name}>
                    Delete
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div style={{ border: "1px solid #ccc", padding: 12 }}>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center", marginBottom: 12 }}>
            <div>
              Active model: <strong>{activeModel || "None"}</strong>
            </div>
            <div>
              Status:{" "}
              {running ? (
                <span style={statusPillStyle("#fff3cd")}>Training…</span>
              ) : isTrained ? (
                <span style={statusPillStyle("#d1e7dd")}>Trained</span>
              ) : activeModel ? (
                <span style={statusPillStyle("#f8d7da")}>Not trained</span>
              ) : (
                <span style={statusPillStyle("#e9ecef")}>Idle</span>
              )}
            </div>
            <div>Unsaved: {dirty ? "Yes" : "No"}</div>
          </div>

          {activeModel ? (
            <div
              style={{
                border: "1px solid #ddd",
                background: "#fafafa",
                padding: 12,
                marginBottom: 16,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontWeight: "bold", marginBottom: 6 }}>Model Availability</div>
                  <div>
                    {isTrained
                      ? `Model artifacts are present for ${modelSummary?.modelName || activeModel}.`
                      : "This model has not been trained yet or no summary/report file was found."}
                  </div>
                  {isTrained ? (
                    <div style={{ marginTop: 6, fontSize: 13, opacity: 0.85 }}>
                      Completed: {formatDateTime(modelSummary?.completedAt)}
                    </div>
                  ) : null}
                </div>

                {isTrained ? (
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-start" }}>
                    <a href="#model-overview">Overview</a>
                    <a href="#model-metrics">Metrics</a>
                    <a href="#model-raw-summary">Raw Summary</a>
                    <a href="#model-predict">Predict</a>
                  </div>
                ) : null}
              </div>
            </div>
          ) : null}

          <div style={{ display: "grid", gap: 10, marginBottom: 16 }}>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              Model type:
              {/* <select
                value={draft.model_type}
                onChange={(e) => setDraft((prev) => ({ ...prev, model_type: e.target.value }))}
                disabled={running}
              >
                <option value="ANN">ANN</option>
                <option value="GPR">GPR</option>
                <option value="PCE">PCE</option>
                <option value="CAT">CAT</option>
                <option value="XGB">XGB</option>
                <option value="RF">RF</option>
                <option value="PR">PR</option>
                <option value="SVR">SVR</option>
              </select>
               */}

              <select
                value={draft.model_type}
                onChange={async (e) => {
                  const newType = e.target.value;

                  try {
                    const newDraft = await fetchDefaultModelDraft(newType, activeModel);

                    setDraft(newDraft);
                    setSavedSnapshot(cloneJson(newDraft));
                    syncEditorsFromDraft(newDraft);
                  } catch (err) {
                    setApiError(err?.message || String(err));
                  }
                }}
                disabled={running}
              >
                {MODEL_TYPE_OPTIONS.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>


            </label>

            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              Sweep:
              <select
                value={draft.sweep_name || ""}
                onChange={(e) => {
                  const nextSweepName = e.target.value;
                  setDraft((prev) => ({ ...prev, sweep_name: nextSweepName }));
                }}
                disabled={running}
                style={{ flex: 1 }}
              >
                <option value="">Select sweep</option>
                {sweepOptions.map((item) => (
                  <option key={item.sweep_name} value={item.sweep_name}>
                    {item.sweep_name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div style={{ display: "grid", gap: 12, marginBottom: 16 }}>
            <TranslationConfigForm
              value={translateForm}
              onChange={setTranslateForm}
              disabled={running}
            />

            <div>
              <div style={{ marginBottom: 6, fontWeight: "bold" }}>model_config.json</div>
              <textarea
                value={modelConfigText}
                onChange={(e) => setModelConfigText(e.target.value)}
                disabled={running}
                style={{ width: "100%", minHeight: 280, fontFamily: "monospace", fontSize: 12 }}
              />
            </div>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
            <button onClick={saveModel} disabled={!activeModel || running}>Save</button>
            <button onClick={resetModel} disabled={running}>Reset</button>
            <button onClick={startTraining} disabled={!activeModel || running}>Train</button>
            <button onClick={stopTraining} disabled={!running}>Stop</button>
            <button onClick={() => setLines([])}>Clear Console</button>
          </div>

          <div
            ref={scrollerRef}
            style={{
              height: 220,
              overflow: "auto",
              padding: 12,
              border: "1px solid #ddd",
              background: "#fafafa",
              whiteSpace: "pre-wrap",
              fontFamily: "monospace",
              fontSize: 12,
              marginBottom: 16,
            }}
          >
            {lines.length === 0
              ? running
                ? "Waiting for training output..."
                : "No output yet."
              : lines.map((x, i) => <div key={i}>{stripAnsi(x.line)}</div>)}
          </div>

          {report ? (
            <div style={{ marginBottom: 16 }}>
              <div id="model-overview" style={{ marginBottom: 16 }}>
                <h4 style={{ marginBottom: 10 }}>Model Overview</h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12, marginBottom: 12 }}>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Model</div>
                    <div style={{ fontWeight: "bold" }}>{modelSummary?.modelName ?? "—"}</div>
                    <div style={{ marginTop: 4 }}>{modelSummary?.modelType ?? "—"}</div>
                  </div>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Framework</div>
                    <div style={{ fontWeight: "bold" }}>{modelSummary?.framework ?? "—"}</div>
                    <div style={{ marginTop: 4 }}>Duration: {formatNumber(modelSummary?.durationSec)} s</div>
                  </div>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Aggregate R2</div>
                    <div style={{ fontWeight: "bold" }}>{formatNumber(modelSummary?.r2)}</div>
                  </div>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}>Aggregate RMSE / MAE</div>
                    <div style={{ fontWeight: "bold" }}>{formatNumber(modelSummary?.rmse)}</div>
                    <div style={{ marginTop: 4 }}>MAE: {formatNumber(modelSummary?.mae)}</div>
                  </div>
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
                <div style={{ border: "1px solid #ddd", padding: 12 }}>
                  <div style={{ fontWeight: "bold", marginBottom: 8 }}>Model Info</div>
                  <div><strong>Name:</strong> {report?.model_info?.model_name ?? "—"}</div>
                  <div><strong>Type:</strong> {report?.model_info?.model_type ?? "—"}</div>
                  <div><strong>Framework:</strong> {report?.model_info?.framework ?? "—"}</div>
                  <div><strong>Framework version:</strong> {report?.model_info?.framework_version ?? "—"}</div>
                  <div><strong>Trainable parameters:</strong> {report?.model_info?.trainable_parameters ?? "—"}</div>
                  <div><strong>Model size (MB):</strong> {report?.model_info?.model_size_mb ?? "—"}</div>
                  <div><strong>Training duration (s):</strong> {report?.model_info?.training_duration_sec ?? "—"}</div>
                  <div><strong>Completed:</strong> {formatDateTime(report?.model_info?.completion_timestamp)}</div>
                </div>
                <div style={{ border: "1px solid #ddd", padding: 12 }}>
                  <div style={{ fontWeight: "bold", marginBottom: 8 }}>Data Info</div>
                  <div><strong>Input dim:</strong> {report?.data_info?.input_dim ?? "—"}</div>
                  <div><strong>Output dim:</strong> {report?.data_info?.output_dim ?? "—"}</div>
                  <div><strong>Total samples:</strong> {report?.data_info?.total_samples ?? "—"}</div>
                  <div><strong>Train samples:</strong> {report?.data_info?.train_samples ?? "—"}</div>
                  <div><strong>Validation samples:</strong> {report?.data_info?.validation_samples ?? "—"}</div>
                  <div><strong>Test samples:</strong> {report?.data_info?.test_samples ?? "—"}</div>
                  <div><strong>Split strategy:</strong> {report?.data_info?.split_strategy ?? "—"}</div>
                </div>
              </div>

              <div id="model-metrics" style={{ marginBottom: 12 }}>
                <h4 style={{ marginBottom: 10 }}>Performance Metrics</h4>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div style={{ fontWeight: "bold", marginBottom: 6 }}>Aggregate</div>
                    <div>R2: {formatNumber(report?.performance?.metrics?.Aggregate?.R2)}</div>
                    <div>RMSE: {formatNumber(report?.performance?.metrics?.Aggregate?.RMSE)}</div>
                    <div>MAE: {formatNumber(report?.performance?.metrics?.Aggregate?.MAE)}</div>
                  </div>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div style={{ fontWeight: "bold", marginBottom: 6 }}>Per-Output</div>
                    <div>RMSE Mean: {formatNumber(report?.performance?.metrics?.["Per-Output"]?.RMSE_Mean)}</div>
                    <div>RMSE Max: {formatNumber(report?.performance?.metrics?.["Per-Output"]?.RMSE_Max)}</div>
                    <div>RMSE Min: {formatNumber(report?.performance?.metrics?.["Per-Output"]?.RMSE_Min)}</div>
                  </div>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div style={{ fontWeight: "bold", marginBottom: 6 }}>Per-Sample</div>
                    <div>RMSE Mean: {formatNumber(report?.performance?.metrics?.["Per-Sample"]?.RMSE_Mean)}</div>
                    <div>RMSE Max: {formatNumber(report?.performance?.metrics?.["Per-Sample"]?.RMSE_Max)}</div>
                  </div>
                </div>
                <div style={{ border: "1px solid #ddd", padding: 12 }}>
                  <div style={{ fontWeight: "bold", marginBottom: 6 }}>Evaluation Protocol</div>
                  <div><strong>Dataset:</strong> {report?.performance?.evaluation_protocol?.evaluation_dataset ?? "—"}</div>
                  <div><strong>Inverse transformed:</strong> {String(report?.performance?.evaluation_protocol?.predictions_inverse_transformed ?? "—")}</div>
                  <div><strong>Normalization used:</strong> {String(report?.performance?.evaluation_protocol?.normalization_used ?? "—")}</div>
                </div>
              </div>

              <details id="model-raw-summary">
                <summary style={{ cursor: "pointer", fontWeight: "bold" }}>Raw summary / report JSON</summary>
                <pre style={{ border: "1px solid #ddd", background: "#fafafa", padding: 12, overflow: "auto", fontSize: 12 }}>
                  {safePretty(report)}
                </pre>
              </details>
            </div>
          ) : null}

          {report ? (
            <div id="model-predict">
              <h4 style={{ marginBottom: 8 }}>Predict</h4>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <div>
                  <div style={{ marginBottom: 6, fontWeight: "bold" }}>Input JSON</div>
                  <textarea
                    value={predictionInput}
                    onChange={(e) => setPredictionInput(e.target.value)}
                    style={{ width: "100%", minHeight: 140, fontFamily: "monospace", fontSize: 12 }}
                  />
                  <div style={{ marginTop: 8 }}>
                    <button onClick={runPrediction} disabled={predicting}>
                      {predicting ? "Predicting..." : "Run Prediction"}
                    </button>
                  </div>
                </div>
                <div>
                  <div style={{ marginBottom: 6, fontWeight: "bold" }}>Prediction Output</div>
                  <textarea
                    value={predictionOutput}
                    readOnly
                    style={{ width: "100%", minHeight: 180, fontFamily: "monospace", fontSize: 12 }}
                  />
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
import { useEffect, useMemo, useRef, useState } from "react";
import { IconPencil, IconTrash } from "../../icons/actionIcons";
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

const TRANSLATION_BASE_TYPES = [
  "FFD",
  "FFI",
  "IFD",
  "IFI",
  "FFD_Inductor",
  "FFI_Inductor",
  "IFD_Inductor",
  "IFI_Inductor",
  "FFD_Transformer",
  "FFI_Transformer",
  "IFD_Transformer",
  "IFI_Transformer",
];

const DEFAULT_TRANSLATE_CONFIG = {
  translation_type: "FFD",
  translation_params: {},
  selection: { x_names: [], y_names: [] },
};

const DEFAULT_DRAFT = {
  sweep_name: "",
  model_type: "ANN",
  translate_config: {
    translation_type: "FFD",
    translation_params: {},
    selection: { x_names: [], y_names: [] },
  },
  model_config: {
    model_name: "",
    normalization: {
      feature_method: "standard",
      target_method: "standard",
      feature_methods: {},
      target_methods: {},
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

const DEFAULT_REPORT = null;
const ANSI_REGEX = /\x1B\[[0-?]*[ -/]*[@-~]/g;
const DEFAULT_ANN_MODEL_CONFIG = {
  model_name: "",
  architecture_type: "sequential",
  normalization: {
    feature_method: "standard",
    target_method: "standard",
    feature_methods: {},
    target_methods: {},
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
  graph: {
    input_name: "features",
    nodes: [],
    outputs: [],
  },
};

const NORMALIZATION_METHOD_OPTIONS = ["standard", "minmax", "robust", "maxabs", "none"];
const OPTIMIZER_TYPE_OPTIONS = ["Adam", "SGD", "RMSprop", "Adagrad"];
const GRAPH_OP_OPTIONS = ["Dense", "Dropout", "Slice", "Concatenate", "Identity"];
const REGULARIZER_TYPE_OPTIONS = ["none", "l1", "l2", "l1_l2"];
const ACTIVATION_OPTIONS = [
  "relu",
  "linear",
  "sigmoid",
  "tanh",
  "softplus",
  "selu",
  "elu",
  "swish",
  "gelu",
];

function normalizeMetricsList(value) {
  if (Array.isArray(value)) return value.map((x) => String(x).trim()).filter(Boolean);
  if (typeof value === "string") return value.split(",").map((x) => x.trim()).filter(Boolean);
  return ["mae"];
}

function csvToList(text) {
  return String(text || "").split(",").map((x) => x.trim()).filter(Boolean);
}

function listToCsv(list) {
  return Array.isArray(list) ? list.join(", ") : "";
}



function CsvTextInput({ value, onCommit, disabled, placeholder = "" }) {
  const [text, setText] = useState(listToCsv(value));

  useEffect(() => {
    setText(listToCsv(value));
  }, [value]);

  return (
    <input
      value={text}
      placeholder={placeholder}
      onChange={(e) => setText(e.target.value)}
      onBlur={() => onCommit(csvToList(text))}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          onCommit(csvToList(text));
          e.currentTarget.blur();
        }
      }}
      disabled={disabled}
    />
  );
}

function NumberCsvTextInput({ value, onCommit, disabled, placeholder = "" }) {
  const [text, setText] = useState(listToCsv(value));

  useEffect(() => {
    setText(listToCsv(value));
  }, [value]);

  return (
    <input
      value={text}
      placeholder={placeholder}
      onChange={(e) => setText(e.target.value)}
      onBlur={() => onCommit(csvToList(text).map((x) => Number(x)).filter((x) => !Number.isNaN(x)))}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          onCommit(csvToList(text).map((x) => Number(x)).filter((x) => !Number.isNaN(x)));
          e.currentTarget.blur();
        }
      }}
      disabled={disabled}
    />
  );
}

function nodeNamePlaceholder(op, index) {
  const base = String(op || "node").toLowerCase();
  return `e.g. ${base}_${Number(index) + 1}`;
}

function buildGraphBuildPreviewRows(graph) {
  const safeGraph = graph && typeof graph === "object" ? graph : {};
  const inputName = String(safeGraph.input_name || "features").trim() || "features";
  const nodes = Array.isArray(safeGraph.nodes) ? safeGraph.nodes : [];
  const outputs = Array.isArray(safeGraph.outputs) ? safeGraph.outputs : [];

  const rows = [
    {
      step: 0,
      ref: inputName,
      kind: "Input",
      inputs: "—",
      details: "Flat translated feature matrix",
      status: "ok",
    },
  ];

  const seen = new Set([inputName]);

  nodes.forEach((node, index) => {
    const op = String(node?.op || "").trim() || "Dense";
    const rawName = String(node?.name || "").trim();
    const ref = rawName || `(unnamed node ${index + 1})`;
    const inputs = Array.isArray(node?.inputs) ? node.inputs.map((x) => String(x).trim()).filter(Boolean) : [];

    let details = "";
    if (op === "Dense") details = `units=${node?.units ?? ""}, activation=${node?.activation || "linear"}`;
    else if (op === "Dropout") details = `rate=${node?.rate ?? 0.1}`;
    else if (op === "Slice") details = `indices=[${Array.isArray(node?.indices) ? node.indices.join(", ") : ""}]`;
    else if (op === "Concatenate") details = `axis=${node?.axis ?? -1}`;
    else if (op === "Identity") details = "pass-through";
    else details = "";

    let status = "ok";
    if (!rawName) status = "missing name";
    else if (seen.has(rawName)) status = "duplicate name";
    else if (inputs.some((name) => !seen.has(name))) status = "unknown / future ref";

    rows.push({
      step: index + 1,
      ref,
      kind: op,
      inputs: inputs.length ? inputs.join(", ") : "—",
      details,
      status,
    });

    if (rawName && !seen.has(rawName)) seen.add(rawName);
  });

  outputs.forEach((name, idx) => {
    const ref = String(name || "").trim();
    rows.push({
      step: nodes.length + idx + 1,
      ref: ref || `(blank output ${idx + 1})`,
      kind: "Output",
      inputs: ref || "—",
      details: "Final model output ref",
      status: ref && seen.has(ref) ? "ok" : "unknown ref",
    });
  });

  return rows;
}

function normalizeAnnModelConfig(config) {
  const src = config && typeof config === "object" && !Array.isArray(config) ? cloneJson(config) : {};
  return {
    ...cloneJson(DEFAULT_ANN_MODEL_CONFIG),
    ...src,
    normalization: {
      ...DEFAULT_ANN_MODEL_CONFIG.normalization,
      ...(src.normalization || {}),
      feature_methods:
        src.normalization &&
        typeof src.normalization.feature_methods === "object" &&
        src.normalization.feature_methods !== null &&
        !Array.isArray(src.normalization.feature_methods)
          ? { ...src.normalization.feature_methods }
          : {},
      target_methods:
        src.normalization &&
        typeof src.normalization.target_methods === "object" &&
        src.normalization.target_methods !== null &&
        !Array.isArray(src.normalization.target_methods)
          ? { ...src.normalization.target_methods }
          : {},
    },
    training: {
      ...DEFAULT_ANN_MODEL_CONFIG.training,
      ...(src.training || {}),
      metrics: normalizeMetricsList((src.training || {}).metrics),
      optimizer: {
        ...DEFAULT_ANN_MODEL_CONFIG.training.optimizer,
        ...((src.training || {}).optimizer || {}),
      },
    },
    early_stopping: {
      ...DEFAULT_ANN_MODEL_CONFIG.early_stopping,
      ...(src.early_stopping || {}),
    },
    architecture: Array.isArray(src.architecture) ? src.architecture : cloneJson(DEFAULT_ANN_MODEL_CONFIG.architecture),
    graph: {
      ...DEFAULT_ANN_MODEL_CONFIG.graph,
      ...(src.graph || {}),
      nodes: Array.isArray(src?.graph?.nodes) ? src.graph.nodes : [],
      outputs: Array.isArray(src?.graph?.outputs) ? src.graph.outputs : [],
    },
  };
}

async function fetchDefaultModelDraft(model_type, model_name = "") {
  const res = await fetch(`${API_BASE}/api/models/default-config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model_type, model_name }),
  });

  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

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

function needsReferenceImpedance(baseType) {
  return (
    typeof baseType === "string" &&
    (baseType.includes("_Inductor") || baseType.includes("_Transformer"))
  );
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
    z0: params.z0 === undefined ? 50.0 : Number(params.z0),
    feature_noise_std:
      params.feature_noise_std === undefined ? 0.01 : Number(params.feature_noise_std),
    target_noise_std:
      params.target_noise_std === undefined ? 0.005 : Number(params.target_noise_std),
    n_augment:
      params.n_augment === undefined ? 3 : Number(params.n_augment),
    clip: params.clip === undefined ? true : Boolean(params.clip),
  };
}

function buildTranslateConfigFromForm(form) {
  const baseType = TRANSLATION_BASE_TYPES.includes(form.baseType)
    ? form.baseType
    : "FFD";

  const augmented = !!form.augmented;
  const translation_type = augmented ? `${baseType}_augmented` : baseType;

  const translation_params = {};

  if (needsReferenceImpedance(baseType)) {
    translation_params.z0 = Number(form.z0 || 50.0);
  }

  if (augmented) {
    translation_params.feature_noise_std = Number(form.feature_noise_std || 0);
    translation_params.target_noise_std = Number(form.target_noise_std || 0);
    translation_params.n_augment = Number(form.n_augment || 0);
    translation_params.clip = !!form.clip;
  }

  return {
    translation_type,
    translation_params,
  };
}

function normalizeSelection(selection) {
  const src =
    selection && typeof selection === "object" && !Array.isArray(selection)
      ? selection
      : {};

  const normalizeList = (value) =>
    Array.isArray(value)
      ? value.map((x) => String(x).trim()).filter(Boolean)
      : [];

  return {
    x_names: normalizeList(src.x_names),
    y_names: normalizeList(src.y_names),
  };
}

function reconcileSelectionWithPreview(selection, preview) {
  const next = normalizeSelection(selection);
  const xAvailable = new Set(preview?.selection?.x?.selectable_names || []);
  const yAvailable = new Set(preview?.selection?.y?.selectable_names || []);

  const x_names = next.x_names.filter((name) => xAvailable.has(name));
  const y_names = next.y_names.filter((name) => yAvailable.has(name));

  return {
    x_names: x_names.length ? x_names : preview?.selection?.x?.selected_names || [],
    y_names: y_names.length ? y_names : preview?.selection?.y?.selected_names || [],
  };
}

function TranslationConfigForm({ value, onChange, disabled }) {
  const showZ0 = needsReferenceImpedance(value.baseType);

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

        {showZ0 ? (
          <label style={{ display: "grid", gap: 6 }}>
            <span>Reference impedance Z0</span>
            <input
              type="number"
              step="any"
              value={value.z0}
              onChange={(e) =>
                onChange((prev) => ({
                  ...prev,
                  z0: e.target.value,
                }))
              }
              disabled={disabled}
            />
          </label>
        ) : null}

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

            <label
              style={{
                display: "flex",
                gap: 8,
                alignItems: "center",
                marginTop: 24,
              }}
            >
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

function SelectionList({ title, info, value, onChange, disabled }) {
  const names = info?.selectable_names || [];
  const selected = Array.isArray(value) ? value : [];
  const selectedSet = new Set(selected);

  if (!names.length) {
    return (
      <div style={{ border: "1px solid #ddd", padding: 12, background: "#fafafa" }}>
        <div style={{ fontWeight: "bold", marginBottom: 8 }}>{title}</div>
        <div style={{ opacity: 0.7 }}>No translated fields available yet.</div>
      </div>
    );
  }

  const toggle = (name) => {
    const next = selectedSet.has(name)
      ? selected.filter((x) => x !== name)
      : [...selected, name];
    onChange(next);
  };

  return (
    <div style={{ border: "1px solid #ddd", padding: 12, background: "#fafafa" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <div>
          <div style={{ fontWeight: "bold" }}>{title}</div>
          <div style={{ fontSize: 12, opacity: 0.7 }}>
            {info?.mode === "grouped"
              ? `Grouped selection • each item maps to ${info?.group_size || 1} translated columns`
              : "Direct translated columns"}
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button type="button" onClick={() => onChange([...names])} disabled={disabled}>All</button>
          <button type="button" onClick={() => onChange([])} disabled={disabled}>None</button>
        </div>
      </div>

      <div style={{ maxHeight: 220, overflow: "auto", border: "1px solid #e5e5e5", background: "#fff", padding: 8 }}>
        <div style={{ display: "grid", gap: 6 }}>
          {names.map((name) => (
            <label key={name} style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                type="checkbox"
                checked={selectedSet.has(name)}
                onChange={() => toggle(name)}
                disabled={disabled}
              />
              <span>{name}</span>
            </label>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>
        Selected: {selected.length} / {names.length}
      </div>
    </div>
  );
}

function SectionCard({ title, subtitle, children }) {
  return (
    <div style={{ border: "1px solid #ddd", padding: 12, background: "#fafafa", minWidth: 0 }}>
      <div style={{ fontWeight: "bold", marginBottom: 6 }}>{title}</div>
      {subtitle ? <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 10 }}>{subtitle}</div> : null}
      <div style={{ display: "grid", gap: 10, minWidth: 0 }}>{children}</div>
    </div>
  );
}


function buildTranslatedFieldOptions(preview, selectedNames, axis) {
  const info = preview?.selection?.[axis];
  const selectableNames = Array.isArray(info?.selectable_names) ? info.selectable_names : [];
  const selectedFromPreview = Array.isArray(info?.selected_names) ? info.selected_names : [];
  const chosenNames = Array.isArray(selectedNames) && selectedNames.length
    ? selectedNames.filter((name) => selectableNames.includes(name))
    : (selectedFromPreview.length ? selectedFromPreview : selectableNames);

  const mode = info?.mode || "direct";
  const groupSize = Number(info?.group_size || 1);

  let offset = 0;
  return chosenNames.map((name) => {
    const width = mode === "grouped" ? Math.max(1, groupSize) : 1;
    const indices = Array.from({ length: width }, (_, i) => offset + i);
    offset += width;
    return { name, indices, width };
  });
}


function getTranslatedAxisFlatWidth(preview, selectedNames, axis) {
  const options = buildTranslatedFieldOptions(preview, selectedNames, axis);
  const total = options.reduce((sum, item) => sum + Number(item.width || 0), 0);
  if (total > 0) return total;
  const flatWidth = Number(preview?.selection?.[axis]?.flat_width || 0);
  return flatWidth > 0 ? flatWidth : 1;
}

function sanitizeNodeBaseName(name) {
  return String(name || "node")
    .trim()
    .replace(/\s+/g, "_")
    .replace(/[^A-Za-z0-9_]/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase() || "node";
}

function buildUniqueNodeName(existingNames, baseName) {
  const used = new Set((existingNames || []).filter(Boolean));
  const base = sanitizeNodeBaseName(baseName);
  if (!used.has(base)) return base;
  let idx = 2;
  while (used.has(`${base}_${idx}`)) idx += 1;
  return `${base}_${idx}`;
}

function renderRegularizerEditor({ regularizer, onChange, disabled }) {
  const type = regularizer?.type || "none";
  return (
    <>
      <label style={{ display: "grid", gap: 6 }}>
        <span>Regularizer</span>
        <select
          value={type}
          onChange={(e) => {
            const nextType = e.target.value;
            if (nextType === "none") {
              onChange(undefined);
            } else if (nextType === "l1_l2") {
              onChange({ type: "l1_l2", l1: regularizer?.l1 ?? 0.001, l2: regularizer?.l2 ?? 0.001 });
            } else {
              onChange({ type: nextType, value: regularizer?.value ?? 0.001 });
            }
          }}
          disabled={disabled}
        >
          {REGULARIZER_TYPE_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}
        </select>
      </label>
      {type === "l1" || type === "l2" ? (
        <label style={{ display: "grid", gap: 6 }}>
          <span>Regularizer value</span>
          <input
            type="number"
            step="any"
            value={regularizer?.value ?? 0.001}
            onChange={(e) => onChange({ ...regularizer, type, value: Number(e.target.value || 0) })}
            disabled={disabled}
          />
        </label>
      ) : null}
      {type === "l1_l2" ? (
        <>
          <label style={{ display: "grid", gap: 6 }}>
            <span>L1</span>
            <input
              type="number"
              step="any"
              value={regularizer?.l1 ?? 0.001}
              onChange={(e) => onChange({ ...regularizer, type: "l1_l2", l1: Number(e.target.value || 0) })}
              disabled={disabled}
            />
          </label>
          <label style={{ display: "grid", gap: 6 }}>
            <span>L2</span>
            <input
              type="number"
              step="any"
              value={regularizer?.l2 ?? 0.001}
              onChange={(e) => onChange({ ...regularizer, type: "l1_l2", l2: Number(e.target.value || 0) })}
              disabled={disabled}
            />
          </label>
        </>
      ) : null}
    </>
  );
}


function AnnModelConfigEditor({ value, onChange, disabled, translatePreview, translateSelection }) {
  const cfg = normalizeAnnModelConfig(value);
  const architectureType = cfg.architecture_type || "sequential";
  const selectedXNames = translateSelection?.x_names || [];
  const selectedYNames = translateSelection?.y_names || [];
  const xNamesKey = selectedXNames.join("\0");
  const yNamesKey = selectedYNames.join("\0");
  const translatedInputOptions = buildTranslatedFieldOptions(translatePreview, selectedXNames, "x");
  const translatedTargetOptions = buildTranslatedFieldOptions(translatePreview, selectedYNames, "y");
  const [showGraphBuildTable, setShowGraphBuildTable] = useState(false);
  const [showKerasArchitecture, setShowKerasArchitecture] = useState(false);
  const [kerasArchitectureLoading, setKerasArchitectureLoading] = useState(false);
  const [kerasArchitectureError, setKerasArchitectureError] = useState("");
  const [kerasArchitectureText, setKerasArchitectureText] = useState("");

  useEffect(() => {
    commit((prev) => {
      const defF = prev.normalization?.feature_method ?? "standard";
      const defT = prev.normalization?.target_method ?? "standard";
      const sx = translateSelection?.x_names || [];
      const sy = translateSelection?.y_names || [];
      let nextFm = { ...(prev.normalization?.feature_methods || {}) };
      let nextTm = { ...(prev.normalization?.target_methods || {}) };
      let changed = false;
      for (const name of sx) {
        if (nextFm[name] === undefined) {
          nextFm[name] = defF;
          changed = true;
        }
      }
      if (sx.length > 0) {
        for (const k of Object.keys(nextFm)) {
          if (!sx.includes(k)) {
            delete nextFm[k];
            changed = true;
          }
        }
      }
      for (const name of sy) {
        if (nextTm[name] === undefined) {
          nextTm[name] = defT;
          changed = true;
        }
      }
      if (sy.length > 0) {
        for (const k of Object.keys(nextTm)) {
          if (!sy.includes(k)) {
            delete nextTm[k];
            changed = true;
          }
        }
      }
      if (!changed) return prev;
      prev.normalization = { ...prev.normalization, feature_methods: nextFm, target_methods: nextTm };
      return prev;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reconcile maps when Translation X/Y selection set changes
  }, [xNamesKey, yNamesKey]);

  const graphBuildPreviewRows = useMemo(() => buildGraphBuildPreviewRows(cfg.graph), [cfg.graph]);
  const previewInputDim = useMemo(
    () => getTranslatedAxisFlatWidth(translatePreview, selectedXNames, "x"),
    [translatePreview, selectedXNames]
  );
  const previewOutputDim = useMemo(
    () => getTranslatedAxisFlatWidth(translatePreview, selectedYNames, "y"),
    [translatePreview, selectedYNames]
  );

  const commit = (updater) => {
    const next = typeof updater === "function" ? updater(cloneJson(cfg)) : cloneJson(updater);
    onChange(normalizeAnnModelConfig(next));
  };

  const setTop = (path, nextValue) => {
    commit((prev) => {
      let cur = prev;
      for (let i = 0; i < path.length - 1; i++) cur = cur[path[i]];
      cur[path[path.length - 1]] = nextValue;
      return prev;
    });
  };

  const addSeqLayer = (type = "Dense") => {
    commit((prev) => {
      prev.architecture.push(
        type === "Dropout"
          ? { type: "Dropout", rate: 0.1 }
          : { type: "Dense", units: 64, activation: "relu" }
      );
      return prev;
    });
  };

  const moveSequentialLayer = (index, direction) => {
    commit((prev) => {
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= prev.architecture.length) return prev;
      const tmp = prev.architecture[index];
      prev.architecture[index] = prev.architecture[nextIndex];
      prev.architecture[nextIndex] = tmp;
      return prev;
    });
  };

  const addGraphNode = (op = "Dense") => {
    const base =
      op === "Slice"
        ? { name: "", op: "Slice", inputs: [cfg.graph.input_name || "features"], indices: [0] }
        : op === "Concatenate"
        ? { name: "", op: "Concatenate", inputs: [] }
        : op === "Dropout"
        ? { name: "", op: "Dropout", inputs: [], rate: 0.1 }
        : op === "Identity"
        ? { name: "", op: "Identity", inputs: [] }
        : { name: "", op: "Dense", inputs: [], units: 64, activation: "relu" };
    commit((prev) => {
      prev.graph.nodes.push(base);
      return prev;
    });
  };

  const moveGraphNode = (index, direction) => {
    commit((prev) => {
      const nextIndex = index + direction;
      if (nextIndex < 0 || nextIndex >= prev.graph.nodes.length) return prev;
      const tmp = prev.graph.nodes[index];
      prev.graph.nodes[index] = prev.graph.nodes[nextIndex];
      prev.graph.nodes[nextIndex] = tmp;
      return prev;
    });
  };


  async function fetchKerasArchitecturePreview() {
    try {
      setKerasArchitectureLoading(true);
      setKerasArchitectureError("");
      setShowKerasArchitecture(true);
      const res = await fetch(`${API_BASE}/api/models/ann/preview-architecture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_config: cloneJson(cfg),
          input_dim: previewInputDim,
          output_dim: previewOutputDim,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setKerasArchitectureText(String(data?.summary_text || ""));
    } catch (err) {
      setKerasArchitectureError(err?.message || String(err));
    } finally {
      setKerasArchitectureLoading(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 12, minWidth: 0 }}>
      <SectionCard title="ANN model_config" subtitle="Interactive editor for ANN settings and architecture.">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
          <label style={{ display: "grid", gap: 6 }}>
            <span>Model name</span>
            <input value={cfg.model_name || ""} onChange={(e) => setTop(["model_name"], e.target.value)} disabled={disabled} />
          </label>
          <label style={{ display: "grid", gap: 6 }}>
            <span>Default feature normalization</span>
            <select value={cfg.normalization.feature_method} onChange={(e) => setTop(["normalization", "feature_method"], e.target.value)} disabled={disabled}>
              {NORMALIZATION_METHOD_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
          </label>
          <label style={{ display: "grid", gap: 6 }}>
            <span>Default target normalization</span>
            <select value={cfg.normalization.target_method} onChange={(e) => setTop(["normalization", "target_method"], e.target.value)} disabled={disabled}>
              {NORMALIZATION_METHOD_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}
            </select>
          </label>
        </div>

        <div style={{ display: "grid", gap: 10, marginTop: 4 }}>
          <div style={{ fontSize: 13, color: "#444" }}>
            Per-field overrides (logical names from Translation &amp; data). Each dropdown below overrides the default feature / target normalization for that name only. New fields copy those defaults. Grouped fields share one name and one scaler across their flat columns.
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16, alignItems: "start" }}>
            <div style={{ display: "grid", gap: 8 }}>
              <strong>Features (X)</strong>
              {selectedXNames.length === 0 ? (
                <span style={{ color: "#888" }}>No X fields selected — choose inputs under Translation &amp; data.</span>
              ) : (
                <div style={{ display: "grid", gap: 6 }}>
                  {selectedXNames.map((name) => (
                    <label key={name} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 8, alignItems: "center" }}>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }} title={name}>{name}</span>
                      <select
                        value={cfg.normalization.feature_methods?.[name] ?? cfg.normalization.feature_method}
                        onChange={(e) => {
                          const v = e.target.value;
                          commit((prev) => {
                            prev.normalization = prev.normalization || {};
                            prev.normalization.feature_methods = { ...(prev.normalization.feature_methods || {}), [name]: v };
                            return prev;
                          });
                        }}
                        disabled={disabled}
                      >
                        {NORMALIZATION_METHOD_OPTIONS.map((x) => (
                          <option key={x} value={x}>{x}</option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
              )}
            </div>
            <div style={{ display: "grid", gap: 8 }}>
              <strong>Targets (Y)</strong>
              {selectedYNames.length === 0 ? (
                <span style={{ color: "#888" }}>No Y fields selected — choose outputs under Translation &amp; data.</span>
              ) : (
                <div style={{ display: "grid", gap: 6 }}>
                  {selectedYNames.map((name) => (
                    <label key={name} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 8, alignItems: "center" }}>
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }} title={name}>{name}</span>
                      <select
                        value={cfg.normalization.target_methods?.[name] ?? cfg.normalization.target_method}
                        onChange={(e) => {
                          const v = e.target.value;
                          commit((prev) => {
                            prev.normalization = prev.normalization || {};
                            prev.normalization.target_methods = { ...(prev.normalization.target_methods || {}), [name]: v };
                            return prev;
                          });
                        }}
                        disabled={disabled}
                      >
                        {NORMALIZATION_METHOD_OPTIONS.map((x) => (
                          <option key={x} value={x}>{x}</option>
                        ))}
                      </select>
                    </label>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

      </SectionCard>

      <SectionCard title="Training">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 12 }}>
          <label style={{ display: "grid", gap: 6 }}><span>Epochs</span><input type="number" value={cfg.training.epochs} onChange={(e) => setTop(["training", "epochs"], Number(e.target.value || 0))} disabled={disabled} /></label>
          <label style={{ display: "grid", gap: 6 }}><span>Batch size</span><input type="number" value={cfg.training.batch_size} onChange={(e) => setTop(["training", "batch_size"], Number(e.target.value || 0))} disabled={disabled} /></label>
          <label style={{ display: "grid", gap: 6 }}><span>Loss</span><input value={cfg.training.loss || ""} onChange={(e) => setTop(["training", "loss"], e.target.value)} disabled={disabled} /></label>
          <label style={{ display: "grid", gap: 6 }}><span>Metrics (csv)</span><CsvTextInput value={cfg.training.metrics} onCommit={(next) => setTop(["training", "metrics"], next)} disabled={disabled} /></label>
          <label style={{ display: "grid", gap: 6 }}><span>Validation split</span><input type="number" step="any" value={cfg.training.validation_split} onChange={(e) => setTop(["training", "validation_split"], Number(e.target.value || 0))} disabled={disabled} /></label>
          <label style={{ display: "grid", gap: 6 }}><span>Optimizer</span><select value={cfg.training.optimizer.type} onChange={(e) => setTop(["training", "optimizer", "type"], e.target.value)} disabled={disabled}>{OPTIMIZER_TYPE_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}</select></label>
          <label style={{ display: "grid", gap: 6 }}><span>Learning rate</span><input type="number" step="any" value={cfg.training.optimizer.learning_rate} onChange={(e) => setTop(["training", "optimizer", "learning_rate"], Number(e.target.value || 0))} disabled={disabled} /></label>
          <label style={{ display: "grid", gap: 6 }}><span>Momentum</span><input type="number" step="any" value={cfg.training.optimizer.momentum} onChange={(e) => setTop(["training", "optimizer", "momentum"], Number(e.target.value || 0))} disabled={disabled} /></label>
        </div>
      </SectionCard>

      <SectionCard title="Early stopping">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
          <label style={{ display: "grid", gap: 6 }}><span>Monitor</span><input value={cfg.early_stopping.monitor || ""} onChange={(e) => setTop(["early_stopping", "monitor"], e.target.value)} disabled={disabled} /></label>
          <label style={{ display: "grid", gap: 6 }}><span>Patience</span><input type="number" value={cfg.early_stopping.patience} onChange={(e) => setTop(["early_stopping", "patience"], Number(e.target.value || 0))} disabled={disabled} /></label>
          <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 24 }}>
            <input type="checkbox" checked={!!cfg.early_stopping.restore_best_weights} onChange={(e) => setTop(["early_stopping", "restore_best_weights"], e.target.checked)} disabled={disabled} />
            Restore best weights
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Architecture builder">
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span>Architecture type</span>
          <select value={architectureType} onChange={(e) => setTop(["architecture_type"], e.target.value)} disabled={disabled}>
            <option value="sequential">sequential</option>
            <option value="graph">graph</option>
          </select>
        </label>

        {architectureType === "sequential" ? (
          <div style={{ display: "grid", gap: 10 }}>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button type="button" onClick={() => addSeqLayer("Dense")} disabled={disabled}>Add Dense</button>
              <button type="button" onClick={() => addSeqLayer("Dropout")} disabled={disabled}>Add Dropout</button>
            </div>
            {(cfg.architecture || []).map((layer, index) => (
              <div key={index} style={{ border: "1px solid #e0e0e0", background: "#fff", padding: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
                  <strong>Layer {index + 1}</strong>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <button type="button" onClick={() => moveSequentialLayer(index, -1)} disabled={disabled || index === 0}>Up</button>
                    <button type="button" onClick={() => moveSequentialLayer(index, 1)} disabled={disabled || index === (cfg.architecture || []).length - 1}>Down</button>
                    <button type="button" onClick={() => commit((prev) => { prev.architecture.splice(index, 1); return prev; })} disabled={disabled}>Remove</button>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 }}>
                  <label style={{ display: "grid", gap: 6 }}><span>Type</span><select value={layer.type || "Dense"} onChange={(e) => commit((prev) => { const nextType = e.target.value; prev.architecture[index] = nextType === "Dropout" ? { type: "Dropout", rate: prev.architecture[index]?.rate ?? 0.1 } : { type: "Dense", units: prev.architecture[index]?.units ?? 64, activation: prev.architecture[index]?.activation || "relu", regularizer: prev.architecture[index]?.regularizer }; return prev; })} disabled={disabled}><option value="Dense">Dense</option><option value="Dropout">Dropout</option></select></label>
                  {layer.type === "Dense" ? (
                    <>
                      <label style={{ display: "grid", gap: 6 }}><span>Units</span><input value={layer.units ?? ""} onChange={(e) => commit((prev) => { prev.architecture[index] = { ...prev.architecture[index], units: e.target.value }; return prev; })} disabled={disabled} /></label>
                      <label style={{ display: "grid", gap: 6 }}><span>Activation</span><select value={layer.activation || "relu"} onChange={(e) => commit((prev) => { prev.architecture[index] = { ...prev.architecture[index], activation: e.target.value }; return prev; })} disabled={disabled}>{ACTIVATION_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}</select></label>
                      {renderRegularizerEditor({
                        regularizer: layer.regularizer,
                        disabled,
                        onChange: (nextRegularizer) => commit((prev) => {
                          const nextLayer = { ...prev.architecture[index] };
                          if (nextRegularizer) nextLayer.regularizer = nextRegularizer;
                          else delete nextLayer.regularizer;
                          prev.architecture[index] = nextLayer;
                          return prev;
                        }),
                      })}
                    </>
                  ) : null}
                  {layer.type === "Dropout" ? (
                    <label style={{ display: "grid", gap: 6 }}><span>Rate</span><input type="number" step="any" value={layer.rate ?? 0.1} onChange={(e) => commit((prev) => { prev.architecture[index] = { ...prev.architecture[index], rate: Number(e.target.value || 0) }; return prev; })} disabled={disabled} /></label>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
              <label style={{ display: "grid", gap: 6 }}><span>Input name</span><input value={cfg.graph.input_name || "features"} onChange={(e) => setTop(["graph", "input_name"], e.target.value)} disabled={disabled} /></label>
              <label style={{ display: "grid", gap: 6 }}><span>Outputs (csv node names)</span><CsvTextInput value={cfg.graph.outputs} onCommit={(next) => setTop(["graph", "outputs"], next)} disabled={disabled} /></label>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div style={{ border: "1px solid #e0e0e0", background: "#fff", padding: 10 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Translated input fields</div>
                <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 8 }}>
                  These are available after translation preview and X selection. Use them as guides for Slice-node indices.
                </div>
                {translatedInputOptions.length ? (
                  <div style={{ display: "grid", gap: 6 }}>
                    {translatedInputOptions.map((field) => (
                      <div key={field.name} style={{ padding: "8px 10px", border: "1px solid #ddd", borderRadius: 4, background: "#fafafa", fontSize: 12 }}>
                        <strong>{field.name}</strong> — indices [{field.indices.join(", ")}]
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Refresh translated fields and choose X fields to see available input references.</div>
                )}
              </div>
              <div style={{ border: "1px solid #e0e0e0", background: "#fff", padding: 10 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Translated target fields</div>
                <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 8 }}>
                  These are available after translation preview and Y selection. Use them as guides when naming final Dense heads and graph outputs.
                </div>
                {translatedTargetOptions.length ? (
                  <div style={{ display: "grid", gap: 6 }}>
                    {translatedTargetOptions.map((field) => (
                      <div key={field.name} style={{ padding: "8px 10px", border: "1px solid #ddd", borderRadius: 4, background: "#fafafa", fontSize: 12 }}>
                        <strong>{field.name}</strong> — width {field.width}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Refresh translated fields and choose Y fields to see available target references.</div>
                )}
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {GRAPH_OP_OPTIONS.map((op) => (
                <button key={op} type="button" onClick={() => addGraphNode(op)} disabled={disabled}>Add {op}</button>
              ))}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <div style={{ fontSize: 12, opacity: 0.75 }}>
                Show the build order that the backend graph builder will follow.
              </div>
              <button type="button" onClick={() => setShowGraphBuildTable((v) => !v)} disabled={disabled === true && !graphBuildPreviewRows.length}>
                {showGraphBuildTable ? "Hide build_graph_model table" : "Show build_graph_model table"}
              </button>
            </div>

            {showGraphBuildTable ? (
              <div style={{ overflowX: "auto", border: "1px solid #e0e0e0", background: "#fff" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: "#f5f5f5" }}>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #ddd" }}>Step</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #ddd" }}>Ref</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #ddd" }}>Kind</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #ddd" }}>Inputs</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #ddd" }}>Details</th>
                      <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #ddd" }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {graphBuildPreviewRows.map((row) => (
                      <tr key={`${row.kind}-${row.step}-${row.ref}`}>
                        <td style={{ padding: 8, borderBottom: "1px solid #eee", verticalAlign: "top" }}>{row.step}</td>
                        <td style={{ padding: 8, borderBottom: "1px solid #eee", verticalAlign: "top", fontFamily: "monospace" }}>{row.ref}</td>
                        <td style={{ padding: 8, borderBottom: "1px solid #eee", verticalAlign: "top" }}>{row.kind}</td>
                        <td style={{ padding: 8, borderBottom: "1px solid #eee", verticalAlign: "top", fontFamily: "monospace" }}>{row.inputs}</td>
                        <td style={{ padding: 8, borderBottom: "1px solid #eee", verticalAlign: "top" }}>{row.details || "—"}</td>
                        <td style={{ padding: 8, borderBottom: "1px solid #eee", verticalAlign: "top" }}>{row.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {(cfg.graph.nodes || []).map((node, index) => {
              const chosenFeature = translatedInputOptions.find((f) => listToCsv(f.indices) === listToCsv(node.indices));
              const availableRefs = [cfg.graph.input_name || "features", ...(cfg.graph.nodes || []).slice(0, index).map((x) => String(x.name || "").trim()).filter(Boolean)];
              return (
                <div key={index} style={{ border: "1px solid #e0e0e0", background: "#fff", padding: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
                    <strong>Node {index + 1}</strong>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      <button type="button" onClick={() => moveGraphNode(index, -1)} disabled={disabled || index === 0}>Up</button>
                      <button type="button" onClick={() => moveGraphNode(index, 1)} disabled={disabled || index === (cfg.graph.nodes || []).length - 1}>Down</button>
                      <button type="button" onClick={() => commit((prev) => { prev.graph.nodes.splice(index, 1); return prev; })} disabled={disabled}>Remove</button>
                    </div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 }}>
                    <label style={{ display: "grid", gap: 6 }}><span>Name</span><input placeholder={nodeNamePlaceholder(node.op, index)} value={node.name || ""} onChange={(e) => commit((prev) => { prev.graph.nodes[index] = { ...prev.graph.nodes[index], name: e.target.value }; return prev; })} disabled={disabled} /></label>
                    <label style={{ display: "grid", gap: 6 }}><span>Op</span><select value={node.op || "Dense"} onChange={(e) => commit((prev) => {
                      const op = e.target.value;
                      const current = { ...prev.graph.nodes[index], op };
                      if (op === "Slice") current.indices = current.indices || [0];
                      if (op === "Dropout") current.rate = current.rate ?? 0.1;
                      if (op === "Concatenate") current.axis = current.axis ?? -1;
                      if (op === "Dense") {
                        current.units = current.units ?? 64;
                        current.activation = current.activation || "relu";
                      }
                      prev.graph.nodes[index] = current;
                      return prev;
                    })} disabled={disabled}>{GRAPH_OP_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}</select></label>
                    <label style={{ display: "grid", gap: 6 }}><span>Inputs (csv)</span><CsvTextInput value={node.inputs} onCommit={(next) => commit((prev) => { prev.graph.nodes[index] = { ...prev.graph.nodes[index], inputs: next }; return prev; })} disabled={disabled} /></label>
                    <div style={{ display: "grid", gap: 6 }}>
                      <span>Available refs</span>
                      <div style={{ padding: "8px 10px", border: "1px solid #ddd", borderRadius: 4, background: "#fafafa", fontSize: 12 }}>
                        {availableRefs.join(", ") || "No refs yet"}
                      </div>
                    </div>

                    {node.op === "Slice" ? (
                      <>
                        <label style={{ display: "grid", gap: 6 }}>
                          <span>Translated feature</span>
                          <select
                            value={chosenFeature?.name || ""}
                            onChange={(e) => {
                              const feature = translatedInputOptions.find((f) => f.name === e.target.value);
                              if (!feature) return;
                              commit((prev) => {
                                const current = { ...prev.graph.nodes[index] };
                                current.inputs = [prev.graph.input_name || "features"];
                                current.indices = feature.indices;
                                prev.graph.nodes[index] = current;
                                return prev;
                              });
                            }}
                            disabled={disabled || !translatedInputOptions.length}
                          >
                            <option value="">Pick feature…</option>
                            {translatedInputOptions.map((f) => <option key={f.name} value={f.name}>{`${f.name} (${listToCsv(f.indices)})`}</option>)}
                          </select>
                        </label>
                        <label style={{ display: "grid", gap: 6 }}><span>Indices (csv)</span><NumberCsvTextInput value={node.indices} onCommit={(next) => commit((prev) => { prev.graph.nodes[index] = { ...prev.graph.nodes[index], indices: next }; return prev; })} disabled={disabled} /></label>
                      </>
                    ) : null}

                    {node.op === "Dense" ? (
                      <>
                        <label style={{ display: "grid", gap: 6 }}><span>Units</span><input value={node.units ?? ""} onChange={(e) => commit((prev) => { prev.graph.nodes[index] = { ...prev.graph.nodes[index], units: e.target.value }; return prev; })} disabled={disabled} /></label>
                        <label style={{ display: "grid", gap: 6 }}><span>Activation</span><select value={node.activation || "relu"} onChange={(e) => commit((prev) => { prev.graph.nodes[index] = { ...prev.graph.nodes[index], activation: e.target.value }; return prev; })} disabled={disabled}>{ACTIVATION_OPTIONS.map((x) => <option key={x} value={x}>{x}</option>)}</select></label>
                        {renderRegularizerEditor({
                          regularizer: node.regularizer,
                          disabled,
                          onChange: (nextRegularizer) => commit((prev) => {
                            const nextNode = { ...prev.graph.nodes[index] };
                            if (nextRegularizer) nextNode.regularizer = nextRegularizer;
                            else delete nextNode.regularizer;
                            prev.graph.nodes[index] = nextNode;
                            return prev;
                          }),
                        })}
                      </>
                    ) : null}

                    {node.op === "Dropout" ? (
                      <label style={{ display: "grid", gap: 6 }}><span>Rate</span><input type="number" step="any" value={node.rate ?? 0.1} onChange={(e) => commit((prev) => { prev.graph.nodes[index] = { ...prev.graph.nodes[index], rate: Number(e.target.value || 0) }; return prev; })} disabled={disabled} /></label>
                    ) : null}

                    {node.op === "Concatenate" ? (
                      <label style={{ display: "grid", gap: 6 }}><span>Axis</span><input type="number" value={node.axis ?? -1} onChange={(e) => commit((prev) => { prev.graph.nodes[index] = { ...prev.graph.nodes[index], axis: Number(e.target.value || 0) }; return prev; })} disabled={disabled} /></label>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <div style={{ display: "grid", gap: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ fontSize: 12, opacity: 0.75 }}>
              Build the current ANN config on the backend and show the real Keras model.summary() output.
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => {
                  if (showKerasArchitecture) {
                    setShowKerasArchitecture(false);
                  } else {
                    void fetchKerasArchitecturePreview();
                  }
                }}
                disabled={disabled || kerasArchitectureLoading}
              >
                {showKerasArchitecture ? "Hide Keras architecture" : "View Keras architecture"}
              </button>
              <button type="button" onClick={fetchKerasArchitecturePreview} disabled={disabled || kerasArchitectureLoading}>
                {kerasArchitectureLoading ? "Loading…" : "Refresh Keras architecture"}
              </button>
            </div>
          </div>

          {showKerasArchitecture ? (
            <div style={{ display: "grid", gap: 8, minWidth: 0, width: "100%" }}>
              <div style={{ fontSize: 12, opacity: 0.75 }}>
                Preview dimensions sent to backend: input_dim={previewInputDim}, output_dim={previewOutputDim}
              </div>
              {kerasArchitectureError ? (
                <div style={{ color: "#b00020", whiteSpace: "pre-wrap", fontSize: 13 }}>
                  {kerasArchitectureError}
                </div>
              ) : null}
              <div
                style={{
                  width: "100%",
                  maxWidth: "100%",
                  minWidth: 0,
                  overflowX: "scroll",
                  overflowY: "auto",
                  maxHeight: 560,
                  border: "1px solid #ddd",
                  borderRadius: 6,
                  background: "#fff",
                  boxSizing: "border-box",
                  WebkitOverflowScrolling: "touch",
                }}
              >
                <pre
                  style={{
                    margin: 0,
                    padding: 12,
                    display: "block",
                    minWidth: "max-content",
                    width: "max-content",
                    maxWidth: "none",
                    fontSize: 12,
                    lineHeight: 1.45,
                    whiteSpace: "pre",
                    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                  }}
                >
                  {kerasArchitectureLoading
                    ? "Loading…"
                    : kerasArchitectureText || "No Keras architecture loaded yet."}
                </pre>
              </div>
              <div style={{ fontSize: 11, opacity: 0.65 }}>
                Use horizontal scroll for wide summaries.
              </div>
            </div>
          ) : null}
        </div>
      </SectionCard>
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
  const [annConfigForm, setAnnConfigForm] = useState(
    normalizeAnnModelConfig(DEFAULT_DRAFT.model_config)
  );
  const [useRawModelConfig, setUseRawModelConfig] = useState(false);
  const [translateSelection, setTranslateSelection] = useState(
    normalizeSelection(DEFAULT_DRAFT.translate_config?.selection)
  );
  const [translatePreview, setTranslatePreview] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  const [sweepOptions, setSweepOptions] = useState([]);
  const [report, setReport] = useState(DEFAULT_REPORT);
  const [lines, setLines] = useState([]);
  const [predictionInput, setPredictionInput] = useState("[[10, 5000000]]");
  const [predictionOutput, setPredictionOutput] = useState("");
  const [apiError, setApiError] = useState("");
  const [predicting, setPredicting] = useState(false);

  const esRef = useRef(null);
  const scrollerRef = useRef(null);
  const previewAbortRef = useRef(null);
  const previewRequestIdRef = useRef(0);

  useEffect(() => {
    refreshSweepOptions();
  }, []);

  useEffect(() => {
    return () => {
      if (previewAbortRef.current) {
        previewAbortRef.current.abort();
      }
    };
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
    if (!draft.sweep_name) {
      setTranslatePreview(null);
      return;
    }

    const handle = setTimeout(() => {
      refreshTranslatePreview().catch(() => {});
    }, 250);

    return () => clearTimeout(handle);
  }, [draft.sweep_name, translateForm, activeModel]);

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

  function syncAnnEditors(nextConfig) {
    const normalized = normalizeAnnModelConfig(nextConfig);
    setAnnConfigForm(normalized);
    setModelConfigText(safePretty(normalized));
  }

  function syncEditorsFromDraft(nextDraft) {
    setTranslateForm(normalizeTranslateConfig(nextDraft.translate_config));
    setTranslateSelection(normalizeSelection(nextDraft.translate_config?.selection));

    if (String(nextDraft.model_type || "").toUpperCase() === "ANN") {
      syncAnnEditors(nextDraft.model_config);
    } else {
      setModelConfigText(safePretty(nextDraft.model_config));
    }
  }

  function handleAnnConfigChange(nextValue) {
    const normalized = normalizeAnnModelConfig(nextValue);
    setAnnConfigForm(normalized);
    setModelConfigText(safePretty(normalized));
  }

  function buildDraftFromEditors() {
    const translate_config = buildTranslateConfigFromForm(translateForm);
    translate_config.selection = normalizeSelection(translateSelection);
    const isAnn = String(draft.model_type || "ANN").toUpperCase() === "ANN";
    const model_config = isAnn && !useRawModelConfig
      ? cloneJson(annConfigForm)
      : parseJsonText(modelConfigText, "Model config");

    return {
      sweep_name: draft.sweep_name || "",
      model_type: String(draft.model_type || "ANN").toUpperCase(),
      translate_config,
      model_config,
    };
  }

  function clearTranslatedFieldSelection() {
    setTranslatePreview(null);
    setTranslateSelection({ x_names: [], y_names: [] });
  }

  function handleTranslateFormChange(updater) {
    clearTranslatedFieldSelection();
    setTranslateForm(updater);
  }

  async function refreshTranslatePreview(customDraft = null) {
    const sourceDraft = customDraft || buildDraftFromEditors();
    if (!sourceDraft.sweep_name) {
      if (previewAbortRef.current) {
        previewAbortRef.current.abort();
        previewAbortRef.current = null;
      }
      setTranslatePreview(null);
      setPreviewLoading(false);
      return;
    }

    if (previewAbortRef.current) {
      previewAbortRef.current.abort();
    }

    const controller = new AbortController();
    previewAbortRef.current = controller;
    const requestId = ++previewRequestIdRef.current;

    try {
      setPreviewLoading(true);
      setApiError("");
      const res = await fetch(`${API_BASE}/api/models/translate-preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sweep_name: sourceDraft.sweep_name,
          config: sourceDraft,
        }),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      if (requestId !== previewRequestIdRef.current) return;

      const preview = data.preview || null;
      setTranslatePreview(preview);
      setTranslateSelection((prev) => reconcileSelectionWithPreview(prev, preview));
    } catch (err) {
      if (err?.name === "AbortError") return;
      if (requestId !== previewRequestIdRef.current) return;
      setTranslatePreview(null);
      setApiError(err?.message || String(err));
    } finally {
      if (requestId === previewRequestIdRef.current) {
        setPreviewLoading(false);
      }
      if (previewAbortRef.current === controller) {
        previewAbortRef.current = null;
      }
    }
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
      return {
        nextActiveModel: "",
        nextRunning: false,
        nextDraft: DEFAULT_DRAFT,
      };
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
        body: JSON.stringify({
          model_name: name,
          model_type: draft.model_type,
        }),
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
      const res = await fetch(
        `${API_BASE}/api/models/${encodeURIComponent(name)}`,
        {
          method: "DELETE",
        }
      );
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

  async function renameModel(name) {
    const next = window.prompt(`Rename model "${name}" to:`, name);
    if (next == null) return;
    const trimmed = next.trim();
    if (!trimmed || trimmed === name) return;

    try {
      setApiError("");
      const res = await fetch(`${API_BASE}/api/models/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from_name: name, to_name: trimmed }),
      });
      if (!res.ok) throw new Error(await res.text());

      const data = await res.json();
      const newName = data.model_name || trimmed;

      if (name === activeModel) {
        await openModel(newName);
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
    <div style={{ minWidth: 0, width: "100%" }}>
      <h3>Model</h3>

      {apiError ? (
        <div
          style={{ marginBottom: 12, color: "crimson", whiteSpace: "pre-wrap" }}
        >
          API error: {apiError}
        </div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "280px minmax(0, 1fr)",
          gap: 16,
          alignItems: "start",
          width: "100%",
          minWidth: 0,
        }}
      >
        <div
          style={{
            border: "1px solid #d9dee7",
            padding: 12,
            background: "#fbfcfe",
            borderRadius: 10,
          }}
        >
          <h4 style={{ marginTop: 0, marginBottom: 12 }}>Models</h4>

          <div
            style={{
              display: "grid",
              display: "flex",
              gap: 8,
              marginBottom: 14,
              alignItems: "center",
            }}
          >
            <input
              value={newModelName}
              onChange={(e) => setNewModelName(e.target.value)}
              placeholder="New model name"
              style={{
                flex: 1,
                minWidth: 0,
                padding: "9px 10px",
                border: "1px solid #d0d7de",
                borderRadius: 8,
                background: "#fff",
              }}
            />
            <button
              onClick={createModel}
              style={{
                padding: "9px 14px",
                borderRadius: 8,
                border: "1px solid #cfd6e4",
                background: "#fff",
                fontWeight: 600,
                whiteSpace: "nowrap",
              }}
            >
              Create
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {models.length === 0 ? (
              <div style={{ opacity: 0.7 }}>No models yet.</div>
            ) : (
              models.map((name) => {
                const isActive = name === activeModel;
                return (
                  <div
                    key={name}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "minmax(0, 1fr) auto auto",
                      gap: 6,
                      alignItems: "center",
                    }}
                  >
                    <button
                      onClick={() => openModel(name)}
                      style={{
                        flex: 1,
                        minWidth: 0,
                        textAlign: "left",
                        fontWeight: isActive ? 700 : 500,
                        padding: "10px 12px",
                        borderRadius: 8,
                        border: isActive ? "1px solid #b9c9ef" : "1px solid #e2e8f0",
                        background: isActive ? "#eef4ff" : "#fff",
                        color: "#1f2937",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={name}
                    >
                      {name}
                    </button>
                    <button
                      type="button"
                      onClick={() => renameModel(name)}
                      disabled={running && activeModel === name}
                      aria-label={`Rename model ${name}`}
                      title="Rename this model"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: 36,
                        height: 36,
                        padding: 0,
                        borderRadius: 8,
                        border: "1px solid #e2e8f0",
                        background: "#fff",
                        color: "#334155",
                        flexShrink: 0,
                      }}
                    >
                      <IconPencil />
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteModel(name)}
                      disabled={running && activeModel === name}
                      aria-label={`Delete model ${name}`}
                      title="Delete this model"
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: 36,
                        height: 36,
                        padding: 0,
                        borderRadius: 8,
                        border: "1px solid #e2e8f0",
                        background: "#fff",
                        color: "#7f1d1d",
                        flexShrink: 0,
                      }}
                    >
                      <IconTrash />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div style={{ border: "1px solid #ccc", padding: 12, minWidth: 0 }}>
          <div
            style={{
              display: "flex",
              gap: 12,
              flexWrap: "wrap",
              alignItems: "center",
              marginBottom: 12,
            }}
          >
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
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <div style={{ fontWeight: "bold", marginBottom: 6 }}>
                    Model Availability
                  </div>
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
                  <div
                    style={{
                      display: "flex",
                      gap: 8,
                      flexWrap: "wrap",
                      alignItems: "flex-start",
                    }}
                  >
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
              <select
                value={draft.model_type}
                onChange={async (e) => {
                  const newType = e.target.value;

                  try {
                    const newDraft = await fetchDefaultModelDraft(
                      newType,
                      activeModel
                    );
                    setDraft(newDraft);
                    setSavedSnapshot(cloneJson(newDraft));
                    syncEditorsFromDraft(newDraft);
                    setTranslatePreview(null);
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
                  clearTranslatedFieldSelection();
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

          <div style={{ display: "grid", gap: 12, marginBottom: 16, minWidth: 0 }}>
            <TranslationConfigForm
              value={translateForm}
              onChange={handleTranslateFormChange}
              disabled={running}
            />


            <div style={{ display: "grid", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontWeight: "bold" }}>Translated training fields</div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>
                    Names are derived from the translated data. For flattened translations, each item selects the full translated block for that field.
                  </div>
                </div>
                <button type="button" onClick={() => refreshTranslatePreview()} disabled={running || !draft.sweep_name || previewLoading}>
                  {previewLoading ? "Loading…" : "Refresh translated fields"}
                </button>
              </div>

              {translatePreview ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <SelectionList
                    title="Include X fields"
                    info={translatePreview.selection?.x}
                    value={translateSelection.x_names}
                    onChange={(next) => setTranslateSelection((prev) => ({ ...prev, x_names: next }))}
                    disabled={running || previewLoading}
                  />
                  <SelectionList
                    title="Include Y fields"
                    info={translatePreview.selection?.y}
                    value={translateSelection.y_names}
                    onChange={(next) => setTranslateSelection((prev) => ({ ...prev, y_names: next }))}
                    disabled={running || previewLoading}
                  />
                </div>
              ) : (
                <div style={{ border: "1px dashed #ccc", padding: 12, background: "#fafafa", fontSize: 13, opacity: 0.8 }}>
                  Select a sweep to preview translated X/Y fields.
                </div>
              )}
            </div>

            <div style={{ display: "grid", gap: 12 }}>
              {String(draft.model_type || "ANN").toUpperCase() === "ANN" ? (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <div>
                      <div style={{ marginBottom: 6, fontWeight: "bold" }}>ANN configuration</div>
                      <div style={{ fontSize: 12, opacity: 0.7 }}>Use the form editor for day-to-day work, or switch to raw JSON for advanced edits.</div>
                    </div>
                    <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <input type="checkbox" checked={useRawModelConfig} onChange={(e) => setUseRawModelConfig(e.target.checked)} disabled={running} />
                      Edit raw JSON
                    </label>
                  </div>

                  {!useRawModelConfig ? (
                    <AnnModelConfigEditor value={annConfigForm} onChange={handleAnnConfigChange} disabled={running} translatePreview={translatePreview} translateSelection={translateSelection} />
                  ) : null}

                  <div>
                    <div style={{ marginBottom: 6, fontWeight: "bold" }}>model_config.json</div>
                    <textarea
                      value={modelConfigText}
                      onChange={(e) => {
                        setModelConfigText(e.target.value);
                        if (useRawModelConfig) {
                          try {
                            handleAnnConfigChange(parseJsonText(e.target.value, "Model config"));
                          } catch {
                            // keep text editable even while JSON is temporarily invalid
                          }
                        }
                      }}
                      disabled={running || !useRawModelConfig}
                      style={{
                        width: "100%",
                        maxWidth: "100%",
                        height: useRawModelConfig ? "400px" : "220px",
                        fontFamily: "monospace",
                        fontSize: "13px",
                        padding: "10px",
                        borderRadius: "8px",
                        border: "1px solid #d0d7de",
                        background: useRawModelConfig ? "#fff" : "#f7f7f7",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>
                </>
              ) : (
                <div>
                  <div style={{ marginBottom: 6, fontWeight: "bold" }}>model_config.json</div>
                  <textarea
                    value={modelConfigText}
                    onChange={(e) => setModelConfigText(e.target.value)}
                    disabled={running}
                    style={{
                      width: "100%",
                      maxWidth: "100%",
                      height: "400px",
                      fontFamily: "monospace",
                      fontSize: "13px",
                      padding: "10px",
                      borderRadius: "8px",
                      border: "1px solid #d0d7de",
                      background: "#fff",
                      boxSizing: "border-box",
                    }}
                  />
                </div>
              )}
            </div>
          </div>

          <div
            style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}
          >
            <button onClick={saveModel} disabled={!activeModel || running}>
              Save
            </button>
            <button onClick={resetModel} disabled={running}>
              Reset
            </button>
            <button onClick={startTraining} disabled={!activeModel || running}>
              Train
            </button>
            <button onClick={stopTraining} disabled={!running}>
              Stop
            </button>
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
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
                    gap: 12,
                    marginBottom: 12,
                  }}
                >
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div
                      style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}
                    >
                      Model
                    </div>
                    <div style={{ fontWeight: "bold" }}>
                      {modelSummary?.modelName ?? "—"}
                    </div>
                    <div style={{ marginTop: 4 }}>
                      {modelSummary?.modelType ?? "—"}
                    </div>
                  </div>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div
                      style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}
                    >
                      Framework
                    </div>
                    <div style={{ fontWeight: "bold" }}>
                      {modelSummary?.framework ?? "—"}
                    </div>
                    <div style={{ marginTop: 4 }}>
                      Duration: {formatNumber(modelSummary?.durationSec)} s
                    </div>
                  </div>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div
                      style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}
                    >
                      Aggregate R2
                    </div>
                    <div style={{ fontWeight: "bold" }}>
                      {formatNumber(modelSummary?.r2)}
                    </div>
                  </div>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div
                      style={{ fontSize: 12, opacity: 0.7, marginBottom: 6 }}
                    >
                      Aggregate RMSE / MAE
                    </div>
                    <div style={{ fontWeight: "bold" }}>
                      {formatNumber(modelSummary?.rmse)}
                    </div>
                    <div style={{ marginTop: 4 }}>
                      MAE: {formatNumber(modelSummary?.mae)}
                    </div>
                  </div>
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 12,
                  marginBottom: 12,
                }}
              >
                <div style={{ border: "1px solid #ddd", padding: 12 }}>
                  <div style={{ fontWeight: "bold", marginBottom: 8 }}>
                    Model Info
                  </div>
                  <div>
                    <strong>Name:</strong>{" "}
                    {report?.model_info?.model_name ?? "—"}
                  </div>
                  <div>
                    <strong>Type:</strong>{" "}
                    {report?.model_info?.model_type ?? "—"}
                  </div>
                  <div>
                    <strong>Framework:</strong>{" "}
                    {report?.model_info?.framework ?? "—"}
                  </div>
                  <div>
                    <strong>Framework version:</strong>{" "}
                    {report?.model_info?.framework_version ?? "—"}
                  </div>
                  <div>
                    <strong>Trainable parameters:</strong>{" "}
                    {report?.model_info?.trainable_parameters ?? "—"}
                  </div>
                  <div>
                    <strong>Model size (MB):</strong>{" "}
                    {report?.model_info?.model_size_mb ?? "—"}
                  </div>
                  <div>
                    <strong>Training duration (s):</strong>{" "}
                    {report?.model_info?.training_duration_sec ?? "—"}
                  </div>
                  <div>
                    <strong>Completed:</strong>{" "}
                    {formatDateTime(report?.model_info?.completion_timestamp)}
                  </div>
                </div>
                <div style={{ border: "1px solid #ddd", padding: 12 }}>
                  <div style={{ fontWeight: "bold", marginBottom: 8 }}>
                    Data Info
                  </div>
                  <div>
                    <strong>Input dim:</strong>{" "}
                    {report?.data_info?.input_dim ?? "—"}
                  </div>
                  <div>
                    <strong>Output dim:</strong>{" "}
                    {report?.data_info?.output_dim ?? "—"}
                  </div>
                  <div>
                    <strong>Total samples:</strong>{" "}
                    {report?.data_info?.total_samples ?? "—"}
                  </div>
                  <div>
                    <strong>Train samples:</strong>{" "}
                    {report?.data_info?.train_samples ?? "—"}
                  </div>
                  <div>
                    <strong>Validation samples:</strong>{" "}
                    {report?.data_info?.validation_samples ?? "—"}
                  </div>
                  <div>
                    <strong>Test samples:</strong>{" "}
                    {report?.data_info?.test_samples ?? "—"}
                  </div>
                  <div>
                    <strong>Split strategy:</strong>{" "}
                    {report?.data_info?.split_strategy ?? "—"}
                  </div>
                </div>
              </div>

              <div id="model-metrics" style={{ marginBottom: 12 }}>
                <h4 style={{ marginBottom: 10 }}>Performance Metrics</h4>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr",
                    gap: 12,
                    marginBottom: 12,
                  }}
                >
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div style={{ fontWeight: "bold", marginBottom: 6 }}>
                      Aggregate
                    </div>
                    <div>
                      R2: {formatNumber(report?.performance?.metrics?.Aggregate?.R2)}
                    </div>
                    <div>
                      RMSE:{" "}
                      {formatNumber(report?.performance?.metrics?.Aggregate?.RMSE)}
                    </div>
                    <div>
                      MAE: {formatNumber(report?.performance?.metrics?.Aggregate?.MAE)}
                    </div>
                  </div>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div style={{ fontWeight: "bold", marginBottom: 6 }}>
                      Per-Output
                    </div>
                    <div>
                      RMSE Mean:{" "}
                      {formatNumber(
                        report?.performance?.metrics?.["Per-Output"]?.RMSE_Mean
                      )}
                    </div>
                    <div>
                      RMSE Max:{" "}
                      {formatNumber(
                        report?.performance?.metrics?.["Per-Output"]?.RMSE_Max
                      )}
                    </div>
                    <div>
                      RMSE Min:{" "}
                      {formatNumber(
                        report?.performance?.metrics?.["Per-Output"]?.RMSE_Min
                      )}
                    </div>
                  </div>
                  <div style={{ border: "1px solid #ddd", padding: 12 }}>
                    <div style={{ fontWeight: "bold", marginBottom: 6 }}>
                      Per-Sample
                    </div>
                    <div>
                      RMSE Mean:{" "}
                      {formatNumber(
                        report?.performance?.metrics?.["Per-Sample"]?.RMSE_Mean
                      )}
                    </div>
                    <div>
                      RMSE Max:{" "}
                      {formatNumber(
                        report?.performance?.metrics?.["Per-Sample"]?.RMSE_Max
                      )}
                    </div>
                  </div>
                </div>
                <div style={{ border: "1px solid #ddd", padding: 12 }}>
                  <div style={{ fontWeight: "bold", marginBottom: 6 }}>
                    Evaluation Protocol
                  </div>
                  <div>
                    <strong>Dataset:</strong>{" "}
                    {report?.performance?.evaluation_protocol?.evaluation_dataset ??
                      "—"}
                  </div>
                  <div>
                    <strong>Inverse transformed:</strong>{" "}
                    {String(
                      report?.performance?.evaluation_protocol
                        ?.predictions_inverse_transformed ?? "—"
                    )}
                  </div>
                  <div>
                    <strong>Normalization used:</strong>{" "}
                    {String(
                      report?.performance?.evaluation_protocol
                        ?.normalization_used ?? "—"
                    )}
                  </div>
                </div>
              </div>

              <details id="model-raw-summary">
                <summary style={{ cursor: "pointer", fontWeight: "bold" }}>
                  Raw summary / report JSON
                </summary>
                <pre
                  style={{
                    border: "1px solid #ddd",
                    background: "#fafafa",
                    padding: 12,
                    overflow: "auto",
                    fontSize: 12,
                  }}
                >
                  {safePretty(report)}
                </pre>
              </details>
            </div>
          ) : null}

          {report ? (
            <div id="model-predict">
              <h4 style={{ marginBottom: 8 }}>Predict</h4>
              <div
                style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}
              >
                <div>
                  <div style={{ marginBottom: 6, fontWeight: "bold" }}>
                    Input JSON
                  </div>
                  <textarea
                    value={predictionInput}
                    onChange={(e) => setPredictionInput(e.target.value)}
                    style={{
                      flex: 1,
                      minHeight: 140,
                      fontFamily: "monospace",
                      fontSize: 12,
                    }}
                  />
                  <div style={{ marginTop: 8 }}>
                    <button onClick={runPrediction} disabled={predicting}>
                      {predicting ? "Predicting..." : "Run Prediction"}
                    </button>
                  </div>
                </div>
                <div>
                  <div style={{ marginBottom: 6, fontWeight: "bold" }}>
                    Prediction Output
                  </div>
                  <textarea
                    value={predictionOutput}
                    readOnly
                    style={{
                      flex: 1,
                      minHeight: 180,
                      fontFamily: "monospace",
                      fontSize: 12,
                    }}
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
import { useEffect, useMemo, useRef, useState } from "react";

function safeObj(x) {
  return x && typeof x === "object" && !Array.isArray(x) ? x : {};
}

export function normalizeEmxConfig(emx) {
  const e = safeObj(emx);

  const remote = safeObj(e.remote);
  const sweepFreq = safeObj(e.sweepFreq);

  const sParam = safeObj(e.SParam);
  const yParam = safeObj(e.YParam);

  const sFormats = safeObj(sParam.formats);
  const yFormats = safeObj(yParam.formats);

  return {
    remote: {
      use: typeof remote.use === "boolean" ? remote.use : true,
      sshHost: remote.sshHost ?? "nano.ifi.uio.no",
    },

    emxPath: e.emxPath ?? "/projects/nanus/eda/Cadence/2021/INTEGRAND60/bin/emx",
    emxProcPath: e.emxProcPath ?? "RC_IRCX_CRN65LP_1P9M+ALRDL_6X1Z1U_typical.proc",

    sweepFreq: {
      startFreq: sweepFreq.startFreq ?? 1_000_000,
      stopFreq: sweepFreq.stopFreq ?? 50_000_000_000,
      stepNum: sweepFreq.stepNum ?? 2000,
      stepSize: sweepFreq.stepSize ?? 10_000_000,
      useStepSize:
        typeof sweepFreq.useStepSize === "boolean" ? sweepFreq.useStepSize : false,
    },

    referenceImpedance: e.referenceImpedance ?? 100,
    edgeWidth: e.edgeWidth ?? 1,
    "3dCond": typeof e["3dCond"] === "boolean" ? e["3dCond"] : true,
    sidewalls: typeof e.sidewalls === "boolean" ? e.sidewalls : false,
    viaSidewalls: typeof e.viaSidewalls === "boolean" ? e.viaSidewalls : false,
    viaInductance: typeof e.viaInductance === "boolean" ? e.viaInductance : false,
    viaEdgeFactor: e.viaEdgeFactor ?? 1,
    thickness: e.thickness ?? 1,
    useCadencePins: typeof e.useCadencePins === "boolean" ? e.useCadencePins : false,
    viaSeparation: e.viaSeparation ?? 0.5,
    labelDepth: e.labelDepth ?? 2,

    InductiveOnly: typeof e.InductiveOnly === "boolean" ? e.InductiveOnly : false,
    CapacitiveOnly: typeof e.CapacitiveOnly === "boolean" ? e.CapacitiveOnly : false,
    ResistiveOnly: typeof e.ResistiveOnly === "boolean" ? e.ResistiveOnly : false,
    ResistiveAndCapacitiveOnly:
      typeof e.ResistiveAndCapacitiveOnly === "boolean"
        ? e.ResistiveAndCapacitiveOnly
        : false,

    dumpConnectivity: typeof e.dumpConnectivity === "boolean" ? e.dumpConnectivity : true,
    quasistatic: typeof e.quasistatic === "boolean" ? e.quasistatic : true,
    fullwave: typeof e.fullwave === "boolean" ? e.fullwave : false,

    parallelCPU: e.parallelCPU ?? 128,
    simultaneousFrequencies: e.simultaneousFrequencies ?? 0,
    recommendedMemory:
      typeof e.recommendedMemory === "boolean" ? e.recommendedMemory : true,
    verbose: e.verbose ?? 3,
    printCommandLine:
      typeof e.printCommandLine === "boolean" ? e.printCommandLine : true,

    format: e.format ?? "touchstone",

    SParam: {
      formats: {
        touchstone:
          typeof sFormats.touchstone === "boolean" ? sFormats.touchstone : true,
        matlab: typeof sFormats.matlab === "boolean" ? sFormats.matlab : true,
        spectre: typeof sFormats.spectre === "boolean" ? sFormats.spectre : true,
        psf: typeof sFormats.psf === "boolean" ? sFormats.psf : true,
      },
    },
    YParam: {
      formats: {
        touchstone:
          typeof yFormats.touchstone === "boolean" ? yFormats.touchstone : true,
        matlab: typeof yFormats.matlab === "boolean" ? yFormats.matlab : true,
        spectre: typeof yFormats.spectre === "boolean" ? yFormats.spectre : true,
        psf: typeof yFormats.psf === "boolean" ? yFormats.psf : true,
      },
    },
  };
}

function Section({ title, children }) {
  return (
    <div
      style={{
        padding: 12,
        border: "1px solid #ddd",
        borderRadius: 6,
        background: "#fff",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 10 }}>{title}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{children}</div>
    </div>
  );
}

function Row({ label, children }) {
  return (
    <label
      style={{
        display: "grid",
        gridTemplateColumns: "220px 1fr",
        gap: 12,
        alignItems: "center",
      }}
    >
      <div style={{ opacity: 0.85 }}>{label}</div>
      <div>{children}</div>
    </label>
  );
}

function TextInput({ value, onChange, placeholder }) {
  return (
    <input
      value={value ?? ""}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      style={{ width: "100%" }}
    />
  );
}

function NumInput({ value, onChange, placeholder }) {
  return (
    <input
      value={value === "" || value === null || value === undefined ? "" : String(value)}
      placeholder={placeholder}
      onChange={(e) => {
        const s = e.target.value;
        if (s.trim() === "") return onChange("");
        const n = Number(s);
        if (Number.isNaN(n)) return;
        onChange(n);
      }}
      style={{ width: "100%" }}
    />
  );
}

function Check({ checked, onChange, label }) {
  return (
    <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <input type="checkbox" checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}

function setAtPath(obj, path, value) {
  const root = safeObj(obj);
  const out = { ...root };
  let cur = out;

  for (let i = 0; i < path.length - 1; i++) {
    const k = path[i];
    const next = safeObj(cur[k]);
    cur[k] = { ...next };
    cur = cur[k];
  }

  cur[path[path.length - 1]] = value;
  return out;
}

export default function EmxConfig({
  draftSimConfig,
  setDraftSimConfig,
  markDirty,
  resetToken = 0,
}) {
  const emxFromProps = useMemo(() => {
    const cfg = safeObj(draftSimConfig);
    return normalizeEmxConfig(cfg.emx_config);
  }, [draftSimConfig]);

  const [local, setLocal] = useState(() => emxFromProps);
  const lastPushedRef = useRef(JSON.stringify(emxFromProps));

  useEffect(() => {
    setLocal(emxFromProps);
    lastPushedRef.current = JSON.stringify(emxFromProps);
  }, [resetToken, emxFromProps]);

  useEffect(() => {
    const nextJson = JSON.stringify(local);

    if (nextJson === lastPushedRef.current) return;

    setDraftSimConfig?.((prev) => {
      const p = safeObj(prev);
      const prevEmx = normalizeEmxConfig(p.emx_config);
      const prevJson = JSON.stringify(prevEmx);

      if (prevJson === nextJson) {
        lastPushedRef.current = nextJson;
        return prev;
      }

      lastPushedRef.current = nextJson;
      return { ...p, emx_config: local };
    });
  }, [local, setDraftSimConfig]);

  function patch(path, value) {
    markDirty?.();
    setLocal((prev) => setAtPath(prev, path, value));
  }

  const remote = safeObj(local.remote);
  const sweep = safeObj(local.sweepFreq);
  const sFormats = safeObj(safeObj(local.SParam).formats);
  const yFormats = safeObj(safeObj(local.YParam).formats);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <h5 style={{ margin: 0 }}>EMX</h5>

      <Section title="Remote">
        <Check checked={remote.use} label="use" onChange={(v) => patch(["remote", "use"], v)} />
        <Row label="sshHost">
          <TextInput
            value={remote.sshHost}
            placeholder="nano.ifi.uio.no"
            onChange={(v) => patch(["remote", "sshHost"], v)}
          />
        </Row>
      </Section>

      <Section title="Paths">
        <Row label="emxPath">
          <TextInput
            value={local.emxPath}
            placeholder="/path/to/emx"
            onChange={(v) => patch(["emxPath"], v)}
          />
        </Row>

        <Row label="emxProcPath">
          <TextInput
            value={local.emxProcPath}
            placeholder="something.proc"
            onChange={(v) => patch(["emxProcPath"], v)}
          />
        </Row>
      </Section>

      <Section title="Sweep Frequency">
        <Row label="startFreq">
          <NumInput
            value={sweep.startFreq}
            placeholder="1000000"
            onChange={(v) => patch(["sweepFreq", "startFreq"], v)}
          />
        </Row>

        <Row label="stopFreq">
          <NumInput
            value={sweep.stopFreq}
            placeholder="50000000000"
            onChange={(v) => patch(["sweepFreq", "stopFreq"], v)}
          />
        </Row>

        <Row label="stepNum">
          <NumInput
            value={sweep.stepNum}
            placeholder="2000"
            onChange={(v) => patch(["sweepFreq", "stepNum"], v)}
          />
        </Row>

        <Row label="stepSize">
          <NumInput
            value={sweep.stepSize}
            placeholder="10000000"
            onChange={(v) => patch(["sweepFreq", "stepSize"], v)}
          />
        </Row>

        <Check
          checked={!!sweep.useStepSize}
          label="useStepSize"
          onChange={(v) => patch(["sweepFreq", "useStepSize"], v)}
        />
      </Section>

      <Section title="Parameters">
        <Row label="referenceImpedance">
          <NumInput
            value={local.referenceImpedance}
            placeholder="100"
            onChange={(v) => patch(["referenceImpedance"], v)}
          />
        </Row>

        <Row label="edgeWidth">
          <NumInput
            value={local.edgeWidth}
            placeholder="1"
            onChange={(v) => patch(["edgeWidth"], v)}
          />
        </Row>

        <Row label="viaEdgeFactor">
          <NumInput
            value={local.viaEdgeFactor}
            placeholder="1"
            onChange={(v) => patch(["viaEdgeFactor"], v)}
          />
        </Row>

        <Row label="thickness">
          <NumInput
            value={local.thickness}
            placeholder="1"
            onChange={(v) => patch(["thickness"], v)}
          />
        </Row>

        <Row label="viaSeparation">
          <NumInput
            value={local.viaSeparation}
            placeholder="0.5"
            onChange={(v) => patch(["viaSeparation"], v)}
          />
        </Row>

        <Row label="labelDepth">
          <NumInput
            value={local.labelDepth}
            placeholder="2"
            onChange={(v) => patch(["labelDepth"], v)}
          />
        </Row>

        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          <Check checked={!!local["3dCond"]} label="3dCond" onChange={(v) => patch(["3dCond"], v)} />
          <Check checked={!!local.sidewalls} label="sidewalls" onChange={(v) => patch(["sidewalls"], v)} />
          <Check
            checked={!!local.viaSidewalls}
            label="viaSidewalls"
            onChange={(v) => patch(["viaSidewalls"], v)}
          />
          <Check
            checked={!!local.viaInductance}
            label="viaInductance"
            onChange={(v) => patch(["viaInductance"], v)}
          />
          <Check
            checked={!!local.useCadencePins}
            label="useCadencePins"
            onChange={(v) => patch(["useCadencePins"], v)}
          />
        </div>

        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          <Check
            checked={!!local.dumpConnectivity}
            label="dumpConnectivity"
            onChange={(v) => patch(["dumpConnectivity"], v)}
          />
          <Check checked={!!local.quasistatic} label="quasistatic" onChange={(v) => patch(["quasistatic"], v)} />
          <Check checked={!!local.fullwave} label="fullwave" onChange={(v) => patch(["fullwave"], v)} />
        </div>
      </Section>

      <Section title="Run Settings">
        <Row label="parallelCPU">
          <NumInput
            value={local.parallelCPU}
            placeholder="128"
            onChange={(v) => patch(["parallelCPU"], v)}
          />
        </Row>

        <Row label="simultaneousFrequencies">
          <NumInput
            value={local.simultaneousFrequencies}
            placeholder="0"
            onChange={(v) => patch(["simultaneousFrequencies"], v)}
          />
        </Row>

        <Row label="verbose">
          <NumInput
            value={local.verbose}
            placeholder="3"
            onChange={(v) => patch(["verbose"], v)}
          />
        </Row>

        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          <Check
            checked={!!local.recommendedMemory}
            label="recommendedMemory"
            onChange={(v) => patch(["recommendedMemory"], v)}
          />
          <Check
            checked={!!local.printCommandLine}
            label="printCommandLine"
            onChange={(v) => patch(["printCommandLine"], v)}
          />
        </div>
      </Section>

      <Section title="Modes">
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
          <Check
            checked={!!local.InductiveOnly}
            label="InductiveOnly"
            onChange={(v) => patch(["InductiveOnly"], v)}
          />
          <Check
            checked={!!local.CapacitiveOnly}
            label="CapacitiveOnly"
            onChange={(v) => patch(["CapacitiveOnly"], v)}
          />
          <Check
            checked={!!local.ResistiveOnly}
            label="ResistiveOnly"
            onChange={(v) => patch(["ResistiveOnly"], v)}
          />
          <Check
            checked={!!local.ResistiveAndCapacitiveOnly}
            label="ResistiveAndCapacitiveOnly"
            onChange={(v) => patch(["ResistiveAndCapacitiveOnly"], v)}
          />
        </div>
      </Section>

      <Section title="Output">
        <Row label="format">
          <select
            value={local.format ?? "touchstone"}
            onChange={(e) => patch(["format"], e.target.value)}
            style={{ width: "100%" }}
          >
            <option value="touchstone">touchstone</option>
            <option value="matlab">matlab</option>
            <option value="spectre">spectre</option>
            <option value="psf">psf</option>
          </select>
        </Row>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div style={{ border: "1px solid #eee", borderRadius: 6, padding: 10 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>SParam.formats</div>
            <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
              <Check
                checked={!!sFormats.touchstone}
                label="touchstone"
                onChange={(v) => patch(["SParam", "formats", "touchstone"], v)}
              />
              <Check
                checked={!!sFormats.matlab}
                label="matlab"
                onChange={(v) => patch(["SParam", "formats", "matlab"], v)}
              />
              <Check
                checked={!!sFormats.spectre}
                label="spectre"
                onChange={(v) => patch(["SParam", "formats", "spectre"], v)}
              />
              <Check
                checked={!!sFormats.psf}
                label="psf"
                onChange={(v) => patch(["SParam", "formats", "psf"], v)}
              />
            </div>
          </div>

          <div style={{ border: "1px solid #eee", borderRadius: 6, padding: 10 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>YParam.formats</div>
            <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
              <Check
                checked={!!yFormats.touchstone}
                label="touchstone"
                onChange={(v) => patch(["YParam", "formats", "touchstone"], v)}
              />
              <Check
                checked={!!yFormats.matlab}
                label="matlab"
                onChange={(v) => patch(["YParam", "formats", "matlab"], v)}
              />
              <Check
                checked={!!yFormats.spectre}
                label="spectre"
                onChange={(v) => patch(["YParam", "formats", "spectre"], v)}
              />
              <Check
                checked={!!yFormats.psf}
                label="psf"
                onChange={(v) => patch(["YParam", "formats", "psf"], v)}
              />
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
}
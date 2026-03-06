import { useUiStore } from "../../state/uiStore";

import Config from "./sim/SimConfig";
import Simulate from "./sim/Simulate";
import Preview from "./sim/Preview";

const SIM_TABS = [
  { key: "config", label: "Config" },
  { key: "simulate", label: "Simulate" },
  { key: "preview", label: "Preview" },
];

export default function Sim() {
  const tab = useUiStore((s) => s.getValue(["nav", "home", "sim", "tab"], "config"));
  const setValue = useUiStore((s) => s.setValue);

  return (
    <div>
      <h3>Simulator</h3>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        {SIM_TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setValue(["nav", "home", "sim", "tab"], t.key)}
            style={{ fontWeight: tab === t.key ? "bold" : "normal" }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ padding: 12, border: "1px solid #ccc" }}>
        {tab === "config" && <Config />}
        {tab === "simulate" && <Simulate />}
        {tab === "preview" && <Preview />}
      </div>
    </div>
  );
}
import { useUiStore } from "../state/uiStore";

import Artgen from "./tabs/Artgen";
import Sim from "./tabs/Sim";
import Sweep from "./tabs/Sweep";
import Model from "./tabs/Model";
import Optimz from "./tabs/Optimz";

const TABS = [
  { key: "artgen", label: "Artwork Generator" },
  { key: "sim", label: "Simulator" },
  { key: "sweep", label: "Sweep" },
  { key: "model", label: "Model Builder" },
  { key: "optimz", label: "Optimizer" },
];

function Home({ onBack }) {
  const tab = useUiStore((s) => s.getValue(["nav", "tab"], "artgen"));
  const setValue = useUiStore((s) => s.setValue);

  return (
    <div style={{ padding: 16 }}>
      <h1>CONURE</h1>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setValue(["nav", "tab"], t.key)}
            style={{ fontWeight: tab === t.key ? "bold" : "normal" }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ padding: 12, border: "1px solid #ccc" }}>
        {tab === "artgen" && <Artgen />}
        {tab === "sim" && <Sim />}
        {tab === "sweep" && <Sweep />}
        {tab === "model" && <Model />}
        {tab === "optimz" && <Optimz />}
      </div>

      <div style={{ marginTop: 12 }}>
        <button onClick={onBack}>Back</button>
      </div>
    </div>
  );
}

export default Home;
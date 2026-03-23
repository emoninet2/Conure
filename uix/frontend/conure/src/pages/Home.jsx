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
  const projectId = useUiStore((s) => s.getValue(["project", "id"], ""));
  const projectName = useUiStore((s) => s.getValue(["project", "name"], ""));
  const setValue = useUiStore((s) => s.setValue);

  return (
    <div
      style={{
        padding: 16,
        height: "100vh",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 16,
          borderBottom: "1px solid #ddd",
          paddingBottom: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: 1 }}>
            CONURE
          </div>

          {projectName && (
            <div
              style={{
                background: "#f5f5f5",
                padding: "6px 12px",
                borderRadius: 6,
                fontSize: 14,
                color: "#444",
              }}
            >
              Project: <strong>{projectName}</strong>
            </div>
          )}
        </div>

        <button
          onClick={onBack}
          style={{
            padding: "6px 12px",
            borderRadius: 6,
            border: "1px solid #ccc",
            background: "#f2f2f2",
            cursor: "pointer",
            fontWeight: 500,
          }}
        >
          Projects
        </button>
      </div>

      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 16,
          borderBottom: "1px solid #ddd",
          paddingBottom: 8,
        }}
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setValue(["nav", "tab"], t.key)}
            style={{
              padding: "6px 12px",
              border: "none",
              borderRadius: 6,
              cursor: "pointer",
              background: tab === t.key ? "#2d6cdf" : "#f2f2f2",
              color: tab === t.key ? "white" : "#333",
              fontWeight: 500,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div
        key={projectId || "no-project"}
        style={{
          flex: 1,
          padding: 12,
          border: "1px solid #ccc",
          borderRadius: 6,
          background: "#fafafa",
          overflow: "auto",
        }}
      >
        {tab === "artgen" && <Artgen />}
        {tab === "sim" && <Sim />}
        {tab === "sweep" && <Sweep />}
        {tab === "model" && <Model />}
        {tab === "optimz" && <Optimz />}
      </div>
    </div>
  );
}

export default Home;

// src/components/Artwork/Artwork.jsx
import React, { useState } from "react";
import { useArtworkContext } from "../../context/ArtworkContext";
import { uploadArtwork, downloadArtwork } from "../../services/api";
import { saveArtworkData, loadAndApplyArtwork } from "../../services/artworkHelper";

import "../../styles/Artwork.css";

import Metadata from "./Artwork/Metadata.jsx";
import Parameters from "./Artwork/Parameters.jsx";
import Segments from "./Artwork/Segments.jsx";
import Arms from "./Artwork/Arms.jsx";
import Ports from "./Artwork/Ports.jsx";
import Bridges from "./Artwork/Bridges.jsx";
import ViaPadStack from "./Artwork/ViaPadStack.jsx";
import Vias from "./Artwork/Vias.jsx";
import GuardRing from "./Artwork/GuardRing.jsx";
import Layers from "./Artwork/Layers.jsx";
import Preview from "./Artwork/Preview.jsx";

function Artwork() {
  const [activeTab, setActiveTab] = useState("Metadata");
  const context = useArtworkContext();

  const tabs = [
    { key: "Metadata", label: "Metadata", content: <Metadata /> },
    { key: "Parameters", label: "Parameters", content: <Parameters /> },
    { key: "Segments", label: "Segments", content: <Segments /> },
    { key: "Arms", label: "Arms", content: <Arms /> },
    { key: "Ports", label: "Ports", content: <Ports /> },
    { key: "Bridges", label: "Bridges", content: <Bridges /> },
    { key: "ViaPadStack", label: "Via Pad Stack", content: <ViaPadStack /> },
    { key: "Vias", label: "Vias", content: <Vias /> },
    { key: "GuardRing", label: "Guard Ring", content: <GuardRing /> },
    { key: "Layers", label: "Layers", content: <Layers /> },
    { key: "Preview", label: "Preview", content: <Preview /> }
  ];

  const handleSave = async () => {
    const result = await saveArtworkData(context);
    alert(result.message);
  };

  const handleLoad = async () => {
    const result = await loadAndApplyArtwork(context);
    alert(result.message);
  };

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      await uploadArtwork(file);
      alert("✅ Upload successful!");
    } catch (error) {
      alert("❌ Upload failed: " + error.message);
    }
  };

  const handleDownload = async () => {
    try {
      await downloadArtwork();
      alert("✅ Artwork download started!");
    } catch (error) {
      alert("❌ Download failed: " + error.message);
    }
  };

  return (
    <div className="tab-container">
      <h3 className="artwork-heading">🎨 Artwork Tab</h3>

      <div className="button-group">
        <button onClick={handleSave} className="btn primary">💾 Save</button>
        <button onClick={handleLoad} className="btn primary">📂 Auto Load</button>
        <label htmlFor="upload-input" className="btn primary upload-label">
          ⬆️ Upload
          <input
            id="upload-input"
            type="file"
            accept=".json"
            onChange={handleUpload}
            style={{ display: "none" }}
          />
        </label>
        <button onClick={handleDownload} className="btn primary">⬇️ Download</button>
      </div>

      <div className="tab-button-group">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`tab-button ${activeTab === tab.key ? "active" : ""}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {tabs.find((tab) => tab.key === activeTab)?.content}
      </div>
    </div>
  );
}

export default Artwork;

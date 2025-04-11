import { useState } from 'react';
import { useArtworkContext } from '../../context/ArtworkContext';
import {
  saveArtwork,
  loadArtwork,
  uploadArtwork,
  downloadArtwork
} from '../../services/api';

import '../../styles/Artwork.css';

import Metadata from './Artwork/Metadata.jsx';
import Parameters from './Artwork/Parameters.jsx';
import Segments from './Artwork/Segments.jsx';
import Arms from './Artwork/Arms.jsx';
import Ports from './Artwork/Ports.jsx';
import Bridges from './Artwork/Bridges.jsx';
import ViaPadStack from './Artwork/ViaPadStack.jsx';
import Vias from './Artwork/Vias.jsx';
import GuardRing from './Artwork/GuardRing.jsx';
import Layers from './Artwork/Layers.jsx';
import Preview from './Artwork/Preview.jsx';

function Artwork() {
  const [activeTab, setActiveTab] = useState('Metadata');
  const context = useArtworkContext();

  const tabs = [
    { key: 'Metadata', label: 'Metadata', content: <Metadata /> },
    { key: 'Parameters', label: 'Parameters', content: <Parameters /> },
    { key: 'Segments', label: 'Segments', content: <Segments /> },
    { key: 'Arms', label: 'Arms', content: <Arms /> },
    { key: 'Ports', label: 'Ports', content: <Ports /> },
    { key: 'Bridges', label: 'Bridges', content: <Bridges /> },
    { key: 'ViaPadStack', label: 'Via Pad Stack', content: <ViaPadStack /> },
    { key: 'Vias', label: 'Vias', content: <Vias /> },
    { key: 'GuardRing', label: 'Guard Ring', content: <GuardRing /> },
    { key: 'Layers', label: 'Layers', content: <Layers /> },
    { key: 'Preview', label: 'Preview', content: <Preview /> }
  ];

  const handleSave = async () => {
    const allData = {};
    for (const key in context) {
      const section = context[key];
      for (const stateKey in section) {
        if (stateKey.startsWith('set')) continue;
        allData[stateKey] = section[stateKey];
      }
    }

    try {
      await saveArtwork(allData);
      alert('✅ Artwork saved!');
    } catch (error) {
      alert('❌ Save failed: ' + error.message);
    }
  };

  const handleLoad = async () => {
    try {
      const result = await loadArtwork();
      const data = result.data || {};

      const orderedKeys = [
        ['metaData', 'metadata'],
        ['parameterData', 'parameter'],
        ['layerData', 'layers'],
        ['viaData', 'vias'],
        ['viaPadStackData', 'viaPadStack'],
        ['bridgeData', 'bridges'],
        ['portData', 'ports'],
        ['simPortData', 'ports'],
        ['armData', 'arms'],
        ['segmentData', 'segments'],
        ['guardRingData', 'guardRing'],
        ['guardRingDummyData', 'guardRing'],
        ['useGuardRing', 'guardRing'],
        ['guardRingDistance', 'guardRing']
      ];

      for (const [dataKey, contextKey] of orderedKeys) {
        const section = context[contextKey];
        if (!section) continue;

        for (const stateKey in section) {
          if (typeof section[stateKey] === 'function' && stateKey.startsWith('set')) {
            const expectedKey =
              stateKey.replace(/^set/, '').charAt(0).toLowerCase() +
              stateKey.replace(/^set/, '').slice(1);

            if (expectedKey === dataKey && data[dataKey] !== undefined) {
              section[stateKey](data[dataKey]);
            } else if (dataKey === expectedKey && data[dataKey] !== undefined) {
              section[stateKey](data[dataKey]);
            }
          }
        }
      }

      alert('✅ Artwork loaded!');
    } catch (error) {
      alert('❌ Load failed: ' + error.message);
    }
  };

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      await uploadArtwork(file);
      alert('✅ Upload successful!');
    } catch (error) {
      alert('❌ Upload failed: ' + error.message);
    }
  };

  const handleDownload = async () => {
    try {
      await downloadArtwork();
      alert('✅ Artwork download started!');
    } catch (error) {
      alert('❌ Download failed: ' + error.message);
    }
  };

  return (
    <div className="artwork-controls">

      {/* Header */}
      <h3 className="artwork-heading">🎨 Artwork Tab</h3>

      
      {/* Button Bar */}
      <div className="button-group">
        <button onClick={handleSave} className="artwork-button">💾 Save</button>
        <button onClick={handleLoad} className="artwork-button">📂 Auto Load</button>
        <label htmlFor="upload-input" className="artwork-button upload-label">
          ⬆️ Upload
          <input
            id="upload-input"
            type="file"
            accept=".json"
            onChange={handleUpload}
            style={{ display: 'none' }}
          />
        </label>

        <button onClick={handleDownload} className="artwork-button">⬇️ Download</button>
        
      </div>

      

      {/* Tabs */}
      <div className="artwork-tab-button-group">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`artwork-tab-button ${activeTab === tab.key ? 'active' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="artwork-tab-content">
        {tabs.find((tab) => tab.key === activeTab)?.content}
      </div>
    </div>
  );
}

export default Artwork;

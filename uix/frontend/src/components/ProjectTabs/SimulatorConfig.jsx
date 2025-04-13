import { useState } from 'react';

import '../../styles/SimulatorConfig.css';

// Import the actual EMX component
import EMXTab from './SimulatorConfigTabs/emxConfigTab'; // adjust path based on actual file location
import OpenEMSTab from './SimulatorConfigTabs/openEmsConfigTab'; // optional: move others to tabs folder
import RaptorTab from './SimulatorConfigTabs/raptorConfigTab';   // optional

function SimulatorConfig() {
  const [activeTab, setActiveTab] = useState('EMX');

  const tabs = [
    { key: 'EMX', label: 'EMX', content: <EMXTab /> ,  disabled: false},
    { key: 'openEMS', label: 'openEMS', content: <OpenEMSTab /> , disabled: true},
    { key: 'ANSYSRaptor', label: 'ANSYS Raptor', content: <RaptorTab /> ,  disabled: true}
  ];

  return (
    <div className="simulator-config">
      <h3 className="simulator-heading">🧪 Simulator Configuration</h3>

      <div className="simulator-tab-button-group">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`simulator-tab-button ${activeTab === tab.key ? 'active' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="simulator-tab-content">
        {tabs.find((tab) => tab.key === activeTab)?.content}
      </div>
    </div>
  );
}

export default SimulatorConfig;

import { useState } from 'react';
import '../../styles/ProjectView.css';  // <- reuse ProjectView styles
import EMXTab from './SimulatorConfigTabs/emxConfigTab';
import OpenEMSTab from './SimulatorConfigTabs/openEmsConfigTab';
import RaptorTab from './SimulatorConfigTabs/raptorConfigTab';

function SimulatorConfig() {
  const [activeTab, setActiveTab] = useState('EMX');

  const tabs = [
    { key: 'EMX',        label: 'EMX',         content: <EMXTab />,   disabled: false },
    { key: 'openEMS',    label: 'openEMS',     content: <OpenEMSTab />, disabled: true  },
    { key: 'ANSYSRaptor',label: 'ANSYS Raptor', content: <RaptorTab />, disabled: true  },
  ];

  return (
    <div className="simulator-config">
      <h3 className="simulator-heading">🧪 Simulator Configuration</h3>

      {/* TABS */}
      <div className="tab-buttons">
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            disabled={tab.disabled}
            className={`tab-button ${activeTab === tab.key ? 'active' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* CONTENT */}
      <div className="tab-content">
        {tabs.find(tab => tab.key === activeTab)?.content}
      </div>
    </div>
  );
}

export default SimulatorConfig;

import { useState } from 'react'
import App from '../App'
import '../styles/ProjectView.css'
import Artwork from '../components/ProjectTabs/Artwork.jsx'
import Sweep from '../components/ProjectTabs/Sweep.jsx'
import Simulate from '../components/ProjectTabs/Simulate.jsx'
import Modeling from '../components/ProjectTabs/Modeling.jsx'
import SimulatorConfig from './ProjectTabs/SimulatorConfig.jsx'
import About from '../components/ProjectTabs/About.jsx'
import conureLogo from '../assets/images/logo/logo_nb_large.png'

function ProjectView({ name }) {
  const [goHome, setGoHome] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')

  const tabs = [
    {
      key: 'Artwork',
      label: 'Artwork',
      content: <Artwork />,
    },
    {
      key: 'Simulate',
      label: 'Simulate',
      content: <Simulate />,
    },
    {
      key: 'Sweep',
      label: 'Sweep',
      content: <Sweep />,
    },
    {
      key: 'Modeling',
      label: 'Modeling',
      content: <Modeling />,
    },
    {
      key: 'SimulatorConfig',
      label: 'Simulator Config',
      content: <SimulatorConfig />,
    },
    {
      key: 'About',
      label: 'About',
      content: <About />,
    },
  ]

  const [enabledTabs, setEnabledTabs] = useState({
    Artwork: true,
    Simulate: true,
    Sweep: true,
    Modeling: false,
    SimulatorConfig: true,
    About: true,

  })
  


  if (goHome) return <App />

  return (
    <div className="project-container">
      
      {/* Back Button */}
      <div className="back-button-wrapper">
        
        <button className="back-button" onClick={() => setGoHome(true)}>
          ← Home
        </button>
        
      </div>

      <img
        src={conureLogo}
        className="logo conure-logo"
        alt="Conure logo"
        style={{
          display: 'block',         // force it onto its own line
          marginBottom: '1rem',     // add space below
          alignSelf: 'flex-start',  // keep it flush left in the flex container
        }}
      />

      {/* Now your title will start on a fresh line: */}
      <div className="project-title">
        {/* <h2>Conure</h2> */}
        <p><b>Project:</b> {name}</p>
      </div>


      {/* Tabs */}
      <div className="tab-buttons">
        {tabs.map((tab) => (
          <button
          key={tab.key}
          onClick={() => setActiveTab(tab.key)}
          disabled={!enabledTabs[tab.key]}
          className={`tab-button ${activeTab === tab.key ? 'active' : ''}`}
        >
          {tab.label}
        </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {tabs.find((tab) => tab.key === activeTab)?.content}
      </div>
    </div>
  )
}

export default ProjectView



import { useState } from 'react'
import App from '../App'
import '../styles/ProjectView.css'
import Artwork from '../components/ProjectTabs/Artwork.jsx'
import Sweep from '../components/ProjectTabs/Sweep.jsx'
import Simulate from '../components/ProjectTabs/Simulate.jsx'
import Modeling from '../components/ProjectTabs/Modeling.jsx'
import About from '../components/ProjectTabs/About.jsx'

function ProjectView({ name, path }) {
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
      key: 'About',
      label: 'About',
      content: <About />,
    },
  ]

  const [enabledTabs, setEnabledTabs] = useState({
    Simulate: false,
    Sweep: false,
    Modeling: false,
    About: true,
    Artwork: true,
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

      {/* Title */}
      <div className="project-title">
        <h2>Project</h2>
        <p> <b>Project name: </b>{name}</p>
        <p> <b>Project path: </b>{path}</p>
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



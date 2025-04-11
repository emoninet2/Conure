// App.jsx
import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import conureLogo from './assets/images/logo/logo_nb_large.png'
import './App.css'
import { createProject, openProject } from './services/api'
import ProjectView from './components/ProjectView'

function App() {
  const [message, setMessage] = useState('')
  const [currentView, setCurrentView] = useState('home')
  const [projectName, setProjectName] = useState('')
  const [projectPath, setProjectPath] = useState('')

  const handleCreateProject = async () => {
    const name = window.prompt('Enter your name:')
    const location = window.prompt('Enter your location:')
    if (!name || !location) {
      alert('Both name and location are required!')
      return
    }
    try {
      const data = await createProject(name, location)
      setMessage(data.data.message)
      setProjectName(name)
      setProjectPath(location)
      setCurrentView('project')
    } catch (err) {
      console.error('Error creating project:', err)
      alert('Failed to create project.')
    }
  }

  const handleOpenProject = async () => {
    const location = window.prompt('Enter the project location to open:')
    if (!location) {
      alert('Location is required!')
      return
    }
    try {
      const data = await openProject(location)
      setMessage(data.data.message)
      setProjectName("SOME OPENED PROJECT")
      setProjectPath(location)
      setCurrentView('project')
    } catch (err) {
      console.error('Error opening project:', err)
      alert('Failed to open project.')
    }
  }

  return (
    <>
      {currentView === 'home' ? (
        <div className="card">
          <div>
            <a href="https://vite.dev" target="_blank">
              <div className="logo-circle">
                <img src={conureLogo} className="logo conure-logo" alt="Conure logo" />
              </div>
            </a>
          </div>
          <h1>CONURE</h1>
          <button onClick={handleCreateProject} style={{ marginTop: '1rem' }}>
            Create Project
          </button>
          <button onClick={handleOpenProject} style={{ marginTop: '1rem' }}>
            Open Project
          </button>
        </div>
      ) : (
        <ProjectView
          name={projectName}
          path={projectPath}
        />
      )}
    </>
  )
}

export default App

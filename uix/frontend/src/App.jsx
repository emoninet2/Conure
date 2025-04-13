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


  // Only ask for a name when creating a project
  const handleCreateProject = async () => {
    const name = window.prompt('Enter your name:')
    if (!name) {
      alert('Name is required!')
      return
    }
    try {
      const data = await createProject(name)
      setMessage(data.data.message)
      setProjectName(name)
      // For createProject, you might not have a location yet,
      // so we can leave projectPath empty or set a default value.
 
      setCurrentView('project')
    } catch (err) {
      console.error('Error creating project:', err)
      alert('Failed to create project.')
    }
  }

  // Ask for both location and name when opening a project
  const handleOpenProject = async () => {

    const name = window.prompt('Enter the project name:')
    if (!name ) {
      alert('Name required!')
      return
    }
    try {
      const data = await openProject(name)
      setMessage(data.data.message)
      setProjectName(name)
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
        <ProjectView name={projectName} />
      )}
    </>
  )
}

export default App

import { useState, useEffect } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import conureLogo from './assets/images/logo/logo_nb_large.png'
import './App.css'
import { createProject, openProject } from './services/api'
import ProjectView from './components/ProjectView'
import { useArtworkContext } from './context/ArtworkContext';
import { saveArtworkData, loadAndApplyArtwork } from './services/artworkHelper';



function App() {
  const [message, setMessage] = useState('')
  const [currentView, setCurrentView] = useState('home')
  const [projectName, setProjectName] = useState('')
  const artworkContext = useArtworkContext();




  // Prompt before refresh/close when in the project view
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      e.preventDefault()
      e.returnValue = ''
    }

    if (currentView === 'project') {
      window.addEventListener('beforeunload', handleBeforeUnload)
    }

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [currentView])


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
      await loadAndApplyArtwork(artworkContext); //load the artwrok opening existing project
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
          <div className="home-button-group" >
          <h1>CONURE</h1>
          <button onClick={handleCreateProject} style={{ marginTop: '1rem' }}>
            Create Project
          </button>
          <button onClick={handleOpenProject} style={{ marginTop: '1rem' }}>
            Open Project
          </button>

          </div>
    
        </div>
      ) : (
        <ProjectView name={projectName} />
      )}
    </>
  )
}

export default App

import { useState, useEffect } from 'react'
import conureLogo from './assets/images/logo/logo_nb_large.png'
import './App.css'
import {
  createProject,
  openProject,
  open_workspace,
  close_workspace
} from './services/api'
import ProjectView from './components/ProjectView'
import { useArtworkContext } from './context/ArtworkContext';
import { loadAndApplyArtwork } from './services/artworkHelper';

function App() {

  useEffect(() => {
    const baseURL = `${import.meta.env.VITE_API_HOST}:${import.meta.env.VITE_BACKEND_PORT}`;
    const url = `${baseURL}/api/health`;

    console.log("Calling health check:", url);

    fetch(url)
      .then((res) => res.json())
      .then((data) => console.log("Backend health:", data))
      .catch((err) => console.error("Health check failed:", err));
  }, []);
  
  const [message, setMessage] = useState('')
  const [currentView, setCurrentView] = useState('home')
  const [projectName, setProjectName] = useState('')
  const [workspaceMounted, setWorkspaceMounted] = useState(false)
  const artworkContext = useArtworkContext();



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


  const handleMountWorkspace = async () => {
    const path = window.prompt("Enter absolute path to your workspace folder:")
    if (!path) return

    try {
      const res = await open_workspace(path)
      console.log("Workspace mounted:", res)
      setWorkspaceMounted(true)
    } catch (err) {
      console.error("Failed to mount workspace", err)
      alert("Failed to mount workspace.")
    }
  }

  const handleUnmountWorkspace = async () => {
    try {
      await close_workspace()
      setWorkspaceMounted(false)
      setCurrentView('home')
      setProjectName('')
    } catch (err) {
      console.error("Failed to unmount workspace", err)
      alert("Failed to unmount workspace.")
    }
  }


  const handleCreateProject = async () => {
    const name = window.prompt('Enter your project name:')
    if (!name) {
      alert('Name is required!')
      return
    }
    try {
      const data = await createProject(name)
      setMessage(data.data.message)
      setProjectName(name)
      setCurrentView('project')
    } catch (err) {
      console.error('Error creating project:', err)
      alert('Failed to create project.')
    }
  }

  const handleOpenProject = async () => {
    const name = window.prompt('Enter the project name:')
    if (!name) {
      alert('Name required!')
      return
    }
    try {
      const data = await openProject(name)
      setMessage(data.data.message)
      setProjectName(name)
      await loadAndApplyArtwork(artworkContext)
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
            <div className="logo-circle">
              <img src={conureLogo} className="logo conure-logo" alt="Conure logo" />
            </div>
          </div>
          <div className="home-button-group">
            <h1>CONURE</h1>

            {!workspaceMounted ? (
              <button onClick={handleMountWorkspace} style={{ marginTop: '1rem' }}>
                Mount Workspace
              </button>
            ) : (
              <>
                <button onClick={handleCreateProject} style={{ marginTop: '1rem' }}>
                  Create Project
                </button>
                <button onClick={handleOpenProject} style={{ marginTop: '1rem' }}>
                  Open Project
                </button>
                <button onClick={handleUnmountWorkspace} style={{ marginTop: '1rem' }}>
                  Close Workspace
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        <ProjectView name={projectName} />
      )}
    </>
  )
}

export default App

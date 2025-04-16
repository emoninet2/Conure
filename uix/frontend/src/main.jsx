import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ArtworkProvider } from './context/ArtworkContext.jsx'
import { SweepProvider } from './context/SweepContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ArtworkProvider>
      <SweepProvider>
        <App />
      </SweepProvider>
    </ArtworkProvider>
  </StrictMode>
);

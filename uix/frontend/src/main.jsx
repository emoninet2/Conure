import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ArtworkProvider } from './context/ArtworkContext.jsx'
import { SweepProvider } from './context/SweepContext.jsx'
import { SimulateProvider } from './context/SimulateContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ArtworkProvider>
      <SweepProvider>
        <SimulateProvider>
          <App />
        </SimulateProvider>
      </SweepProvider>
    </ArtworkProvider>
  </StrictMode>
);

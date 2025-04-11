import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { ArtworkProvider } from './context/ArtworkContext.jsx';


// createRoot(document.getElementById('root')).render(
//   <StrictMode>
//     <App />
//   </StrictMode>,
// )




createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ArtworkProvider>
      <App />
    </ArtworkProvider>
  </StrictMode>
);
// src/SimulateContext.jsx
import React, { createContext, useContext, useState } from 'react';

const SimulateContext = createContext();

export function SimulateProvider({ children }) {
  const [simulator, setSimulator] = useState('EMX');
  const [status, setStatus] = useState('Idle');
  const [isRunning, setIsRunning] = useState(false); // <-- new

  return (
    <SimulateContext.Provider value={{ simulator, setSimulator, status, setStatus, isRunning, setIsRunning }}>
      {children}
    </SimulateContext.Provider>
  );
}

export function useSimulate() {
  const ctx = useContext(SimulateContext);
  if (!ctx) {
    throw new Error('useSimulate must be used within a SimulateProvider');
  }
  return ctx;
}
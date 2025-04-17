// src/SimulateContext.jsx
import React, { createContext, useContext, useState } from 'react';

const SimulateContext = createContext();

/**
 * Provider component. Wrap your app (or your Tabs) in this once.
 */
export function SimulateProvider({ children }) {
  const [simulator, setSimulator] = useState('EMX');
  const [status, setStatus]       = useState('Idle');

  return (
    <SimulateContext.Provider value={{ simulator, setSimulator, status, setStatus }}>
      {children}
    </SimulateContext.Provider>
  );
}

/**
 * Hook to consume simulation state.
 * Must be used inside a SimulateProvider.
 */
export function useSimulate() {
  const ctx = useContext(SimulateContext);
  if (!ctx) {
    throw new Error('useSimulate must be used within a SimulateProvider');
  }
  return ctx;
}

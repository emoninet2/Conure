import React, { createContext, useContext, useState, useRef } from 'react';
import { saveSweep, prepareSweepForSaving } from '../services/api';

const SweepContext = createContext();

export const SweepProvider = ({ children }) => {
  // --- existing state ---
  const [mode, setMode] = useState("new");
  const [sweepName, setSweepName] = useState("");
  const [sweepParams, setSweepParams] = useState([
    { parameterName: "", from: "", to: "", type: "npoints", value: "" }
  ]);

  // --- new, persisted state ---
  const [enableLayout, setEnableLayout]               = useState(false);
  const [enableSvg, setEnableSvg]                     = useState(false);
  const [enableSimulation, setEnableSimulation]       = useState(false);
  const [enableForceOverwrite, setEnableForceOverwrite] = useState(false);
  const [simulator, setSimulator]                     = useState('EMX');
  const [status, setStatus]                           = useState('Idle');

  // pollingRef and polling can stay here too if you want them global:
  const pollingRef = useRef(null);
  const [polling, setPolling] = useState(false);

  const handleModeChange = (e) => {
    const newMode = e.target.value;
    setMode(newMode);
    setSweepName("");
    setSweepParams([{ parameterName: "", from: "", to: "", type: "npoints", value: "" }]);
  };

  const handleSweepNameChange = (e) => {
    setSweepName(e.target.value);
  };

  const addRow = () => {
    setSweepParams(ps => [
      ...ps,
      { parameterName: "", from: "", to: "", type: "npoints", value: "" }
    ]);
  };

  const deleteRow = (index) => {
    setSweepParams(ps => ps.filter((_,i) => i!==index));
  };

  const handleRowChange = (index, field, value) => {
    setSweepParams(ps => {
      const copy = [...ps];
      copy[index][field] = value;
      return copy;
    });
  };

  const handleSave = async () => {
    const data = prepareSweepForSaving(sweepName, sweepParams);
    await saveSweep(data);
  };

  return (
    <SweepContext.Provider value={{
      // existing
      mode, sweepName, sweepParams,
      setSweepParams, handleModeChange,
      handleSweepNameChange, addRow,
      deleteRow, handleRowChange,
      handleSave,
      // new
      enableLayout, setEnableLayout,
      enableSvg, setEnableSvg,
      enableSimulation, setEnableSimulation,
      enableForceOverwrite, setEnableForceOverwrite,
      simulator, setSimulator,
      status, setStatus,
      pollingRef, polling, setPolling
    }}>
      {children}
    </SweepContext.Provider>
  );
};

export const useSweep = () => {
  const ctx = useContext(SweepContext);
  if (!ctx) throw new Error("useSweep must be inside SweepProvider");
  return ctx;
};

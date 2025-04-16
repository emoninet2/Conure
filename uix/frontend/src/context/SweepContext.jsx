// src/contexts/SweepContext.jsx
import React, { createContext, useContext, useState } from 'react';
import { saveSweep, prepareSweepForSaving } from '../services/api';

const SweepContext = createContext();

export const SweepProvider = ({ children }) => {
  // Mode: "new" or "open"
  const [mode, setMode] = useState("new");
  const [sweepName, setSweepName] = useState("");

  // Simple table state for sweep parameters
  const [sweepParams, setSweepParams] = useState([
    { parameterName: "", from: "", to: "", type: "npoints", value: "" }
  ]);

  // Handler for mode selection change
  const handleModeChange = (e) => {
    const newMode = e.target.value;
    setMode(newMode);
    // Reset sweep name and parameters when switching modes
    setSweepName("");
    setSweepParams([
      { parameterName: "", from: "", to: "", type: "npoints", value: "" }
    ]);
  };

  // Handler for sweep name change
  const handleSweepNameChange = (e) => {
    setSweepName(e.target.value);
  };

  // Table row functions
  const addRow = () => {
    setSweepParams([
      ...sweepParams,
      { parameterName: "", from: "", to: "", type: "npoints", value: "" }
    ]);
  };

  const deleteRow = (index) => {
    const newParams = [...sweepParams];
    newParams.splice(index, 1);
    setSweepParams(newParams);
  };

  const handleRowChange = (index, field, value) => {
    const newParams = [...sweepParams];
    newParams[index][field] = value;
    setSweepParams(newParams);
  };

  // Handler for saving the sweep via the API.
  // prepareSweepForSaving converts local state into the API's expected format.
  // saveSweep sends the formatted data to the backend.
  const handleSave = async () => {
    try {
      const data = prepareSweepForSaving(sweepName, sweepParams);
      console.log("AHAHAH", data)
      await saveSweep(data);
      console.log("Sweep saved successfully:", data);
      alert("Sweep saved successfully (check console for details).");
    } catch (error) {
      console.error("Error saving sweep:", error);
      alert("Failed to save sweep.");
    }
  };

  return (
    <SweepContext.Provider
      value={{
        mode,
        sweepName,
        sweepParams,
        setSweepParams, // <-- Added this line
        handleModeChange,
        handleSweepNameChange,
        addRow,
        deleteRow,
        handleRowChange,
        handleSave,
      }}
    >
      {children}
    </SweepContext.Provider>
  );
};

export const useSweep = () => useContext(SweepContext);

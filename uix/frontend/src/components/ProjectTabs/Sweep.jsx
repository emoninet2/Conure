import React, { useState, useEffect, useRef } from 'react';
import { useSweep } from '../../context/SweepContext';
import { useArtworkContext } from '../../context/ArtworkContext';
import {
  listSweeps,
  loadSweep,
  processLoadedSweep,
  deleteSweep,
  startSweep,
  stopSweep,
  getSweepStatus
} from '../../services/api';
import '../../styles/theme.css';

const Sweep = () => {
  const {
    mode, sweepName, sweepParams,
    setSweepParams, setSweepName,
    handleModeChange,
    handleSweepNameChange, addRow,
    deleteRow, handleRowChange, handleSave
  } = useSweep();

  const { parameter: { parameterData } } = useArtworkContext();
  const [sweepOptions, setSweepOptions] = useState([]);

  const [enableLayout, setEnableLayout] = useState(false);
  const [enableSvg, setEnableSvg] = useState(false);
  const [enableSimulation, setEnableSimulation] = useState(false);
  const [enableForceOverwrite, setEnableForceOverwrite] = useState(false);
  const [simulator, setSimulator] = useState('EMX');
  const [status, setStatus] = useState('Idle');

  const pollingRef = useRef(null);
  const [polling, setPolling] = useState(false);

  const refreshSweepList = async () => {
    try {
      const result = await listSweeps();
      if (result.success && result.sweeps) {
        setSweepOptions(result.sweeps);
      }
    } catch (error) {
      console.error("Error fetching sweeps:", error);
    }
  };

  const startPollingStatus = () => {
    if (!sweepName || pollingRef.current) return;
    setPolling(true);
    pollingRef.current = setInterval(async () => {
      try {
        const result = await getSweepStatus(sweepName);
        if (result.status) setStatus(result.status);
      } catch (err) {
        setStatus(`❌ Error reading sweep status: ${err.message}`);
        stopPollingStatus();
      }
    }, 1000);
  };

  const stopPollingStatus = () => {
    clearInterval(pollingRef.current);
    pollingRef.current = null;
    setPolling(false);
  };

  useEffect(() => {
    if (mode === 'open') {
      refreshSweepList();
    }
  }, [mode]);

  useEffect(() => {
    if (mode === 'open' && sweepName) {
      const fetchSweepDetails = async () => {
        try {
          const response = await loadSweep(sweepName);
          const { sweepParams: loadedSweepParams } = processLoadedSweep(response);
          setSweepParams(loadedSweepParams);
        } catch (error) {
          console.error("Error loading sweep details:", error);
        }
      };
      fetchSweepDetails();
    }
  }, [sweepName, mode, setSweepParams]);

  useEffect(() => {
    return () => {
      stopPollingStatus();
    };
  }, []);

  const handleSaveSweep = async () => {
    try {
      await handleSave();
      setStatus('✅ Sweep saved successfully');

      setTimeout(async () => {
        await refreshSweepList();
        if (mode === 'new') {
          handleModeChange({ target: { value: 'open' } });
          setTimeout(() => {
            handleSweepNameChange({ target: { value: sweepName } });
          }, 50);
        }
      }, 100);
    } catch (err) {
      setStatus(`❌ Error saving sweep: ${err.message}`);
    }
  };

  const handleDeleteSweep = async () => {
    if (!sweepName) {
      alert('⚠️ No sweep selected.');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete "${sweepName}"?`)) return;

    try {
      await deleteSweep(sweepName);
      handleSweepNameChange({ target: { value: '' } });
      setSweepParams([]);
      await refreshSweepList();
      setStatus(`🗑️ Sweep "${sweepName}" deleted.`);
    } catch (err) {
      setStatus(`❌ Error deleting sweep: ${err.message}`);
    }
  };

  const handleStartSweep = async () => {
    setStatus('🚀 Starting sweep...');
    try {
      const result = await startSweep({
        sweepName,
        enableLayout,
        enableSvg,
        enableSimulation,
        simulator,
        forceOverwrite: enableForceOverwrite
      });
      setStatus(`✅ ${result.status || 'Sweep started successfully'}`);
      startPollingStatus();
    } catch (err) {
      setStatus(`❌ Error starting sweep: ${err.message}`);
    }
  };

  const handleStopSweep = async () => {
    setStatus('🛑 Stopping sweep...');
    try {
      const result = await stopSweep();
      setStatus(`🧹 ${result.status || 'Sweep stopped successfully'}`);
      stopPollingStatus();
    } catch (err) {
      setStatus(`❌ Error stopping sweep: ${err.message}`);
    }
  };

  return (

    <div className="tab-container">
      <h3 className="artwork-heading">🌀 Sweep</h3>

      {sweepName && (
        <div className="input-group">
          <strong>Current Sweep:</strong> {sweepName}
        </div>
      )}


      <div className="mode-selection">
        <label className="mode-label">
          <input type="radio" name="mode" value="new" checked={mode === "new"} onChange={handleModeChange} />
          Create New Sweep
        </label>
        <label className="mode-label">
          <input type="radio" name="mode" value="open" checked={mode === "open"} onChange={handleModeChange} />
          Open Existing Sweep
        </label>
      </div>

      <div className="input-group">
        {mode === "new" ? (
          <label>
            Enter new sweep name:
            <input type="text" value={sweepName} onChange={handleSweepNameChange} className="input-field" placeholder="New Sweep Name" />
          </label>
        ) : (
          <label>
            Select sweep data:
            <select value={sweepName} onChange={handleSweepNameChange} className="input-field">
              <option value="">-- Select Sweep Data --</option>
              {sweepOptions.map((option) => (
                <option key={option.sweep_name} value={option.sweep_name}>{option.sweep_name}</option>
              ))}
            </select>
          </label>
        )}
      </div>



      <div className="button-group">
        <button onClick={handleSaveSweep} className="btn primary">💾 Save Sweep</button>
        <button onClick={handleDeleteSweep} className="btn primary">❌ Delete Sweep</button>
      </div>

      <table className="artwork-table">
        <thead>
          <tr>
            <th>Parameter Name</th>
            <th>From</th>
            <th>To</th>
            <th>Type</th>
            <th>nPoints / Step</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sweepParams.length > 0 ? (
            sweepParams.map((row, index) => {
              const otherSelected = sweepParams.filter((_, i) => i !== index).map(r => r.parameterName);
              const availableOptions = parameterData.filter(
                item => !otherSelected.includes(item.parameter) || item.parameter === row.parameterName
              );
              return (
                <tr key={index}>
                  <td>
                    <select
                      value={row.parameterName}
                      onChange={(e) => handleRowChange(index, "parameterName", e.target.value)}
                      className="input-field"
                    >
                      <option value="">-- Select --</option>
                      {availableOptions.map((item, i) => (
                        <option key={i} value={item.parameter}>{item.parameter}</option>
                      ))}
                    </select>
                  </td>
                  <td><input type="number" value={row.from} onChange={(e) => handleRowChange(index, "from", e.target.value)} className="input-field" /></td>
                  <td><input type="number" value={row.to} onChange={(e) => handleRowChange(index, "to", e.target.value)} className="input-field" /></td>
                  <td>
                    <select value={row.type} onChange={(e) => handleRowChange(index, "type", e.target.value)} className="input-field">
                      <option value="npoints">nPoints</option>
                      <option value="step">Step</option>
                    </select>
                  </td>
                  <td><input type="number" value={row.value} onChange={(e) => handleRowChange(index, "value", e.target.value)} className="input-field" /></td>
                  <td><button onClick={() => deleteRow(index)} className="btn-table-action delete">Delete</button></td>
                </tr>
              );
            })
          ) : (
            <tr><td colSpan="6" className="centered">No parameters available.</td></tr>
          )}
        </tbody>
      </table>

      <button onClick={addRow} className="btn-table-action add" style={{ display: 'block' }}>
        ➕ Add Row
      </button>

      <hr />

      <div className="input-group">
        <label><input type="checkbox" checked={enableLayout} onChange={(e) => setEnableLayout(e.target.checked)} /> Enable Layout</label>
        <label><input type="checkbox" checked={enableSvg} onChange={(e) => setEnableSvg(e.target.checked)} style={{ marginLeft: '1rem' }} /> Enable SVG</label>
        <label><input type="checkbox" checked={enableSimulation} onChange={(e) => setEnableSimulation(e.target.checked)} style={{ marginLeft: '1rem' }} /> Enable Simulation</label>
        <label><input type="checkbox" checked={enableForceOverwrite} onChange={(e) => setEnableForceOverwrite(e.target.checked)} style={{ marginLeft: '1rem' }} /> Force Overwrite</label>
      </div>

      {enableSimulation && (
        <div className="input-group">
          <label>
            Choose Simulator:
            <select value={simulator} onChange={(e) => setSimulator(e.target.value)} className="input-field" style={{ marginLeft: '1rem' }}>
              <option value="EMX">EMX</option>
              <option value="openEMS">openEMS</option>
              <option value="ANSYS Raptor">ANSYS Raptor</option>
            </select>
          </label>
        </div>
      )}

      <div className="button-group">
        <button onClick={handleStartSweep} className="btn primary">▶️ Start Sweep</button>
        <button onClick={handleStopSweep} className="btn primary">⏹ Stop Sweep</button>
      </div>

      <div style={{ marginTop: '1rem' }}>
        <label>Status:</label>
        <textarea
          value={status}
          readOnly
          className="input-field"
          style={{
            width: '100%',
            height: '300px',
            fontFamily: 'monospace',
            backgroundColor: '#f9f9f9',
            border: '1px solid #ccc',
            borderRadius: '6px',
            marginTop: '0.5rem',
            color: '#333',
            padding: '0.5rem'
          }}
        />
      </div>
    </div>
  );
};

export default Sweep;

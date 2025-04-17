// src/pages/Sweep.jsx
import React, { useState, useEffect } from 'react';
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
    mode,
    sweepName,
    sweepParams,
    setSweepParams,
    handleModeChange,
    handleSweepNameChange,
    addRow,
    deleteRow,
    handleRowChange,
    handleSave,

    enableLayout,
    setEnableLayout,
    enableSvg,
    setEnableSvg,
    enableSimulation,
    setEnableSimulation,
    enableForceOverwrite,
    setEnableForceOverwrite,

    simulator,
    setSimulator,

    status,
    setStatus,

    pollingRef,
    polling,
    setPolling
  } = useSweep();

  const { parameter: { parameterData } } = useArtworkContext();

  // Local state for the list of sweeps
  const [sweepOptions, setSweepOptions] = useState([]);

  // If polling is true, a sweep is running
  const isRunning = polling;

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
        setStatus(`❌ Error: ${err.message}`);
        stopPollingStatus();
      }
    }, 1000);
  };

  const stopPollingStatus = () => {
    clearInterval(pollingRef.current);
    pollingRef.current = null;
    setPolling(false);
  };

  // Refresh list when switching to "open" mode
  useEffect(() => {
    if (mode === 'open') {
      refreshSweepList();
    }
  }, [mode]);

  // Load parameters when a sweep is selected
  useEffect(() => {
    if (mode === 'open' && sweepName) {
      (async () => {
        try {
          const response = await loadSweep(sweepName);
          const { sweepParams: loadedSweepParams } = processLoadedSweep(response);
          setSweepParams(loadedSweepParams);
        } catch (error) {
          console.error("Error loading sweep details:", error);
        }
      })();
    }
  }, [mode, sweepName, setSweepParams]);

  // --- note: no longer cleaning up on unmount here ---

  const handleSaveSweep = async () => {
    try {
      await handleSave();
      setStatus('✅ Sweep saved successfully');
      // After saving, switch to open mode and refresh
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
      return alert('⚠️ No sweep selected.');
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
      setStatus(`✅ ${result.status || 'Sweep started'}`);
      startPollingStatus();
    } catch (err) {
      setStatus(`❌ Error starting sweep: ${err.message}`);
    }
  };

  const handleStopSweep = async () => {
    setStatus('🛑 Stopping sweep...');
    try {
      const result = await stopSweep();
      setStatus(`🧹 ${result.status || 'Sweep stopped'}`);
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
          <input
            type="radio"
            name="mode"
            value="new"
            checked={mode === 'new'}
            onChange={handleModeChange}
          />
          Create New Sweep
        </label>
        <label className="mode-label">
          <input
            type="radio"
            name="mode"
            value="open"
            checked={mode === 'open'}
            onChange={handleModeChange}
          />
          Open Existing Sweep
        </label>
      </div>

      <div className="input-group">
        {mode === 'new' ? (
          <input
            type="text"
            value={sweepName}
            onChange={handleSweepNameChange}
            className="input-field"
            placeholder="New Sweep Name"
          />
        ) : (
          <select
            value={sweepName}
            onChange={handleSweepNameChange}
            className="input-field"
          >
            <option value="">-- Select Sweep Data --</option>
            {sweepOptions.map(option => (
              <option key={option.sweep_name} value={option.sweep_name}>
                {option.sweep_name}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="button-group">
        <button onClick={handleSaveSweep} className="btn primary">
          💾 Save Sweep
        </button>
        <button onClick={handleDeleteSweep} className="btn primary">
          ❌ Delete Sweep
        </button>
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
              const otherSelected = sweepParams
                .filter((_, i) => i !== index)
                .map(r => r.parameterName);
              const availableOptions = parameterData.filter(
                item =>
                  !otherSelected.includes(item.parameter) ||
                  item.parameter === row.parameterName
              );
              return (
                <tr key={index}>
                  <td>
                    <select
                      value={row.parameterName}
                      onChange={e =>
                        handleRowChange(index, 'parameterName', e.target.value)
                      }
                      className="input-field"
                    >
                      <option value="">-- Select --</option>
                      {availableOptions.map((item, i) => (
                        <option key={i} value={item.parameter}>
                          {item.parameter}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      value={row.from}
                      onChange={e =>
                        handleRowChange(index, 'from', e.target.value)
                      }
                      className="input-field"
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={row.to}
                      onChange={e =>
                        handleRowChange(index, 'to', e.target.value)
                      }
                      className="input-field"
                    />
                  </td>
                  <td>
                    <select
                      value={row.type}
                      onChange={e =>
                        handleRowChange(index, 'type', e.target.value)
                      }
                      className="input-field"
                    >
                      <option value="npoints">nPoints</option>
                      <option value="step">Step</option>
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      value={row.value}
                      onChange={e =>
                        handleRowChange(index, 'value', e.target.value)
                      }
                      className="input-field"
                    />
                  </td>
                  <td>
                    <button
                      onClick={() => deleteRow(index)}
                      className="btn-table-action delete"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              );
            })
          ) : (
            <tr>
              <td colSpan="6" className="centered">
                No parameters available.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <button onClick={addRow} className="btn-table-action add">
        ➕ Add Row
      </button>

      <hr />

      <div className="input-group">
        <label>
          <input
            type="checkbox"
            checked={enableLayout}
            onChange={e => setEnableLayout(e.target.checked)}
          />{' '}
          Enable Layout
        </label>
        <label style={{ marginLeft: '1rem' }}>
          <input
            type="checkbox"
            checked={enableSvg}
            onChange={e => setEnableSvg(e.target.checked)}
          />{' '}
          Enable SVG
        </label>
        <label style={{ marginLeft: '1rem' }}>
          <input
            type="checkbox"
            checked={enableSimulation}
            onChange={e => setEnableSimulation(e.target.checked)}
          />{' '}
          Enable Simulation
        </label>
        <label style={{ marginLeft: '1rem' }}>
          <input
            type="checkbox"
            checked={enableForceOverwrite}
            onChange={e => setEnableForceOverwrite(e.target.checked)}
          />{' '}
          Force Overwrite
        </label>
      </div>

      {enableSimulation && (
        <div className="input-group">
          <label>
            Select Simulator:
            <select
              value={simulator}
              onChange={e => setSimulator(e.target.value)}
              className="input-field"
              style={{ marginLeft: '1rem' }}
            >
              <option value="EMX">EMX</option>
              <option value="openEMS">openEMS</option>
              <option value="ANSYS Raptor">ANSYS Raptor</option>
            </select>
          </label>
        </div>
      )}

      <div className="button-group">
        <button
          onClick={handleStartSweep}
          disabled={isRunning}
          className="btn primary"
          style={{
            opacity: isRunning ? 0.5 : 1,
            cursor: isRunning ? 'not-allowed' : 'pointer'
          }}
        >
          ▶️ Start Sweep
        </button>
        <button
          onClick={handleStopSweep}
          disabled={!isRunning}
          className="btn primary"
          style={{
            opacity: !isRunning ? 0.5 : 1,
            cursor: !isRunning ? 'not-allowed' : 'pointer'
          }}
        >
          ⏹ Stop Sweep
        </button>
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

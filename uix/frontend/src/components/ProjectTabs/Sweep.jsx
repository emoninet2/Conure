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
  const [sweepOptions, setSweepOptions] = useState([]);
  const isRunning = polling;

  const refreshSweepList = async () => {
    try {
      const result = await listSweeps();
      if (result.success && result.sweeps) setSweepOptions(result.sweeps);
    } catch (error) {
      console.error("Error fetching sweeps:", error);
    }
  };

  // Poll sweep status every second
  const startPollingStatus = () => {
    if (!sweepName || pollingRef.current) return;
    setPolling(true);
    pollingRef.current = setInterval(async () => {
      try {
        const response = await getSweepStatus(sweepName);
        // response.status is a JSON string; parse it
        let parsed;
        try {
          parsed = JSON.parse(response.status);
        } catch (e) {
          console.error('Failed to parse status JSON:', e);
          setStatus(response.status);
          return;
        }
        setStatus(JSON.stringify(parsed, null, 2));
        // Detect completion
        const done =
          parsed.progress_percentage === 100 ||
          parsed.completed_runs >= parsed.total_permutations;
        if (done) {
          setStatus('✅ Sweep completed');
          stopPollingStatus();
        }
      } catch (err) {
        setStatus(`❌ Error: ${err.message}`);
        stopPollingStatus();
      }
    }, 1000);
  };

  const stopPollingStatus = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    setPolling(false);
  };

  // Refresh list on mode change to 'open'
  useEffect(() => {
    if (mode === 'open') refreshSweepList();
  }, [mode]);

  // Load sweep params when sweepName changes
  useEffect(() => {
    if (mode === 'open' && sweepName) {
      (async () => {
        try {
          const res = await loadSweep(sweepName);
          const { sweepParams: loadedSweepParams } = processLoadedSweep(res);
          setSweepParams(loadedSweepParams);
        } catch (error) {
          console.error("Error loading sweep:", error);
        }
      })();
    }
  }, [mode, sweepName, setSweepParams]);

  const handleSaveSweep = async () => {
    try {
      await handleSave();
      setStatus('✅ Sweep saved successfully');
      setTimeout(async () => {
        await refreshSweepList();
        if (mode === 'new') {
          handleModeChange({ target: { value: 'open' } });
          setTimeout(() => handleSweepNameChange({ target: { value: sweepName } }), 50);
        }
      }, 100);
    } catch (err) {
      setStatus(`❌ Error saving sweep: ${err.message}`);
    }
  };

  const handleDeleteSweep = async () => {
    if (!sweepName) return alert('⚠️ No sweep selected.');
    if (!window.confirm(`Delete "${sweepName}"?`)) return;
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
      const res = await startSweep({
        sweepName,
        enableLayout,
        enableSvg,
        enableSimulation,
        simulator,
        forceOverwrite: enableForceOverwrite
      });
      setStatus(`✅ ${res.status || 'Sweep started'}`);
      startPollingStatus();
    } catch (err) {
      setStatus(`❌ Error starting sweep: ${err.message}`);
    }
  };

  const handleStopSweep = async () => {
    // Stop polling immediately
    stopPollingStatus();
    setStatus('🛑 Stopping sweep...');
    try {
      const res = await stopSweep();
      setStatus(`🧹 ${res.status || 'Sweep stopped'}`);
    } catch (err) {
      setStatus(`❌ Error stopping sweep: ${err.message}`);
    }
  };

  return (
    <div className="tab-container">
      <h3 className="artwork-heading">🌀 Sweep</h3>
      {sweepName && <div className="input-group"><strong>Current:</strong> {sweepName}</div>}
      <div className="mode-selection">
        <label>
          <input type="radio" name="mode" value="new" checked={mode==='new'} onChange={handleModeChange}/>
          Create New
        </label>
        <label>
          <input type="radio" name="mode" value="open" checked={mode==='open'} onChange={handleModeChange}/>
          Open Existing
        </label>
      </div>
      <div className="input-group">
        {mode==='new' ? (
          <input
            type="text"
            value={sweepName}
            onChange={handleSweepNameChange}
            className="input-field"
            placeholder="Sweep Name"
          />
        ) : (
          <select
            value={sweepName}
            onChange={handleSweepNameChange}
            className="input-field"
          >
            <option value="">-- Select --</option>
            {sweepOptions.map(o => <option key={o.sweep_name} value={o.sweep_name}>{o.sweep_name}</option>)}
          </select>
        )}
      </div>
      <div className="button-group">
        <button onClick={handleSaveSweep} className="btn primary">💾 Save Sweep</button>
        <button onClick={handleDeleteSweep} className="btn primary">❌ Delete Sweep</button>
      </div>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Param</th><th>From</th><th>To</th><th>Type</th><th>Count</th><th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sweepParams.length > 0 ? sweepParams.map((row, i) => {
            const other = sweepParams.filter((_, j) => j !== i).map(r => r.parameterName);
            const opts = parameterData.filter(item => !other.includes(item.parameter) || item.parameter === row.parameterName);
            return (
              <tr key={i}>
                <td>
                  <select
                    value={row.parameterName}
                    onChange={e => handleRowChange(i, 'parameterName', e.target.value)}
                    className="input-field"
                  >
                    <option value="">--</option>
                    {opts.map((it, j) => <option key={j} value={it.parameter}>{it.parameter}</option>)}
                  </select>
                </td>
                <td><input type="number" value={row.from} onChange={e => handleRowChange(i, 'from', e.target.value)} className="input-field"/></td>
                <td><input type="number" value={row.to} onChange={e => handleRowChange(i, 'to', e.target.value)} className="input-field"/></td>
                <td>
                  <select value={row.type} onChange={e => handleRowChange(i, 'type', e.target.value)} className="input-field">
                    <option value="npoints">nPoints</option><option value="step">Step</option>
                  </select>
                </td>
                <td><input type="number" value={row.value} onChange={e => handleRowChange(i, 'value', e.target.value)} className="input-field"/></td>
                <td><button onClick={() => deleteRow(i)} className="btn-table-action delete">Delete</button></td>
              </tr>
            );
          }) : <tr><td colSpan="6" className="centered">No params</td></tr>}
        </tbody>
      </table>
      <button onClick={addRow} className="btn-table-action add">➕ Add Row</button>
      <hr />
      <div className="input-group">
        <label><input type="checkbox" checked={enableLayout} onChange={e => setEnableLayout(e.target.checked)}/> Layout</label>
        <label style={{ marginLeft: '1rem' }}><input type="checkbox" checked={enableSvg} onChange={e => setEnableSvg(e.target.checked)}/> SVG</label>
        <label style={{ marginLeft: '1rem' }}><input type="checkbox" checked={enableSimulation} onChange={e => setEnableSimulation(e.target.checked)}/> Simulation</label>
        <label style={{ marginLeft: '1rem' }}><input type="checkbox" checked={enableForceOverwrite} onChange={e => setEnableForceOverwrite(e.target.checked)}/> Overwrite</label>
      </div>
      {enableSimulation && (
        <div className="input-group">
          <label>Select Simulator:
            <select value={simulator} onChange={e => setSimulator(e.target.value)} className="input-field" style={{ marginLeft: '1rem' }}>
              <option value="EMX">EMX</option><option value="openEMS">openEMS</option><option value="ANSYS Raptor">ANSYS Raptor</option>
            </select>
          </label>
        </div>
      )}
      <div className="button-group">
        <button onClick={handleStartSweep} disabled={isRunning} className="btn primary" style={{ opacity: isRunning ? 0.5 : 1, cursor: isRunning ? 'not-allowed' : 'pointer' }}>▶️ Start</button>
        <button onClick={handleStopSweep} disabled={!isRunning} className="btn primary" style={{ opacity: !isRunning ? 0.5 : 1, cursor: !isRunning ? 'not-allowed' : 'pointer' }}>⏹ Stop</button>
      </div>
      <div style={{ marginTop: '1rem' }}>
        <label>Status:</label>
        <textarea
          value={status}
          readOnly
          className="input-field"
          style={{ width: '100%', height: '200px', fontFamily: 'monospace', background: '#f9f9f9', padding: '0.5rem', borderRadius: '4px' }}
        />
      </div>
    </div>
  );
};

export default Sweep;

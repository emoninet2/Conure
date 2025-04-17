// src/Simulate.jsx
import React from 'react';
import { useSimulate } from '../../context/SimulateContext';
import '../../styles/theme.css';

function Simulate() {
  const { simulator, setSimulator, status, setStatus } = useSimulate();

  const handleStart = async () => {
    setStatus('Starting...');
    try {
      const res = await fetch(`/api/start_simulation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ simulator }),
      });
      const { status: newStatus, error } = await res.json();
      if (!res.ok) throw new Error(error);
      setStatus(newStatus || 'Running');
    } catch (err) {
      console.error(err);
      setStatus(`❌ Error: ${err.message}`);
    }
  };

  const handleStop = async () => {
    setStatus('Stopping...');
    try {
      const res = await fetch(`/api/stop_simulation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const { status: newStatus, error } = await res.json();
      if (!res.ok) throw new Error(error);
      setStatus(newStatus || 'Stopped');
    } catch (err) {
      console.error(err);
      setStatus(`❌ Error: ${err.message}`);
    }
  };

  return (
    <div className="tab-container">

      <h3 className="artwork-heading">🎛 Simulation Control Panel</h3>

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

      
      <div className="button-group" style={{ marginTop: 20 }}>
        <button
          onClick={handleStart}
          disabled={status === 'Running' || status === 'Starting...'}
          className="btn primary"
          style={{
            marginRight: 10,
            opacity: (status === 'Running' || status === 'Starting...') ? 0.5 : 1,
            cursor: (status === 'Running' || status === 'Starting...') ? 'not-allowed' : 'pointer',
          }}
        >
          ▶️ Start
        </button>
        <button
          onClick={handleStop}
          disabled={!(status === 'Running' || status === 'Starting...')}
          className="btn primary"
          style={{
            opacity: !(status === 'Running' || status === 'Starting...') ? 0.5 : 1,
            cursor: !(status === 'Running' || status === 'Starting...') ? 'not-allowed' : 'pointer',
          }}
        >
          ⏹ Stop
        </button>
      </div>

      <div style={{ marginTop: 20 }}>
        <label>Status:</label>
        <textarea
          value={status}
          readOnly
          style={{
            width: '100%',
            height: 100,
            marginTop: 10,
            fontFamily: 'monospace',
            background: '#f4f4f4',
            padding: 10,
            borderRadius: 6,
            border: '1px solid #ccc',
          }}
        />
      </div>
    </div>
  );
}

export default Simulate;

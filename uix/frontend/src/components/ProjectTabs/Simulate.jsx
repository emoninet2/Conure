import React, { useState } from 'react';

function Simulate() {
  const [simulator, setSimulator] = useState('EMX');
  const [status, setStatus] = useState('Idle');

  const handleStart = async () => {
    setStatus('Starting...');
    try {
      const res = await fetch(`/api/start_simulation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ simulator }),
      });
      const result = await res.json();
      if (!res.ok) throw new Error(result.error);
      setStatus(result.status || 'Running');
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
      const result = await res.json();
      if (!res.ok) throw new Error(result.error);
      setStatus(result.status || 'Stopped');
    } catch (err) {
      console.error(err);
      setStatus(`❌ Error: ${err.message}`);
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '20px 0', padding: '20px', textAlign: 'left' }}>
      <h3>🎛 Simulation Control Panel</h3>

      <label>
        Select Simulator:
        <select
          value={simulator}
          onChange={(e) => setSimulator(e.target.value)}
          style={{ marginLeft: '10px' }}
        >
          <option value="EMX">EMX</option>
          <option value="openEMS">openEMS</option>
          <option value="ANSYS Raptor">ANSYS Raptor</option>
        </select>
      </label>

      <div style={{ marginTop: '20px' }}>
        <button onClick={handleStart} style={{ marginRight: '10px' }}>
          ▶️ Start
        </button>
        <button onClick={handleStop}>⏹ Stop</button>
      </div>

      <div style={{ marginTop: '20px' }}>
        <label>Status:</label>
        <textarea
          value={status}
          readOnly
          style={{
            width: '100%',
            height: '100px',
            marginTop: '10px',
            fontFamily: 'monospace',
            background: '#f4f4f4',
            color: '#000', // force text color to black
            padding: '10px',
            borderRadius: '6px',
            border: '1px solid #ccc',
          }}
        />
      </div>
    </div>
  );
}

export default Simulate;

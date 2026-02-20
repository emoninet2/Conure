// src/Simulate.jsx
import React, { useRef, useEffect, useState } from 'react';
import { useSimulate } from '../../context/SimulateContext';
import '../../styles/theme.css';

function Simulate() {
  //const { simulator, setSimulator } = useSimulate();
  const { simulator, setSimulator, status, setStatus, isRunning, setIsRunning } = useSimulate();
  //const [status, setStatus] = useState('');
  //const [isRunning, setIsRunning] = useState(false);
  const eventSourceRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll on status update
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.scrollTop = textareaRef.current.scrollHeight;
    }
  }, [status]);

  const handleStart = () => {
    if (eventSourceRef.current) eventSourceRef.current.close();

    setStatus('');
    setIsRunning(true);

    const eventSource = new EventSource(
      `/api/start_simulation?simulator=${encodeURIComponent(simulator)}`
    );

    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setStatus(prev => prev + `🚀 Starting ${simulator} simulation...\n\n`);
    };

    eventSource.onmessage = (event) => {
      setStatus(prev => prev + event.data + "\n");
    };

    eventSource.onerror = (err) => {
      console.error("SSE error:", err);
      setStatus(prev => prev + "\n⚠️ Connection closed.\n");
      setIsRunning(false);
      eventSource.close();
    };
  };

  const handleStop = async () => {
    setStatus(prev => prev + "\n⏹ Stopping simulation...\n");

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const res = await fetch(`/api/stop_simulation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await res.json();
      setStatus(prev => prev + (data.status || "Stopped") + "\n");
      setIsRunning(false);
    } catch (err) {
      console.error(err);
      setStatus(prev => prev + `❌ Error stopping simulation: ${err.message}\n`);
      setIsRunning(false);
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
          disabled={isRunning}  // ⬅ Start disabled when running
          className="btn primary"
          style={{
            marginRight: 10,
            opacity: isRunning ? 0.5 : 1,
            cursor: isRunning ? 'not-allowed' : 'pointer'
          }}
        >
          ▶️ Start
        </button>

        <button
          onClick={handleStop}
          disabled={!isRunning} // ⬅ Stop disabled when not running
          className="btn primary"
          style={{
            opacity: !isRunning ? 0.5 : 1,
            cursor: !isRunning ? 'not-allowed' : 'pointer'
          }}
        >
          ⏹ Stop
        </button>
      </div>

      <div style={{ marginTop: 20 }}>
        <label>Status:</label>
        <textarea
          ref={textareaRef}
          value={status}
          readOnly
          style={{
            width: '100%',
            height: 250,
            marginTop: 10,
            fontFamily: 'monospace',
            background: '#111',
            color: '#00ff88',
            padding: 10,
            borderRadius: 6,
            border: '1px solid #333',
            whiteSpace: 'pre-wrap',
            overflowY: 'auto'
          }}
        />
      </div>
    </div>
  );
}

export default Simulate;


// // src/Simulate.jsx
// import React from 'react';
// import { useSimulate } from '../../context/SimulateContext';
// import '../../styles/theme.css';

// function Simulate() {
//   const { simulator, setSimulator, status, setStatus } = useSimulate();

//   const handleStart = async () => {
//     setStatus('Starting...');
//     try {
//       const res = await fetch(`/api/start_simulation`, {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ simulator }),
//       });
//       const { status: newStatus, error } = await res.json();
//       if (!res.ok) throw new Error(error);
//       setStatus(newStatus || 'Running');
//     } catch (err) {
//       console.error(err);
//       setStatus(`❌ Error: ${err.message}`);
//     }
//   };

//   const handleStop = async () => {
//     setStatus('Stopping...');
//     try {
//       const res = await fetch(`/api/stop_simulation`, {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//       });
//       const { status: newStatus, error } = await res.json();
//       if (!res.ok) throw new Error(error);
//       setStatus(newStatus || 'Stopped');
//     } catch (err) {
//       console.error(err);
//       setStatus(`❌ Error: ${err.message}`);
//     }
//   };

//   return (
//     <div className="tab-container">

//       <h3 className="artwork-heading">🎛 Simulation Control Panel</h3>

//       <div className="input-group">
//           <label>
//             Select Simulator:
//             <select
//               value={simulator}
//               onChange={e => setSimulator(e.target.value)}
//               className="input-field"
//               style={{ marginLeft: '1rem' }}
//             >
//               <option value="EMX">EMX</option>
//               <option value="openEMS">openEMS</option>
//               <option value="ANSYS Raptor">ANSYS Raptor</option>
//             </select>
//           </label>
//         </div>

      
//       <div className="button-group" style={{ marginTop: 20 }}>
//         <button
//           onClick={handleStart}
//           disabled={status === 'Running' || status === 'Starting...'}
//           className="btn primary"
//           style={{
//             marginRight: 10,
//             opacity: (status === 'Running' || status === 'Starting...') ? 0.5 : 1,
//             cursor: (status === 'Running' || status === 'Starting...') ? 'not-allowed' : 'pointer',
//           }}
//         >
//           ▶️ Start
//         </button>
//         <button
//           onClick={handleStop}
//           disabled={!(status === 'Running' || status === 'Starting...')}
//           className="btn primary"
//           style={{
//             opacity: !(status === 'Running' || status === 'Starting...') ? 0.5 : 1,
//             cursor: !(status === 'Running' || status === 'Starting...') ? 'not-allowed' : 'pointer',
//           }}
//         >
//           ⏹ Stop
//         </button>
//       </div>

//       <div style={{ marginTop: 20 }}>
//         <label>Status:</label>
//         <textarea
//           value={status}
//           readOnly
//           style={{
//             width: '100%',
//             height: 100,
//             marginTop: 10,
//             fontFamily: 'monospace',
//             background: '#f4f4f4',
//             padding: 10,
//             borderRadius: 6,
//             border: '1px solid #ccc',
//           }}
//         />
//       </div>
//     </div>
//   );
// }

// export default Simulate;

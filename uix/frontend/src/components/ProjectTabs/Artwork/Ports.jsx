import { useArtworkContext } from '../../../context/ArtworkContext';
import '../../../styles/Artwork/Common.css'; // ✅ Import the CSS file

function Ports() {
  const { ports } = useArtworkContext();
  const { portData, setPortData, simPortData, setSimPortData } = ports;

  // --- Standard Ports Handlers ---
  const handlePortChange = (index, field, value) => {
    const updated = [...portData];
    updated[index][field] = value;
    setPortData(updated);
  };

  const handleAddPort = () => {
    setPortData([...portData, { name: '', label: '' }]);
  };

  const handleDeletePort = (index) => {
    setPortData(portData.filter((_, i) => i !== index));
  };

  // --- Simulation Ports Handlers ---
  const handleSimPortChange = (index, field, value) => {
    const updated = [...simPortData];
    updated[index][field] = value;
    setSimPortData(updated);
  };

  const handleAddSimPort = () => {
    setSimPortData([
      ...simPortData,
      { portId: '', portType: '', plusPort: '', minusPort: '', enable: false }
    ]);
  };

  const handleDeleteSimPort = (index) => {
    setSimPortData(simPortData.filter((_, i) => i !== index));
  };

  const availablePorts = portData.filter(p => p.name?.trim() !== '');

  return (
    <div className="ports-container">
      {/* Standard Ports */}
      <h4>🔌 Ports Table</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Label</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {portData.map((row, index) => (
            <tr key={index}>
              <td>
                <input
                  type="text"
                  value={row.name}
                  onChange={(e) => handlePortChange(index, 'name', e.target.value)}
                />
              </td>
              <td>
                <input
                  type="text"
                  value={row.label}
                  onChange={(e) => handlePortChange(index, 'label', e.target.value)}
                />
              </td>
              <td>
                <button onClick={() => handleDeletePort(index)} className="delete-row-button">
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <button onClick={handleAddPort} className="add-row-button" style={{ display: 'block' }}>
        Add Port
      </button>

      {/* Spacer */}
      <div style={{ margin: '2rem 0' }} />

      {/* Simulation Ports */}
      <h4>🧪 Simulation Ports Table</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Port ID</th>
            <th>Port Type</th>
            <th>Plus Port</th>
            <th>Minus Port</th>
            <th>Enable</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {simPortData.map((row, index) => (
            <tr key={index}>
              <td>
                {/* <input
                  type="text"
                  value={row.portId}
                  onChange={(e) => handleSimPortChange(index, 'portId', e.target.value)}
                /> */}

                <input
                  type="text"
                  value={index}
                  disabled
                  className="field-disabled"
                />


              </td>
              <td>
                <select
                  value={row.portType}
                  onChange={(e) => handleSimPortChange(index, 'portType', e.target.value)}
                >
                  <option value="">Select Type</option>
                  <option value="single-ended">Single-Ended</option>
                  <option value="differential">Differential</option>
                </select>
              </td>
              <td>
                <select
                  value={row.plusPort}
                  onChange={(e) => handleSimPortChange(index, 'plusPort', e.target.value)}
                >
                  <option value="">Select Port</option>
                  {availablePorts.map((port, i) => (
                    <option key={i} value={port.name}>
                      {port.name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <select
                  value={row.minusPort}
                  onChange={(e) => handleSimPortChange(index, 'minusPort', e.target.value)}
                  disabled={row.portType === 'single-ended'}
                >
                  <option value="">Select Port</option>
                  {availablePorts.map((port, i) => (
                    <option key={i} value={port.name}>
                      {port.name}
                    </option>
                  ))}
                </select>
              </td>
              <td style={{ textAlign: 'center' }}>
                <input
                  type="checkbox"
                  checked={!!row.enable}
                  onChange={(e) => handleSimPortChange(index, 'enable', e.target.checked)}
                />
              </td>
              <td>
                <button onClick={() => handleDeleteSimPort(index)} className="delete-row-button">
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <button onClick={handleAddSimPort} className="add-row-button" style={{ display: 'block' }}>
        Add Simulation Port
      </button>
    </div>
  );
}

export default Ports;

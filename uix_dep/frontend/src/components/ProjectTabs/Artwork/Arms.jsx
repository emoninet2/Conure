import { useArtworkContext } from '../../../context/ArtworkContext';

function Arms() {
  const { arms, ports, layers, viaPadStack } = useArtworkContext();
  const { armData, setArmData } = arms;
  const { portData } = ports;
  const { layerData } = layers;
  const { viaPadStackData } = viaPadStack;

  const handleChange = (index, field, value) => {
    const updated = [...armData];
    updated[index][field] = value;

    if (field === 'type' && value === 'single') {
      updated[index]['spacing'] = '';
      updated[index]['port2'] = '';
    }

    setArmData(updated);
  };

  const handleAddRow = () => {
    setArmData([
      ...armData,
      {
        name: '',
        type: '',
        length: '',
        width: '',
        spacing: '',
        port1: '',
        port2: '',
        layer: '',
        viaPadStack: ''
      }
    ]);
  };

  const handleDeleteRow = (index) => {
    setArmData(armData.filter((_, i) => i !== index));
  };

  const portOptions = portData.filter(p => p.name?.trim());
  const layerOptions = layerData.filter(l => l.name?.trim());
  const viaPadStackOptions = viaPadStackData.filter(v => v.name?.trim());

  return (
    <div className="artwork-subtab-container">
      <h4 className="section-heading">🦾 Arms Table</h4>

      <table className="artwork-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Length</th>
            <th>Width</th>
            <th>Spacing</th>
            <th>Port 1</th>
            <th>Port 2</th>
            <th>Layer</th>
            <th>Via Pad Stack</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {armData.map((row, index) => (
            <tr key={index}>
              <td>
                <input
                  type="text"
                  value={row.name}
                  onChange={(e) => handleChange(index, 'name', e.target.value)}
                  className="input-field"
                />
              </td>
              <td>
                <select
                  value={row.type}
                  onChange={(e) => handleChange(index, 'type', e.target.value)}
                  className="input-field"
                >
                  <option value="">Select Type</option>
                  <option value="single">Single</option>
                  <option value="double">Double</option>
                </select>
              </td>
              <td>
                <input
                  type="text"
                  value={row.length}
                  onChange={(e) => handleChange(index, 'length', e.target.value)}
                  className="input-field"
                />
              </td>
              <td>
                <input
                  type="text"
                  value={row.width}
                  onChange={(e) => handleChange(index, 'width', e.target.value)}
                  className="input-field"
                />
              </td>
              <td>
                <input
                  type="text"
                  value={row.spacing}
                  onChange={(e) => handleChange(index, 'spacing', e.target.value)}
                  disabled={row.type === 'single'}
                  className={`input-field ${row.type === 'single' ? 'field-disabled' : ''}`}
                  title={row.type === 'single' ? 'Spacing is only used for double arms' : ''}
                />
              </td>
              <td>
                <select
                  value={row.port1}
                  onChange={(e) => handleChange(index, 'port1', e.target.value)}
                  className="input-field"
                >
                  <option value="">Select Port 1</option>
                  {portOptions.map((p, i) => (
                    <option key={i} value={p.name}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <select
                  value={row.port2}
                  onChange={(e) => handleChange(index, 'port2', e.target.value)}
                  disabled={row.type === 'single'}
                  className={`input-field ${row.type === 'single' ? 'field-disabled' : ''}`}
                  title={row.type === 'single' ? 'Port 2 is only used for double arms' : ''}
                >
                  <option value="">Select Port 2</option>
                  {portOptions.map((p, i) => (
                    <option key={i} value={p.name}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <select
                  value={row.layer}
                  onChange={(e) => handleChange(index, 'layer', e.target.value)}
                  className="input-field"
                >
                  <option value="">Select Layer</option>
                  {layerOptions.map((l, i) => (
                    <option key={i} value={l.name}>
                      {l.name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <select
                  value={row.viaPadStack}
                  onChange={(e) => handleChange(index, 'viaPadStack', e.target.value)}
                  className="input-field"
                >
                  <option value="">Select Via Pad Stack</option>
                  {viaPadStackOptions.map((v, i) => (
                    <option key={i} value={v.name}>
                      {v.name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <button
                  onClick={() => handleDeleteRow(index)}
                  className="btn-table-action delete"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <button onClick={handleAddRow} className="btn-table-action add" style={{ display: 'block' }}>
        ➕ Add Arm
      </button>
    </div>
  );
}

export default Arms;

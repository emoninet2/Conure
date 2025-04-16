import { useArtworkContext } from '../../../context/ArtworkContext';

function Bridges() {
  const { bridges, layers, vias, viaPadStack } = useArtworkContext();
  const { bridgeData, setBridgeData } = bridges;
  const { layerData } = layers;
  const { viaData } = vias;
  const { viaPadStackData } = viaPadStack;

  const handleChange = (index, field, value) => {
    const updatedRows = [...bridgeData];
    updatedRows[index][field] = value;
    setBridgeData(updatedRows);
  };

  const handleAddRow = () => {
    setBridgeData([
      ...bridgeData,
      {
        name: '',
        layer: '',
        via: '',
        viaWidth: '',
        viaStackCCW: '',
        viaStackCW: ''
      }
    ]);
  };

  const handleDeleteRow = (index) => {
    const updatedRows = bridgeData.filter((_, i) => i !== index);
    setBridgeData(updatedRows);
  };

  const layerOptions = layerData.filter(layer => layer.name?.trim() !== '');
  const viaStackOptions = viaPadStackData.filter(stack => stack.name?.trim() !== '');

  return (
    <div className="artwork-subtab-container">
      <h4 className="section-heading">🌉 Bridges Table</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Layer</th>
            <th>Via Stack CCW</th>
            <th>Via Stack CW</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {bridgeData.map((row, index) => (
            <tr key={index}>
              <td>
                <input
                  type="text"
                  className="input-field"
                  value={row.name}
                  onChange={(e) => handleChange(index, 'name', e.target.value)}
                />
              </td>
              <td>
                <select
                  value={row.layer}
                  onChange={(e) => handleChange(index, 'layer', e.target.value)}
                  className="input-field"
                >
                  <option value="">Select Layer</option>
                  {layerOptions.map((layer, i) => (
                    <option key={i} value={layer.name}>
                      {layer.name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <select
                  value={row.viaStackCCW}
                  onChange={(e) => handleChange(index, 'viaStackCCW', e.target.value)}
                  className="input-field"
                >
                  <option value="">Select Stack</option>
                  {viaStackOptions.map((stack, i) => (
                    <option key={i} value={stack.name}>
                      {stack.name}
                    </option>
                  ))}
                </select>
              </td>
              <td>
                <select
                  value={row.viaStackCW}
                  onChange={(e) => handleChange(index, 'viaStackCW', e.target.value)}
                  className="input-field"
                >
                  <option value="">Select Stack</option>
                  {viaStackOptions.map((stack, i) => (
                    <option key={i} value={stack.name}>
                      {stack.name}
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

      <button
        onClick={handleAddRow}
        className="btn-table-action add full-width"
      >
        ➕ Add Bridge
      </button>
    </div>
  );
}

export default Bridges;

import { useArtworkContext } from '../../../context/ArtworkContext';

function Vias() {
  const { vias, layers } = useArtworkContext();
  const { viaData, setViaData } = vias;
  const { layerData } = layers;

  const handleChange = (index, field, value) => {
    const updatedRows = [...viaData];
    updatedRows[index][field] = value;
    setViaData(updatedRows);
  };

  const handleAddRow = () => {
    setViaData([
      ...viaData,
      { name: '', length: '', width: '', spacing: '', angle: '', layer: '' }
    ]);
  };

  const handleDeleteRow = (index) => {
    const updatedRows = viaData.filter((_, i) => i !== index);
    setViaData(updatedRows);
  };

  const nonEmptyLayers = layerData.filter(layer => layer.name?.trim() !== '');

  return (
    <div className="artwork-subtab-container">
      <h4 className="section-heading">🔩 Vias Table</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Length</th>
            <th>Width</th>
            <th>Spacing</th>
            <th>Angle</th>
            <th>Layer</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {viaData.map((row, index) => (
            <tr key={index}>
              {['name', 'length', 'width', 'spacing', 'angle'].map((field) => (
                <td key={field}>
                  <input
                    type="text"
                    value={row[field]}
                    onChange={(e) => handleChange(index, field, e.target.value)}
                    className="input-field"
                  />
                </td>
              ))}
              <td>
                <select
                  value={row.layer}
                  onChange={(e) => handleChange(index, 'layer', e.target.value)}
                  className="input-field"
                >
                  <option value="">Select Layer</option>
                  {nonEmptyLayers.map((layer, i) => (
                    <option key={i} value={layer.name}>
                      {layer.name}
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
        ➕ Add Via
      </button>
    </div>
  );
}

export default Vias;

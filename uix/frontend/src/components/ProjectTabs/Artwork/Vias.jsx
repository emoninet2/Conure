import { useArtworkContext } from '../../../context/ArtworkContext';
import '../../../styles/Artwork/Common.css' // ✅ Import the CSS file

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

  return (
    <div className="vias-container">
      <h4>🔩 Vias Table</h4>
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
              {['name', 'length', 'width', 'spacing', 'angle', 'layer'].map((field) => (
                <td key={field}>
                  {field === 'layer' ? (
                    <select
                      value={row[field]}
                      onChange={(e) => handleChange(index, field, e.target.value)}
                    >
                      <option value="">Select Layer</option>
                      {layerData
                      .filter(layer => layer.name?.trim() !== '') // ✅ only non-empty names
                      .map((layer, i) => (
                        <option key={i} value={layer.name}>
                          {/* {layer.name || `Layer ${i + 1}`} */}
                          {layer.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={row[field]}
                      onChange={(e) => handleChange(index, field, e.target.value)}
                    />
                  )}
                </td>
              ))}
              <td>
                <button onClick={() => handleDeleteRow(index)}className="delete-row-button" >Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <button onClick={handleAddRow} className="add-row-button" style={{ display: 'block' }}>
        Add Row
      </button>
    </div>
  );
}

export default Vias;

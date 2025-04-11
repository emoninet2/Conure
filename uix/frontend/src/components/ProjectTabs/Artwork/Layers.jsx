import { useArtworkContext } from '../../../context/ArtworkContext';
import '../../../styles/Artwork/Common.css' // ✅ Import the CSS file

function Layers() {
  const { layers } = useArtworkContext();
  const { layerData, setLayerData } = layers;

  const handleChange = (index, field, value) => {
    const updatedRows = [...layerData];
    updatedRows[index][field] = value;
    setLayerData(updatedRows);
  };

  const handleAddRow = () => {
    setLayerData([
      ...layerData,
      { name: '', gdsLayer: '', gdsDatatype: '' }
    ]);
  };

  const handleDeleteRow = (index) => {
    const updatedRows = layerData.filter((_, i) => i !== index);
    setLayerData(updatedRows);
  };

  return (
    <div className="layers-container">
      <h4>🧱 Layers Table</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>GDS Layer</th>
            <th>GDS Datatype</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {layerData.map((row, index) => (
            <tr key={index}>
              <td>
                <input
                  type="text"
                  value={row.name}
                  onChange={(e) => handleChange(index, 'name', e.target.value)}
                />
              </td>
              <td>
                <input
                  type="text"
                  value={row.gdsLayer}
                  onChange={(e) => handleChange(index, 'gdsLayer', e.target.value)}
                />
              </td>
              <td>
                <input
                  type="text"
                  value={row.gdsDatatype}
                  onChange={(e) => handleChange(index, 'gdsDatatype', e.target.value)}
                />
              </td>
              <td>
                <button onClick={() => handleDeleteRow(index)} className="delete-row-button">Delete</button>
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

export default Layers;

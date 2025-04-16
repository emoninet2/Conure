import { useArtworkContext } from '../../../context/ArtworkContext';

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
    <div className="artwork-subtab-container">
      <h4 className="section-heading">🧱 Layers Table</h4>
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
                  className="input-field"
                  value={row.name}
                  onChange={(e) => handleChange(index, 'name', e.target.value)}
                />
              </td>
              <td>
                <input
                  type="text"
                  className="input-field"
                  value={row.gdsLayer}
                  onChange={(e) => handleChange(index, 'gdsLayer', e.target.value)}
                />
              </td>
              <td>
                <input
                  type="text"
                  className="input-field"
                  value={row.gdsDatatype}
                  onChange={(e) => handleChange(index, 'gdsDatatype', e.target.value)}
                />
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
        ➕ Add Layer
      </button>
    </div>
  );
}

export default Layers;

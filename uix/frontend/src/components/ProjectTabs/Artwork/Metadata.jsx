import { useArtworkContext } from '../../../context/ArtworkContext';

function Metadata() {
  const { metadata } = useArtworkContext();
  const { metaData, setMetaData } = metadata;

  const handleChange = (index, field, value) => {
    const updated = [...metaData];
    updated[index][field] = value;
    setMetaData(updated);
  };

  const handleAddRow = () => {
    setMetaData([...metaData, { parameter: '', value: '' }]);
  };

  const handleDeleteRow = (index) => {
    setMetaData(metaData.filter((_, i) => i !== index));
  };

  return (
    <div className="artwork-subtab-container">
      <h4 className="section-heading">📝 Metadata Table</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Parameter</th>
            <th>Value</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {metaData.map((row, index) => (
            <tr key={index}>
              <td>
                <input
                  className="input-field"
                  type="text"
                  value={row.parameter}
                  onChange={(e) => handleChange(index, 'parameter', e.target.value)}
                />
              </td>
              <td>
                <input
                  className="input-field"
                  type="text"
                  value={row.value}
                  onChange={(e) => handleChange(index, 'value', e.target.value)}
                />
              </td>
              <td>
                <button
                  onClick={() => handleDeleteRow(index)}
                  className="btn-table-action delete"
                >
                  🗑 Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <button
        onClick={handleAddRow}
        className="btn-table-action add"
      >
        ➕ Add Metadata
      </button>
    </div>
  );
}

export default Metadata;

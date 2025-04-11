import { useArtworkContext } from '../../../context/ArtworkContext';
import '../../../styles/Artwork/Common.css'; // ✅ styling


function Parameters() {
  const { parameter } = useArtworkContext();
  const { parameterData, setParameterData } = parameter;

  const handleChange = (index, field, value) => {
    const updated = [...parameterData];
    updated[index][field] = value;
    setParameterData(updated);
  };

  const handleAddRow = () => {
    setParameterData([...parameterData, { parameter: '', value: '' }]);
  };

  const handleDeleteRow = (index) => {
    setParameterData(parameterData.filter((_, i) => i !== index));
  };

  return (
    <div className="parameters-container">
      <h4>⚙️ Parameters Table</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Parameter</th>
            <th>Value</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {parameterData.map((row, index) => (
            <tr key={index}>
              <td>
                <input
                  type="text"
                  value={row.parameter}
                  onChange={(e) => handleChange(index, 'parameter', e.target.value)}
                />
              </td>
              <td>
                <input
                  type="text"
                  value={row.value}
                  onChange={(e) => handleChange(index, 'value', e.target.value)}
                />
              </td>
              <td>
                <button
                  onClick={() => handleDeleteRow(index)}
                  className="delete-row-button"
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
        className="add-row-button"
        style={{ display: 'block' }}
      >
        Add Parameter
      </button>
    </div>
  );
}

export default Parameters;


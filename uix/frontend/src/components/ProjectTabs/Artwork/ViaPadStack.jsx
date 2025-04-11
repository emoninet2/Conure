import { useArtworkContext } from '../../../context/ArtworkContext';
import '../../../styles/Artwork/Common.css'; // ✅ Import common styling
import Select from 'react-select';

function ViaPadStack() {
  const { viaPadStack, layers, vias } = useArtworkContext();
  const { viaPadStackData, setViaPadStackData } = viaPadStack;
  const { layerData } = layers;
  const { viaData } = vias;

  const handleChange = (index, field, value) => {
    const updatedRows = [...viaPadStackData];
    updatedRows[index][field] = value;
    setViaPadStackData(updatedRows);
  };

  const handleAddRow = () => {
    setViaPadStackData([
      ...viaPadStackData,
      { name: '', topLayer: '', bottomLayer: '', margin: '', viaList: [] }
    ]);
  };

  const handleDeleteRow = (index) => {
    const updatedRows = viaPadStackData.filter((_, i) => i !== index);
    setViaPadStackData(updatedRows);
  };

  const layerOptions = layerData.filter(layer => layer.name?.trim() !== '');
  const viaOptions = viaData
    .filter(via => via.name?.trim() !== '')
    .map(via => ({ label: via.name, value: via.name }));

  return (
    <div className="via-pad-stack-container">
      <h4>📚 Via Pad Stack Table</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Top Layer</th>
            <th>Bottom Layer</th>
            <th>Margin</th>
            <th>Via List</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {viaPadStackData.map((row, index) => (
            <tr key={index}>
              {/* Name */}
              <td>
                <input
                  type="text"
                  value={row.name}
                  onChange={(e) => handleChange(index, 'name', e.target.value)}
                />
              </td>

              {/* Top Layer */}
              <td>
                <select
                  value={row.topLayer}
                  onChange={(e) => handleChange(index, 'topLayer', e.target.value)}
                >
                  <option value="">Select Top Layer</option>
                  {layerOptions.map((layer, i) => (
                    <option key={i} value={layer.name}>
                      {layer.name}
                    </option>
                  ))}
                </select>
              </td>

              {/* Bottom Layer */}
              <td>
                <select
                  value={row.bottomLayer}
                  onChange={(e) => handleChange(index, 'bottomLayer', e.target.value)}
                >
                  <option value="">Select Bottom Layer</option>
                  {layerOptions.map((layer, i) => (
                    <option key={i} value={layer.name}>
                      {layer.name}
                    </option>
                  ))}
                </select>
              </td>

              {/* Margin */}
              <td>
                <input
                  type="text"
                  value={row.margin}
                  onChange={(e) => handleChange(index, 'margin', e.target.value)}
                />
              </td>

              {/* Via List */}
              <td style={{ minWidth: '200px' }}>
                <Select
                  isMulti
                  options={viaOptions}
                  value={
                    Array.isArray(row.viaList)
                      ? viaOptions.filter(opt => row.viaList.includes(opt.value))
                      : []
                  }
                  onChange={(selectedOptions) => {
                    const values = selectedOptions.map(option => option.value);
                    handleChange(index, 'viaList', values);
                  }}
                  classNamePrefix="select"
                  placeholder="Select vias..."
                />
              </td>

              {/* Delete */}
              <td>
                <button onClick={() => handleDeleteRow(index)} className="delete-row-button" >Delete</button>
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

export default ViaPadStack;

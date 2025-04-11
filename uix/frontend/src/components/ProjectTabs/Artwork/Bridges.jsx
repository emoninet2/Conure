import { useArtworkContext } from '../../../context/ArtworkContext';
import '../../../styles/Artwork/Common.css' // ✅ Import the CSS file

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

  // Filter non-empty values
  const layerOptions = layerData.filter(layer => layer.name?.trim() !== '');
  const viaOptions = viaData.filter(via => via.name?.trim() !== '');
  const viaStackOptions = viaPadStackData.filter(stack => stack.name?.trim() !== '');

  return (
    <div className="bridges-container">
      <h4>🌉 Bridges Table</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Layer</th>
            {/* <th>Via</th>
            <th>Via Width</th> */}
            <th>Via Stack CCW</th>
            <th>Via Stack CW</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {bridgeData.map((row, index) => (
            <tr key={index}>
              {/* Name input */}
              <td>
                <input
                  type="text"
                  value={row.name}
                  onChange={(e) => handleChange(index, 'name', e.target.value)}
                />
              </td>

              {/* Layer dropdown */}
              <td>
                <select
                  value={row.layer}
                  onChange={(e) => handleChange(index, 'layer', e.target.value)}
                >
                  <option value="">Select Layer</option>
                  {layerOptions.map((layer, i) => (
                    <option key={i} value={layer.name}>
                      {layer.name}
                    </option>
                  ))}
                </select>
              </td>

              {/* Via dropdown */}
              {/* <td>
                <select
                  value={row.via}
                  onChange={(e) => handleChange(index, 'via', e.target.value)}
                >
                  <option value="">Select Via</option>
                  {viaOptions.map((via, i) => (
                    <option key={i} value={via.name}>
                      {via.name}
                    </option>
                  ))}
                </select>
              </td> */}

              {/* Via Width input */}
              {/* <td>
                <input
                  type="text"
                  value={row.viaWidth}
                  onChange={(e) => handleChange(index, 'viaWidth', e.target.value)}
                />
              </td> */}

              {/* Via Stack CCW dropdown */}
              <td>
                <select
                  value={row.viaStackCCW}
                  onChange={(e) => handleChange(index, 'viaStackCCW', e.target.value)}
                >
                  <option value="">Select Stack</option>
                  {viaStackOptions.map((stack, i) => (
                    <option key={i} value={stack.name}>
                      {stack.name}
                    </option>
                  ))}
                </select>
              </td>

              {/* Via Stack CW dropdown */}
              <td>
                <select
                  value={row.viaStackCW}
                  onChange={(e) => handleChange(index, 'viaStackCW', e.target.value)}
                >
                  <option value="">Select Stack</option>
                  {viaStackOptions.map((stack, i) => (
                    <option key={i} value={stack.name}>
                      {stack.name}
                    </option>
                  ))}
                </select>
              </td>

              {/* Delete button */}
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

export default Bridges;

import { useArtworkContext } from '../../../context/ArtworkContext';
import '../../../styles/Artwork/Common.css';

function Segments() {
  const { segments, bridges, ports, layers, arms } = useArtworkContext();
  const { segmentData, setSegmentData } = segments;
  const { bridgeData } = bridges;
  const { portData } = ports; //REMOVE THIS 
  const { armData } = arms;
  const { layerData } = layers;

  const handleChange = (segmentIndex, rowIndex, field, value) => {
    const updated = [...segmentData];
    updated[segmentIndex][rowIndex][field] = value;

    if (field === 'type') {
      updated[segmentIndex][rowIndex]['item'] = '';
      updated[segmentIndex][rowIndex]['jump'] = '';
    }

    setSegmentData(updated);
  };

  const handleAddRow = (segmentIndex) => {
    const updated = [...segmentData];
    
    // Ensure there's a valid array at that index
    if (!Array.isArray(updated[segmentIndex])) {
      updated[segmentIndex] = [];
    }
  
    updated[segmentIndex].push({ type: '', item: '', layer: '', jump: '' });
    setSegmentData(updated);
  };
  

  const handleDeleteRow = (segmentIndex, rowIndex) => {
    const updated = [...segmentData];
    updated[segmentIndex] = updated[segmentIndex].filter((_, i) => i !== rowIndex);
    setSegmentData(updated);
  };

  const typeOptions = ['default', 'bridge', 'port'];
  const bridgeOptions = bridgeData.filter(b => b.name?.trim());
  const portOptions = portData.filter(p => p.name?.trim()); // REMOVE THIS 
  const armOptions = armData.filter(a => a.name?.trim());
  const layerOptions = layerData.filter(l => l.name?.trim());

  return (
    <div className="segments-container">
      <h4>🧩 Segments (8 Groups)</h4>
      {segmentData.map((segment, segmentIndex) => (
        <div key={segmentIndex} className="segment-block">
          <h5>Segment {segmentIndex + 1}</h5>
          <table className="artwork-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Item</th>
                <th>Layer</th>
                <th>Jump</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {segment.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {/* Type Dropdown */}
                  <td>
                    <select
                      value={row.type}
                      onChange={(e) =>
                        handleChange(segmentIndex, rowIndex, 'type', e.target.value)
                      }
                    >
                      <option value="">Select Type</option>
                      {typeOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </td>

                  {/* Item Dropdown (or disabled input) */}
                  <td>
                    {row.type === 'bridge' ? (
                      <select
                        value={row.item}
                        onChange={(e) =>
                          handleChange(segmentIndex, rowIndex, 'item', e.target.value)
                        }
                      >
                        <option value="">Select Bridge</option>
                        {bridgeOptions.map((b, i) => (
                          <option key={i} value={b.name}>
                            {b.name}
                          </option>
                        ))}
                      </select>
                    ) : row.type === 'port' ? (
                      <select
                      value={row.item}
                      onChange={(e) =>
                        handleChange(segmentIndex, rowIndex, 'item', e.target.value)
                      }
                    >
                      <option value="">Select Arm</option>
                      {armOptions.map((a, i) => (
                        <option key={i} value={a.name}>
                          {a.name}
                        </option>
                      ))}
                    </select>
                    ) : (
                      <input
                        type="text"
                        disabled
                        value="Not available"
                        className="field-disabled"
                      />
                    )}
                  </td>

                  {/* Layer Dropdown */}
                  <td>
                    <select
                      value={row.layer}
                      onChange={(e) =>
                        handleChange(segmentIndex, rowIndex, 'layer', e.target.value)
                      }
                    >
                      <option value="">Select Layer</option>
                      {layerOptions.map((l, i) => (
                        <option key={i} value={l.name}>
                          {l.name}
                        </option>
                      ))}
                    </select>
                  </td>

                  {/* Jump Input (only for bridge) */}
                  <td>
                    {row.type === 'bridge' ? (
                      <input
                        type="text"
                        value={row.jump}
                        onChange={(e) =>
                          handleChange(segmentIndex, rowIndex, 'jump', e.target.value)
                        }
                      />
                    ) : (
                      <input
                        type="text"
                        disabled
                        value="Not available"
                        className="field-disabled"
                      />
                    )}
                  </td>

                  {/* Delete Row */}
                  <td>
                    <button
                      onClick={() => handleDeleteRow(segmentIndex, rowIndex)}
                      className="delete-row-button"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>


          <button onClick={() => handleAddRow(segmentIndex)} className="add-row-button" style={{ display: 'block' }}>
            Add Row to Segment {segmentIndex + 1}
          </button>

          <hr style={{ margin: '2rem 0' }} />
        </div>
      ))}
    </div>
  );
}

export default Segments;

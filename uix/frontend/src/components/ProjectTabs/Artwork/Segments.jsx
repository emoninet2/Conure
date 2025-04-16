import { useArtworkContext } from '../../../context/ArtworkContext';

function Segments() {
  const { segments, bridges, arms, layers } = useArtworkContext();
  const { segmentData, setSegmentData } = segments;
  const { bridgeData } = bridges;
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
  const armOptions = armData.filter(a => a.name?.trim());
  const layerOptions = layerData.filter(l => l.name?.trim());

  return (
    <div className="artwork-subtab-container">
      <h4 className="section-heading">🧩 Segments (8 Groups)</h4>

      {segmentData.map((segment, segmentIndex) => (
        <div key={segmentIndex} className="segment-block">
          <h5 className="section-heading">Segment {segmentIndex + 1}</h5>

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
                  <td>
                    <select
                      value={row.type}
                      onChange={(e) => handleChange(segmentIndex, rowIndex, 'type', e.target.value)}
                      className="input-field"
                    >
                      <option value="">Select Type</option>
                      {typeOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </td>

                  <td>
                    {row.type === 'bridge' ? (
                      <select
                        value={row.item}
                        onChange={(e) => handleChange(segmentIndex, rowIndex, 'item', e.target.value)}
                        className="input-field"
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
                        onChange={(e) => handleChange(segmentIndex, rowIndex, 'item', e.target.value)}
                        className="input-field"
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
                        className="input-field field-disabled"
                      />
                    )}
                  </td>

                  <td>
                    <select
                      value={row.layer}
                      onChange={(e) => handleChange(segmentIndex, rowIndex, 'layer', e.target.value)}
                      className="input-field"
                    >
                      <option value="">Select Layer</option>
                      {layerOptions.map((l, i) => (
                        <option key={i} value={l.name}>
                          {l.name}
                        </option>
                      ))}
                    </select>
                  </td>

                  <td>
                    {row.type === 'bridge' ? (
                      <input
                        type="text"
                        value={row.jump}
                        onChange={(e) => handleChange(segmentIndex, rowIndex, 'jump', e.target.value)}
                        className="input-field"
                      />
                    ) : (
                      <input
                        type="text"
                        disabled
                        value="Not available"
                        className="input-field field-disabled"
                      />
                    )}
                  </td>

                  <td>
                    <button
                      onClick={() => handleDeleteRow(segmentIndex, rowIndex)}
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
            onClick={() => handleAddRow(segmentIndex)}
            className="btn-table-action add full-width"
            style={{ display: 'block' }}
          >
            ➕ Add Row to Segment {segmentIndex + 1}
          </button>

          <hr style={{ margin: '2rem 0' }} />
        </div>
      ))}
    </div>
  );
}

export default Segments;

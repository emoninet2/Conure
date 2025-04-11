import { useArtworkContext } from '../../../context/ArtworkContext';
import '../../../styles/Artwork/Common.css'; // ✅ Import the CSS file
import Select from 'react-select';

function GuardRing() {
  const { guardRing, viaPadStack, layers } = useArtworkContext();
  const {
    guardRingData, setGuardRingData,
    guardRingDummyData, setGuardRingDummyData,
    useGuardRing, setUseGuardRing,
    guardRingDistance, setGuardRingDistance
  } = guardRing;
  const { viaPadStackData } = viaPadStack;
  const { layerData } = layers;

  // === Guard Ring ===
  const handleRingChange = (index, field, value) => {
    const updated = [...guardRingData];
    updated[index][field] = value;
    setGuardRingData(updated);
  };

  const addGuardRingRow = () => {
    setGuardRingData([
      ...guardRingData,
      {
        name: '', shape: '', offset: '', width: '', layer: '',
        contacts: false, viaPadStack: '', UsePartialCut: false,
        partialCutSegments: '', spacing: ''
      }
    ]);
  };

  const deleteGuardRingRow = (index) => {
    setGuardRingData(guardRingData.filter((_, i) => i !== index));
  };

  // === Dummy Filling ===
  const handleDummyChange = (index, field, value) => {
    const updated = [...guardRingDummyData];
    updated[index][field] = value;
    setGuardRingDummyData(updated);
  };

  const addDummyRow = () => {
    setGuardRingDummyData([
      ...guardRingDummyData,
      { name: '', shape: 'rect', length: '', height: '', offsetX: '', offsetY: '', layers: [] }
    ]);
  };

  const deleteDummyRow = (index) => {
    setGuardRingDummyData(guardRingDummyData.filter((_, i) => i !== index));
  };

  const viaPadStackOptions = viaPadStackData.filter(v => v.name?.trim() !== '');
  const layerOptions = layerData
    .filter(l => l.name?.trim() !== '')
    .map(l => ({ label: l.name, value: l.name }));

  return (
    <div className="guard-ring-container">
      <h4>🛡️ Guard Ring Settings</h4>

      <div className="guard-ring-settings-box">
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
          <label>
            <input
              type="checkbox"
              checked={!!useGuardRing}
              onChange={(e) => setUseGuardRing(e.target.checked)}
              style={{ marginRight: '0.5rem' }}
            />
            Use Guard Ring
          </label>
          <label style={{ display: 'flex', alignItems: 'center' }}>
            Distance:&nbsp;
            <input
              type="text"
              value={guardRingDistance}
              onChange={(e) => setGuardRingDistance(e.target.value)}
              style={{ width: '100px' }}
              disabled={!useGuardRing}
              className={!useGuardRing ? 'field-disabled-style' : ''}
            />
          </label>
        </div>
      </div>

      {/* Guard Ring Table */}
      <h4>🧱 Guard Ring Table</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Shape</th>
            <th>Offset</th>
            <th>Width</th>
            <th>Layer</th>
            <th>Contacts</th>
            <th>Via Pad Stack</th>
            <th>Use Partial Cut</th>
            <th>Partial Cut Segments</th>
            <th>Spacing</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {guardRingData.map((row, index) => {
            const isShapeOctagonRing = row.shape === 'octagonRing';
            return (
              <tr key={index}>
                <td><input type="text" value={row.name} onChange={(e) => handleRingChange(index, 'name', e.target.value)} /></td>
                <td>
                  <select value={row.shape} onChange={(e) => handleRingChange(index, 'shape', e.target.value)}>
                    <option value="">Select Shape</option>
                    <option value="octagon">Octagon</option>
                    <option value="octagonRing">Octagon Ring</option>
                  </select>
                </td>
                <td><input type="text" value={row.offset} onChange={(e) => handleRingChange(index, 'offset', e.target.value)} /></td>
                <td><input type="text" value={row.width} onChange={(e) => handleRingChange(index, 'width', e.target.value)} /></td>
                <td>
                  <select value={row.layer} onChange={(e) => handleRingChange(index, 'layer', e.target.value)}>
                    <option value="">Select Layer</option>
                    {layerOptions.map((layer, i) => (
                      <option key={i} value={layer.value}>{layer.label}</option>
                    ))}
                  </select>
                </td>
                <td style={{ textAlign: 'center' }}>
                  <input type="checkbox" checked={!!row.contacts} onChange={(e) => handleRingChange(index, 'contacts', e.target.checked)} />
                </td>
                <td>
                  <select value={row.viaPadStack} onChange={(e) => handleRingChange(index, 'viaPadStack', e.target.value)} disabled={!row.contacts}>
                    <option value="">Select Stack</option>
                    {viaPadStackOptions.map((v, i) => (
                      <option key={i} value={v.name}>{v.name}</option>
                    ))}
                  </select>
                </td>
                <td style={{ textAlign: 'center' }}>
                  <input type="checkbox" checked={!!row.UsePartialCut} onChange={(e) => handleRingChange(index, 'UsePartialCut', e.target.checked)} disabled={!isShapeOctagonRing} />
                </td>
                <td>
                  <input type="text" value={row.partialCutSegments} onChange={(e) => handleRingChange(index, 'partialCutSegments', e.target.value)} disabled={!isShapeOctagonRing || !row.UsePartialCut} />
                </td>
                <td>
                  <input type="text" value={row.spacing} onChange={(e) => handleRingChange(index, 'spacing', e.target.value)} disabled={!isShapeOctagonRing || !row.UsePartialCut} />
                </td>
                <td>
                  <button onClick={() => deleteGuardRingRow(index)} className="delete-row-button">Delete</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <button onClick={addGuardRingRow} className="add-row-button" style={{ display: 'block' }}>
        Add Guard Ring
      </button>

      <hr style={{ margin: '2rem 0' }} />

      {/* Dummy Fillings Table */}
      <h4>🧱 Dummy Fillings</h4>
      <table className="artwork-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Shape</th>
            <th>Length</th>
            <th>Height</th>
            <th>Offset X</th>
            <th>Offset Y</th>
            <th>Layers</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {guardRingDummyData.map((row, index) => (
            <tr key={index}>
              <td><input type="text" value={row.name} onChange={(e) => handleDummyChange(index, 'name', e.target.value)} /></td>
              <td>
                <select value={row.shape} onChange={(e) => handleDummyChange(index, 'shape', e.target.value)} >
                  <option value="rect">Rect</option>
                </select>
              </td>
              <td><input type="text" value={row.length} onChange={(e) => handleDummyChange(index, 'length', e.target.value)} /></td>
              <td><input type="text" value={row.height} onChange={(e) => handleDummyChange(index, 'height', e.target.value)} /></td>
              <td><input type="text" value={row.offsetX} onChange={(e) => handleDummyChange(index, 'offsetX', e.target.value)} /></td>
              <td><input type="text" value={row.offsetY} onChange={(e) => handleDummyChange(index, 'offsetY', e.target.value)} /></td>
              <td style={{ minWidth: '200px' }}>
                <Select
                  isMulti
                  options={layerOptions}
                  value={
                    Array.isArray(row.layers)
                      ? layerOptions.filter(opt => row.layers.includes(opt.value))
                      : []
                  }
                  onChange={(selectedOptions) =>
                    handleDummyChange(index, 'layers', selectedOptions.map(opt => opt.value))
                  }
                  placeholder="Select Layers..."
                  classNamePrefix="select"
                />
              </td>
              <td>
                <button onClick={() => deleteDummyRow(index)} className="delete-row-button">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <button onClick={addDummyRow} className="add-row-button" style={{ display: 'block' }}>
        Add Dummy Filling
      </button>
    </div>
  );
}

export default GuardRing;

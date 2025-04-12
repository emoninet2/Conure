import { useState } from 'react';
import { generatePreview, getPreviewSvgUrl, downloadGDSII } from '../../../services/api';
import '../../../styles/Artwork/Preview.css'; // ✅ Import the CSS file


function Preview() {
  const [svgUrl, setSvgUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGeneratePreview = async () => {
    setLoading(true);
    setError('');
    try {
      await generatePreview();
      // Append timestamp to bust cache
      const url = getPreviewSvgUrl() + `?t=${Date.now()}`;
      setSvgUrl(url);
    } catch (err) {
      setError(err.message || 'Failed to generate preview');
    } finally {
      setLoading(false);
    }
  };
  

  return (
    <div className="preview-container">
      <p>This is the About of the project.</p>

      <div className="button-row">
        <button className="preview-button" onClick={handleGeneratePreview} disabled={loading}>
          {loading ? 'Generating...' : 'Generate Preview'}
        </button>
        <button className="preview-button" onClick={downloadGDSII}>
          Download GDSII
        </button>
      </div>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {svgUrl && (
        <div>
          <h3>SVG Preview:</h3>
          <img src={svgUrl} alt="Artwork Preview" style={{ maxWidth: '50%' }} />
        </div>
      )}
    </div>
  );
}

export default Preview;

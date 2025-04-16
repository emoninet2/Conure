import { useState } from 'react';
import { generatePreview, getPreviewSvgUrl, downloadGDSII } from '../../../services/api';

function Preview() {
  const [svgUrl, setSvgUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGeneratePreview = async () => {
    setLoading(true);
    setError('');
    try {
      await generatePreview();
      const url = getPreviewSvgUrl() + `?t=${Date.now()}`;
      setSvgUrl(url);
    } catch (err) {
      setError(err.message || 'Failed to generate preview');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="artwork-subtab-container">
      <p>This is the About of the project.</p>

      <div className="button-group">
        <button
          className="btn primary"
          onClick={handleGeneratePreview}
          disabled={loading}
        >
          {loading ? 'Generating...' : 'Generate Preview'}
        </button>
        <button
          className="btn primary"
          onClick={downloadGDSII}
        >
          Download GDSII
        </button>
      </div>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {svgUrl && (
        <div>
          <h4 className="section-heading">SVG Preview</h4>
          <img src={svgUrl} alt="Artwork Preview" style={{ maxWidth: '60%' }} />
        </div>
      )}
    </div>
  );
}

export default Preview;

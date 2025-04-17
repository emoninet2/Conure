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

      {error && <p className="error-text">{error}</p>}

      {svgUrl && (
        <div className="preview-container">
          <h4 className="section-heading">SVG Preview</h4>
          <div className="preview-image-wrapper">
            <img
              src={svgUrl}
              alt="Artwork Preview"
              className="preview-image"
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default Preview;

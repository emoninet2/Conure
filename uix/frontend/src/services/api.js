const host = import.meta.env.VITE_API_HOST || 'http://localhost';
const port = import.meta.env.VITE_BACKEND_BASE_URL || 5001;
const VITE_BACKEND_BASE_URL = `${host}:${port}`;

// 🔧 Helper for JSON requests
const fetchJson = async (url, options = {}) => {
  const res = await fetch(url, options);
  const result = await res.json();
  if (!res.ok) throw new Error(result.error || 'API request failed');
  return result;
};

// 🎯 Helper for POST with JSON
const postJson = (url, data) =>
  fetchJson(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

// ===================
// PROJECT
// ===================

// Create project now only sends name
export const createProject = async (name) =>
  postJson('/api/create_project', { name });

// Open project now sends both location and name
export const openProject = async (name) =>
  postJson('/api/open_project', { name });

// ===================
// ARTWORK
// ===================

export const saveArtwork = async (data) =>
  fetchJson('/api/save_artwork', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

export const loadArtwork = async () => fetchJson('/api/load_artwork');

export const uploadArtwork = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/api/upload_artwork', {
    method: 'POST',
    body: formData,
  });

  const result = await res.json();
  if (!res.ok) throw new Error(result.error || 'Upload failed');
  return result;
};

export const downloadArtwork = async () => {
  const res = await fetch('/api/download_artwork');
  if (!res.ok) {
    const result = await res.json();
    throw new Error(result.error || 'Download failed');
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'artwork.json';
  a.click();
  window.URL.revokeObjectURL(url);
};

// ===================
// PREVIEW
// ===================

// Trigger preview generation (runs the generator script)
export const generatePreview = async () => postJson('/api/preview_artwork', {});

// Returns the SVG preview file (as a URL)
export const getPreviewSvgUrl = () => '/api/preview_svg';

export const downloadGDSII = async () => {
  const res = await fetch('/api/download_gdsii');
  if (!res.ok) {
    const result = await res.json();
    throw new Error(result.error || 'Download failed');
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'artwork.gds';
  a.click();
  window.URL.revokeObjectURL(url);
};

// ===================
// SWEEP
// ===================

// Raw API call to save sweep data.
export const saveSweep = async (data) =>
  postJson('/api/save_sweep', data);

// Raw API call to load a sweep given a name.
export const loadSweep = async (sweepName) =>
  fetchJson(`/api/load_sweep?sweepName=${encodeURIComponent(sweepName)}`);

// List all available sweeps.
export const listSweeps = async () => fetchJson('/api/list_sweeps');

// Delete a sweep by name.
export const deleteSweep = async (sweep_name) =>
  postJson('/api/delete_sweep', { sweep_name });

/* ---------------------------------------------------------
   Processing functions for adapting sweep data
   to/from the file format.
--------------------------------------------------------- */

/**
 * Prepares the sweep data from your context for the API.
 * Converts an array of sweep parameters into an object keyed
 * by the parameter name.
 *
 * @param {string} sweepName - The name of the sweep.
 * @param {array} sweepParams - An array of parameter objects.
 * @returns {object} The formatted data object to send to the API.
 *
 * Expected format of sweepParams:
 * [
 *   { parameterName: 'apothem', from: 90, to: 110, type: 'npoints', value: 3 },
 *   { parameterName: 'width',   from: 6,  to: 12,  type: 'step',    value: 3 }
 * ]
 *
 * Transformed into:
 * {
 *   "parameters": {
 *     "apothem": { from: 90, to: 110, type: "npoints", value: 3 },
 *     "width":   { from: 6,  to: 12,  type: "step",    value: 3 }
 *   }
 * }
 */
export const prepareSweepForSaving = (sweepName, sweepParams) => {
  const parameters = {};
  sweepParams.forEach((row) => {
    if (row.parameterName) {
      parameters[row.parameterName] = {
        from: row.from,
        to: row.to,
        type: row.type,
        value: row.value,
      };
    }
  });
  // Return an object with the key "parameters"
  return { sweepName, parameters };
};
/**
 * Processes the sweep data received from the API and returns an object
 * with keys matching your table context expectations.
 *
 * Expects the API response to have the structure:
 * {
 *   "success": true,
 *   "sweep": {
 *      "sweepName": "...",      // if present
 *      "parameters": {
 *         "apothem": { from: 90, to: 110, type: "npoints", value: 3 },
 *         "width":   { from: 6,  to: 12, type: "step",    value: 3 }
 *      }
 *   }
 * }
 *
 * Returns an object with:
 * {
 *   sweepName: "...",
 *   sweepParams: [
 *     { parameterName: 'apothem', from: 90, to: 110, type: 'npoints', value: 3 },
 *     { parameterName: 'width',   from: 6,  to: 12, type: 'step',    value: 3 }
 *   ]
 * }
 *
 * @param {object} apiResponse - The JSON object from /api/load_sweep.
 * @returns {object} Processed sweep data { sweepName, sweepParams }.
 */
export const processLoadedSweep = (apiResponse) => {
  if (apiResponse && apiResponse.success && apiResponse.sweep) {
    const { sweepName, parameters } = apiResponse.sweep;
    const sweepParams = Object.entries(parameters || {}).map(
      ([parameterName, details]) => ({
        parameterName,
        ...details,
      })
    );
    return { sweepName, sweepParams };
  }
  throw new Error('Invalid sweep data received from API');
};

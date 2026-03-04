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

// **NEW**: Mount the user‑chosen workspace directory under /data
export async function open_workspace(path) {
  const res = await fetch('/api/workspace/open', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) throw new Error(`Mount failed: ${res.statusText}`);
  return res.json();
}

// **NEW**: Unmount the current workspace
export async function close_workspace() {
  const res = await fetch('/api/workspace/close', {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Unmount failed: ${res.statusText}`);
  return res.json();
}


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


export const prepareSweepForSaving = (sweepName, sweepParams) => {
  const parameters = {};
  sweepParams.forEach((row) => {
    if (row.parameterName) {
      parameters[row.parameterName] = {
        from: parseFloat(row.from),
        to: parseFloat(row.to),
        type: row.type,
        value: parseFloat(row.value),
      };
    }
  });
  // Return an object with the key "parameters"
  return { sweepName, parameters };
};


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



// START sweep
export async function startSweep(options) {
  console.log("Sending sweep options", options);  // ✅ optional debug
  const response = await postJson('/api/start_sweep', options);  // ✅ remove "flags"
  return response;
}

// GET sweep status
export const getSweepStatus = async (sweepName) => {
  if (!sweepName) throw new Error("Sweep name is required.");
  return await fetchJson(`/api/sweep_status?sweep_name=${encodeURIComponent(sweepName)}`);
};


// STOP sweep
export async function stopSweep() {

  return response.data;
}

// DELETE sweep
export async function deleteSweep(sweepName) {
  const response = await postJson('/api/delete_sweep', {
    sweep_name: sweepName  // ✅ Do NOT encode here — backend will handle names safely
  });
  return response;
}



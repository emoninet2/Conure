const host = import.meta.env.VITE_API_HOST || 'http://localhost';
const port = import.meta.env.VITE_BACKEND_BASE_URL || 5001;
const VITE_BACKEND_BASE_URL = `${host}:${port}`;

// 🔧 Helper for JSON requests
const fetchJson = async (url, options = {}) => {
  const res = await fetch(url, options)
  const result = await res.json()
  if (!res.ok) throw new Error(result.error || 'API request failed')
  return result
}

// 🎯 Helper for POST with JSON
const postJson = (url, data) =>
  fetchJson(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

// ===================
// PROJECT
// ===================

// Create project now only sends name
export const createProject = async (name) =>
  postJson('/api/create_project', { name })

// Open project now sends both location and name
export const openProject = async (name) =>
  postJson('/api/open_project', {name })

// ===================
// ARTWORK
// ===================

export const saveArtwork = async (data) =>
  fetchJson('/api/save_artwork', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

export const loadArtwork = async () =>
  fetchJson('/api/load_artwork')

export const uploadArtwork = async (file) => {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch('/api/upload_artwork', {
    method: 'POST',
    body: formData,
  })

  const result = await res.json()
  if (!res.ok) throw new Error(result.error || 'Upload failed')
  return result
}

export const downloadArtwork = async () => {
  const res = await fetch('/api/download_artwork')
  if (!res.ok) {
    const result = await res.json()
    throw new Error(result.error || 'Download failed')
  }
  const blob = await res.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'artwork.json'
  a.click()
  window.URL.revokeObjectURL(url)
}

// ===================
// PREVIEW
// ===================

// Trigger preview generation (runs the generator script)
export const generatePreview = async () => {
  return postJson('/api/preview_artwork', {})
}

// Returns the SVG preview file (as a URL)
export const getPreviewSvgUrl = () => {
  return '/api/preview_svg'
}

export const downloadGDSII = async () => {
  const res = await fetch('/api/download_gdsii')
  if (!res.ok) {
    const result = await res.json()
    throw new Error(result.error || 'Download failed')
  }
  const blob = await res.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'artwork.gds'
  a.click()
  window.URL.revokeObjectURL(url)
}

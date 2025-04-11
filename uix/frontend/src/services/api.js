// frontend/src/services/api.js

const BASE_URL = import.meta.env.VITE_API_BASE_URL;


export const createProject = async (name, location) => {
    const res = await fetch('${BASE_URL}/api/download_artwork', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, location }),
    })
  
    return await res.json()
  }
  
  export const openProject = async (location) => {
    const res = await fetch('/api/open_project', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ location }),
    })
  
    return await res.json()
  }
  

  export const saveArtwork = async (data) => {
    const res = await fetch('/api/save_artwork', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
  
    return await res.json();
  };
  
  export const loadArtwork = async () => {
    const res = await fetch('/api/load_artwork', {
      method: 'GET',
    });
  
    return await res.json();
  };
  

  export const uploadArtwork = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/upload_artwork', {
        method: 'POST',
        body: formData
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Upload failed');
    return result;
};


export const downloadArtwork = async () => {
  const response = await fetch(`${BASE_URL}/api/download_artwork`);

  if (!response.ok) {
      const result = await response.json();
      throw new Error(result.error || 'Download failed');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'artwork.json';
  a.click();
  window.URL.revokeObjectURL(url);
};
// frontend/src/services/api.js

export const createProject = async (name, location) => {
    const res = await fetch('/api/create_project', {
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

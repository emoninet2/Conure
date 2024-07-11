function loadJsonData(jsonPath, successCallback, errorCallback) {
    fetch('/load_json', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path: jsonPath }),
    })
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Failed to load JSON file.');
            }
        })
        .then(data => {
            if (data.success) {
                successCallback(data.data); // Pass the loaded data to the success callback
            } else {
                errorCallback('Failed to load JSON data.');
            }
        })
        .catch(error => {
            errorCallback('Error: ' + error.message);
            console.error('Error:', error);
        });
}

function saveJsonData(dataToSave, url, successCallback, errorCallback) {
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(dataToSave),
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                successCallback();
            } else {
                errorCallback('Failed to save data.');
            }
        })
        .catch(error => {
            errorCallback('Error: ' + error.message);
            console.error('Error:', error);
        });
}
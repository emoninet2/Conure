function createProject() {
    var directoryPath = document.getElementById('projectDirectory').value.trim();
    if (directoryPath !== '') {
        fetch('/create_project', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ directoryPath: directoryPath }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('selectedProjectDirectory').innerHTML = '<strong>Project Directory:</strong> ' + directoryPath;
                    alert('Project created successfully!');
                } else {
                    alert('Failed to create project. Please check the server logs.');
                }
            })
            .catch(error => console.error('Error:', error));
    } else {
        alert('Please enter a valid directory path.');
    }
}
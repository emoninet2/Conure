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


function loadArtworkDescriptionFile() {
    var jsonPath = "test/layer.json";

    loadJsonData(jsonPath,
        function (data) {
            populateArtworkDescriptionData(data); // Call function to populate table with loaded data
            alert('JSON data loaded successfully!');
            updateTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
            updateTabsAvailability(); // Update tabs on error
        }
    );
}

function populateArtworkDescriptionData(jsonData) {
    populateLayersTable(jsonData.layer);
    populateViaTable(jsonData.via);
    populateViaPadStackTable(jsonData.viaPadStack);
    populateBridgeTable(jsonData.bridges);
    populatePortsAndSimPortsTable(jsonData.ports);
    populateArmTable(jsonData.arms);
    
}




document.addEventListener('DOMContentLoaded', function () {
    loadArtworkDescriptionFile(); // Update tabs after deleting row
});


async function createProject() {
    try {
        // Fetch the session mode from the server
        const appModeResponse = await fetch('/get_app_mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        const appModeData = await appModeResponse.json();

        // Ensure projectName is defined or fetched from an input field
        const projectName = document.getElementById('projectName').value.trim();
        if (!projectName) {
            alert('Please enter a valid project name.');
            return;
        }

        // Check the session mode (True = public, False = private)
        if (appModeData.session_mode === true) {
            // Public session
            fetch('/create_project_public', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ projectName: projectName }),
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Update project directory element (public session doesn't need directory input)
                        document.getElementById('selectedProjectDirectory').innerHTML = '<strong>Project Directory:</strong> Public Session';
                    } else {
                        alert('Failed to create project. ' + (data.error || 'Please check the server logs.'));
                    }
                })
                .catch(error => console.error('Error:', error));
        } else {
            // Private session
            const directoryPath = document.getElementById('projectDirectory').value.trim();

            if (directoryPath !== '') {
                fetch('/create_project', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ directoryPath: directoryPath, projectName: projectName }),
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById('selectedProjectDirectory').innerHTML = '<strong>Project Directory:</strong> ' + directoryPath;

                            //loadArtworkDescriptionFile(directoryPath, "ARD.json");
                            //saveArtworkDescriptionData(directoryPath, "ARD_out.json");
                        } else {
                            alert('Failed to create project. ' + (data.error || 'Please check the server logs.'));
                        }
                    })
                    .catch(error => console.error('Error:', error));
            } else {
                alert('Please enter a valid directory path.');
            }
        }
    } catch (error) {
        console.error('Error fetching session mode or creating project:', error);
        alert('Failed to retrieve session mode. Please try again.');
    }
}


function createProjectName() {
    projectName = document.getElementById('projectName').value.trim();
    document.getElementById('selectedProjectName').innerHTML = '<strong>Project Name:</strong> ' + projectName;
}


function createProjectAndName() {
    createProjectName();
    createProject();
    
    //alert('Project Configured!');
}



function saveArtworkDescriptionData(filePath, fileName) {
    var artworkDescriptionDataJSON = {
        layer: getLayersJSON().layer,
        via: getViaJSON().via,
        viaPadStack: getViaPadStackJSON().viaPadStack,
        bridges: getBridgeJSON().bridges,
        ports: getPortsJSON().ports,
        arms: getArmsJSON().arms,
        segments: getSegmentsJSON().segments,
        guardRing: getGuardRingJSON().guardRing
    };

    var flaskJsonData = {
        data: artworkDescriptionDataJSON,
        savePath: filePath,
        saveName: fileName
    };

    // Call saveJsonData to save the JSON data
    saveJsonData(
        flaskJsonData,
        '/save_json',
        function () {
            alert('Data saved successfully!');
            updateArtworkTabsAvailability(); // Update tabs after saving data
        },
        function (errorMessage) {
            alert(errorMessage);
            // Optionally handle further error logic here
            updateArtworkTabsAvailability(); // Update tabs after error
        }
    );
}


document.addEventListener('DOMContentLoaded', async function () {

    //loadArtworkDescriptionFile("test", "AGDF.json");

    // try {
    //     await loadArtworkDescriptionFile("test", "layer.json"); // Load and process the data
    //     saveArtworkDescriptionData("test", "ARD.json"); // Save the processed data
    // } catch (error) {
    //     console.error('Error during processing:', error);
    // }


});
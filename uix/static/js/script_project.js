var projectDirectoryPath = '';
var projectName = '';




function createProject() {
    // var directoryPath = document.getElementById('projectDirectory').value.trim();
    // projectDirectoryPath = directoryPath;

    var directoryPath = document.getElementById('projectDirectory').value.trim();
    directoryPath = directoryPath + '/' + projectName;
    projectDirectoryPath = directoryPath;

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
                    
                    //loadArtworkDescriptionFile(projectDirectoryPath, "ARD.json");


                    //loadArtworkDescriptionFile(projectDirectoryPath, "ARD.json"); // Load and process the data
                    //saveArtworkDescriptionData(projectDirectoryPath, "ARD_out.json"); // Save the processed data
                 



                } else {
                    alert('Failed to create project. ' + (data.error || 'Please check the server logs.'));
                }
            })
            .catch(error => console.error('Error:', error));
    } else {
        alert('Please enter a valid directory path.');
    }
}

function createProjectName() {
    projectName = document.getElementById('projectName').value.trim();
    document.getElementById('selectedProjectName').innerHTML = '<strong>Project Name:</strong> ' + projectName;
}


function createProjectAndName() {
    createProjectName();
    createProject();
    
    alert('Project Configured!');
}


// function loadArtworkDescriptionFile(filePath, fileName) {

//     var jsonPath = filePath + '/' + fileName;

//     loadJsonData(jsonPath,
//         function (data) {
//             populateArtworkDescriptionData(data); // Call function to populate table with loaded data
//             alert('JSON data loaded successfully!');
//             updateArtworkTabsAvailability(); // Update tabs after loading data
//             return 0;
//         },
//         function (errorMessage) {
//             alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
//             updateArtworkTabsAvailability(); // Update tabs on error
//             return errorMessage;
//         }
//     );
// }





// function saveArtworkDescriptionData(filePath, fileName) {
//     var artworkDescriptionDataJSON = {
//         layer: getLayersJSON().layer,
//         via: getViaJSON().via,
//         viaPadStack: getViaPadStackJSON().viaPadStack,
//         bridges: getBridgeJSON().bridges,
//         ports: getPortsJSON().ports,
//         arms: getArmsJSON().arms,
//         segments: getSegmentsJSON().segments
//     };

//     var flaskJsonData = {
//         data: artworkDescriptionDataJSON,
//         savePath: filePath,
//         saveName: fileName
//     };

//     // Call saveJsonData to save the JSON data
//     saveJsonData(
//         flaskJsonData,
//         '/save_json',
//         function () {
//             alert('Data saved successfully!');
//             updateArtworkTabsAvailability(); // Update tabs after saving data
//         },
//         function (errorMessage) {
//             alert(errorMessage);
//             // Optionally handle further error logic here
//             updateArtworkTabsAvailability(); // Update tabs after error
//         }
//     );

// }

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




// document.addEventListener('DOMContentLoaded', function () {

//     loadArtworkDescriptionFile("test", "layer.json"); // Update tabs after deleting row
//     saveArtworkDescriptionData("test", "ARD.json"); // Save data after loading

// });



document.addEventListener('DOMContentLoaded', async function () {


    //loadArtworkDescriptionFile("test", "AGDF.json");


    // try {
    //     await loadArtworkDescriptionFile("test", "layer.json"); // Load and process the data
    //     saveArtworkDescriptionData("test", "ARD.json"); // Save the processed data
    // } catch (error) {
    //     console.error('Error during processing:', error);
    // }


});
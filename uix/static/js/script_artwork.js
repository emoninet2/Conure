


var tabButton = {};

tabButton.parameters = document.getElementById('btn-sel-artwork-parameters');
tabButton.segment = document.getElementById('btn-sel-artwork-segment');
tabButton.arms = document.getElementById('btn-sel-artwork-arms');
tabButton.ports = document.getElementById('btn-sel-artwork-ports');
tabButton.bridges = document.getElementById('btn-sel-artwork-bridges');
tabButton.viaPadStack = document.getElementById('btn-sel-artwork-viaPadStack');
tabButton.via = document.getElementById('btn-sel-artwork-via');
tabButton.guardRing = document.getElementById('btn-sel-artwork-guardRing');
tabButton.layers = document.getElementById('btn-sel-artwork-layers');
tabButton.preview = document.getElementById('btn-sel-artwork-preview');

// JavaScript to handle sub-tab visibility
document.addEventListener("DOMContentLoaded", function () {
    // Initially hide all sub-tab contents except for "Layers"
    var subTabs = document.getElementsByClassName('sub-tab-content');
    for (var i = 0; i < subTabs.length; i++) {
        // if (subTabs[i].id !== 'layers') {
        //     subTabs[i].style.display = 'none';
        // }

        subTabs[i].style.display = 'none';

    }
});

function showArtworkTab(subTabName) {
    var subTabs = document.getElementsByClassName('sub-tab-content');
    for (var i = 0; i < subTabs.length; i++) {
        subTabs[i].style.display = 'none';
    }
    document.getElementById(subTabName).style.display = 'block';


    for (var key in tabButton) {
        if (tabButton[key]) {
            tabButton[key].classList.remove('active-tab');
        }
    }



    switch (subTabName) {
        case 'parameters':
            // Code for segment sub-tab
            tabButton.parameters.classList.add('active-tab');
            break;
        case 'segment':
            // Code for segment sub-tab
            tabButton.segment.classList.add('active-tab');
            break;
        case 'arms':
            // Code for arms sub-tab
            tabButton.arms.classList.add('active-tab');
            break;
        case 'ports':
            // Code for ports sub-tab
            tabButton.ports.classList.add('active-tab');
            break;
        case 'bridges':
            // Code for bridges sub-tab
            tabButton.bridges.classList.add('active-tab');
            break;
        case 'viaPadStack':
            // Code for viaPadStack sub-tab
            tabButton.viaPadStack.classList.add('active-tab');
            break;
        case 'via':
            // Code for via sub-tab
            tabButton.via.classList.add('active-tab');
            break;
        case 'guardRing':
            // Code for guardRing sub-tab
            tabButton.guardRing.classList.add('active-tab');
            break;
        case 'layers':
            // Code for layers sub-tab
            tabButton.layers.classList.add('active-tab');
            break;
        case 'preview':
            // Code for layers sub-tab
            tabButton.preview.classList.add('active-tab');
            break;
        default:
            // Code for default case
            break;
    }
}


function updateArtworkTabsAvailability() {

   
    var layersTable = document.getElementById('layersTable').getElementsByTagName('tbody')[0];
    var viaTable = document.getElementById('viaTable').getElementsByTagName('tbody')[0];
    var viaPadStackTable = document.getElementById('viaPadStackTable').getElementsByTagName('tbody')[0];
    var bridgeTable = document.getElementById('bridgesTable').getElementsByTagName('tbody')[0];
    var portTable = document.getElementById('portsTable').getElementsByTagName('tbody')[0];
    var armTable = document.getElementById('armsTable').getElementsByTagName('tbody')[0];
    var segmentTable = document.getElementById('segmentTable').getElementsByTagName('tbody')[0];


    var isLayerTableEmpty = layersTable.rows.length === 0;
    var isViaTableEmpty = viaTable.rows.length === 0;
    var isViaPadStackTableEmpty = viaPadStackTable.rows.length === 0;
    var isBridgeTableEmpty = bridgeTable.rows.length === 0;
    var isPortTableEmpty = portTable.rows.length === 0;
    var isArmTableEmpty = armTable.rows.length === 0;
    //var isSegmentTableEmpty = segmentTable.rows.length === 0;

    var tabsToDisable = ['parameters','segment', 'arms', 'ports', 'bridges', 'viaPadStack', 'via', 'guardRing'];

    tabsToDisable.forEach(function (tabName) {
        var tabButton = document.querySelector(`button[onclick="showArtworkTab('${tabName}')"]`);
        if (tabButton) {
            if (tabName === 'via') {
                tabButton.disabled = isLayerTableEmpty;
            }
            if (tabName === 'viaPadStack') {
                tabButton.disabled = isLayerTableEmpty || isViaTableEmpty;
            }
            if (tabName === 'bridges') {
                tabButton.disabled = isLayerTableEmpty || isViaTableEmpty || isViaPadStackTableEmpty;
            }
            if (tabName === 'arms') {
                tabButton.disabled = isLayerTableEmpty || isViaPadStackTableEmpty || isPortTableEmpty;
            }
            if (tabName === 'segment') {
                tabButton.disabled = isLayerTableEmpty || (isBridgeTableEmpty && isArmTableEmpty);
            }
            if (tabName === 'guardRing') {
                tabButton.disabled = isLayerTableEmpty ;
            }
            if (tabName === 'parameters') {
                tabButton.disabled = isLayerTableEmpty;
            }
        }
    });




    // var isLayersEmpty = layersTable.rows.length === 0;
    // var isViaEmpty = viaTable.rows.length === 0;

    // var tabsToDisable = ['segment', 'arms', 'ports', 'bridges', 'viaPadStack', 'via', 'guardRing'];

    // tabsToDisable.forEach(function (tabName) {
    //     var tabButton = document.querySelector(`button[onclick="showArtworkTab('${tabName}')"]`);
    //     if (tabButton) {
    //         if (isLayersEmpty) {
    //             tabButton.disabled = true;
    //         } else {
    //             tabButton.disabled = false;
    //         }
    //     }
    // });

}


function populateArtworkDescriptionData(jsonData) {
    if (jsonData.parameters){
        populateParamTable(jsonData.parameters);
    }
    if (jsonData.layer) {
        populateLayersTable(jsonData.layer);
    }
    if (jsonData.via) {
        populateViaTable(jsonData.via);
    }
    if (jsonData.viaPadStack) {
        populateViaPadStackTable(jsonData.viaPadStack);
    }
    if (jsonData.bridges) {
        populateBridgeTable(jsonData.bridges);
    }
    if (jsonData.ports) {
        populatePortsAndSimPortsTable(jsonData.ports);
    }
    if (jsonData.arms) {
        populateArmTable(jsonData.arms);
    }
    if (jsonData.segments && jsonData.segments.data) {
        populateSegmentTable(jsonData.segments);
    }
    if (jsonData.guardRing && jsonData.guardRing.data) {
        populateGuardRingTable(jsonData.guardRing);
        populateDummyFillTable(jsonData.guardRing);
    }


}


function loadArtworkDescriptionFile(filePath, fileName) {
    return new Promise((resolve, reject) => {
        var jsonPath = filePath + '/' + fileName;

        loadJsonData(jsonPath,
            function (data) {
                populateArtworkDescriptionData(data); // Call function to populate table with loaded data
                //alert('JSON data loaded successfully!');
                updateArtworkTabsAvailability(); // Update tabs after loading data
                resolve(); // Resolve the promise when data is loaded and processed
            },
            function (errorMessage) {
                alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
                updateArtworkTabsAvailability(); // Update tabs on error
                reject(errorMessage); // Reject the promise on error
            }
        );
    });
    
}


function loadADF() {
    var bridgeJsonPath = document.getElementById('adfJsonPath').value.trim();

    loadJsonData(bridgeJsonPath,
        function (data) {
            populateArtworkDescriptionData(data)
            //alert('JSON data loaded successfully!');
            updateArtworkTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
            updateArtworkTabsAvailability(); // Update tabs on error
        }
    );
}



function uploadAndLoadFromADF() {
    // Fetch session path first
    fetch('/get_session_path')
        .then(response => response.json())
        .then(data => {
            if (data.session_path) {
                const fileInput = document.getElementById('fileInput');
                const file = fileInput.files[0];
                const uploadFolder = data.session_path + '/temp/uploads';  // Use the fetched session path
                const formData = new FormData();
                formData.append('file', file);
                formData.append('uploadFolder', uploadFolder);

                const fullPath = uploadFolder + '/' + file.name;

                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/upload', true);
                xhr.onload = function () {
                    if (xhr.status === 200) {
                        loadJsonData(fullPath,
                            function (data) {
                                populateArtworkDescriptionData(data);
                                deleteFile(fullPath);  // Delete the file after loading data
                                updateArtworkTabsAvailability();
                            },
                            function (errorMessage) {
                                alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
                                deleteFile(fullPath);  // Delete the file on error
                                updateArtworkTabsAvailability();
                            }
                        );
                    } else {
                        alert('File upload failed');
                        updateArtworkTabsAvailability();
                    }
                };

                xhr.send(formData);

                // Reset the file input value
                document.getElementById('fileInput').value = '';
            } else {
                alert('Failed to fetch session path');
            }
        })
        .catch(error => {
            console.error('Error fetching session path:', error);
        });
}


function getArtworkDescriptionDataJSON(){
    var artworkDescriptionDataJSON = {
        parameters: getParamJSON().parameters,
        layer: getLayersJSON().layer,
        via: getViaJSON().via,
        viaPadStack: getViaPadStackJSON().viaPadStack,
        bridges: getBridgeJSON().bridges,
        ports: getPortsJSON().ports,
        arms: getArmsJSON().arms,
        segments: getSegmentsJSON().segments,
        guardRing: getGuardRingJSON().guardRing
    };


    return artworkDescriptionDataJSON;
}

function saveArtworkDescriptionData(filePath, fileName) {
    // var artworkDescriptionDataJSON = {
    //     parameters: getParamJSON().parameters,
    //     layer: getLayersJSON().layer,
    //     via: getViaJSON().via,
    //     viaPadStack: getViaPadStackJSON().viaPadStack,
    //     bridges: getBridgeJSON().bridges,
    //     ports: getPortsJSON().ports,
    //     arms: getArmsJSON().arms,
    //     segments: getSegmentsJSON().segments,
    //     guardRing: getGuardRingJSON().guardRing
    // };

    var artworkDescriptionDataJSON = getArtworkDescriptionDataJSON()

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
            //alert('Data saved successfully!');
            updateArtworkTabsAvailability(); // Update tabs after saving data
        },
        function (errorMessage) {
            alert(errorMessage);
            // Optionally handle further error logic here
            updateArtworkTabsAvailability(); // Update tabs after error
        }
    );
}

async function saveADF() {
    try {
        // Fetch the session path first
        const sessionResponse = await fetch('/get_session_path');
        const sessionData = await sessionResponse.json();

        if (!sessionData.session_path) {
            throw new Error('Session path not found');
        }

        const sessionPath = sessionData.session_path;  

        // Attempt to save the artwork description data
        saveArtworkDescriptionData(sessionPath, projectName + ".json");

        // If no errors occur, display success message
        alert('ARD data saved successfully!');
    } catch (error) {
        // Handle the error here
        console.error('An error occurred while saving JSON data:', error);
        alert('Error saving ARD data.');
    }
}




var tabButton = {};

tabButton.segment = document.getElementById('btn-sel-artwork-segment');
tabButton.arms = document.getElementById('btn-sel-artwork-arms');
tabButton.ports = document.getElementById('btn-sel-artwork-ports');
tabButton.bridges = document.getElementById('btn-sel-artwork-bridges');
tabButton.viaPadStack = document.getElementById('btn-sel-artwork-viaPadStack');
tabButton.via = document.getElementById('btn-sel-artwork-via');
tabButton.guardRing = document.getElementById('btn-sel-artwork-guardRing');
tabButton.layers = document.getElementById('btn-sel-artwork-layers');


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

function showSubTab(subTabName) {
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
        default:
            // Code for default case
            break;
    }
}


function updateTabsAvailability() {


    var layersTable = document.getElementById('layersTable').getElementsByTagName('tbody')[0];
    var viaTable = document.getElementById('viaTable').getElementsByTagName('tbody')[0];
    var isLayersEmpty = layersTable.rows.length === 0;
    var isViaEmpty = viaTable.rows.length === 0;

    var tabsToDisable = ['segment', 'arms', 'ports', 'bridges', 'viaPadStack', 'via', 'guardRing'];

    tabsToDisable.forEach(function (tabName) {
        var tabButton = document.querySelector(`button[onclick="showSubTab('${tabName}')"]`);
        if (tabButton) {
            if (isLayersEmpty) {
                tabButton.disabled = true;
            } else {
                tabButton.disabled = false;
            }
        }
    });

}


function populateArtworkDescriptionData(jsonData) {
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
}


function loadArtworkDescriptionFile(filePath, fileName) {
    return new Promise((resolve, reject) => {
        var jsonPath = filePath + '/' + fileName;

        loadJsonData(jsonPath,
            function (data) {
                populateArtworkDescriptionData(data); // Call function to populate table with loaded data
                alert('JSON data loaded successfully!');
                updateTabsAvailability(); // Update tabs after loading data
                resolve(); // Resolve the promise when data is loaded and processed
            },
            function (errorMessage) {
                alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
                updateTabsAvailability(); // Update tabs on error
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
            alert('JSON data loaded successfully!');
            updateTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
            updateTabsAvailability(); // Update tabs on error
        }
    );
}



function uploadAndLoadFromADF() {
    // Upload the file
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    const uploadFolder = projectDirectoryPath + '/temp/uploads';
    const formData = new FormData();
    formData.append('file', file);
    formData.append('uploadFolder', uploadFolder);

    const fullPath = uploadFolder + '/' + file.name;
    alert('Uploading file to: ' + fullPath);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);
    xhr.onload = function () {
        if (xhr.status === 200) {
            alert('File uploaded successfully');
            // Load the file after successful upload
            loadJsonData(fullPath,
                function (data) {
                    populateArtworkDescriptionData(data);
                    alert('JSON data loaded successfully!');
                    deleteFile(fullPath); // Delete the file after loading data
                    updateTabsAvailability(); // Update tabs after loading data
                },
                function (errorMessage) {
                    alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
                    deleteFile(fullPath); // Delete the file on error
                    updateTabsAvailability(); // Update tabs on error
                }
            );
        } else {
            alert('File upload failed');
            updateTabsAvailability(); // Update tabs on error
        }
    };

    xhr.send(formData);
}


function saveADF() {
    
    //saveArtworkDescriptionData(projectDirectoryPath, "mysavedARD.json"); // Save data after loading
    saveArtworkDescriptionData(projectDirectoryPath, projectName + ".json"); // Save data after loading
}
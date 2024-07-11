// script_layers.js

function showSubTab(subTabName) {
    var subTabs = document.getElementsByClassName('sub-tab-content');
    for (var i = 0; i < subTabs.length; i++) {
        subTabs[i].style.display = 'none';
    }
    document.getElementById(subTabName).style.display = 'block';
}

function addLayerRow() {
    var table = document.getElementById('layersTable').getElementsByTagName('tbody')[0];
    var rowCount = table.rows.length + 1;
    var newRow = table.insertRow();
    var cell1 = newRow.insertCell(0);
    var cell2 = newRow.insertCell(1);
    var cell3 = newRow.insertCell(2);
    var cell4 = newRow.insertCell(3);
    cell1.innerHTML = '<input type="text" name="name' + rowCount + '">';
    cell2.innerHTML = '<input type="text" name="gdsLayer' + rowCount + '">';
    cell3.innerHTML = '<input type="text" name="gdsDatatype' + rowCount + '">';
    cell4.innerHTML = '<button onclick="deleteLayerRow(this)">Delete</button>';
    updateTabsAvailability(); // Update tabs after deleting row
    updateSegmentDropdowns(); // Update segment dropdowns after deleting row
}

function deleteLayerRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);

    updateTabsAvailability(); // Update tabs after deleting row
    updateSegmentDropdowns(); // Update segment dropdowns after deleting row
}



function saveLayers() {
    var layers = {};

    // Iterate through table rows to collect data
    var tableRows = document.querySelectorAll('#layersTable tbody tr');
    tableRows.forEach(function (row, index) {
        var nameInput = row.querySelector('input[name^="name"]');
        var gdsLayerInput = row.querySelector('input[name^="gdsLayer"]');
        var gdsDatatypeInput = row.querySelector('input[name^="gdsDatatype"]');

        var name = nameInput.value.trim();
        var gdsLayer = parseInt(gdsLayerInput.value.trim());
        var gdsDatatype = parseInt(gdsDatatypeInput.value.trim());

        if (name && !isNaN(gdsLayer) && !isNaN(gdsDatatype)) {
            layers[name] = {
                gds: {
                    layer: gdsLayer,
                    datatype: gdsDatatype
                }
            };
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        data: { layer: layers }, // Making it more generic by wrapping layers in a "data" object
        savePath: document.getElementById('savePath').value.trim(),
        saveName: document.getElementById('saveName').value.trim()
    };

    // Call saveJsonData to save the JSON data
    saveJsonData(
        jsonData,
        '/save_json',
        function () {
            alert('Data saved successfully!');
            updateTabsAvailability(); // Update tabs after saving data
        },
        function (errorMessage) {
            alert(errorMessage);
            // Optionally handle further error logic here
            updateTabsAvailability(); // Update tabs after error
        }
    );
}





function loadLayers() {
    var layerJsonPath = document.getElementById('layerJsonPath').value.trim();

    loadJsonData(layerJsonPath,
        function (data) {
            populateLayersTable(data.layer);
            alert('JSON data loaded successfully!');
            updateTabsAvailability(); // Update tabs after loading data
            updateSegmentDropdowns(); // Update segment dropdowns after loading data
        },
        function (errorMessage) {
            alert(errorMessage);
            updateTabsAvailability(); // Update tabs on error
            updateSegmentDropdowns(); // Update segment dropdowns on error
        }
    );
}


function populateLayersTable(layersData) {
    var table = document.getElementById('layersTable').getElementsByTagName('tbody')[0];
    table.innerHTML = ''; // Clear existing rows

    Object.keys(layersData).forEach(function (name) {
        var layer = layersData[name].gds ? layersData[name].gds.layer : '';
        var datatype = layersData[name].gds ? layersData[name].gds.datatype : '';

        var newRow = table.insertRow();
        var cell1 = newRow.insertCell(0);
        var cell2 = newRow.insertCell(1);
        var cell3 = newRow.insertCell(2);
        var cell4 = newRow.insertCell(3);
        cell1.innerHTML = '<input type="text" name="name" value="' + name + '">';
        cell2.innerHTML = '<input type="text" name="gdsLayer" value="' + layer + '">';
        cell3.innerHTML = '<input type="text" name="gdsDatatype" value="' + datatype + '">';
        cell4.innerHTML = '<button onclick="deleteLayerRow(this)">Delete</button>';
    });

    // Add one empty row at the end for adding new entries
    //addLayerRow();

    updateTabsAvailability(); // Update tabs after populating layers
    updateSegmentDropdowns(); // Update segment dropdowns after populating layers
}

function getLayerNames() {
    var layerNames = [];
    var layersTable = document.getElementById('layersTable').getElementsByTagName('tbody')[0];
    var rows = layersTable.getElementsByTagName('tr');
    for (var i = 0; i < rows.length; i++) {
        var nameInput = rows[i].querySelector('input[name^="name"]');
        if (nameInput) {
            layerNames.push(nameInput.value.trim());
        }
    }
    return layerNames;
}




// Function to get layer options HTML
function getLayerOptions(includeDefaultOption = true) {
    var layerNames = getLayerNames();
    var layerOptions = layerNames.map(name => `<option value="${name}">${name}</option>`).join('');
    if (includeDefaultOption) {
        return `<option value="">-- Select Layer --</option>${layerOptions}`;
    } else {
        return layerOptions;
    }
}



// Function to handle input changes in layersTable
function handleLayerInputChange(event) {
    var target = event.target;
    if (target.tagName === 'INPUT' && target.name.startsWith('name')) {
        // If input field name starts with 'name', update segment dropdowns
        updateSegmentDropdowns();
        updateViaDropdowns(); // Call function to update via dropdowns
    } else if (target.tagName === 'INPUT' && target.name.startsWith('gdsLayer')) {
        // If input field name starts with 'gdsLayer', update segment dropdowns
        updateSegmentDropdowns();
        updateViaDropdowns(); // Call function to update via dropdowns
    } else if (target.tagName === 'INPUT' && target.name.startsWith('gdsDatatype')) {
        // If input field name starts with 'gdsDatatype', update segment dropdowns
        updateSegmentDropdowns();
        updateViaDropdowns(); // Call function to update via dropdowns
    }
}

// Add event listener to layersTable to capture input changes
document.getElementById('layersTable').addEventListener('input', handleLayerInputChange);

// Optional: Throttle function to limit how often handleLayerInputChange is called
function throttle(func, limit) {
    let inThrottle;
    return function () {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}


// Add event listener to layersTable to capture input changes
document.getElementById('layersTable').addEventListener('input', handleLayerInputChange);


document.addEventListener('DOMContentLoaded', function () {
    updateTabsAvailability(); // Update tabs after deleting row
    updateSegmentDropdowns(); // Update segment dropdowns after deleting row
});



// Update via dropdowns every 1 second
// setInterval(function () {
//     updateSegmentDropdowns
//     updateViaDropdowns();
// }, 1000); // 1000 milliseconds = 1 second
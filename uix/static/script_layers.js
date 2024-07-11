// script_layers.js

function showSubTab(subTabName) {
    var subTabs = document.getElementsByClassName('sub-tab-content');
    for (var i = 0; i < subTabs.length; i++) {
        subTabs[i].style.display = 'none';
    }
    document.getElementById(subTabName).style.display = 'block';
}

function addRow() {
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
    cell4.innerHTML = '<button onclick="deleteRow(this)">Delete</button>';
    updateTabsAvailability(); // Update tabs after deleting row
    updateSegmentDropdowns(); // Update segment dropdowns after deleting row
}

function deleteRow(btn) {
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
        layers: layers,
        savePath: document.getElementById('savePath').value.trim(),
        saveName: document.getElementById('saveName').value.trim()
    };

    // Send data to Flask to save to custom file path and name
    fetch('/save_layers_custom', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(jsonData),
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Layers data saved successfully!');
            } else {
                alert('Failed to save layers data.');
            }
        })
        .catch(error => console.error('Error:', error));
    updateTabsAvailability(); // Update tabs after saving layers
}


function loadLayers() {
    var jsonPath = document.getElementById('jsonPath').value.trim();

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
                populateLayersTable(data.layers);
                alert('JSON data loaded successfully!');
            } else {
                alert('Failed to load JSON data.');
            }
        })
        .catch(error => {
            alert('Error: ' + error.message);
            console.error('Error:', error);
        });
    updateTabsAvailability(); // Update tabs after deleting row
    updateSegmentDropdowns(); // Update segment dropdowns after deleting row
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
        cell4.innerHTML = '<button onclick="deleteRow(this)">Delete</button>';
    });

    // Add one empty row at the end for adding new entries
    //addRow();

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

function updateTabsAvailability() {
    var layersTable = document.getElementById('layersTable').getElementsByTagName('tbody')[0];
    var isEmpty = layersTable.rows.length === 0;

    var tabsToDisable = ['segment', 'arms', 'ports', 'bridges', 'viaPadStack', 'via', 'guardRing'];

    tabsToDisable.forEach(function (tabName) {
        var tabButton = document.querySelector(`button[onclick="showSubTab('${tabName}')"]`);
        if (tabButton) {
            if (isEmpty) {
                tabButton.disabled = true;
            } else {
                tabButton.disabled = false;
            }
        }
    });
}

// Function to handle input changes in layersTable
function handleLayerInputChange(event) {
    var target = event.target;
    if (target.tagName === 'INPUT' && target.name.startsWith('name')) {
        // If input field name starts with 'name', update segment dropdowns
        updateSegmentDropdowns();
    } else if (target.tagName === 'INPUT' && target.name.startsWith('gdsLayer')) {
        // If input field name starts with 'gdsLayer', update segment dropdowns
        updateSegmentDropdowns();
    } else if (target.tagName === 'INPUT' && target.name.startsWith('gdsDatatype')) {
        // If input field name starts with 'gdsDatatype', update segment dropdowns
        updateSegmentDropdowns();
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

document.addEventListener('DOMContentLoaded', function () {
    updateTabsAvailability(); // Update tabs after deleting row
    updateSegmentDropdowns(); // Update segment dropdowns after deleting row
});
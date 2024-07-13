// script_bridges.js

function addBridgeRow() {
    var table = document.getElementById('bridgesTable').getElementsByTagName('tbody')[0];
    var rowCount = table.rows.length + 1;
    var newRow = table.insertRow();
    var cell1 = newRow.insertCell(0);
    var cell2 = newRow.insertCell(1);
    var cell3 = newRow.insertCell(2);
    var cell4 = newRow.insertCell(3);
    var cell5 = newRow.insertCell(4);
    var cell6 = newRow.insertCell(5);
    var cell7 = newRow.insertCell(6);

    cell1.innerHTML = '<input type="text" name="bridgeName' + rowCount + '">';

    cell2.innerHTML = '<select name="bridgeLayer' + rowCount + '">' + getLayerOptions() + '</select>';
    cell3.innerHTML = '<select name="bridgeVia' + rowCount + '">' + getViaOptions() + '</select>';
    cell4.innerHTML = '<input type="number" name="viaWidth' + rowCount + '">';
    cell5.innerHTML = '<input type="number" name="viaStackCCW' + rowCount + '">';
    cell6.innerHTML = '<input type="number" name="viaStackCW' + rowCount + '">';

    cell7.innerHTML = '<button onclick="deleteBridgeRow(this)">Delete</button>';

    updateTabsAvailability(); // Update tabs after adding row
    updateBridgeDropdowns();
}

function deleteBridgeRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
    updateTabsAvailability(); // Update tabs after deleting row
    updateBridgeDropdowns();
}

function saveBridges() {
    var bridges = {};

    // Iterate through table rows to collect data
    var tableRows = document.querySelectorAll('#bridgesTable tbody tr');
    tableRows.forEach(function (row, index) {
        var nameInput = row.querySelector('input[name^="bridgeName"]');
        var layerSelect = row.querySelector('select[name^="bridgeLayer"]');
        var viaSelect = row.querySelector('select[name^="bridgeVia"]');
        var widthInput = row.querySelector('input[name^="viaWidth"]');
        var stackCCWInput = row.querySelector('input[name^="viaStackCCW"]');
        var stackCWInput = row.querySelector('input[name^="viaStackCW"]');

        var name = nameInput.value.trim();
        var layer = layerSelect.value.trim();
        var via = viaSelect.value.trim();
        var width = parseInt(widthInput.value.trim());
        var stackCCW = parseInt(stackCCWInput.value.trim());
        var stackCW = parseInt(stackCWInput.value.trim());

        if (name && layer && via && !isNaN(width) && !isNaN(stackCCW) && !isNaN(stackCW)) {
            bridges[name] = {
                layer: layer,
                via: via,
                viaWidth: width,
                viaStackCCW: stackCCW,
                viaStackCW: stackCW
            };
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        data: { bridges: bridges },
        savePath: document.getElementById('bridgeSavePath').value.trim(),
        saveName: document.getElementById('bridgeSaveName').value.trim()
    };

    // Send data to Flask to save to custom file path and name
    fetch('/save_json', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(jsonData),
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Data saved successfully!');
            } else {
                alert('Failed to save data.');
            }
        })
        .catch(error => console.error('Error:', error));

    updateTabsAvailability(); // Update tabs after saving data
}

function loadBridges() {
    var bridgeJsonPath = document.getElementById('bridgeJsonPath').value.trim();

    loadJsonData(bridgeJsonPath,
        function (data) {
            populateBridgeTable(data.bridges);
            alert('JSON data loaded successfully!');
            updateTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
            updateTabsAvailability(); // Update tabs on error
        }
    );
    updateBridgeDropdowns();
}

function populateBridgeTable(bridgesData) {
    var table = document.getElementById('bridgesTable').getElementsByTagName('tbody')[0];
    table.innerHTML = ''; // Clear existing rows

    Object.keys(bridgesData).forEach(function (key, index) {
        var bridge = bridgesData[key];
        var newRow = table.insertRow();
        var cell1 = newRow.insertCell(0);
        var cell2 = newRow.insertCell(1);
        var cell3 = newRow.insertCell(2);
        var cell4 = newRow.insertCell(3);
        var cell5 = newRow.insertCell(4);
        var cell6 = newRow.insertCell(5);
        var cell7 = newRow.insertCell(6);

        cell1.innerHTML = '<input type="text" name="bridgeName' + index + '" value="' + key + '">';
        cell2.innerHTML = '<select name="bridgeLayer' + index + '">' + getLayerOptions() + '</select>';
        cell2.querySelector('select').value = bridge.layer; // Set selected value
        cell3.innerHTML = '<select name="bridgeVia' + index + '">' + getViaOptions() + '</select>';
        cell3.querySelector('select').value = bridge.via; // Set selected value
        cell4.innerHTML = '<input type="number" name="viaWidth' + index + '" value="' + bridge.viaWidth + '">';
        cell5.innerHTML = '<input type="number" name="viaStackCCW' + index + '" value="' + bridge.viaStackCCW + '">';
        cell6.innerHTML = '<input type="number" name="viaStackCW' + index + '" value="' + bridge.viaStackCW + '">';

        cell7.innerHTML = '<button onclick="deleteBridgeRow(this)">Delete</button>';
    });

    updateTabsAvailability(); // Update tabs after populating bridges
    updateBridgeDropdowns();
}

// Function to update via and layer dropdowns after changes
function updateBridgeDropdowns() {
    var bridgeTable = document.getElementById('bridgesTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    // Update layer select elements
    for (var i = 0; i < bridgeTable.length; i++) {
        var selectElement = bridgeTable[i].querySelector('select[name^="bridgeLayer"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getLayerOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

    // Update via select elements
    for (var i = 0; i < bridgeTable.length; i++) {
        var selectElement = bridgeTable[i].querySelector('select[name^="bridgeVia"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getViaOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }
}
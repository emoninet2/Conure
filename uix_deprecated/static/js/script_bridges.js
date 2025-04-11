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
    cell5.innerHTML = '<select name="viaStackCCW' + rowCount + '">' + getViaPadStackOptions() + '</select>';
    cell6.innerHTML = '<select name="viaStackCW' + rowCount + '">' + getViaPadStackOptions() + '</select>';

    cell7.innerHTML = '<button onclick="deleteBridgeRow(this)">Delete</button>';

    //updateArtworkTabsAvailability(); // Update tabs after adding row

}

function deleteBridgeRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
    //updateArtworkTabsAvailability(); // Update tabs after deleting row

}



function getBridgeJSON() {
    var bridges = {};

    // Iterate through table rows to collect data
    var tableRows = document.querySelectorAll('#bridgesTable tbody tr');
    tableRows.forEach(function (row, index) {
        var nameInput = row.querySelector('input[name^="bridgeName"]');
        var layerSelect = row.querySelector('select[name^="bridgeLayer"]');
        var viaSelect = row.querySelector('select[name^="bridgeVia"]');
        var widthInput = row.querySelector('input[name^="viaWidth"]');
        var stackCCWSelect = row.querySelector('select[name^="viaStackCCW"]');
        var stackCWSelect = row.querySelector('select[name^="viaStackCW"]');

        var name = nameInput.value.trim();
        var layer = layerSelect.value.trim();
        var via = viaSelect ? viaSelect.value.trim() : undefined;
        var width = widthInput ? parseFloat(widthInput.value.trim()) : undefined;
        var stackCCW = stackCCWSelect ? stackCCWSelect.value.trim() : undefined;
        var stackCW = stackCWSelect ? stackCWSelect.value.trim() : undefined;

        if (name && layer) {
            bridges[name] = { layer: layer };

            if (via) {
                bridges[name].Via = via;  // Updated key to camel case
            }
            if (!isNaN(width)) {
                bridges[name].ViaWidth = width;  // Updated key to camel case
            }
            if (stackCCW) {
                bridges[name].ViaStackCCW = stackCCW;  // Updated key to camel case
            }
            if (stackCW) {
                bridges[name].ViaStackCW = stackCW;  // Updated key to camel case
            }
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        bridges: bridges
    };

    return jsonData;
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
        var stackCCWSelect = row.querySelector('select[name^="viaStackCCW"]');
        var stackCWSelect = row.querySelector('select[name^="viaStackCW"]');

        var name = nameInput.value.trim();
        var layer = layerSelect.value.trim();
        var via = viaSelect ? viaSelect.value.trim() : undefined;
        var width = widthInput ? parseFloat(widthInput.value.trim()) : undefined;
        var stackCCW = stackCCWSelect ? stackCCWSelect.value.trim() : undefined;
        var stackCW = stackCWSelect ? stackCWSelect.value.trim() : undefined;

        if (name && layer) {
            bridges[name] = { layer: layer };

            if (via) {
                bridges[name].Via = via;  // Updated key to camel case
            }
            if (!isNaN(width)) {
                bridges[name].ViaWidth = width;  // Updated key to camel case
            }
            if (stackCCW) {
                bridges[name].ViaStackCCW = stackCCW;  // Updated key to camel case
            }
            if (stackCW) {
                bridges[name].ViaStackCW = stackCW;  // Updated key to camel case
            }
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        data: { bridges: bridges },
        savePath: projectDirectoryPath + '/' +   document.getElementById('bridgeSavePath').value.trim(),
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

    //updateArtworkTabsAvailability(); // Update tabs after saving data
}

function loadBridges() {
    var bridgeJsonPath = document.getElementById('bridgeJsonPath').value.trim();

    loadJsonData(bridgeJsonPath,
        function (data) {
            populateBridgeTable(data.bridges);
            alert('JSON data loaded successfully!');
            //updateArtworkTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
            //updateArtworkTabsAvailability(); // Update tabs on error
        }
    );
 
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

        if (bridge.Via) {  // Use camel case property name
            cell3.innerHTML = '<select name="bridgeVia' + index + '">' + getViaOptions() + '</select>';
            cell3.querySelector('select').value = bridge.Via; // Set selected value
        } else {
            cell3.innerHTML = '<select name="bridgeVia' + index + '">' + getViaOptions() + '</select>';
        }

        if (bridge.ViaWidth !== undefined) {  // Use camel case property name
            cell4.innerHTML = '<input type="number" name="viaWidth' + index + '" value="' + bridge.ViaWidth + '">';
        } else {
            cell4.innerHTML = '<input type="number" name="viaWidth' + index + '">';
        }

        if (bridge.ViaStackCCW) {  // Use camel case property name
            cell5.innerHTML = '<select name="viaStackCCW' + index + '">' + getViaPadStackOptions() + '</select>';
            cell5.querySelector('select').value = bridge.ViaStackCCW; // Set selected value
        } else {
            cell5.innerHTML = '<select name="viaStackCCW' + index + '">' + getViaPadStackOptions() + '</select>';
        }

        if (bridge.ViaStackCW) {  // Use camel case property name
            cell6.innerHTML = '<select name="viaStackCW' + index + '">' + getViaPadStackOptions() + '</select>';
            cell6.querySelector('select').value = bridge.ViaStackCW; // Set selected value
        } else {
            cell6.innerHTML = '<select name="viaStackCW' + index + '">' + getViaPadStackOptions() + '</select>';
        }

        cell7.innerHTML = '<button onclick="deleteBridgeRow(this)">Delete</button>';
    });

    //updateArtworkTabsAvailability(); // Update tabs after populating bridges
}



function getBridgeNames() {
    var bridgeNames = [];
    var bridgeTable = document.getElementById('bridgesTable').getElementsByTagName('tbody')[0];
    var rows = bridgeTable.getElementsByTagName('tr');
    for (var i = 0; i < rows.length; i++) {
        var nameInput = rows[i].querySelector('input[name^="bridgeName"]');
        if (nameInput) {
            bridgeNames.push(nameInput.value.trim());
        }
    }
    return bridgeNames;
}

function getBridgeOptions(includeDefaultOption = true) {
    var bridgeNames = getBridgeNames();
    var bridgeOptions = bridgeNames.map(name => `<option value="${name}">${name}</option>`).join('');
    if (includeDefaultOption) {
        return `<option value="">-- Select Bridge --</option>${bridgeOptions}`;
    } else {
        return bridgeOptions;
    }
}

// Function to update via dropdowns after layer changes
function updateDropdownsInViaBridges() {
    var bridgesTable = document.getElementById('bridgesTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    // Update top layer select elements
    for (var i = 0; i < bridgesTable.length; i++) {
        var selectElement = bridgesTable[i].querySelector('select[name^="bridgeLayer"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getLayerOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

    

    // Update top layer select elements
    for (var i = 0; i < bridgesTable.length; i++) {
        var selectElement = bridgesTable[i].querySelector('select[name^="bridgeVia"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getViaOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

    // Update top layer select elements
    for (var i = 0; i < bridgesTable.length; i++) {
        var selectElement = bridgesTable[i].querySelector('select[name^="viaStackCCW"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getViaPadStackOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }


    // Update top layer select elements
    for (var i = 0; i < bridgesTable.length; i++) {
        var selectElement = bridgesTable[i].querySelector('select[name^="viaStackCW"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getViaPadStackOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

}

// Function to initialize both MutationObserver and input listener for bridgesTable
function initializeBridgeChangeObserver(handleChangeFunction) {
    // Select the bridgesTable element
    const bridgesTable = document.getElementById('bridgesTable');

    // Create a MutationObserver instance
    const observer = new MutationObserver(function (mutationsList) {
        for (let mutation of mutationsList) {
            if (mutation.type === 'childList') {
                // Trigger the provided change handling function whenever a child element changes (like adding or removing rows)
                handleChangeFunction();
                return; // Exit the loop after triggering the function once
            }
        }
    });

    // Configure the observer to watch for changes in the bridgesTable element and its children
    observer.observe(bridgesTable, { childList: true, subtree: true });

    // Listen for input changes and trigger the provided change handling function
    bridgesTable.addEventListener('input', handleChangeFunction);
}

initializeLayerChangeObserver(updateDropdownsInViaBridges);
initializeViaChangeObserver(updateDropdownsInViaBridges)
initializeViaPadStackChangeObserver(updateDropdownsInViaBridges)
initializeBridgeChangeObserver(updateArtworkTabsAvailability);
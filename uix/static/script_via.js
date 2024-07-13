// script_via.js

function addViaRow() {
    var table = document.getElementById('viaTable').getElementsByTagName('tbody')[0];
    var rowCount = table.rows.length + 1;
    var newRow = table.insertRow();
    var cell1 = newRow.insertCell(0);
    var cell2 = newRow.insertCell(1);
    var cell3 = newRow.insertCell(2);
    var cell4 = newRow.insertCell(3);
    var cell5 = newRow.insertCell(4);
    var cell6 = newRow.insertCell(5);
    var cell7 = newRow.insertCell(6);
    cell1.innerHTML = '<input type="text" name="viaName' + rowCount + '">';
    cell2.innerHTML = '<input type="number" name="viaLength' + rowCount + '">';
    cell3.innerHTML = '<input type="number" name="viaWidth' + rowCount + '">';
    cell4.innerHTML = '<input type="number" name="viaSpacing' + rowCount + '">';
    cell5.innerHTML = '<input type="number" name="viaAngle' + rowCount + '">';
    cell6.innerHTML = '<select name="viaLayer' + rowCount + '">' + getLayerOptions() + '</select>';
    cell7.innerHTML = '<button onclick="deleteViaRow(this)">Delete</button>';
    updateTabsAvailability(); // Update tabs after adding row
  
}



function deleteViaRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
    updateTabsAvailability(); // Update tabs after deleting row

}

function saveVia() {
    var vias = {};

    // Iterate through table rows to collect data
    var tableRows = document.querySelectorAll('#viaTable tbody tr');
    tableRows.forEach(function (row, index) {
        var nameInput = row.querySelector('input[name^="viaName"]');
        var lengthInput = row.querySelector('input[name^="viaLength"]');
        var widthInput = row.querySelector('input[name^="viaWidth"]');
        var spacingInput = row.querySelector('input[name^="viaSpacing"]');
        var angleInput = row.querySelector('input[name^="viaAngle"]');
        var layerSelect = row.querySelector('select[name^="viaLayer"]');

        var name = nameInput.value.trim();
        var length = parseInt(lengthInput.value.trim());
        var width = parseInt(widthInput.value.trim());
        var spacing = parseInt(spacingInput.value.trim());
        var angle = parseInt(angleInput.value.trim());
        var layer = layerSelect.value.trim(); // Get selected value from dropdown

        // Validate all inputs including layer
        if (name && !isNaN(length) && !isNaN(width) && !isNaN(spacing) && !isNaN(angle) && layer) {
            vias[name] = {
                length: length,
                width: width,
                spacing: spacing,
                angle: angle,
                layer: layer
            };
        } else {
            // Handle invalid data if necessary (e.g., alert or console log)
            console.log('Invalid data found in row:', index + 1);
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        data: { via: vias },
        savePath: document.getElementById('viaSavePath').value.trim(),
        saveName: document.getElementById('viaSaveName').value.trim()
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


function loadVia() {
    var viaJsonPath = document.getElementById('viaJsonPath').value.trim();

    loadJsonData(viaJsonPath,
        function (data) {
            populateViaTable(data.via);
            alert('JSON data loaded successfully!');
            updateTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
            updateTabsAvailability(); // Update tabs on error
        }
    );

}

function populateViaTable(viasData) {
    var table = document.getElementById('viaTable').getElementsByTagName('tbody')[0];
    table.innerHTML = ''; // Clear existing rows

    Object.keys(viasData).forEach(function (key, index) {
        var via = viasData[key];
        var newRow = table.insertRow();
        var cell1 = newRow.insertCell(0);
        var cell2 = newRow.insertCell(1);
        var cell3 = newRow.insertCell(2);
        var cell4 = newRow.insertCell(3);
        var cell5 = newRow.insertCell(4);
        var cell6 = newRow.insertCell(5);
        var cell7 = newRow.insertCell(6);

        cell1.innerHTML = '<input type="text" name="viaName' + index + '" value="' + key + '">';
        cell2.innerHTML = '<input type="number" name="viaLength' + index + '" value="' + via.length + '">';
        cell3.innerHTML = '<input type="number" name="viaWidth' + index + '" value="' + via.width + '">';
        cell4.innerHTML = '<input type="number" name="viaSpacing' + index + '" value="' + via.spacing + '">';
        cell5.innerHTML = '<input type="number" name="viaAngle' + index + '" value="' + via.angle + '">';

        // Determine if via.layer is in the available layer options
        var layerOptionsHTML = getLayerOptions();
        if (layerOptionsHTML.includes('value="' + via.layer + '"')) {
            cell6.innerHTML = '<select name="viaLayer' + index + '">' + layerOptionsHTML + '</select>';
            // Set the value after setting innerHTML
            cell6.querySelector('select').value = via.layer;
        } else {
            cell6.innerHTML = '<select name="viaLayer' + index + '"><option value="">-- Select Layer --</option>' + layerOptionsHTML + '</select>';
        }

        cell7.innerHTML = '<button onclick="deleteViaRow(this)">Delete</button>';
    });

    updateTabsAvailability(); // Update tabs after populating vias

}




function getViaNames(){
    var viaNames = [];
    var viaTable = document.getElementById('viaTable').getElementsByTagName('tbody')[0];
    var rows = viaTable.getElementsByTagName('tr');
    for (var i = 0; i < rows.length; i++) {
        var nameInput = rows[i].querySelector('input[name^="viaName"]');
        if (nameInput) {
            viaNames.push(nameInput.value.trim());
        }
    }
    return viaNames;

}


function getViaOptions(includeDefaultOption = true) {
    var viaNames = getViaNames();
    var viaOptions = viaNames.map(name => `<option value="${name}">${name}</option>`).join('');
    if (includeDefaultOption) {
        return `<option value="">-- Select Via --</option>${viaOptions}`;
    } else {
        return viaOptions;
    }
}




// Function to update via dropdowns after layer changes
function updateDropdownsInVia() {
    var viaTables = document.getElementById('viaTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    for (var i = 0; i < viaTables.length; i++) {
        var selectElement = viaTables[i].querySelector('select[name^="viaLayer"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getLayerOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }
}





// Function to initialize both MutationObserver and input listener
function initializeViaChangeObserver(handleChangeFunction) {
    // Select the layersTable element
    const layersTable = document.getElementById('viaTable');

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

    // Configure the observer to watch for changes in the layersTable element and its children
    observer.observe(layersTable, { childList: true, subtree: true });

    // Listen for input changes and trigger the provided change handling function
    layersTable.addEventListener('input', handleChangeFunction);
}


initializeLayerChangeObserver(updateDropdownsInVia);


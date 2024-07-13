function addArmRow() {
    var table = document.getElementById('armsTable').getElementsByTagName('tbody')[0];
    var rowCount = table.rows.length + 1;
    var newRow = table.insertRow();
    var cell1 = newRow.insertCell(0);
    var cell2 = newRow.insertCell(1);
    var cell3 = newRow.insertCell(2);
    var cell4 = newRow.insertCell(3);
    var cell5 = newRow.insertCell(4);
    var cell6 = newRow.insertCell(5);
    var cell7 = newRow.insertCell(6);
    var cell8 = newRow.insertCell(7); // New cell for the delete button

    cell1.innerHTML = '<input type="text" name="armName' + rowCount + '">';
    cell2.innerHTML = '<select name="armType' + rowCount + '">' +
        '<option value="single">Single</option>' +
        '<option value="differential">Differential</option>' +
        '</select>';
    cell3.innerHTML = '<input type="number" name="armLength' + rowCount + '">';
    cell4.innerHTML = '<input type="number" name="armWidth' + rowCount + '">';
    cell5.innerHTML = '<input type="text" name="armPort' + rowCount + '">';
    cell6.innerHTML = '<select name="armLayer' + rowCount + '">' + getLayerOptions() + '</select>';
    cell7.innerHTML = '<select name="armViaStack' + rowCount + '">' + getViaPadStackOptions() + '</select>';
    cell8.innerHTML = '<button onclick="deleteArmRow(this)">Delete</button>'; // Delete button

    updateTabsAvailability(); // Update tabs after adding row
}

function deleteArmRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
    updateTabsAvailability(); // Update tabs after deleting row
}
function saveArms() {
    var arms = {};

    // Iterate through table rows to collect data
    var tableRows = document.querySelectorAll('#armsTable tbody tr');
    tableRows.forEach(function (row, index) {
        var nameInput = row.querySelector('input[name^="armName"]');
        var typeSelect = row.querySelector('select[name^="armType"]');
        var lengthInput = row.querySelector('input[name^="armLength"]');
        var widthInput = row.querySelector('input[name^="armWidth"]');
        var portInput = row.querySelector('input[name^="armPort"]');
        var layerSelect = row.querySelector('select[name^="armLayer"]');
        var viaPadStackSelect = row.querySelector('select[name^="armViaPadStack"]');

        var name = nameInput.value.trim();
        var type = typeSelect.value.trim();
        var length = parseInt(lengthInput.value.trim());
        var width = parseInt(widthInput.value.trim());
        var port = portInput.value.trim().split(',').map(function (item) { return item.trim(); }); // Convert ports to array
        var layer = layerSelect.value.trim();
        var viaPadStack = viaPadStackSelect.value.trim();

        if (name && type && !isNaN(length) && length > 0 && !isNaN(width) && width > 0 && layer && viaPadStack) {
            arms[name] = {
                type: type,
                length: length,
                width: width,
                port: port,
                layer: layer,
                viaPadStack: viaPadStack
            };
        }
    });

    // Prepare data to send to server
    var jsonData = {
        arms: arms,
        savePath: document.getElementById('armsSavePath').value.trim(),
        saveName: document.getElementById('armsSaveName').value.trim()
    };

    // Send data to server to save
    fetch('/save_json_arms', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(jsonData)
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



function loadArms() {
    var armJsonPath = document.getElementById('armsJsonPath').value.trim(); // Ensure correct ID is used

    loadJsonData(armJsonPath,
        function (data) {
            populateArmTable(data.arms); // Call function to populate table with loaded data
            alert('JSON data loaded successfully!');
            updateTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
            updateTabsAvailability(); // Update tabs on error
        }
    );
}
function populateArmTable(armsData) {
    var table = document.getElementById('armsTable').getElementsByTagName('tbody')[0];
    table.innerHTML = ''; // Clear existing rows

    Object.keys(armsData).forEach(function (key, index) {
        var arm = armsData[key];
        var newRow = table.insertRow();
        var cell1 = newRow.insertCell(0);
        var cell2 = newRow.insertCell(1);
        var cell3 = newRow.insertCell(2);
        var cell4 = newRow.insertCell(3);
        var cell5 = newRow.insertCell(4);
        var cell6 = newRow.insertCell(5);
        var cell7 = newRow.insertCell(6);
        var cell8 = newRow.insertCell(7); // New cell for the delete button

        cell1.innerHTML = '<input type="text" name="armName' + index + '" value="' + key + '">';

        cell2.innerHTML = '<select name="armType' + index + '">' +
            '<option value="double">DOUBLE</option>' +
            '<option value="single">SINGLE</option>' +
            '</select>';
        cell2.querySelector('select').value = arm.type.toLowerCase(); // Set selected value based on type

        cell3.innerHTML = '<input type="number" name="armLength' + index + '" value="' + arm.length + '">';

        cell4.innerHTML = '<input type="number" name="armWidth' + index + '" value="' + arm.width + '">';

        if (Array.isArray(arm.port)) {
            cell5.innerHTML = '<input type="text" name="armPort' + index + '" value="' + arm.port.join(', ') + '">';
        } else {
            cell5.innerHTML = '<input type="text" name="armPort' + index + '" value="' + arm.port + '">';
        }

        cell6.innerHTML = '<select name="armLayer' + index + '">' + getLayerOptions() + '</select>';
        cell6.querySelector('select').value = arm.layer; // Set selected value

        cell7.innerHTML = '<select name="armViaPadStack' + index + '">' + getViaPadStackOptions() + '</select>';
        cell7.querySelector('select').value = arm.viaStack || ''; // Set selected value, if available

        cell8.innerHTML = '<button onclick="deleteArmRow(this)">Delete</button>'; // Delete button
    });

    updateTabsAvailability(); // Update tabs after populating arms
}


function updateDropdownsInArmTable() {
    var armsTable = document.getElementById('armsTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    // Update type select elements
    for (var i = 0; i < armsTable.length; i++) {
        var selectElement = armsTable[i].querySelector('select[name^="armType"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = '<option value="differential">Differential</option>' +
                '<option value="single">Single</option>';
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

    // Update layer select elements
    for (var i = 0; i < armsTable.length; i++) {
        var selectElement = armsTable[i].querySelector('select[name^="armLayer"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getLayerOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

    // Update viaPadStack select elements
    for (var i = 0; i < armsTable.length; i++) {
        var selectElement = armsTable[i].querySelector('select[name^="armViaPadStack"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getViaPadStackOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }
}

initializeLayerChangeObserver(updateDropdownsInArmTable);
initializeViaPadStackChangeObserver(updateDropdownsInArmTable);
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
        '<option value="single">SINGLE</option>' +
        '<option value="double">DOUBLE</option>' +
        '</select>';
    cell3.innerHTML = '<input type="number" name="armLength' + rowCount + '">';
    cell4.innerHTML = '<input type="number" name="armWidth' + rowCount + '">';
    cell5.innerHTML = '<select name="armPort' + rowCount + '">' + getPortOptions() + '</select>';
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
    var table = document.getElementById('armsTable').getElementsByTagName('tbody')[0];
    var rows = table.getElementsByTagName('tr');
    var armsData = {};

    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var arm = {};

        arm.name = row.querySelector('input[name^="armName"]').value.trim();
        arm.type = row.querySelector('select[name^="armType"]').value;
        arm.length = parseInt(row.querySelector('input[name^="armLength"]').value);
        arm.width = parseInt(row.querySelector('input[name^="armWidth"]').value);

        var selectedPorts = [];
        var portSelect = row.querySelector('select[name^="armPort"]');
        for (var j = 0; j < portSelect.options.length; j++) {
            if (portSelect.options[j].selected) {
                selectedPorts.push(portSelect.options[j].value);
            }
        }
        arm.port = selectedPorts.length === 1 ? selectedPorts[0] : selectedPorts;

        arm.layer = row.querySelector('select[name^="armLayer"]').value;
        arm.viaStack = row.querySelector('select[name^="armViaPadStack"]').value;

        armsData[arm.name] = arm;
    }

    var jsonData = {
        data: armsData,
        //arms: armsData,
        savePath: document.getElementById('armsSavePath').value.trim(),
        saveName: document.getElementById('armsSaveName').value.trim()
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


        cell5.innerHTML = '<select name="armPort' + index + '" multiple>' + getPortOptions(false) + '</select>';
        var portListSelect = cell5.querySelector('select');
        if (Array.isArray(arm.port)) {
            arm.port.forEach(function (port) {
                for (var i = 0; i < portListSelect.options.length; i++) {
                    if (portListSelect.options[i].value === port) {
                        portListSelect.options[i].selected = true;
                        break;
                    }
                }
            });
        } else {
            // If arm.port is not an array (single value case)
            for (var i = 0; i < portListSelect.options.length; i++) {
                if (portListSelect.options[i].value === arm.port) {
                    portListSelect.options[i].selected = true;
                    break;
                }
            }
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



    // Update Port elements
    for (var i = 0; i < armsTable.length; i++) {
        var selectElement = armsTable[i].querySelector('select[name^="armPort"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getPortOptions();
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
initializePortChangeObserver(updateDropdownsInArmTable);
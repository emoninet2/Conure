function armTypeChange(selectElement, rowCount) {
    var cell5 = selectElement.parentNode.parentNode.cells[4]; // cell5 is the 5th cell in the row
    var selectedValue = selectElement.value;
    if (selectedValue === "single") {
        cell5.innerHTML = '<select name="armPort' + rowCount + '">' + getPortOptions('single') + '</select>';
    } else if (selectedValue === "double") {
        cell5.innerHTML = '<select name="armPort' + rowCount + '" multiple>' + getPortOptions('double') + '</select>';
    }
}



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
    cell2.innerHTML = '<select name="armType' + rowCount + '" onchange="armTypeChange(this, ' + rowCount + ')">' +
        '<option value="single">SINGLE</option>' +
        '<option value="double">DOUBLE</option>' +
        '</select>';
    cell3.innerHTML = '<input type="number" name="armLength' + rowCount + '">';
    cell4.innerHTML = '<input type="number" name="armWidth' + rowCount + '">';

    cell5.innerHTML = '<select name="armPort' + rowCount + '">' + getPortOptions('single') + '</select>';

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

        cell2.innerHTML = '<select name="armType' + index + '" onchange="armTypeChange(this, ' + index + ')">' +
            '<option value="single">SINGLE</option>' +
            '<option value="double">DOUBLE</option>' +
            '</select>';
        cell2.querySelector('select').value = arm.type.toLowerCase(); // Set selected value based on type
        //armTypeChange(this, index);

        cell3.innerHTML = '<input type="number" name="armLength' + index + '" value="' + arm.length + '">';

        cell4.innerHTML = '<input type="number" name="armWidth' + index + '" value="' + arm.width + '">';

        if (arm.type === 'SINGLE') {
            cell5.innerHTML = '<select name="armPort' + index + '">' + getPortOptions() + '</select>';
        } else if (arm.type === 'DOUBLE') {
            cell5.innerHTML = '<select name="armPort' + index + '" multiple>' + getPortOptions() + '</select>';

        }


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

function getArmNames() {
    var armNames = [];
    var armsTable = document.getElementById('armsTable').getElementsByTagName('tbody')[0];
    var rows = armsTable.getElementsByTagName('tr');
    for (var i = 0; i < rows.length; i++) {
        var nameInput = rows[i].querySelector('input[name^="armName"]');
        if (nameInput) {
            armNames.push(nameInput.value.trim());
        }
    }
    return armNames;
}

function getArmOptions(includeDefaultOption = true) {
    var armNames = getArmNames();
    var armOptions = armNames.map(name => `<option value="${name}">${name}</option>`).join('');
    if (includeDefaultOption) {
        return `<option value="">-- Select Arm --</option>${armOptions}`;
    } else {
        return armOptions;
    }
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




// Function to initialize both MutationObserver and input listener for armsTable
function initializeArmChangeObserver(handleChangeFunction) {
    // Select the armsTable element
    const armsTable = document.getElementById('armsTable');

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

    // Configure the observer to watch for changes in the armsTable element and its children
    observer.observe(armsTable, { childList: true, subtree: true });

    // Listen for input changes and trigger the provided change handling function
    armsTable.addEventListener('input', handleChangeFunction);
}



initializeLayerChangeObserver(updateDropdownsInArmTable);
initializeViaPadStackChangeObserver(updateDropdownsInArmTable);
initializePortChangeObserver(updateDropdownsInArmTable);
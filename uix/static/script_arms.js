


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
    var cell8 = newRow.insertCell(7);
    var cell9 = newRow.insertCell(8); // New cell for the delete button

    cell1.innerHTML = '<input type="text" name="armName' + rowCount + '">';
    cell2.innerHTML = '<select name="armType' + rowCount + '">' +
        '<option value="single">SINGLE</option>' +
        '<option value="double">DOUBLE</option>' +
        '</select>';


    cell3.innerHTML = '<input type="number" name="armLength' + rowCount + '">';
    cell4.innerHTML = '<input type="number" name="armWidth' + rowCount + '">';

    cell5.innerHTML = '<select name="armPort1' + rowCount + '">' + getPortOptions('single') + '</select>';
    cell6.innerHTML = '<select name="armPort2' + rowCount + '">' + getPortOptions('single') + '</select>';

    cell7.innerHTML = '<select name="armLayer' + rowCount + '">' + getLayerOptions() + '</select>';
    cell8.innerHTML = '<select name="armViaStack' + rowCount + '">' + getViaPadStackOptions() + '</select>';
    cell9.innerHTML = '<button onclick="deleteArmRow(this)">Delete</button>'; // Delete button

    updateTabsAvailability(); // Update tabs after adding row
}

function deleteArmRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
    updateTabsAvailability(); // Update tabs after deleting row
}



function getArmsJSON() {
    var table = document.getElementById('armsTable').getElementsByTagName('tbody')[0];
    var rows = table.getElementsByTagName('tr');
    var armsData = {};

    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var arm = {};

        var name = row.querySelector('input[name^="armName"]').value.trim();
        arm.type = row.querySelector('select[name^="armType"]').value.toUpperCase();
        arm.length = parseInt(row.querySelector('input[name^="armLength"]').value);
        arm.width = parseInt(row.querySelector('input[name^="armWidth"]').value);

        if (arm.type === "SINGLE") {
            arm.port = row.querySelector('select[name^="armPort1"]').value;
        } else if (arm.type === "DOUBLE") {
            arm.port = [row.querySelector('select[name^="armPort1"]').value, row.querySelector('select[name^="armPort2"]').value];
        }
        
        arm.layer = row.querySelector('select[name^="armLayer"]').value;

        
        var viaStackSelected = row.querySelector('select[name^="armViaPadStack"]').value;
        if (viaStackSelected) {
            arm.viaStack = viaStackSelected;
        }

        armsData[name] = arm;
    }

    var jsonData = { arms: armsData };


    return jsonData;
}

function saveArms() {
    var table = document.getElementById('armsTable').getElementsByTagName('tbody')[0];
    var rows = table.getElementsByTagName('tr');
    var armsData = {};

    for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var arm = {};

        var name = row.querySelector('input[name^="armName"]').value.trim();
        arm.type = row.querySelector('select[name^="armType"]').value.toUpperCase();
        arm.length = parseInt(row.querySelector('input[name^="armLength"]').value);
        arm.width = parseInt(row.querySelector('input[name^="armWidth"]').value);

        if (arm.type === "SINGLE") {
            arm.port = row.querySelector('select[name^="armPort1"]').value;
        } else if (arm.type === "DOUBLE") {
            arm.port = [row.querySelector('select[name^="armPort1"]').value, row.querySelector('select[name^="armPort2"]').value];
        }
        
        arm.layer = row.querySelector('select[name^="armLayer"]').value;

        
        var viaStackSelected = row.querySelector('select[name^="armViaPadStack"]').value;
        if (viaStackSelected) {
            arm.viaStack = viaStackSelected;
        }

        armsData[name] = arm;
    }

    var jsonData = {
        data: { arms: armsData },
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
        var cell8 = newRow.insertCell(7);
        var cell9 = newRow.insertCell(8); // New cell for the delete button

        cell1.innerHTML = '<input type="text" name="armName' + index + '" value="' + key + '">';

        cell2.innerHTML = '<select name="armType' + index + '">' +
            '<option value="single">SINGLE</option>' +
            '<option value="double">DOUBLE</option>' +
            '</select>';
        cell2.querySelector('select').value = arm.type.toLowerCase(); // Set selected value based on type
        //armTypeChange(this, index);

        cell3.innerHTML = '<input type="number" name="armLength' + index + '" value="' + arm.length + '">';

        cell4.innerHTML = '<input type="number" name="armWidth' + index + '" value="' + arm.width + '">';







        if (arm.type === 'SINGLE') {
            cell5.innerHTML = '<select name="armPort1' + index + '">' + getPortOptions() + '</select>';
            cell5.querySelector('select').value = arm.port; // Set selected value

            //Create a hidden cell for port2
            cell6.innerHTML = '<select name="armPort2' + index + '">' + getPortOptions() + '</select>';
            //cell6.disable = true;
        } else if (arm.type === 'DOUBLE') {
            cell5.innerHTML = '<select name="armPort1' + index + '">' + getPortOptions() + '</select>';
            cell5.querySelector('select').value = arm.port[0]; // Set selected value
            cell6.innerHTML = '<select name="armPort2' + index + '">' + getPortOptions() + '</select>';
            cell6.querySelector('select').value = arm.port[1]; // Set selected value
        }




       

        cell7.innerHTML = '<select name="armLayer' + index + '">' + getLayerOptions() + '</select>';
        cell7.querySelector('select').value = arm.layer; // Set selected value

        cell8.innerHTML = '<select name="armViaPadStack' + index + '">' + getViaPadStackOptions() + '</select>';
        cell8.querySelector('select').value = arm.viaStack || ''; // Set selected value, if available

        cell9.innerHTML = '<button onclick="deleteArmRow(this)">Delete</button>'; // Delete button
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
    const armsTable = document.getElementById('armsTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    // Update Port elements
    for (let i = 0; i < armsTable.length; i++) {
        const selectElement = armsTable[i].querySelector('select[name^="armPort1"]');
        if (selectElement) {
            const currentValue = selectElement.value;
            selectElement.innerHTML = getPortOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }

        const selectElement2 = armsTable[i].querySelector('select[name^="armPort2"]'); // Ensure to update armPort2
        if (selectElement2) {
            const currentValue2 = selectElement2.value;
            selectElement2.innerHTML = getPortOptions();
            selectElement2.value = currentValue2;  // Restore previous selection
        }


    }

    // Update layer select elements
    for (let i = 0; i < armsTable.length; i++) {
        const selectElement = armsTable[i].querySelector('select[name^="armLayer"]');
        if (selectElement) {
            const currentValue = selectElement.value;
            selectElement.innerHTML = getLayerOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

    // Update viaPadStack select elements
    for (let i = 0; i < armsTable.length; i++) {
        const selectElement = armsTable[i].querySelector('select[name^="armViaPadStack"]');
        if (selectElement) {
            const currentValue = selectElement.value;
            selectElement.innerHTML = getViaPadStackOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

    //disablePort2ForSingleArmType(); // Call after updating the dropdowns
}



function disablePort2ForSingleArmType() {
    const armsTable = document.getElementById('armsTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    for (let i = 0; i < armsTable.length; i++) {
        const armTypeSelect = armsTable[i].querySelector('select[name^="armType"]');
        const port2Select = armsTable[i].querySelector('select[name^="armPort2"]');

        if (armTypeSelect && port2Select) {
            if (armTypeSelect.value.toLowerCase() === 'single') {
                port2Select.disabled = true;
            } else {
                port2Select.disabled = false;
            }
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
initializeArmChangeObserver(disablePort2ForSingleArmType);
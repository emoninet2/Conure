// Example without initializePortNames()

function addPortRow() {
    var table = document.getElementById('portsTable').getElementsByTagName('tbody')[0];
    var rowCount = table.rows.length + 1;
    var newRow = table.insertRow();
    var cell1 = newRow.insertCell(0);
    var cell2 = newRow.insertCell(1);
    var cell3 = newRow.insertCell(2);

    cell1.innerHTML = '<input type="text" name="portName' + rowCount + '">';
    cell2.innerHTML = '<input type="text" name="portLabel' + rowCount + '">';
    cell3.innerHTML = '<button onclick="deletePortRow(this)">Delete</button>';

    updateTabsAvailability(); // Update tabs after adding row

}


function deletePortRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
    updateTabsAvailability(); // Update tabs after deleting row
}



// Function to add a row to the Sim Ports Table
function addSimPortRow() {
    var table = document.getElementById('simPortsTable').getElementsByTagName('tbody')[0];
    var rowCount = table.rows.length;

    var newRow = table.insertRow();
    var cell1 = newRow.insertCell(0);
    var cell2 = newRow.insertCell(1);
    var cell3 = newRow.insertCell(2);
    var cell4 = newRow.insertCell(3);
    var cell5 = newRow.insertCell(4);
    var cell6 = newRow.insertCell(5);

    // Incrementing Port ID starting from 0
    cell1.innerHTML = '<input type="text" name="portID' + rowCount + '" value="' + rowCount + '" readonly>';

    // Selectable Port Type (Single or Differential)
    cell2.innerHTML = '<select name="portType' + rowCount + '">' +
        '<option value="Single">Single</option>' +
        '<option value="Differential">Differential</option>' +
        '</select>';

    // Selectable Port Plus (from portNames array)
    cell3.innerHTML = '<select name="portPlus' + rowCount + '">' + getPortOptions() + '</select>';

    // Selectable Port Minus (from portNames array)
    cell4.innerHTML = '<select name="portMinus' + rowCount + '">' + getPortOptions() + '</select>';
    //cell4.innerHTML = generatePortDropdown('portMinus' + rowCount);

    // Enable Checkbox
    cell5.innerHTML = '<input type="checkbox" name="portEnable' + rowCount + '">';

    // Delete button
    cell6.innerHTML = '<button onclick="deleteSimPortRow(this)">Delete</button>';

    updateTabsAvailability(); // Update tabs after adding row
}

function deleteSimPortRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
    updateTabsAvailability(); // Update tabs after deleting row
}

function savePorts() {
    // Get the ports data from the tables
    var portsData = {
        ports: {
            config: {
                simulatingPorts: []
            },
            data: {}
        }
    };

    // Save data from portsTable
    var portsTable = document.getElementById('portsTable').getElementsByTagName('tbody')[0];
    for (var i = 0; i < portsTable.rows.length; i++) {

        var portName = portsTable.rows[i].querySelector('input[name^="portName"]').value.trim()
        var portLabel = portsTable.rows[i].querySelector('input[name^="portLabel"]').value.trim()

        // Populate data
        portsData.ports.data[portName] = {
            label: portLabel
        };
    }

    // Save data from simPortsTable
    var simPortsTable = document.getElementById('simPortsTable').getElementsByTagName('tbody')[0];
    for (var j = 0; j < simPortsTable.rows.length; j++) {


        var portID = simPortsTable.rows[j].querySelector('input[name^="portID"]')
            ? parseInt(simPortsTable.rows[j].querySelector('input[name^="portID"]').value.trim())
            : undefined;

        var portType = simPortsTable.rows[j].querySelector('select[name^="portType"]')
            ? simPortsTable.rows[j].querySelector('select[name^="portType"]').value.trim()
            : undefined;

        var portPlus = simPortsTable.rows[j].querySelector('select[name^="portPlus"]')
            ? simPortsTable.rows[j].querySelector('select[name^="portPlus"]').value.trim()
            : undefined;

        var portMinus = simPortsTable.rows[j].querySelector('select[name^="portMinus"]')
            ? simPortsTable.rows[j].querySelector('select[name^="portMinus"]').value.trim()
            : undefined;

        var enable = simPortsTable.rows[j].querySelector('input[name^="portEnable"]')
            ? simPortsTable.rows[j].querySelector('input[name^="portEnable"]').checked
            : undefined;

        // Populate config
        portsData.ports.config.simulatingPorts.push({
            id: portID,
            type: portType,
            plus: portPlus,
            minus: portMinus,
            enable: enable
        });
    }

    // Prepare data to send to Flask
    var jsonData = {
        data: portsData,
        savePath: document.getElementById('portsSavePath').value.trim(),
        saveName: document.getElementById('portsSaveName').value.trim()
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

    // Optional: update tabs or other UI elements after saving data
    updateTabsAvailability();
}

function loadPorts() {
    var portsJsonPath = document.getElementById('portsJsonPath').value.trim();

    loadJsonData(portsJsonPath,
        function (data) {
            populatePortsAndSimPortsTable(data.ports);
            alert('JSON data loaded successfully!');
            updateTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
            updateTabsAvailability(); // Update tabs on error
        }
    );
}

function populatePortsAndSimPortsTable(jsonData) {
    var portsData = jsonData;

    // Populate portsTable
    var portsTable = document.getElementById('portsTable').getElementsByTagName('tbody')[0];
    // Clear existing rows
    portsTable.innerHTML = '';
    Object.keys(portsData.data).forEach(function (portName) {
        var row = portsTable.insertRow();
        var cell1 = row.insertCell(0);
        var cell2 = row.insertCell(1);
        var cell3 = row.insertCell(2);

        // Port Name
        cell1.innerHTML = '<input type="text" name="portName' + portName + '" value="' + portName + '" readonly>';

        // Port Label
        cell2.innerHTML = '<input type="text" name="portLabel' + portName + '" value="' + portsData.data[portName].label + '">';

        // Optionally add delete button or other actions if needed
        cell3.innerHTML = '<button onclick="deletePortRow(this)">Delete</button>';
    });



    // Populate simPortsTable
    var simPortsTable = document.getElementById('simPortsTable').getElementsByTagName('tbody')[0];
    // Clear existing rows
    simPortsTable.innerHTML = '';
    portsData.config.simulatingPorts.forEach(function (simPort, index) {
        var row = simPortsTable.insertRow();
        var cell1 = row.insertCell(0);
        var cell2 = row.insertCell(1);
        var cell3 = row.insertCell(2);
        var cell4 = row.insertCell(3);
        var cell5 = row.insertCell(4);
        var cell6 = row.insertCell(5);

        // Incrementing Port ID starting from 0
        cell1.innerHTML = '<input type="text" name="portID' + index + '" value="' + simPort.id + '" readonly>';

        // Selectable Port Type (Single or Differential)
        cell2.innerHTML = '<select name="portType' + index + '">' +
            '<option value="Single"' + (simPort.type === 'single' ? ' selected' : '') + '>Single</option>' +
            '<option value="Differential"' + (simPort.type === 'differential' ? ' selected' : '') + '>Differential</option>' +
            '</select>';

        // Selectable Port Plus (from portNames array)
        cell3.innerHTML = '<select name="portPlus' + index + '">' + getPortOptions() + '</select>';
        cell3.querySelector('select').value = simPort.plus;

        // Selectable Port Minus (from portNames array)
        cell4.innerHTML = '<select name="portMinus' + index + '">' + getPortOptions() + '</select>';
        cell4.querySelector('select').value = simPort.minus;

        // Enable Checkbox
        cell5.innerHTML = '<input type="checkbox" name="portEnable' + index + '"' + (simPort.enable ? ' checked' : '') + '>';

        // Delete button
        cell6.innerHTML = '<button onclick="deleteSimPortRow(this)">Delete</button>';
    });

    // Update dropdowns in simPortsTable
    updateDropdownsInSimPorts();
    updateTabsAvailability();

}

function collectPortData(tableName) {
    var portData = [];
    var tableRows = document.getElementById(tableName).getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    for (var i = 0; i < tableRows.length; i++) {
        var port = {
            name: tableRows[i].querySelector('input[name^="portName"]').value.trim(),
            label: tableRows[i].querySelector('input[name^="portLabel"]').value.trim()
        };
        portData.push(port);
    }

    return portData;
}


function getPortNames() {
    var portNames = [];
    var portsTable = document.getElementById('portsTable').getElementsByTagName('tbody')[0];
    var rows = portsTable.getElementsByTagName('tr');
    for (var i = 0; i < rows.length; i++) {
        var nameInput = rows[i].querySelector('input[name^="portName"]');
        if (nameInput) {
            portNames.push(nameInput.value.trim());
        }
    }
    return portNames;
}

function getPortOptions(includeDefaultOption = true) {
    var portNames = getPortNames();
    var portOptions = portNames.map(name => `<option value="${name}">${name}</option>`).join('');
    if (includeDefaultOption) {
        return `<option value="">-- Select Port --</option>${portOptions}`;
    } else {
        return portOptions;
    }
}


function getSimPortNames() {
    var simPortNames = [];
    var simPortsTable = document.getElementById('simPortsTable').getElementsByTagName('tbody')[0];
    var rows = simPortsTable.getElementsByTagName('tr');
    for (var i = 0; i < rows.length; i++) {
        var nameInput = rows[i].querySelector('input[name^="portID"]');
        if (nameInput) {
            simPortNames.push(nameInput.value.trim());
        }
    }
    return simPortNames;
}


function getSimPortOptions() {
    var simPortNames = getSimPortNames();
    var simPortOptions = simPortNames.map(function (name, index) {
        return { value: index, label: name };
    });
    return simPortOptions;
}



function updateDropdownsInSimPorts() {
    var portsTable = document.getElementById('simPortsTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    // Check if portsTable is null or undefined
    if (!portsTable || portsTable.length === 0) {
        // Handle the case where no rows exist in simPortsTable
        console.log('No rows found in simPortsTable.');
        return;
    }

    // Update Port Plus and Port Minus dropdowns
    for (var i = 0; i < portsTable.length; i++) {
        var selectElementPlus = portsTable[i].querySelector('select[name^="portPlus"]');
        var selectElementMinus = portsTable[i].querySelector('select[name^="portMinus"]');
        if (selectElementPlus || selectElementMinus  ) {
            var currentValuePlus = selectElementPlus.value;
            selectElementPlus.innerHTML = getPortOptions();
            selectElementPlus.value = currentValuePlus;  // Restore previous selection

            var currentValueMinus = selectElementMinus.value;
            selectElementMinus.innerHTML = getPortOptions();
            selectElementMinus.value = currentValueMinus;  // Restore previous selection
        }
    }


}



function updatePortMinusVisibility() {
    var simPortsTable = document.getElementById('simPortsTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    // Check if portsTable is null or undefined
    if (!simPortsTable || simPortsTable.length === 0) {
        // Handle the case where no rows exist in simPortsTable
        console.log('No rows found in simPortsTable.');
        return;
    }

    // Update Port Plus and Port Minus dropdowns
    for (var i = 0; i < simPortsTable.length; i++) {
        const selectElementPortType = simPortsTable[i].querySelector('select[name^="portType"]');
        if (selectElementPortType.value === 'Single') {
            simPortsTable[i].querySelector('select[name^="portMinus"]').disabled = true;
        }
        else if (selectElementPortType.value === 'Differential') {
            simPortsTable[i].querySelector('select[name^="portMinus"]').disabled = false;
        }
    }
}




// Function to initialize both MutationObserver and input listener
function initializePortChangeObserver(handleChangeFunction) {
    // Select the portsTable element
    const portsTable = document.getElementById('portsTable');

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

    // Configure the observer to watch for changes in the portsTable element and its children
    observer.observe(portsTable, { childList: true, subtree: true });

    // Listen for input changes and trigger the provided change handling function
    portsTable.addEventListener('input', handleChangeFunction);
}





// Function to initialize both MutationObserver and input listener
function initializeSimPortChangeObserver(handleChangeFunction) {
    // Select the simPortsTable element
    const simPortsTable = document.getElementById('simPortsTable');

    // Create a MutationObserver instance
    const observer = new MutationObserver(function (mutationsList) {
        for (let mutation of mutationsList) {
            if (mutation.type === 'childList') {

                handleChangeFunction();
                return; // Exit the loop after triggering the function once
            }
        }
    });

    // Configure the observer to watch for changes in the simPortsTable element and its children
    observer.observe(simPortsTable, { childList: true, subtree: true });

    // Listen for input changes and trigger handleChangeFunction function
    simPortsTable.addEventListener('input', handleChangeFunction);
}




initializePortChangeObserver(updateDropdownsInSimPorts);
initializeSimPortChangeObserver(updatePortMinusVisibility);

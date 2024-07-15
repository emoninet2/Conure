// script_viaPadStack.js

function addViaPadStackRow() {
    var table = document.getElementById('viaPadStackTable').getElementsByTagName('tbody')[0];
    var rowCount = table.rows.length + 1;
    var newRow = table.insertRow();
    var cell1 = newRow.insertCell(0);
    var cell2 = newRow.insertCell(1);
    var cell3 = newRow.insertCell(2);
    var cell4 = newRow.insertCell(3);
    var cell5 = newRow.insertCell(4);
    var cell6 = newRow.insertCell(5);

    cell1.innerHTML = '<input type="text" name="viaPadStackName' + rowCount + '">';

    cell2.innerHTML = '<select name="viaPadStackTopLayer' + rowCount + '">' + getLayerOptions() + '</select>';
    cell3.innerHTML = '<select name="viaPadStackBottomLayer' + rowCount + '">' + getLayerOptions() + '</select>';
    cell4.innerHTML = '<input type="number" name="viaPadStackMargin' + rowCount + '">';
    
    //cell5.innerHTML = '<select name="viaPadStackViaList' + rowCount + '">' + getViaOptions() + '</select>';
    cell5.innerHTML = '<select name="viaPadStackViaList' + rowCount + '" multiple>' + getViaOptions() + '</select>';
    cell6.innerHTML = '<button onclick="deleteViaPadStackRow(this)">Delete</button>';

    updateTabsAvailability(); // Update tabs after adding row
   
}


function deleteViaPadStackRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
    updateTabsAvailability(); // Update tabs after deleting row
  
}

function getViaPadStackJSON() {
    var viaPadStacks = {};

    // Iterate through table rows to collect data
    var tableRows = document.querySelectorAll('#viaPadStackTable tbody tr');
    tableRows.forEach(function (row, index) {
        var nameInput = row.querySelector('input[name^="viaPadStackName"]');
        var topLayerSelect = row.querySelector('select[name^="viaPadStackTopLayer"]');
        var bottomLayerSelect = row.querySelector('select[name^="viaPadStackBottomLayer"]');
        var marginInput = row.querySelector('input[name^="viaPadStackMargin"]');
        var viaListSelect = row.querySelector('select[name^="viaPadStackViaList"]');

        var name = nameInput.value.trim();
        var topLayer = topLayerSelect.value.trim();
        var bottomLayer = bottomLayerSelect.value.trim();
        var margin = parseInt(marginInput.value.trim());

        var viaList = Array.from(viaListSelect.selectedOptions).map(option => option.value.trim());

        if (name && topLayer && bottomLayer && !isNaN(margin) && viaList.length > 0) {
            viaPadStacks[name] = {
                topLayer: topLayer,
                bottomLayer: bottomLayer,
                margin: margin,
                vias: viaList
            };
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        viaPadStack: viaPadStacks
    };

    return jsonData;
}


function saveViaPadStack() {
    var viaPadStacks = {};

    // Iterate through table rows to collect data
    var tableRows = document.querySelectorAll('#viaPadStackTable tbody tr');
    tableRows.forEach(function (row, index) {
        var nameInput = row.querySelector('input[name^="viaPadStackName"]');
        var topLayerSelect = row.querySelector('select[name^="viaPadStackTopLayer"]');
        var bottomLayerSelect = row.querySelector('select[name^="viaPadStackBottomLayer"]');
        var marginInput = row.querySelector('input[name^="viaPadStackMargin"]');
        var viaListSelect = row.querySelector('select[name^="viaPadStackViaList"]');

        var name = nameInput.value.trim();
        var topLayer = topLayerSelect.value.trim();
        var bottomLayer = bottomLayerSelect.value.trim();
        var margin = parseInt(marginInput.value.trim());

        var viaList = Array.from(viaListSelect.selectedOptions).map(option => option.value.trim());

        if (name && topLayer && bottomLayer && !isNaN(margin) && viaList.length > 0) {
            viaPadStacks[name] = {
                topLayer: topLayer,
                bottomLayer: bottomLayer,
                margin: margin,
                vias: viaList
            };
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        data: { viaPadStack: viaPadStacks },
        savePath: projectDirectoryPath + '/' +  document.getElementById('viaPadStackSavePath').value.trim(),
        saveName: document.getElementById('viaPadStackSaveName').value.trim()
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


function loadViaPadStack() {
    var viaPadStackJsonPath = document.getElementById('viaPadStackJsonPath').value.trim();

    loadJsonData(viaPadStackJsonPath,
        function (data) {
            populateViaPadStackTable(data.viaPadStack);
            alert('JSON data loaded successfully!');
            updateTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
            updateTabsAvailability(); // Update tabs on error
        }
    );
   
}

function populateViaPadStackTable(viaPadStacksData) {
    var table = document.getElementById('viaPadStackTable').getElementsByTagName('tbody')[0];
    table.innerHTML = ''; // Clear existing rows

    Object.keys(viaPadStacksData).forEach(function (key, index) {
        var viaPadStack = viaPadStacksData[key];
        var newRow = table.insertRow();
        var cell1 = newRow.insertCell(0);
        var cell2 = newRow.insertCell(1);
        var cell3 = newRow.insertCell(2);
        var cell4 = newRow.insertCell(3);
        var cell5 = newRow.insertCell(4);
        var cell6 = newRow.insertCell(5);

        cell1.innerHTML = '<input type="text" name="viaPadStackName' + index + '" value="' + key + '">';
        cell2.innerHTML = '<select name="viaPadStackTopLayer' + index + '">' + getLayerOptions() + '</select>';
        cell2.querySelector('select').value = viaPadStack.topLayer; // Set selected value
        cell3.innerHTML = '<select name="viaPadStackBottomLayer' + index + '">' + getLayerOptions() + '</select>';
        cell3.querySelector('select').value = viaPadStack.bottomLayer; // Set selected value
        cell4.innerHTML = '<input type="number" name="viaPadStackMargin' + index + '" value="' + viaPadStack.margin + '">';

        // Populate multiple select for vias
        cell5.innerHTML = '<select name="viaPadStackViaList' + index + '" multiple>' + getViaOptions() + '</select>';
        var viaListSelect = cell5.querySelector('select');
        viaPadStack.vias.forEach(function (via) {
            for (var i = 0; i < viaListSelect.options.length; i++) {
                if (viaListSelect.options[i].value === via) {
                    viaListSelect.options[i].selected = true;
                    break;
                }
            }
        });

        cell6.innerHTML = '<button onclick="deleteViaPadStackRow(this)">Delete</button>';
    });

    updateTabsAvailability(); // Update tabs after populating viaPadStacks

}


function getViaPadStackNames() {
    var viaPadStackNames = [];
    var viaPadStackTable = document.getElementById('viaPadStackTable').getElementsByTagName('tbody')[0];
    var rows = viaPadStackTable.getElementsByTagName('tr');
    for (var i = 0; i < rows.length; i++) {
        var nameInput = rows[i].querySelector('input[name^="viaPadStackName"]');
        if (nameInput) {
            viaPadStackNames.push(nameInput.value.trim());
        }
    }
    return viaPadStackNames;
}

function getViaPadStackOptions(includeDefaultOption = true) {
    var viaPadStackNames = getViaPadStackNames();
    var viaPadStackOptions = viaPadStackNames.map(name => `<option value="${name}">${name}</option>`).join('');
    if (includeDefaultOption) {
        return `<option value="">-- Select Via --</option>${viaPadStackOptions}`;
    } else {
        return viaPadStackOptions;
    }
}



// Function to update via dropdowns after layer changes
function updateDropdownsInViaPadStack() {
    var viaPadStackTable = document.getElementById('viaPadStackTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    // Update top layer select elements
    for (var i = 0; i < viaPadStackTable.length; i++) {
        var selectElement = viaPadStackTable[i].querySelector('select[name^="viaPadStackTopLayer"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getLayerOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

    // Update bottom layer select elements
    for (var i = 0; i < viaPadStackTable.length; i++) {
        var selectElement = viaPadStackTable[i].querySelector('select[name^="viaPadStackBottomLayer"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getLayerOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

    // Update via list select elements
    for (var i = 0; i < viaPadStackTable.length; i++) {
        var selectElement = viaPadStackTable[i].querySelector('select[name^="viaPadStackViaList"]');
        if (selectElement) {
            // Store current selected options
            var selectedOptions = Array.from(selectElement.selectedOptions).map(option => option.value);
            selectElement.innerHTML = getViaOptions();
            // Restore previous selected options
            selectedOptions.forEach(value => {
                for (var j = 0; j < selectElement.options.length; j++) {
                    if (selectElement.options[j].value === value) {
                        selectElement.options[j].selected = true;
                    }
                }
            });
        }
    }
}



// Function to initialize both MutationObserver and input listener
function initializeViaPadStackChangeObserver(handleChangeFunction) {
    // Select the layersTable element
    const layersTable = document.getElementById('viaPadStackTable');

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


initializeLayerChangeObserver(updateDropdownsInViaPadStack);
initializeViaChangeObserver(updateDropdownsInViaPadStack)
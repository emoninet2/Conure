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
    //cell5.innerHTML = '<input type="text" name="viaPadStackViaList' + rowCount + '">';
    cell5.innerHTML = '<select name="viaPadStackViaList' + rowCount + '">' + getViaOptions() + '</select>';
    cell6.innerHTML = '<button onclick="deleteViaPadStackRow(this)">Delete</button>';


    

    updateTabsAvailability(); // Update tabs after adding row
    updateViaPadStackDropdowns();
}


function deleteViaPadStackRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
    updateTabsAvailability(); // Update tabs after deleting row
    updateViaPadStackDropdowns();
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
        var viaList = viaListSelect.value.trim();

        if (name && topLayer && bottomLayer && !isNaN(margin) && viaList) {
            viaPadStacks[name] = {
                topLayer: topLayer,
                bottomLayer: bottomLayer,
                margin: margin,
                viaList: viaList
            };
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        data: { viaPadStack: viaPadStacks },
        savePath: document.getElementById('viaPadStackSavePath').value.trim(),
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
    updateViaPadStackDropdowns();
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
        cell3.innerHTML = '<select name="viaPadStackBottomLayer' + index + '">' + getLayerOptions() + '</select>';
        cell4.innerHTML = '<input type="number" name="viaPadStackMargin' + index + '" value="' + viaPadStack.margin + '">';
        //cell5.innerHTML = '<input type="text" name="viaPadStackViaList' + index + '" value="' + viaPadStack.viaList + '">';
        cell5.innerHTML = '<input type="text" name="viaPadStackViaList' + rowCount + '">' + getViaOptions() + '</select>';
        cell6.innerHTML = '<button onclick="deleteViaPadStackRow(this)">Delete</button>';
    });

    updateTabsAvailability(); // Update tabs after populating viaPadStacks
    updateViaPadStackDropdowns();
}



// Function to update via dropdowns after layer changes
function updateViaPadStackDropdowns() {
    
    var viaPadStackTable = document.getElementById('viaPadStackTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    for (var i = 0; i < viaPadStackTable.length; i++) {
        var selectElement = viaPadStackTable[i].querySelector('select[name^="viaPadStackTopLayer"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getLayerOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

    var viaPadStackTable = document.getElementById('viaPadStackTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    for (var i = 0; i < viaPadStackTable.length; i++) {
        var selectElement = viaPadStackTable[i].querySelector('select[name^="viaPadStackBottomLayer"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getLayerOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }


    var viaPadStackTable = document.getElementById('viaPadStackTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    for (var i = 0; i < viaPadStackTable.length; i++) {
        var selectElement = viaPadStackTable[i].querySelector('select[name^="viaPadStackViaList"]');
        if (selectElement) {
            var currentValue = selectElement.value;
            selectElement.innerHTML = getViaOptions();
            selectElement.value = currentValue;  // Restore previous selection
        }
    }

}


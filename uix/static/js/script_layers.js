
function addLayerRow() {
    var table = document.getElementById('layersTable').getElementsByTagName('tbody')[0];
    var rowCount = table.rows.length + 1;
    var newRow = table.insertRow();
    var cell1 = newRow.insertCell(0);
    var cell2 = newRow.insertCell(1);
    var cell3 = newRow.insertCell(2);
    var cell4 = newRow.insertCell(3);
    cell1.innerHTML = '<input type="text" name="name' + rowCount + '">';
    cell2.innerHTML = '<input type="text" name="gdsLayer' + rowCount + '">';
    cell3.innerHTML = '<input type="text" name="gdsDatatype' + rowCount + '">';
    cell4.innerHTML = '<button onclick="deleteLayerRow(this)">Delete</button>';
    updateTabsAvailability(); // Update tabs after deleting row

}

function deleteLayerRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);

    updateTabsAvailability(); // Update tabs after deleting row

}


function getLayersJSON() {
    var layers = {};

    // Iterate through table rows to collect data
    var tableRows = document.querySelectorAll('#layersTable tbody tr');
    tableRows.forEach(function (row, index) {
        var nameInput = row.querySelector('input[name^="name"]');
        var gdsLayerInput = row.querySelector('input[name^="gdsLayer"]');
        var gdsDatatypeInput = row.querySelector('input[name^="gdsDatatype"]');

        var name = nameInput.value.trim();
        var gdsLayer = parseInt(gdsLayerInput.value.trim());
        var gdsDatatype = parseInt(gdsDatatypeInput.value.trim());

        if (name && !isNaN(gdsLayer) && !isNaN(gdsDatatype)) {
            layers[name] = {
                gds: {
                    layer: gdsLayer,
                    datatype: gdsDatatype
                }
            };
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        layer : layers // Making it more generic by wrapping layers in a "data" object
    };

    return jsonData;
}

function saveLayers() {
    var layers = {};

    // Iterate through table rows to collect data
    var tableRows = document.querySelectorAll('#layersTable tbody tr');
    tableRows.forEach(function (row, index) {
        var nameInput = row.querySelector('input[name^="name"]');
        var gdsLayerInput = row.querySelector('input[name^="gdsLayer"]');
        var gdsDatatypeInput = row.querySelector('input[name^="gdsDatatype"]');

        var name = nameInput.value.trim();
        var gdsLayer = parseInt(gdsLayerInput.value.trim());
        var gdsDatatype = parseInt(gdsDatatypeInput.value.trim());

        if (name && !isNaN(gdsLayer) && !isNaN(gdsDatatype)) {
            layers[name] = {
                gds: {
                    layer: gdsLayer,
                    datatype: gdsDatatype
                }
            };
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        data: { layer: layers }, // Making it more generic by wrapping layers in a "data" object
        savePath: projectDirectoryPath + '/' +  document.getElementById('savePath').value.trim(),
        saveName: document.getElementById('saveName').value.trim()
    };

    // Call saveJsonData to save the JSON data
    saveJsonData(
        jsonData,
        '/save_json',
        function () {
            alert('Data saved successfully!');
            updateTabsAvailability(); // Update tabs after saving data
        },
        function (errorMessage) {
            alert(errorMessage);
            // Optionally handle further error logic here
            updateTabsAvailability(); // Update tabs after error
        }
    );
}









function loadLayers() {
    var layerJsonPath = document.getElementById('layerJsonPath').value.trim();

    loadJsonData(layerJsonPath,
        function (data) {
            populateLayersTable(data.layer);
            alert('JSON data loaded successfully!');
            updateTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert(errorMessage);
            updateTabsAvailability(); // Update tabs on error
        }
    );
}


function populateLayersTable(layersData) {
    var table = document.getElementById('layersTable').getElementsByTagName('tbody')[0];
    table.innerHTML = ''; // Clear existing rows

    Object.keys(layersData).forEach(function (name) {
        var layer = layersData[name].gds ? layersData[name].gds.layer : '';
        var datatype = layersData[name].gds ? layersData[name].gds.datatype : '';

        var newRow = table.insertRow();
        var cell1 = newRow.insertCell(0);
        var cell2 = newRow.insertCell(1);
        var cell3 = newRow.insertCell(2);
        var cell4 = newRow.insertCell(3);
        cell1.innerHTML = '<input type="text" name="name" value="' + name + '">';
        cell2.innerHTML = '<input type="text" name="gdsLayer" value="' + layer + '">';
        cell3.innerHTML = '<input type="text" name="gdsDatatype" value="' + datatype + '">';
        cell4.innerHTML = '<button onclick="deleteLayerRow(this)">Delete</button>';
    });

    // Add one empty row at the end for adding new entries
    //addLayerRow();

    updateTabsAvailability(); // Update tabs after populating layers
}

function getLayerNames() {
    var layerNames = [];
    var layersTable = document.getElementById('layersTable').getElementsByTagName('tbody')[0];
    var rows = layersTable.getElementsByTagName('tr');
    for (var i = 0; i < rows.length; i++) {
        var nameInput = rows[i].querySelector('input[name^="name"]');
        if (nameInput) {
            layerNames.push(nameInput.value.trim());
        }
    }
    return layerNames;
}




// Function to get layer options HTML
function getLayerOptions(includeDefaultOption = true) {
    var layerNames = getLayerNames();
    var layerOptions = layerNames.map(name => `<option value="${name}">${name}</option>`).join('');
    if (includeDefaultOption) {
        return `<option value="">-- Select Layer --</option>${layerOptions}`;
    } else {
        return layerOptions;
    }
}




// Function to initialize both MutationObserver and input listener
function initializeLayerChangeObserver(handleChangeFunction) {
    // Select the layersTable element
    const layersTable = document.getElementById('layersTable');

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





document.addEventListener('DOMContentLoaded', function () {
    updateTabsAvailability(); // Update tabs after deleting row
});





// Update via dropdowns every 1 second
// setInterval(function () {
//     updateSegmentDropdowns
//     updateDropdownsInVia();
// }, 1000); // 1000 milliseconds = 1 second
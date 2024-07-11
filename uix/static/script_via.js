function loadVias(event) {

}

function addViaRow(event) {
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
    cell1.innerHTML = '<input type="text" name="name' + rowCount + '">';
    cell2.innerHTML = '<input type="text" name="length' + rowCount + '">';
    cell3.innerHTML = '<input type="text" name="width' + rowCount + '">';
    cell4.innerHTML = '<input type="text" name="spacing' + rowCount + '">';
    cell5.innerHTML = '<input type="text" name="angle' + rowCount + '">';
    cell6.innerHTML = '<input type="text" name="layer' + rowCount + '">';
    cell7.innerHTML = '<button onclick="deleteViaRow(this)">Delete</button>';
    // updateTabsAvailability(); // Update tabs after deleting row
    // updateSegmentDropdowns(); // Update segment dropdowns after deleting row
}

function deleteViaRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);

    //updateTabsAvailability(); // Update tabs after deleting row
    //updateSegmentDropdowns(); // Update segment dropdowns after deleting row
}

function saveVias(event) {
    var vias = {};

    // Iterate through table rows to collect data
    var tableRows = document.querySelectorAll('#viaTable tbody tr');
    tableRows.forEach(function (row, index) {
        var nameInput = row.querySelector('input[name^="name"]');
        var lengthInput = row.querySelector('input[name^="length"]');
        var widthInput = row.querySelector('input[name^="width"]');
        var spacingInput = row.querySelector('input[name^="spacing"]');
        var angleInput = row.querySelector('input[name^="angle"]');
        var layerInput = row.querySelector('input[name^="layer"]');


        var name = nameInput.value.trim();
        var length = parseInt(gdsLayerInput.value.trim());
        var width = parseInt(gdsLayerInput.value.trim());
        var spacing = parseInt(gdsLayerInput.value.trim());
        var angle = parseInt(gdsLayerInput.value.trim());
        var layer = layerInput.value.trim();


        var gdsLayer = parseInt(gdsLayerInput.value.trim());
        var gdsDatatype = parseInt(gdsDatatypeInput.value.trim());

        if (name && !isNaN(length) && !isNaN(width) && !isNaN(spacing) && !isNaN(angle) && layer) {
            vias[name] = {

                length: length,
                width: width,
                spacing: spacing,
                angle: angle,
                layer: layer
                
            };
        }
    });

    // Prepare data to send to Flask
    var jsonData = {
        via: vias,
        savePath: document.getElementById('savePath').value.trim(),
        saveName: document.getElementById('saveName').value.trim()
    };

    // Send data to Flask to save to custom file path and name
    fetch('/save_via_custom', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(jsonData),
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Layers data saved successfully!');
            } else {
                alert('Failed to save layers data.');
            }
        })
        .catch(error => console.error('Error:', error));
    updateTabsAvailability(); // Update tabs after saving layers
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
    updateSegmentDropdowns(); // Update segment dropdowns after populating layers
}
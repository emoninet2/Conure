// script_guardRing.js

function addGuardRingRow() {
    var table = document.getElementById('guardRingTable').getElementsByTagName('tbody')[0];
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
    var cell9 = newRow.insertCell(8);
    var cell10 = newRow.insertCell(9);
    var cell11 = newRow.insertCell(10);

    cell1.innerHTML = '<input type="text" name="guardRingName' + rowCount + '">';
    //cell2.innerHTML = '<input type="text" name="guardRingShape' + rowCount + '">';


    cell2.innerHTML = '<select name="guardRingShape' + rowCount + '">' +
        '<option value="hex">hex</option>' +
        '<option value="hexRing">hexRing</option>' +
        '</select>';

    cell3.innerHTML = '<input type="number" name="guardRingOffset' + rowCount + '">';
    cell4.innerHTML = '<input type="number" name="guardRingWidth' + rowCount + '">';
    cell5.innerHTML = '<select name="guardRingLayer' + rowCount + '">' + getLayerOptions() + '</select>';

    cell6.innerHTML = '<input type="checkbox" name="guardRingContacts' + rowCount + '">';

    cell7.innerHTML = '<select name="guardRingContactsViaPadStack' + rowCount + '">' + getViaPadStackOptions() + '</select>';
    //cell8.innerHTML = '<input type="text" name="guardRingPartialCut' + rowCount + '">';

    cell8.innerHTML = '<input type="checkbox" name="guardRingPartialCut' + rowCount + '">';

    //cell9.innerHTML = '<input type="text" name="guardRingSegment' + rowCount + '">';



    // Selectable Port Type (Single or Differential)
    cell9.innerHTML = '<select name="guardRingSegment' + rowCount + '">' +
        '<option value="0">0</option>' +
        '<option value="1">1</option>' +
        '<option value="2">2</option>' +
        '<option value="3">3</option>' +
        '<option value="4">4</option>' +
        '<option value="5">5</option>' +
        '<option value="6">6</option>' +
        '<option value="7">7</option>' +

        '</select>';


    cell10.innerHTML = '<input type="number" name="guardRingSpacing' + rowCount + '">';
    cell11.innerHTML = '<button onclick="deleteGuardRingRow(this)">Delete</button>';
}

function deleteGuardRingRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
}

function addDummyFillRow() {
    var table = document.getElementById('guardRingdummyFillTable').getElementsByTagName('tbody')[0];
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

    cell1.innerHTML = '<input type="text" name="dummyFillName' + rowCount + '">';
    //cell2.innerHTML = '<input type="text" name="dummyFillShape' + rowCount + '">';

    cell2.innerHTML = '<select name="dummyFillShape' + rowCount + '">' +
        '<option value="rect">rect</option>' +
        '</select>';


    cell3.innerHTML = '<input type="number" name="dummyFillLength' + rowCount + '">';
    cell4.innerHTML = '<input type="number" name="dummyFillHeight' + rowCount + '">';
    cell5.innerHTML = '<input type="number" name="dummyFillOffsetX' + rowCount + '">';
    cell6.innerHTML = '<input type="number" name="dummyFillOffsetY' + rowCount + '">';
    cell7.innerHTML = '<select name="dummyFillLayers' + rowCount + '" multiple>' + getLayerOptions() + '</select>';
    cell8.innerHTML = '<button onclick="deleteDummyFillRow(this)">Delete</button>';
}

function deleteDummyFillRow(btn) {
    var row = btn.parentNode.parentNode;
    row.parentNode.removeChild(row);
}

function getGuardRingJSON() {
    var guardRings = {};
    var dummyFills = {
        "type": "checkered", // Assuming type is fixed as in the JSON file.
        "groupSpacing": 2,  // Assuming groupSpacing is fixed as in the JSON file.
        "items": {}
    };


    //var guardRingDistanceValue = document.getElementById('guardRingDistance').value;
    var guardRingDistanceValue = parseInt(document.getElementById('guardRingDistance').value, 10);
    

    
    // Process guard ring table
    var guardRingTable = document.getElementById('guardRingTable').getElementsByTagName('tbody')[0];
    for (var i = 0, row; row = guardRingTable.rows[i]; i++) {
        var name = row.cells[0].getElementsByTagName('input')[0].value;
        var shape = row.cells[1].getElementsByTagName('select')[0].value;
        var offset = parseFloat(row.cells[2].getElementsByTagName('input')[0].value);
        var width = parseFloat(row.cells[3].getElementsByTagName('input')[0].value);
        var layer = row.cells[4].getElementsByTagName('select')[0].value;
        var contacts = row.cells[5].getElementsByTagName('input')[0].checked;
        var viaPadStack = row.cells[6].getElementsByTagName('select')[0].value;
        var partialCut = row.cells[7].getElementsByTagName('input')[0].checked;
        var segment = row.cells[8].getElementsByTagName('select')[0].value;
        var spacing = parseFloat(row.cells[9].getElementsByTagName('input')[0].value);



        guardRings[name] = {
            "shape": shape,
            "offset": offset,
            ...(width? { "width": width } : {}),
            "layer": layer,
            ...(contacts ? { "contacts": { "use": true, "viaStack": viaPadStack } } : {}),
            ...(partialCut ? { "partialCut": { "use": true, "segment": segment, "spacing": spacing } } : {})
        };

        // guardRings[name] = {
        //     "shape": shape,
        //     "offset": offset,
        //     ...(width !== null && width !== undefined ? { "width": width } : {}),
        //     "layer": layer,
        //     ...(contacts ? { "contacts": { "use": true, "viaStack": viaPadStack } } : {}),
        //     ...(partialCut ? { "partialCut": { "use": true, "segment": segment, "spacing": spacing } } : {})
        // };





        // guardRings[name] = {
        //     "shape": shape,
        //     "offset": offset,
        //     ...width !== null && { "width": width },
        //     "layer": layer,
        //     ...contacts && { "contacts": { "use": true, "viaStack": viaPadStack } },
        //     ...partialCut && { "partialCut": { "use": true, "segment": segment, "spacing": spacing } }
        // };


        // guardRings[name] = {
        //     "shape": shape,
        //     "offset": offset,
        //     "width": width,
        //     "layer": layer,
        //     "contacts": contacts ? { "use": true, "viaStack": viaPadStack } : null,
        //     "partialCut": partialCut ? { "use": true, "segment": segment, "spacing": spacing } : null
        // };

    }

    // Process dummy fill table
    var dummyFillTable = document.getElementById('guardRingdummyFillTable').getElementsByTagName('tbody')[0];
    for (var i = 0, row; row = dummyFillTable.rows[i]; i++) {
        var name = row.cells[0].getElementsByTagName('input')[0].value;
        var shape = row.cells[1].getElementsByTagName('select')[0].value;
        var length = parseFloat(row.cells[2].getElementsByTagName('input')[0].value);
        var height = parseFloat(row.cells[3].getElementsByTagName('input')[0].value);
        var offsetX = parseFloat(row.cells[4].getElementsByTagName('input')[0].value);
        var offsetY = parseFloat(row.cells[5].getElementsByTagName('input')[0].value);
        var layers = Array.from(row.cells[6].getElementsByTagName('select')[0].selectedOptions).map(option => option.value);

        dummyFills.items[name] = {
            "shape": shape,
            "length": length,
            "height": height,
            "offsetX": offsetX,
            "offsetY": offsetY,
            "layers": layers
        };
    }

    return {
        "guardRing": {
            "data": {
                "distance": guardRingDistanceValue,
                "segments": guardRings,
                "dummyFills": dummyFills
            }
        }
    };
}


function saveGuardRings() {
    var jsonData = {
        data: getGuardRingJSON(),
        savePath: projectDirectoryPath + '/' + document.getElementById('guardRingSavePath').value.trim(),
        saveName: document.getElementById('guardRingSaveName').value.trim()
    };

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
}

function loadGuardRings() {
    var guardRingJsonPath = document.getElementById('guardRingJsonPath').value.trim();

    loadJsonData(guardRingJsonPath,
        function (data) {
            populateGuardRingTable(data.guardRings);
            populateDummyFillTable(data.dummyFills);
            alert('JSON data loaded successfully!');
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
        }
    );
}

function populateGuardRingTable(guardRingsData) {
    var guardRingTable = document.getElementById('guardRingTable').getElementsByTagName('tbody')[0];
    guardRingTable.innerHTML = '';  // Clear existing table


    guardRingData = guardRingsData.data.segments;

    var guardRingDistance = guardRingsData?.data?.distance ?? null;
    document.getElementById('guardRingDistance').value = guardRingDistance; // Set the value to 10, for example



    Object.keys(guardRingData).forEach(function (key, index) {

        var data = guardRingData[key];

        
        var name = key ?? null;  // Assign the key itself to the name
        var shape = data?.shape ?? null;
        var offset = data?.offset ?? null;
        var width = data?.width ?? null;
        var layer = data?.layer ?? null;
        var contacts = data?.contacts ?? null;
        var contactsViaPadStack = data?.contacts?.viaStack ?? null;
        var partialCut = data?.partialCut ?? null;
        var partialCutSegment = data?.partialCut?.segment ?? null;
        var partialCutSpacing = data?.partialCut?.spacing ?? null;

        // Logging to verify
        console.log('Name:', name);
        console.log('Shape:', shape);
        console.log('Offset:', offset);
        console.log('Width:', width);
        console.log('Layer:', layer);
        console.log('Contacts:', contacts);
        console.log('Contacts Via Pad Stack:', contactsViaPadStack);
        console.log('Partial Cut:', partialCut);
        console.log('Partial Cut Segment:', partialCutSegment);
        console.log('Partial Cut Spacing:', partialCutSpacing);


        


        var newRow = guardRingTable.insertRow();

        var cell1 = newRow.insertCell(0);
        var cell2 = newRow.insertCell(1);
        var cell3 = newRow.insertCell(2);
        var cell4 = newRow.insertCell(3);
        var cell5 = newRow.insertCell(4);
        var cell6 = newRow.insertCell(5);
        var cell7 = newRow.insertCell(6);
        var cell8 = newRow.insertCell(7);
        var cell9 = newRow.insertCell(8);
        var cell10 = newRow.insertCell(9);
        var cell11 = newRow.insertCell(10);

        cell1.innerHTML = '<input type="text" name="guardRingName' + index + '" value="' + name + '">';
        cell2.innerHTML = '<select name="guardRingShape' + index + '">' +
            '<option value="hex"' + (shape === "hex" ? ' selected' : '') + '>hex</option>' +
            '<option value="hexRing"' + (shape === "hexRing" ? ' selected' : '') + '>hexRing</option>' +
            '</select>';




        cell3.innerHTML = '<input type="number" name="guardRingOffset' + index + '" value="' + offset + '">';

 
        cell4.innerHTML = `<input type="number" name="guardRingWidth${index}" ${width ? `value="${width}"` : ''}>`;


        //cell4.innerHTML = '<input type="number" name="guardRingWidth' + index + '" value="' + width + '">';
        

        cell5.innerHTML = '<select name="guardRingLayer' + index + '">' + getLayerOptions(layer) + '</select>';
        cell5.querySelector('select').value = layer;


        cell6.innerHTML = '<input type="checkbox" name="guardRingContacts' + index + '" ' + (contacts ? 'checked' : '') + '>';
        cell7.innerHTML = '<select name="guardRingContactsViaPadStack' + index + '">' + getViaPadStackOptions() + '</select>';
        if (contacts) {
            cell6.querySelector('input').checked = contacts;
            cell7.querySelector('select').value = contactsViaPadStack;
        }


        cell8.innerHTML = '<input type="checkbox" name="guardRingPartialCut' + index + '" ' + (partialCut ? 'checked' : '') + '>';
        cell9.innerHTML = '<select name="guardRingSegment' + index + '">' + 
        '<option value="0"' + (partialCutSegment == 0 ? ' selected' : '') + '>0</option>' +
        '<option value="1"' + (partialCutSegment == 1 ? ' selected' : '') + '>1</option>' +
        '<option value="2"' + (partialCutSegment == 2 ? ' selected' : '') + '>2</option>' +
        '<option value="3"' + (partialCutSegment == 3 ? ' selected' : '') + '>3</option>' +
        '<option value="4"' + (partialCutSegment == 4 ? ' selected' : '') + '>4</option>' +
        '<option value="5"' + (partialCutSegment == 5 ? ' selected' : '') + '>5</option>' +
        '<option value="6"' + (partialCutSegment == 6 ? ' selected' : '') + '>6</option>' +
        '<option value="7"' + (partialCutSegment == 7 ? ' selected' : '') + '>7</option>' +
        '</select>';

        cell10.innerHTML = `<input type="number" name="guardRingSpacing${index}" ${partialCutSpacing ? `value="${partialCutSpacing}"` : ''}>`;
        //cell10.innerHTML = '<input type="number" name="guardRingSpacing' + index + '" value="' + partialCutSpacing + '">';
        
        if (partialCut && shape === "hexRing"){
            cell8.querySelector('input').checked = partialCut;
            cell9.querySelector('select').value = partialCutSegment;
            cell10.querySelector('input').value = partialCutSpacing;

        }

        cell11.innerHTML = '<button onclick="deleteGuardRingRow(this)">Delete</button>';

    });
}


function populateDummyFillTable(dummyFillsData) {





    var dummyFillTable = document.getElementById('guardRingdummyFillTable').getElementsByTagName('tbody')[0];
    dummyFillTable.innerHTML = '';  // Clear existing table rows

    dummyFillData = dummyFillsData.data.dummyFills.items;

    Object.keys(dummyFillData).forEach(function (key, index) {

        var data = dummyFillData[key];

        var name = key ?? null;
        var shape = data?.shape ?? null;
        var length = data?.length ?? null;
        var height = data?.height ?? null;
        var offsetX = data?.offsetX ?? null;
        var offsetY = data?.offsetY ?? null;
        var layers = data?.layers ?? null;

        // // Logging to verify
        // console.log('Shape:', shape);
        // console.log('Length:', length);
        // console.log('Height:', height);
        // console.log('OffsetX:', offsetX);
        // console.log('OffsetY:', offsetY);
        // console.log('Layers:', layers);

        var newRow = dummyFillTable.insertRow();

        var cell1 = newRow.insertCell(0);
        var cell2 = newRow.insertCell(1);
        var cell3 = newRow.insertCell(2);
        var cell4 = newRow.insertCell(3);
        var cell5 = newRow.insertCell(4);
        var cell6 = newRow.insertCell(5);
        var cell7 = newRow.insertCell(6);
        var cell8 = newRow.insertCell(7);

        cell1.innerHTML = '<input type="text" name="dummyFillShape' + index + '" value="' + name + '">';
        cell2.innerHTML = '<select name="dummyFillShape' + index + '">' + 
        '<option value="rect"' + (shape === "rect" ? ' selected' : '') + '>rect</option>' +
        '</select>';

        cell3.innerHTML = '<input type="number" name="dummyFillLength' + index + '" value="' + length + '">';
        cell4.innerHTML = '<input type="number" name="dummyFillHeight' + index + '" value="' + height + '">';
        cell5.innerHTML = '<input type="number" name="dummyFillOffsetX' + index + '" value="' + offsetX + '">';
        cell6.innerHTML = '<input type="number" name="dummyFillOffsetY' + index + '" value="' + offsetY + '">';
        cell7.innerHTML = '<select name="dummyFillLayers' + index + '" multiple>' + getLayerOptions(layers) + '</select>';
        
        var layerSelect = cell7.querySelector('select');
        layers.forEach(function (layer) {
            for (var i = 0; i < layerSelect.options.length; i++) {
                if (layerSelect.options[i].value === layer) {
                    layerSelect.options[i].selected = true;
                    break;
                }
            }
        });


        cell8.innerHTML = '<button onclick="deleteDummyFillRow(this)">Delete</button>';

        // cell2.innerHTML = '<input type="number" name="dummyFillLength' + index + '" value="' + length + '">';
        // cell3.innerHTML = '<input type="number" name="dummyFillHeight' + index + '" value="' + height + '">';
        // cell4.innerHTML = '<input type="number" name="dummyFillOffsetX' + index + '" value="' + offsetX + '">';
        // cell5.innerHTML = '<input type="number" name="dummyFillOffsetY' + index + '" value="' + offsetY + '">';

        // // Create a select element for layers
        // var layerSelect = document.createElement('select');
        // layerSelect.name = 'dummyFillLayers' + index;
        // getLayerOptions().forEach(function (layer) {
        //     var option = document.createElement('option');
        //     option.value = layer;
        //     option.text = layer;
        //     if (layers.includes(layer)) {
        //         option.selected = true;
        //     }
        //     layerSelect.appendChild(option);
        // });

        // cell6.appendChild(layerSelect);

        // cell7.innerHTML = '<button onclick="deleteDummyFillRow(this)">Delete</button>';
    });
}



function updateDropdownsInGuardRing() {
    var guardRingTable = document.getElementById('guardRingTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');
    var dummyFillTable = document.getElementById('guardRingdummyFillTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    // Update dropdowns in guard ring table
    for (var i = 0; i < guardRingTable.length; i++) {
        var selectElementShape = guardRingTable[i].querySelector('select[name^="guardRingShape"]');
        var selectElementLayer = guardRingTable[i].querySelector('select[name^="guardRingLayer"]');
        var selectElementViaPadStack = guardRingTable[i].querySelector('select[name^="guardRingContactsViaPadStack"]');
        var selectElementSegment = guardRingTable[i].querySelector('select[name^="guardRingSegment"]');

        if (selectElementShape) {
            var currentValueShape = selectElementShape.value;
            selectElementShape.innerHTML = '<option value="hex">hex</option><option value="hexRing">hexRing</option>';
            selectElementShape.value = currentValueShape;  // Restore previous selection
        }

        if (selectElementLayer) {
            var currentValueLayer = selectElementLayer.value;
            selectElementLayer.innerHTML = getLayerOptions();
            selectElementLayer.value = currentValueLayer;  // Restore previous selection
        }

        if (selectElementViaPadStack) {
            var currentValueViaPadStack = selectElementViaPadStack.value;
            selectElementViaPadStack.innerHTML = getViaPadStackOptions();
            selectElementViaPadStack.value = currentValueViaPadStack;  // Restore previous selection
        }

        if (selectElementSegment) {
            var currentValueSegment = selectElementSegment.value;
            selectElementSegment.innerHTML = '<option value="0">0</option><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5</option><option value="6">6</option><option value="7">7</option>';
            selectElementSegment.value = currentValueSegment;  // Restore previous selection
        }
    }

    // Update dropdowns in dummy fill table
    for (var i = 0; i < dummyFillTable.length; i++) {
        var selectElementShape = dummyFillTable[i].querySelector('select[name^="dummyFillShape"]');
        var selectElementLayers = dummyFillTable[i].querySelector('select[name^="dummyFillLayers"]');

        if (selectElementShape) {
            var currentValueShape = selectElementShape.value;
            selectElementShape.innerHTML = '<option value="rect">rect</option>';
            selectElementShape.value = currentValueShape;  // Restore previous selection
        }

        if (selectElementLayers) {
            var currentValuesLayers = Array.from(selectElementLayers.selectedOptions).map(option => option.value);
            selectElementLayers.innerHTML = getLayerOptions();  // Assuming getLayerOptions returns the full set of layer options
            for (var j = 0; j < selectElementLayers.options.length; j++) {
                if (currentValuesLayers.includes(selectElementLayers.options[j].value)) {
                    selectElementLayers.options[j].selected = true;  // Restore previous selections
                }
            }
        }
    }
}


function updateFieldsetAvailability() {

    //const guardRingTable = document.getElementById('guardRingTable').getElementsByTagName('tbody')[0];
    const guardRingTable = document.getElementById('guardRingTable').getElementsByTagName('tbody')[0].getElementsByTagName('tr');


    for (let i=0; i < guardRingTable.length; i++) {

        const contacts = guardRingTable[i].querySelector('input[name^="guardRingContacts"]').checked;
        if (contacts) {
            guardRingTable[i].querySelector('select[name^="guardRingContactsViaPadStack"]').disabled = false;
        }
        else {
            guardRingTable[i].querySelector('select[name^="guardRingContactsViaPadStack"]').disabled = true;
        }


        const shape = guardRingTable[i].querySelector('select[name^="guardRingShape"]').value;
        const partialCutSelect = guardRingTable[i].querySelector('input[name^="guardRingPartialCut"]');
        const partialCutSegmentSelect = guardRingTable[i].querySelector('select[name^="guardRingSegment"]');
        const partialCutSpacingInput = guardRingTable[i].querySelector('input[name^="guardRingSpacing"]');

        if(shape === "hexRing"){
            partialCutSelect.disabled = false;

            if(partialCutSelect.checked){
                partialCutSegmentSelect.disabled = false;
                partialCutSpacingInput.disabled = false;
            }
            else {
                partialCutSegmentSelect.disabled = true;
                partialCutSpacingInput.disabled = true;
            }

        }
        else {
            partialCutSelect.disabled = true;
            partialCutSegmentSelect.disabled = true;
            partialCutSpacingInput.disabled = true;
        }
  
    }


}





// Initialize MutationObserver and input listener for guard ring table
function initializeGuardRingChangeObserver(handleChangeFunction) {
    const guardRingTable = document.getElementById('guardRingTable');
    const observer = new MutationObserver(function (mutationsList) {
        for (let mutation of mutationsList) {
            if (mutation.type === 'childList') {
                handleChangeFunction();
                return;
            }
        }
    });
    observer.observe(guardRingTable, { childList: true, subtree: true });
    guardRingTable.addEventListener('input', handleChangeFunction);
}

// Initialize MutationObserver and input listener for dummy fill table
function initializeDummyFillChangeObserver(handleChangeFunction) {
    const dummyFillTable = document.getElementById('guardRingdummyFillTable');
    const observer = new MutationObserver(function (mutationsList) {
        for (let mutation of mutationsList) {
            if (mutation.type === 'childList') {
                handleChangeFunction();
                return;
            }
        }
    });
    observer.observe(dummyFillTable, { childList: true, subtree: true });
    dummyFillTable.addEventListener('input', handleChangeFunction);
}

initializeGuardRingChangeObserver(updateArtworkTabsAvailability);
initializeDummyFillChangeObserver(updateArtworkTabsAvailability);
initializeLayerChangeObserver(updateDropdownsInGuardRing);
initializeViaPadStackChangeObserver(updateDropdownsInGuardRing);
initializeGuardRingChangeObserver(updateFieldsetAvailability);

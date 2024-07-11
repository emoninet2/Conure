// Function to generate the segment tables
function generateSegmentTables() {
    var numRows = parseInt(document.getElementById('numRings').value);

    // Check if numRows is 0 or negative
    if (numRows <= 0 || isNaN(numRows)) {
        return; // Exit function early if numRows is invalid
    }

    var segmentContainer = document.getElementById('segmentContainer');
    var existingTables = segmentContainer.querySelectorAll('table.ring-table');

    // Check if tables already exist and need to be updated
    var tablesToGenerate = 8; // Generate 8 tables as before
    var tablesToUpdate = Math.min(existingTables.length, tablesToGenerate);

    // Update existing tables or create new ones
    for (var i = 0; i < tablesToUpdate; i++) {
        var tbody = existingTables[i].getElementsByTagName('tbody')[0];
        var currentRows = tbody.getElementsByTagName('tr');
        var currentRowCount = currentRows.length;

        // Update rows if the number has changed
        if (currentRowCount !== numRows) {
            if (currentRowCount < numRows) {
                // Add rows if needed
                for (var j = currentRowCount + 1; j <= numRows; j++) {
                    var row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${i + 1}.${j}</td>
                        <td>
                            <select name="type${i + 1}${j}">
                                <option value="Default">Default</option>
                                <option value="Bridge">Bridge</option>
                                <option value="Port">Port</option>
                            </select>
                        </td>
                        <td>
                            <select name="layer${i + 1}${j}">
                                ${getLayerOptions()} 
                            </select>
                        </td>
                    `;
                    tbody.appendChild(row);
                }
            } else {
                // Remove rows if needed
                for (var j = currentRowCount; j > numRows; j--) {
                    tbody.removeChild(currentRows[j - 1]);
                }
            }
        }
    }

    // Generate new tables if necessary
    for (var i = tablesToUpdate; i < tablesToGenerate; i++) {
        var table = document.createElement('table');
        table.classList.add('ring-table');

        // Create table header
        var thead = document.createElement('thead');
        var headerRow = document.createElement('tr');
        headerRow.innerHTML = `<th>Segment ${i + 1}</th><th>Type</th><th>Layer</th>`;
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Create table body
        var tbody = document.createElement('tbody');
        for (var j = 1; j <= numRows; j++) {
            var row = document.createElement('tr');
            row.innerHTML = `
                <td>${i + 1}.${j}</td>
                <td>
                    <select name="type${i + 1}${j}">
                        <option value="Default">Default</option>
                        <option value="Bridge">Bridge</option>
                        <option value="Port">Port</option>
                    </select>
                </td>
                <td>
                    <select name="layer${i + 1}${j}">
                        ${getLayerOptions()} // Include -- Select Layer -- option
                    </select>
                </td>
            `;
            tbody.appendChild(row);
        }
        table.appendChild(tbody);

        // Append table to container
        segmentContainer.appendChild(table);
    }

    // Remove extra existing tables if there are too many
    for (var i = tablesToGenerate; i < existingTables.length; i++) {
        segmentContainer.removeChild(existingTables[i]);
    }

    // Restore state
    restoreSegmentState();
    updateTabsAvailability(); // Update tabs after generating tables
}



// Function to handle changes in numRings
function handleNumRingsChange() {
    generateSegmentTables(); // Regenerate tables when numRings changes
}



function updateSegmentDropdowns() {
    var layerNames = getLayerNames();
    var segmentTables = document.getElementById('segmentContainer').getElementsByTagName('table');
    for (var i = 0; i < segmentTables.length; i++) {
        var selectElements = segmentTables[i].querySelectorAll('select[name^="layer"]');
        for (var j = 0; j < selectElements.length; j++) {
            var currentValue = selectElements[j].value;
            selectElements[j].innerHTML = getLayerOptions();
            selectElements[j].value = currentValue;  // Restore previous selection
        }
    }
}

function saveSegmentState() {
    segmentState = [];
    var segmentTables = document.getElementById('segmentContainer').getElementsByTagName('table');
    for (var i = 0; i < segmentTables.length; i++) {
        var tableState = [];
        var rows = segmentTables[i].getElementsByTagName('tbody')[0].getElementsByTagName('tr');
        for (var j = 0; j < rows.length; j++) {
            var rowState = {
                type: rows[j].querySelector('input[name^="type"]').value,
                layer: rows[j].querySelector('select[name^="layer"]').value,
                jump: rows[j].querySelector('input[name^="jump"]').value,
                bridge: rows[j].querySelector('input[name^="bridge"]').value
            };
            tableState.push(rowState);
        }
        segmentState.push(tableState);
    }
}

function restoreSegmentState() {
    var segmentTables = document.getElementById('segmentContainer').getElementsByTagName('table');
    for (var i = 0; i < segmentTables.length && i < segmentState.length; i++) {
        var rows = segmentTables[i].getElementsByTagName('tbody')[0].getElementsByTagName('tr');
        for (var j = 0; j < rows.length && j < segmentState[i].length; j++) {
            var row = rows[j];
            var state = segmentState[i][j];
            row.querySelector('input[name^="type"]').value = state.type;
            row.querySelector('select[name^="layer"]').value = state.layer;
            row.querySelector('input[name^="jump"]').value = state.jump;
            row.querySelector('input[name^="bridge"]').value = state.bridge;
        }
    }
}

// Initialize
// Add event listener to numRings input
document.getElementById('numRings').addEventListener('change', handleNumRingsChange);
// Initial call to generate tables when the page loads
generateSegmentTables();


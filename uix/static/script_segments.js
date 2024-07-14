document.addEventListener("DOMContentLoaded", function () {
    // Attach the change event to numRings input
    document.getElementById('numRings').addEventListener('change', generateSegmentTables);
});

function generateSegmentTables() {
    const numRings = parseInt(document.getElementById('numRings').value) || 0;
    const segmentTableContainer = document.getElementById('segmentTable');

    // Clear previous tables
    segmentTableContainer.innerHTML = '';

    // Create 8 tables
    for (let i = 0; i < 8; i++) {
        const table = document.createElement('table');
        table.id = `segmentTable${i + 1}`;
        table.style.marginBottom = '20px';

        // Create table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        ['Type', 'Layer', 'Jump', 'Bridge', 'Action'].forEach(text => {
            const th = document.createElement('th');
            th.innerText = text;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Create table body
        const tbody = document.createElement('tbody');
        for (let j = 0; j < numRings; j++) {
            const row = document.createElement('tr');

            // Create the dropdown for 'type'
            const typeTd = document.createElement('td');
            const select = document.createElement('select');
            select.name = `type${i + 1}_${j + 1}`;
            ['DEFAULT', 'BRIDGE', 'PORT'].forEach(optionValue => {
                const option = document.createElement('option');
                option.value = optionValue;
                option.innerText = optionValue;
                select.appendChild(option);
            });
            typeTd.appendChild(select);
            row.appendChild(typeTd);

            // Create the dropdown for 'layer'
            const layerTd = document.createElement('td');
            const layerSelect = document.createElement('select');
            layerSelect.name = `layer${i + 1}_${j + 1}`;
            layerSelect.innerHTML = getLayerOptions(false);  // Generate options as HTML
            layerTd.appendChild(layerSelect);
            row.appendChild(layerTd);

            // Create input field for 'jump'
            const jumpTd = document.createElement('td');
            const jumpInput = document.createElement('input');
            jumpInput.type = 'number';
            jumpInput.name = `jump${i + 1}_${j + 1}`;
            jumpTd.appendChild(jumpInput);
            row.appendChild(jumpTd);

            // Create the dropdown for 'bridge'
            const bridgeTd = document.createElement('td');
            const bridgeSelect = document.createElement('select');
            bridgeSelect.name = `bridge${i + 1}_${j + 1}`;
            bridgeSelect.innerHTML = getBridgeOptions(false);  // Generate options as HTML
            bridgeTd.appendChild(bridgeSelect);
            row.appendChild(bridgeTd);

            // Add action cell for delete button
            const actionTd = document.createElement('td');
            const deleteButton = document.createElement('button');
            deleteButton.innerText = 'Delete';
            deleteButton.onclick = function () {
                const row = this.parentNode.parentNode;
                row.parentNode.removeChild(row);
            };
            actionTd.appendChild(deleteButton);
            row.appendChild(actionTd);

            tbody.appendChild(row);
        }
        table.appendChild(tbody);

        // Append table to the container
        segmentTableContainer.appendChild(table);
    }
}


// Function to update dropdowns in segment tables
function updateDropdownsInSegment() {
    var segmentTables = document.getElementById('segmentTable').getElementsByTagName('table');

    for (var i = 0; i < segmentTables.length; i++) {
        var rows = segmentTables[i].getElementsByTagName('tbody')[0].getElementsByTagName('tr');

        for (var j = 0; j < rows.length; j++) {
            // Update layer select elements
            var layerSelect = rows[j].querySelector('select[name^="layer"]');
            if (layerSelect) {
                var currentValue = layerSelect.value;
                layerSelect.innerHTML = getLayerOptions();  // Generate options as HTML
                layerSelect.value = currentValue;  // Restore previous selection
            }

            // Update bridge select elements
            var bridgeSelect = rows[j].querySelector('select[name^="bridge"]');
            if (bridgeSelect) {
                var currentValue = bridgeSelect.value;
                bridgeSelect.innerHTML = getBridgeOptions();  // Generate options as HTML
                bridgeSelect.value = currentValue;  // Restore previous selection
            }
        }
    }
}

initializeLayerChangeObserver(updateDropdownsInSegment);
initializeBridgeChangeObserver(updateDropdownsInSegment);





document.addEventListener("DOMContentLoaded", function () {
    document.getElementById('numRings').addEventListener('change', function () {
        generateSegmentTables();
        updateDropdownsInSegment();  // Ensure dropdowns are updated after generating tables
    });
});

function generateSegmentTables() {
    const numRings = parseInt(document.getElementById('numRings').value) || 0;
    const segmentTableContainer = document.getElementById('segmentTable');

    // Store current values
    const currentValues = {};
    for (let i = 0; i < 8; i++) {
        const table = document.getElementById(`segmentTable${i + 1}`);
        if (table) {
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            for (let j = 0; j < rows.length; j++) {
                currentValues[`type${i + 1}_${j + 1}`] = rows[j].querySelector(`select[name="type${i + 1}_${j + 1}"]`).value;
                currentValues[`layer${i + 1}_${j + 1}`] = rows[j].querySelector(`select[name="layer${i + 1}_${j + 1}"]`).value;
                currentValues[`jump${i + 1}_${j + 1}`] = rows[j].querySelector(`input[name="jump${i + 1}_${j + 1}"]`).value;
                currentValues[`bridgeArm${i + 1}_${j + 1}`] = rows[j].querySelector(`select[name="bridgeArm${i + 1}_${j + 1}"]`).value;
            }
        }
    }

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
        ['Type', 'Layer', 'Jump', 'Bridge/Arm', 'Action'].forEach(text => {
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
            select.value = currentValues[`type${i + 1}_${j + 1}`] || 'DEFAULT';
            select.addEventListener('change', function () {
                updateDropdownsInSegment();
            });
            typeTd.appendChild(select);
            row.appendChild(typeTd);

            // Create the dropdown for 'layer'
            const layerTd = document.createElement('td');
            const layerSelect = document.createElement('select');
            layerSelect.name = `layer${i + 1}_${j + 1}`;
            layerSelect.innerHTML = getLayerOptions(false);  // Generate options as HTML
            layerSelect.value = currentValues[`layer${i + 1}_${j + 1}`] || '';
            layerTd.appendChild(layerSelect);
            row.appendChild(layerTd);

            // Create input field for 'jump'
            const jumpTd = document.createElement('td');
            const jumpInput = document.createElement('input');
            jumpInput.type = 'number';
            jumpInput.name = `jump${i + 1}_${j + 1}`;
            jumpInput.value = currentValues[`jump${i + 1}_${j + 1}`] || '';
            jumpTd.appendChild(jumpInput);
            row.appendChild(jumpTd);

            // Create the dropdown for 'bridge/arm'
            const bridgeArmTd = document.createElement('td');
            const bridgeArmSelect = document.createElement('select');
            bridgeArmSelect.name = `bridgeArm${i + 1}_${j + 1}`;
            bridgeArmTd.appendChild(bridgeArmSelect);
            row.appendChild(bridgeArmTd);

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
    updateDropdownsInSegment();
}


function saveSegments() {
    var segments = {
        config: {
            bridge_extension_aligned: true
        },
        data: {}
    };

    var segmentTables = document.getElementById('segmentTable').getElementsByTagName('table');

    for (var i = 0; i < segmentTables.length; i++) {
        var segmentId = `S${i}`;
        segments.data[segmentId] = {
            id: i,
            group: []
        };

        var rows = segmentTables[i].getElementsByTagName('tbody')[0].getElementsByTagName('tr');

        for (var j = 0; j < rows.length; j++) {
            var typeSelect = rows[j].querySelector('select[name^="type"]').value;
            var layerSelect = rows[j].querySelector('select[name^="layer"]').value;
            var jumpInput = rows[j].querySelector('input[name^="jump"]').value;
            var bridgeArmSelect = rows[j].querySelector('select[name^="bridgeArm"]').value;

            var groupItem = {
                type: typeSelect,
                data: {
                    layer: layerSelect
                }
            };

            if (typeSelect === 'BRIDGE') {
                groupItem.data.jump = parseInt(jumpInput) || 0;
                groupItem.data.bridge = bridgeArmSelect;
            } else if (typeSelect === 'PORT') {
                groupItem.data.arm = bridgeArmSelect;
            }

            segments.data[segmentId].group.push(groupItem);
        }
    }

    // Prepare data to send to Flask
    var jsonData = {
        data: { segments: segments },
        savePath: document.getElementById('segmentsSavePath').value.trim(),
        saveName: document.getElementById('segmentsSaveName').value.trim()
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


function loadSegments() {
    var segmentJsonPath = document.getElementById('segmentsJsonPath').value.trim();

    loadJsonData(segmentJsonPath,
        function (data) {
            populateSegmentTable(data.segments);
            alert('JSON data loaded successfully!');
            updateTabsAvailability(); // Update tabs after loading data
        },
        function (errorMessage) {
            alert('Error loading JSON data:\n' + JSON.stringify(errorMessage));
            updateTabsAvailability(); // Update tabs on error
        }
    );
}

function populateSegmentTable(segments) {
    var numRings = 0;
    for (var key in segments.data) {
        if (segments.data.hasOwnProperty(key)) {
            var numRows = segments.data[key].group.length;
            if (numRows > numRings) {
                numRings = numRows;
            }
        }
    }

    document.getElementById('numRings').value = numRings;
    generateSegmentTables(); // Ensure the tables are generated with the correct number of rings

    var segmentTables = document.getElementById('segmentTable').getElementsByTagName('table');

    for (var i = 0; i < segmentTables.length; i++) {
        var segmentId = `S${i}`;
        if (segments.data.hasOwnProperty(segmentId)) {
            var rows = segmentTables[i].getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            var group = segments.data[segmentId].group;

            for (var j = 0; j < group.length; j++) {
                if (rows[j]) {
                    var typeSelect = rows[j].querySelector('select[name^="type"]');
                    var layerSelect = rows[j].querySelector('select[name^="layer"]');
                    var jumpInput = rows[j].querySelector('input[name^="jump"]');
                    var bridgeArmSelect = rows[j].querySelector('select[name^="bridgeArm"]');

                    typeSelect.value = group[j].type;
                    layerSelect.value = group[j].data.layer;

                    if (group[j].type === 'BRIDGE') {
                        jumpInput.value = group[j].data.jump || 0;
                        bridgeArmSelect.innerHTML = getBridgeOptions(false);
                        bridgeArmSelect.value = group[j].data.bridge || '';
                    } else if (group[j].type === 'PORT') {
                        jumpInput.value = '';
                        bridgeArmSelect.innerHTML = getArmOptions(false);
                        bridgeArmSelect.value = group[j].data.arm || '';
                    } else {
                        jumpInput.value = '';
                        bridgeArmSelect.innerHTML = '<option value="">-- N/A --</option>';
                    }
                }
            }
        }
    }
   
}

function updateDropdownsInSegment() {
    var segmentTables = document.getElementById('segmentTable').getElementsByTagName('table');

    for (var i = 0; i < segmentTables.length; i++) {
        var rows = segmentTables[i].getElementsByTagName('tbody')[0].getElementsByTagName('tr');

        for (var j = 0; j < rows.length; j++) {
            // Update layer select elements
            var layerSelect = rows[j].querySelector('select[name^="layer"]');
            if (layerSelect) {
                var currentLayerValue = layerSelect.value;
                layerSelect.innerHTML = getLayerOptions(false);  // Generate options as HTML
                layerSelect.value = currentLayerValue;  // Restore previous selection
            }

            // Update bridge/arm select elements based on type
            var typeSelect = rows[j].querySelector('select[name^="type"]');
            var bridgeArmSelect = rows[j].querySelector('select[name^="bridgeArm"]');
            if (typeSelect.value === 'BRIDGE') {
                var currentBridgeValue = bridgeArmSelect.value;
                bridgeArmSelect.innerHTML = getBridgeOptions(false);
                bridgeArmSelect.value = currentBridgeValue;  // Restore previous selection
            } else if (typeSelect.value === 'PORT') {
                var currentArmValue = bridgeArmSelect.value;
                bridgeArmSelect.innerHTML = getArmOptions(false);
                bridgeArmSelect.value = currentArmValue;  // Restore previous selection
            } else {
                bridgeArmSelect.innerHTML = '<option value="">-- N/A --</option>';
            }
        }
    }
}


initializeLayerChangeObserver(updateDropdownsInSegment);
initializeBridgeChangeObserver(updateDropdownsInSegment);
initializeArmChangeObserver(updateDropdownsInSegment);
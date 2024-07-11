    // Function to add a new row to the Via table
    function addViaRow() {
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
        cell1.innerHTML = '<input type="text" name="viaName' + rowCount + '">';
        cell2.innerHTML = '<input type="number" name="viaLength' + rowCount + '">';
        cell3.innerHTML = '<input type="number" name="viaWidth' + rowCount + '">';
        cell4.innerHTML = '<input type="number" name="viaSpacing' + rowCount + '">';
        cell5.innerHTML = '<input type="number" name="viaAngle' + rowCount + '">';
        cell6.innerHTML = '<select name="viaLayer' + rowCount + '">' + getLayerOptions() + '</select>';  cell7.innerHTML = '<button onclick="deleteViaRow(this)">Delete</button>';
    }

    // Function to delete a Via table row (similar to deleteRow in script_layers.js)
    function deleteViaRow(btn) {
        var row = btn.parentNode.parentNode;
        row.parentNode.removeChild(row);
    }
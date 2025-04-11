

function getParamJSON() {

    var apothem = parseFloat(document.getElementById('apothem').value);
    var condWidth = parseFloat(document.getElementById('condWidth').value);
    var condSpacing = parseFloat(document.getElementById('condSpacing').value);


    var parameters = {
        "name": projectName,
        "class": "Spiral",
        "type": "Coplanar",
        "corners": 8,
        "rings": 4,
        "apothem": apothem,
        "width": condWidth,
        "spacing": condSpacing,
        "precision": 0.005,
        "outputDir": "./ARTWORK"
    };

    return { "parameters": parameters };
}


function populateParamTable(paramData) {

    var apothem = paramData.apothem;
    var condWidth = paramData.width;
    var condSpacing = paramData.spacing;

    document.getElementById('apothem').value = apothem;

    document.getElementById('condWidth').value = condWidth;

    document.getElementById('condSpacing').value = condSpacing;

    // Add one empty row at the end for adding new entries
    //addLayerRow();

    //updateArtworkTabsAvailability(); // Update tabs after populating layers
}
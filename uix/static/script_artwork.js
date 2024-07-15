
var tabButton = {};

tabButton.segment = document.getElementById('btn-sel-artwork-segment');
tabButton.arms = document.getElementById('btn-sel-artwork-arms');
tabButton.ports = document.getElementById('btn-sel-artwork-ports');
tabButton.bridges = document.getElementById('btn-sel-artwork-bridges');
tabButton.viaPadStack = document.getElementById('btn-sel-artwork-viaPadStack');
tabButton.via = document.getElementById('btn-sel-artwork-via');
tabButton.guardRing = document.getElementById('btn-sel-artwork-guardRing');
tabButton.layers = document.getElementById('btn-sel-artwork-layers');


// JavaScript to handle sub-tab visibility
document.addEventListener("DOMContentLoaded", function () {
    // Initially hide all sub-tab contents except for "Layers"
    var subTabs = document.getElementsByClassName('sub-tab-content');
    for (var i = 0; i < subTabs.length; i++) {
        // if (subTabs[i].id !== 'layers') {
        //     subTabs[i].style.display = 'none';
        // }

        subTabs[i].style.display = 'none';

    }
});

function showSubTab(subTabName) {
    var subTabs = document.getElementsByClassName('sub-tab-content');
    for (var i = 0; i < subTabs.length; i++) {
        subTabs[i].style.display = 'none';
    }
    document.getElementById(subTabName).style.display = 'block';


    for (var key in tabButton) {
        if (tabButton[key]) {
            tabButton[key].classList.remove('active-tab');
        }
    }



    switch (subTabName) {
        case 'segment':
            // Code for segment sub-tab
            tabButton.segment.classList.add('active-tab');
            break;
        case 'arms':
            // Code for arms sub-tab
            tabButton.arms.classList.add('active-tab');
            break;
        case 'ports':
            // Code for ports sub-tab
            tabButton.ports.classList.add('active-tab');
            break;
        case 'bridges':
            // Code for bridges sub-tab
            tabButton.bridges.classList.add('active-tab');
            break;
        case 'viaPadStack':
            // Code for viaPadStack sub-tab
            tabButton.viaPadStack.classList.add('active-tab');
            break;
        case 'via':
            // Code for via sub-tab
            tabButton.via.classList.add('active-tab');
            break;
        case 'guardRing':
            // Code for guardRing sub-tab
            tabButton.guardRing.classList.add('active-tab');
            break;
        case 'layers':
            // Code for layers sub-tab
            tabButton.layers.classList.add('active-tab');
            break;
        default:
            // Code for default case
            break;
    }
}


function updateTabsAvailability() {




    var layersTable = document.getElementById('layersTable').getElementsByTagName('tbody')[0];
    var viaTable = document.getElementById('viaTable').getElementsByTagName('tbody')[0];
    var isLayersEmpty = layersTable.rows.length === 0;
    var isViaEmpty = viaTable.rows.length === 0;

    var tabsToDisable = ['segment', 'arms', 'ports', 'bridges', 'viaPadStack', 'via', 'guardRing'];

    tabsToDisable.forEach(function (tabName) {
        var tabButton = document.querySelector(`button[onclick="showSubTab('${tabName}')"]`);
        if (tabButton) {
            if (isLayersEmpty) {
                tabButton.disabled = true;
            } else {
                tabButton.disabled = false;
            }
        }
    });








}
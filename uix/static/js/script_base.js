var tabButtonsMainPane = {};

tabButtonsMainPane.project = document.getElementById('btn-sel-project');
tabButtonsMainPane.artwork = document.getElementById('btn-sel-artwork');
tabButtonsMainPane.simulate = document.getElementById('btn-sel-simulate');
tabButtonsMainPane.sweep = document.getElementById('btn-sel-sweep');
tabButtonsMainPane.about = document.getElementById('btn-sel-about');


function showTab(tabName) {
    var tabs = document.getElementsByClassName('tab-content');
    for (var i = 0; i < tabs.length; i++) {
        tabs[i].classList.remove('active');
    }
    document.getElementById(tabName).classList.add('active');

    for (var key in tabButtonsMainPane) {
        if (tabButtonsMainPane[key]) {
            tabButtonsMainPane[key].classList.remove('active-tab');
        }
    }



    switch (tabName) {
        case 'project':
            // Code for segment sub-tab
            tabButtonsMainPane.project.classList.add('active-tab');
            break;
        case 'artwork':
            // Code for arms sub-tab
            tabButtonsMainPane.artwork.classList.add('active-tab');
            break;
        case 'simulate':
            // Code for ports sub-tab
            tabButtonsMainPane.simulate.classList.add('active-tab');
            break;
        case 'sweep':
            // Code for ports sub-tab
            tabButtonsMainPane.sweep.classList.add('active-tab');
            break;
        case 'about':
            // Code for ports sub-tab
            tabButtonsMainPane.about.classList.add('active-tab');
            break;
        default:
            // Code for default case
            break;
    }



}
var projectDirectoryPath = '';
var projectName = '';


const PUBLIC_SESSION = false


const layersTable = document.getElementById('layersTable');


function deleteFile(filePath) {
    const formData = new FormData();
    formData.append('filePath', filePath);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/delete_file', true);
    xhr.onload = function () {
        if (xhr.status === 200) {
            //alert('File deleted successfully');
        } else {
            alert('File deletion failed');
        }
    };

    xhr.send(formData);
}


function downloadJSON(json, filename) {
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}
const layersTable = document.getElementById('layersTable');


function deleteFile(filePath) {
    const formData = new FormData();
    formData.append('filePath', filePath);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/delete_file', true);
    xhr.onload = function () {
        if (xhr.status === 200) {
            alert('File deleted successfully');
        } else {
            alert('File deletion failed');
        }
    };

    xhr.send(formData);
}
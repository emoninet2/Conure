async function preview() {
    const ADF = projectDirectoryPath + "/ARD.json";
    const outputPath = projectDirectoryPath + "/temp/OUTPUT";
    const outputName = projectName;
    const svgFilePath = `${outputPath}/${outputName}.svg`;

    try {
        const response = await fetch('/generate_preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ ADF, outputPath, outputName }),
        });

        const data = await response.json();

        if (data.status === 'success') {
            // Expand the path on the client side if necessary
            const expandedSvgFilePath = svgFilePath.replace('~', '/Users/habiburrahman'); // Replace with the correct home directory

            const svgResponse = await fetch(`/get_svg?path=${expandedSvgFilePath}`);
            const svgText = await svgResponse.text();

            const previewDiv = document.getElementById('svg-preview');
            if (!previewDiv) {
                throw new Error('Preview div not found');
            }
            previewDiv.innerHTML = svgText;
            previewDiv.style.display = 'block'; // Ensure the preview div is visible

            // Optionally delete the SVG file after displaying it
            // const deleteResponse = await fetch('/delete_file', {
            //     method: 'POST',
            //     headers: {
            //         'Content-Type': 'application/x-www-form-urlencoded',
            //     },
            //     body: new URLSearchParams({
            //         filePath: expandedSvgFilePath
            //     }),
            // });

            // if (deleteResponse.ok) {
            //     console.log('File deleted successfully');
            // } else {
            //     console.error('Failed to delete file');
            // }
        } else {
            console.error('Error generating preview:', data.error);
        }
    } catch (error) {
        console.error('Error during preview generation:', error);
    }
}

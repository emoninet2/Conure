async function preview() {
    
    const outputPath = projectDirectoryPath + "/temp/preview/";
    const outputName = projectName;
    

    saveArtworkDescriptionData(outputPath, outputName + ".json");

    const ADF = projectDirectoryPath + "/temp/preview/" + projectName + ".json";

    try {
        const response = await fetch('/generate_preview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ ADF, outputPath, outputName }),
        });

        const data = await response.json();

        const svgFilePath = `${outputPath}/${outputName}.svg`;

        if (data.status === 'success') {
            // No need to expand the path on the client side
            const svgResponse = await fetch(`/get_svg?path=${svgFilePath}`);
            const svgText = await svgResponse.text();

            const previewDiv = document.getElementById('svg-preview');
            console.log('Preview Div:', previewDiv); // Debugging log
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
            //         filePath: svgFilePath
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

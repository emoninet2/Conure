async function preview() {
    const outputPath = projectDirectoryPath + "/temp/preview";
    const outputName = projectName;

    saveArtworkDescriptionData(outputPath, outputName + ".json");

    const ADF = projectDirectoryPath + "/temp/preview/" + projectName + ".json";

    try {
        // Display the "generating preview" message
        const previewDiv = document.getElementById('svg-preview');
        if (!previewDiv) {
            throw new Error('Preview div not found');
        }
        previewDiv.innerHTML = "Generating preview, please wait...";
        previewDiv.style.display = 'block'; // Ensure the preview div is visible

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
            const svgResponse = await fetch(`/get_svg?path=${svgFilePath}`);
            const svgText = await svgResponse.text();

            previewDiv.innerHTML = svgText;

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
            previewDiv.innerHTML = 'Error generating preview';
        }
    } catch (error) {
        console.error('Error during preview generation:', error);
        const previewDiv = document.getElementById('svg-preview');
        if (previewDiv) {
            previewDiv.innerHTML = 'Error during preview generation';
        }
    }
}
function generateSteps(from, to, stepSize) {
    let steps = [];
    for (let value = from; value <= to; value += stepSize) {
        steps.push(parseFloat(value.toFixed(2)));
    }
    return steps;
}

function getSweepJSON() {
    const apothemFrom = parseFloat(document.getElementById('apothemFrom').value);
    const apothemTo = parseFloat(document.getElementById('apothemTo').value);
    const apothemStep = parseFloat(document.getElementById('apothemStep').value);

    const widthFrom = parseFloat(document.getElementById('widthFrom').value);
    const widthTo = parseFloat(document.getElementById('widthTo').value);
    const widthStep = parseFloat(document.getElementById('widthStep').value);

    const spacingFrom = parseFloat(document.getElementById('spacingFrom').value);
    const spacingTo = parseFloat(document.getElementById('spacingTo').value);
    const spacingStep = parseFloat(document.getElementById('spacingStep').value);

    const parameters = {
        apothem: generateSteps(apothemFrom, apothemTo, apothemStep),
        width: generateSteps(widthFrom, widthTo, widthStep),
        spacing: generateSteps(spacingFrom, spacingTo, spacingStep)
    };

    const json = JSON.stringify({ parameters }, null, 4);
    return json;
    downloadJSON(json, 'parameters.json');
    return json;
    
}



async function sweep() {
    // Ensure uniqueSweepName is initialized
    var uniqueSweepName = new Date().getTime();
    var outputPath = projectDirectoryPath + "/sweep/" + uniqueSweepName;
    // Get the JSON data for the sweep
    var json = getSweepJSON();
    var enableSimulation = document.getElementById('enableSimulation').checked;

    // Construct the data to be sent to the server
    var flaskJsonData = {
        data: JSON.parse(json),
        savePath: outputPath,
        saveName: "sweep.json"
    };

    // Call saveJsonData to save the JSON data
    saveJsonData(
        flaskJsonData,
        '/save_json',
        function () {
            // Handle success
            console.log("Data saved successfully.");
        },
        function (errorMessage) {
            // Handle error
            alert(errorMessage);
            console.error("Error saving data:", errorMessage);
            // Optionally handle further error logic here
        }
    );

    const sweepConfigPath = outputPath + "/" + "sweep.json";
    const ADFPath = projectDirectoryPath + "/" + projectName + ".json";
    const statusPath = outputPath + "/status.json";

    // Function to fetch and print status.json content
    async function fetchStatus() {
        try {
            const response = await fetch('/load_json', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ path: statusPath }),
            });

            if (response.ok) {
                const result = await response.json();
                if (result.success) {
                    console.log("Current status:", result.data);
                    document.getElementById('statusContent').textContent = JSON.stringify(result.data, null, 2);

                    // Update progress bar
                    const totalPermutations = result.data.total_permutations;
                    const completedRuns = result.data.completed_runs;
                    const progressPercentage = (completedRuns / totalPermutations) * 100;

                    document.getElementById('progressBar').style.width = progressPercentage + '%';
                    document.getElementById('progressText').textContent = `Progress: ${completedRuns} / ${totalPermutations} (${progressPercentage.toFixed(2)}%)`;
                } else {
                    console.error("Error loading status:", result.message);
                }
            } else {
                console.error("Failed to fetch status:", response.statusText);
            }
        } catch (error) {
            console.error("Error during status fetch:", error);
        }
    }

    // Start fetching status every 5 seconds
    const statusInterval = setInterval(fetchStatus, 5000);

    try {
        const response = await fetch('/sweep_generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ ADFPath, enableSimulation, sweepConfigPath, outputPath, uniqueSweepName }),
        });

        if (response.ok) {
            // Handle sweep generation success
            console.log("Sweep generation completed successfully.");
        } else {
            console.error("Sweep generation failed:", response.statusText);
        }
    }
    catch (error) {
        console.error('Error during sweep generation:', error);
    }
    finally {
        // Stop fetching status after sweep generation is complete
        clearInterval(statusInterval);

        // Fetch status one final time to update progress bar to 100%
        await fetchStatus();
    }
}

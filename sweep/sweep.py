import argparse
import os
import shlex
import json
import sys
import itertools
import copy
import subprocess
import time
import json
import numpy as np
import skrf as rf
import glob




#CONURE_PATH = os.environ.get('CONURE_PATH')
CONURE_PATH = "/home/emon/projects/Conure"


if CONURE_PATH is None:
    print("CONURE_PATH is not set!")
else:
    print(f"CONURE_PATH is set to: {CONURE_PATH}")

ARTWORK_GENERATOR_PATH = os.path.join(CONURE_PATH, "artwork_generator", "artwork_generator.py")
SIMULATOR_PATH = os.path.join(CONURE_PATH, "simulator", "simulate.py")



def sweep(simulator, artworkData, sweepParam, simulatorConfig, outputDir, outputName, enableLayoutGeneration, generateSVG, enableSimulation, packSimulationResults):

    sweepPar = []
    sweepData = []
    for param, paramSweepData in sweepParam["parameters"].items():
        sweepPar.append(param)
        sweepData.append(paramSweepData)

    permutations = itertools.product(*sweepData)

    # Calculate and print the total number of permutations
    total_permutations = len(list(itertools.product(*sweepData)))
    print("Total number of permutations:", total_permutations)

    status = {
        "total_permutations": total_permutations,
        "completed_runs": 0,
        "status_message": ''
    }

    STATUS_FILE_PATH = os.path.join(outputDir, "status.json")

    RunID = 0
    completedRuns = 0
    for permutation in permutations:

        InductorDataX = copy.deepcopy(artworkData)
        InductorDataX["parameters"]["outputDir"] = outputDir + \
            "/RunID_" + "{:04d}".format(RunID)
        # InductorDataX["parameters"]["outputDir"] +=  "/RunID_" + "{:04d}".format(RunID)

        if outputName == None:
            InductorDataX["parameters"]["name"] += "_RunID_" + \
                "{:04d}".format(RunID)
        else:
            InductorDataX["parameters"]["name"] = outputName
            InductorDataX["parameters"]["name"] += "_RunID_" + \
                "{:04d}".format(RunID)

        print(InductorDataX["parameters"]["name"] + "\r\nRUN ID: " +
              str(RunID) + "\r\n" + str(permutation) + "\r\n")

        if os.path.exists(InductorDataX["parameters"]["outputDir"] + "/parameters.json"):
            RunID += 1

        else:
            runData = {
                "runID": RunID,
                "parameters": {},
            }

            TotalRuns = len(permutation)
            # print(TotalRuns)
            for i in range(TotalRuns):
                InductorDataX["parameters"][sweepPar[i]] = permutation[i]
                # used to just write as a text file of the parameter value
                runData["parameters"][sweepPar[i]] = permutation[i]

            runData["parameters"]["rings"] = InductorDataX["parameters"]["rings"]
            runDataJSON = json.dumps(runData)

            if not os.path.exists(InductorDataX["parameters"]["outputDir"]):
                os.makedirs(InductorDataX["parameters"]["outputDir"])

            with open(InductorDataX["parameters"]["outputDir"] + "/parameters.json", "w") as parfile:
                parfile.write(runDataJSON)

            RunID += 1

        portCount = len(InductorDataX["ports"]["config"]["simulatingPorts"])
        gdsPath = InductorDataX["parameters"]["outputDir"] + \
            "/" + InductorDataX["parameters"]["name"] + ".gds"
        sParamPath = InductorDataX["parameters"]["outputDir"] + "/" + \
            InductorDataX["parameters"]["name"] + ".s" + str(portCount) + "p"
        yParamPath = InductorDataX["parameters"]["outputDir"] + "/" + \
            InductorDataX["parameters"]["name"] + ".s" + str(portCount) + "p"

        if (enableLayoutGeneration or enableSimulation) and not os.path.exists(gdsPath):

            status["status_message"] = f"Generating Artwork for RunID: {RunID}"
            with open(STATUS_FILE_PATH, "w") as status_file:
                json.dump(status, status_file, indent=4)

            print("Generating layout for RunID ", RunID)
            # Define the command as a list of arguments, including the JSON content

            command = [
                "python",
                ARTWORK_GENERATOR_PATH,
                # Pass the JSON content directly
                "-a", json.dumps(InductorDataX),
                "-o", InductorDataX["parameters"]["outputDir"],
                "-n", InductorDataX["parameters"]["name"],
            ]

            if (generateSVG):
                command.append("--svg")

            # print(command)
            process = subprocess.run(command)
            # command_list = shlex.split(command)
            # print(command_list)

            # Use subprocess to run the command
            # process = subprocess.Popen(
            #    command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # # Capture the output and error
            # stdout, stderr = process.communicate()

            # Check the return code to see if the process was successful
            return_code = process.returncode

            if return_code == 0:
                print("Layout generation completed successfully.")
            else:
                print(f"Script failed with return code {return_code}")
                print("Error output:")
                # print(stderr.decode('utf-8'))

        if enableSimulation and os.path.exists(gdsPath) and not os.path.exists(sParamPath):

            status["status_message"] = f"Performing EM simulation for RunID: {
                RunID}"
            with open(STATUS_FILE_PATH, "w") as status_file:
                json.dump(status, status_file, indent=4)

            print("Performing EM simulation for RunID ", RunID)
            json_content = json.dumps(InductorDataX)

            command = [
                "python",
                SIMULATOR_PATH,
                "-f", gdsPath,
                "-a", json.dumps(InductorDataX),
                "-c", simulatorConfig,
                "--sim", simulator,
                "-o", InductorDataX["parameters"]["outputDir"],
                "-n", InductorDataX["parameters"]["name"]
            ]

            process = subprocess.run(command)

            # process = subprocess.Popen(
            #     command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # # Capture the output and error
            # stdout, stderr = process.communicate()

            # Check the return code to see if the process was successful
            return_code = process.returncode

            if return_code == 0:
                print("EM simulation completed successfully.")
                if os.path.exists(sParamPath):
                    print("S parameter file found")
                else:
                    pass
                    print("S parameter file NOT found")
                    # simulate(InductorDataX, emxConfig)
            else:
                print(f"Script failed with return code {return_code}")
                print("Error output:")
                # print(stderr.decode('utf-8'))





        completedRuns = completedRuns + 1
        status["completed_runs"] = completedRuns
        with open(STATUS_FILE_PATH, "w") as status_file:
            json.dump(status, status_file, indent=4)

        pass
    

    if packSimulationResults:
        print("PACKING RESULTS ", outputDir, " (***) " ,outputName)
        pack(outputDir)
    pass





def pack(sweep_dir):

    data_dir = sweep_dir
    print(f"Data directory: {data_dir}")
    features_list = []
    targets_list = []
    feature_names = None  # Initialize to store feature names
    target_names = None   # Initialize to store target (S-parameter) names
    frequency_points = None  # Initialize to store frequency points

    # Loop through each run folder
    for run_folder in os.listdir(data_dir):
        if run_folder.startswith('RunID'):
            run_id = run_folder
            
            # Load the parameters from parameters.json
            with open(os.path.join(data_dir, run_folder, 'parameters.json'), 'r') as param_file:
                params = json.load(param_file)
                params_values = list(params['parameters'].values())
                
                # Save feature names only once
                if feature_names is None:
                    feature_names = list(params['parameters'].keys())
                
                features_list.append(params_values)
            
            # Find any touchstone file (e.g., .s2p, .s4p, .sNp) in the folder
            touchstone_files = glob.glob(os.path.join(data_dir, run_folder, f"*.s*p"))

            if touchstone_files:  # Check if there's at least one file found
                touchstone_path = touchstone_files[0]  # Take the first matching file
                print(f"Touchstone file found: {touchstone_path}")  # Print the path of the touchstone file
                network = rf.Network(touchstone_path)
                
                # Get the number of frequency points
                num_freqs = network.frequency.npoints
                num_ports = network.s.shape[1]  # Number of ports (shape: [freqs, ports, ports])
                
                # Save the frequency points only once
                if frequency_points is None:
                    frequency_points = network.f  # Frequency points in Hz
                
                # Save target names (S-parameter keys) only once
                if target_names is None:
                    target_names = []
                    for i in range(num_ports):
                        for j in range(num_ports):
                            target_names.append(f"S{i+1}{j+1}_real")
                            target_names.append(f"S{i+1}{j+1}_imag")

                # Prepare real and imaginary parts for all S-parameters at each frequency
                s_real_imag = []
                for i in range(num_ports):
                    for j in range(num_ports):
                        s_real_imag.append(network.s[:, i, j].real)  # Append real part
                        s_real_imag.append(network.s[:, i, j].imag)  # Append imaginary part

                # Stack the real and imaginary parts in alternating order
                s_real_imag = np.stack(s_real_imag, axis=0)  # Shape: [2*num_ports^2, num_freqs]

                # Append this run's target data, keeping the shape [2*num_ports^2, num_freqs]
                targets_list.append(s_real_imag)
            else:
                print(f"TOUCHSTONE FILE NOT FOUND for {run_id}")

    # Convert lists to arrays
    features_array = np.array(features_list)
    targets_array = np.array(targets_list)  # Shape: [num_runs, 2*num_ports^2, num_freqs]

    # Save the data in npz format, including feature names, target names, and frequency points
    np.savez(os.path.join(data_dir, 's_parameters_data.npz'), 
             features=features_array, 
             targets=targets_array, 
             feature_names=feature_names, 
             target_names=target_names,
             frequency_points=frequency_points)  # Store frequency points


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Your script description here")

    # Add command-line argument for JSON input file
    parser.add_argument("--artwork", "-a", required=True,
                        help="JSON data or file path to JSON data")
    parser.add_argument("--sweep", required=True, help="JSON file path")
    # Add command-line arguments for output path and file name
    parser.add_argument("--output", "-o", required=True, help="Output path")
    parser.add_argument("--name", "-n", help="Output file name")
    # Add the --layout flag to enable layout generation in GDSII
    parser.add_argument("--layout", action="store_true",
                        help="Enable generation of layout in GDSII")

    parser.add_argument("--svg", action="store_true",
                        help="Enable generation of layout in SVG")

    # Add the --simulate flag to enable simulation
    parser.add_argument("--simulate", action="store_true",
                        help="Enable simulation")
    
    # Add the --pack_sim flag to enable simulation
    parser.add_argument("--pack_sim", action="store_true",
                        help="Package the simulated results")

    # Add the --simulator or -s argument with choices
    parser.add_argument("--simulator", "--sim",
                        choices=["emx", "openems", "empro"], help="Choose a simulator")

    # Add the --config or -c argument for the JSON file (optional)
    parser.add_argument(
        "--config", "-c", help="Simulator configuration file", default=None)

    args = parser.parse_args()

    artworkData = []
    sweepData = []
    enableLayoutGeneration = 0
    enableSimulation = 0
    packSimRes = 0

    if args.layout:
        enableLayoutGeneration = 1
    else:
        enableLayoutGeneration = 0

    if args.simulate:
        enableSimulation = 1
    else:
        enableSimulation = 0

    if args.pack_sim:
        packSimRes = 1
    else:
        packSimRes = 0


    if args.svg:
        generateSVG = 1
    else:
        generateSVG = 0

    # Check if the --artwork argument is provided
    if args.artwork:
        try:
            # Try to load the input as a JSON string
            artworkData = json.loads(args.artwork)
        except json.JSONDecodeError:
            # If loading as JSON string fails, assume it's a file path and load the file
            try:
                with open(args.artwork, "r") as json_file:
                    artworkData = json.load(json_file)
            except FileNotFoundError:
                print(f"Error: File '{args.artwork}' not found.")
                exit(1)
            except json.JSONDecodeError:
                print(
                    f"Error: The file '{args.artwork}' does not contain valid JSON.")
                exit(1)
    else:
        print("Error: --artwork argument is required.")
        exit(1)

    # Check if the --sweep argument is provided
    if args.sweep:
        try:
            # Try to load the input as a JSON string
            sweepData = json.loads(args.sweep)
        except json.JSONDecodeError:
            # If loading as JSON string fails, assume it's a file path and load the file
            try:
                with open(args.sweep, "r") as json_file:
                    sweepData = json.load(json_file)
            except FileNotFoundError:
                print(f"Error: File '{args.sweep}' not found.")
                exit(1)
            except json.JSONDecodeError:
                print(
                    f"Error: The file '{args.sweep}' does not contain valid JSON.")
                exit(1)
    else:
        print("Error: --sweep argument is required.")
        exit(1)

    if args.simulator:
        if args.simulator == "emx":
            print("Simulator available")

    config = None
    if args.config:
        try:
            # Try to load the input as a JSON string
            config = json.loads(args.config)
        except json.JSONDecodeError:
            # If loading as JSON string fails, assume it's a file path and load the file
            try:
                with open(args.config, "r") as config_file:
                    config = json.load(config_file)
            except FileNotFoundError:
                print(f"Error: Configuration file '{args.config}' not found.")
                config = None
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in the configuration file: {e}")
            config = None

    # Run the source command
    command = 'source /projects/bitstream/emon/projects/conure/simulator/TSMC65nmRF_session_IC618'
    process = subprocess.Popen(command, shell=True, executable='/bin/bash')
    process.communicate()

    sweep(args.simulator, artworkData, sweepData, args.config,
          args.output, args.name, enableLayoutGeneration, generateSVG, enableSimulation, packSimRes)

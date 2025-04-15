#!/usr/bin/env python3
"""
Refactored sweep.py for artwork generation and simulation using .env configuration.

This script loads environment variables from the .env file (located in the project root, e.g., /conure)
and builds relative paths for:
  - CONURE_PATH
  - CONURE_ARTWORK_GENERATOR_PATH
  - CONURE_SWEEP_PATH
  - CONURE_SIMULATOR_PATH

It then uses these paths when invoking the artwork generator and simulator.
"""

import argparse
import os
import json
import sys
import itertools
import copy
import subprocess
import glob
import logging
import numpy as np
import skrf as rf
from pathlib import Path
from dotenv import load_dotenv

# ------------------------------------------------------------------------------
# Load .env and Build Relative Paths
# ------------------------------------------------------------------------------

# Assume this file is in conure/sweep/ and the .env file is in conure/.
project_root = Path(__file__).resolve().parents[1]
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Get environment variable values and build full paths.
conure_path_env = os.getenv("CONURE_PATH")
if not conure_path_env:
    raise ValueError("CONURE_PATH is not set in the .env file!")
conure_path = (project_root / conure_path_env).resolve()

artwork_generator_rel = os.getenv("CONURE_ARTWORK_GENERATOR_PATH")
if not artwork_generator_rel:
    raise ValueError("CONURE_ARTWORK_GENERATOR_PATH is not set in the .env file!")
artwork_generator_path = (conure_path / artwork_generator_rel).resolve()

sweep_rel = os.getenv("CONURE_SWEEP_PATH")
if not sweep_rel:
    raise ValueError("CONURE_SWEEP_PATH is not set in the .env file!")
sweep_path = (conure_path / sweep_rel).resolve()

simulator_rel = os.getenv("CONURE_SIMULATOR_PATH")
if not simulator_rel:
    raise ValueError("CONURE_SIMULATOR_PATH is not set in the .env file!")
simulator_path = (conure_path / simulator_rel).resolve()

# ------------------------------------------------------------------------------
# Initialize Logging
# ------------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger()

# ------------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------------

def load_json_data(input_arg):
    """
    Load JSON data either from a direct JSON string or from a file.
    """
    try:
        return json.loads(input_arg)
    except json.JSONDecodeError:
        try:
            with open(input_arg, "r") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            logger.error("File '%s' not found.", input_arg)
            sys.exit(1)
        except json.JSONDecodeError:
            logger.error("File '%s' does not contain valid JSON.", input_arg)
            sys.exit(1)

# ------------------------------------------------------------------------------
# Sweep Function
# ------------------------------------------------------------------------------

def sweep(simulator, artworkData, sweepParam, simulatorConfig, base_output_dir, outputName,
          enableLayoutGeneration, generateSVG, enableSimulation, packSimulationResults):
    """
    Sweep over a set of parameters to generate artwork layouts and optionally run simulations.
    Each run output is placed in a unique subdirectory under base_output_dir.
    """
    sweepPar = list(sweepParam["parameters"].keys())
    sweepData = [sweepParam["parameters"][param] for param in sweepPar]
    permutations = list(itertools.product(*sweepData))
    total_permutations = len(permutations)
    logger.info("Total number of permutations: %d", total_permutations)
    
    status = {
        "total_permutations": total_permutations,
        "completed_runs": 0,
        "status_message": ""
    }
    status_file_path = os.path.join(base_output_dir, "status.json")
    
    RunID = 0
    completedRuns = 0
    
    for permutation in permutations:
        # Deep copy the base artwork JSON so each run is independent.
        run_artwork = copy.deepcopy(artworkData)
        
        # Define a run-specific output directory.
        run_output_dir = os.path.join(base_output_dir, "RunID_{:04d}".format(RunID))
        if not os.path.exists(run_output_dir):
            os.makedirs(run_output_dir)
        
        # Create a run name: use artwork metadata name if no output name provided.
        if outputName is None:
            run_name = run_artwork["metadata"]["name"] + "_RunID_{:04d}".format(RunID)
        else:
            run_name = outputName + "_RunID_{:04d}".format(RunID)
        
        # Update the artwork data with the run name.
        run_artwork["metadata"]["name"] = run_name
        
        logger.info("RunID: %d, Permutation: %s, Run Name: %s", RunID, permutation, run_name)
        
        # Write run-specific parameters to a JSON file.
        run_parameters_json_path = os.path.join(run_output_dir, "parameters.json")
        if os.path.exists(run_parameters_json_path):
            logger.info("RunID %d already exists, skipping setup.", RunID)
            RunID += 1
            continue
        
        runData = {"runID": RunID, "parameters": {}}
        for i, param in enumerate(sweepPar):
            run_artwork["parameters"][param] = permutation[i]
            runData["parameters"][param] = permutation[i]
        runData["parameters"]["rings"] = run_artwork["parameters"].get("rings", None)
        
        with open(run_parameters_json_path, "w") as parfile:
            json.dump(runData, parfile, indent=4)
        
        portCount = len(run_artwork["ports"]["config"].get("simulatingPorts", []))
        gdsPath = os.path.join(run_output_dir, run_name + ".gds")
        sParamPath = os.path.join(run_output_dir, run_name + f".s{portCount}p")
        
        # Generate layout if enabled or if simulation is enabled and layout doesn't exist.
        if (enableLayoutGeneration or enableSimulation) and not os.path.exists(gdsPath):
            status["status_message"] = f"Generating Artwork for RunID: {RunID}"
            with open(status_file_path, "w") as status_file:
                json.dump(status, status_file, indent=4)
            logger.info("Generating layout for RunID %d", RunID)
            
            command = [
                "python",
                str(artwork_generator_path),
                "-a", json.dumps(run_artwork),
                "-o", run_output_dir,
                "-n", run_name,
            ]
            if generateSVG:
                command.append("--svg")
            
            logger.debug("Running layout command: %s", command)
            process = subprocess.run(command)
            if process.returncode == 0:
                logger.info("Layout generation succeeded for RunID %d", RunID)
            else:
                logger.error("Layout generation failed for RunID %d with code %d", RunID, process.returncode)
        
        # Run simulation if enabled, layout exists, and simulation output is not yet present.
        if enableSimulation and os.path.exists(gdsPath) and not os.path.exists(sParamPath):
            status["status_message"] = f"Performing EM simulation for RunID: {RunID}"
            with open(status_file_path, "w") as status_file:
                json.dump(status, status_file, indent=4)
            logger.info("Performing EM simulation for RunID %d", RunID)
            
            command = [
                "python",
                str(simulator_path),
                "-f", gdsPath,
                "-a", json.dumps(run_artwork),
                "-c", simulatorConfig if simulatorConfig else "",
                "--sim", simulator,
                "-o", run_output_dir,
                "-n", run_name
            ]
            # Remove empty arguments.
            command = [arg for arg in command if arg]
            logger.debug("Running simulation command: %s", command)
            process = subprocess.run(command)
            if process.returncode == 0:
                logger.info("Simulation succeeded for RunID %d", RunID)
                if os.path.exists(sParamPath):
                    logger.info("S-parameter file found for RunID %d", RunID)
                else:
                    logger.warning("S-parameter file not found for RunID %d", RunID)
            else:
                logger.error("Simulation failed for RunID %d with code %d", RunID, process.returncode)
        
        completedRuns += 1
        status["completed_runs"] = completedRuns
        with open(status_file_path, "w") as status_file:
            json.dump(status, status_file, indent=4)
        
        RunID += 1

    # Optionally, pack simulation results.
    if packSimulationResults:
        logger.info("Packing simulation results from base output: %s", base_output_dir)
        pack(base_output_dir)

# ------------------------------------------------------------------------------
# Pack Function
# ------------------------------------------------------------------------------

def pack(sweep_dir):
    """
    Gather simulation run parameters and S-parameter data,
    then pack them into a compressed NPZ file.
    """
    logger.info("Packing simulation results from directory: %s", sweep_dir)
    features_list = []
    targets_list = []
    feature_names = None
    target_names = None
    frequency_points = None
    
    for run_folder in os.listdir(sweep_dir):
        if run_folder.startswith('RunID'):
            run_path = os.path.join(sweep_dir, run_folder)
            parameters_path = os.path.join(run_path, 'parameters.json')
            if not os.path.exists(parameters_path):
                continue
            with open(parameters_path, 'r') as param_file:
                params = json.load(param_file)
                params_values = list(params['parameters'].values())
                if feature_names is None:
                    feature_names = list(params['parameters'].keys())
                features_list.append(params_values)
            touchstone_files = glob.glob(os.path.join(run_path, "*.s*p"))
            if touchstone_files:
                touchstone_path = touchstone_files[0]
                logger.info("Touchstone file found: %s", touchstone_path)
                network = rf.Network(touchstone_path)
                num_ports = network.s.shape[1]
                if frequency_points is None:
                    frequency_points = network.f
                if target_names is None:
                    target_names = []
                    for i in range(num_ports):
                        for j in range(num_ports):
                            target_names.append(f"S{i+1}{j+1}_real")
                            target_names.append(f"S{i+1}{j+1}_imag")
                s_real_imag = []
                for i in range(num_ports):
                    for j in range(num_ports):
                        s_real_imag.append(network.s[:, i, j].real)
                        s_real_imag.append(network.s[:, i, j].imag)
                s_real_imag = np.stack(s_real_imag, axis=0)
                targets_list.append(s_real_imag)
            else:
                logger.warning("No touchstone file found for %s", run_folder)
    
    features_array = np.array(features_list)
    targets_array = np.array(targets_list)
    output_npz_path = os.path.join(sweep_dir, 's_parameters_data.npz')
    np.savez(output_npz_path,
             features=features_array,
             targets=targets_array,
             feature_names=feature_names,
             target_names=target_names,
             frequency_points=frequency_points)
    logger.info("Packed simulation results saved to: %s", output_npz_path)

# ------------------------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sweep script for artwork generation and simulation using .env paths."
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--artwork", "-a", required=True, help="JSON data or file path for artwork")
    parser.add_argument("--sweep", required=True, help="JSON file path for sweep parameters")
    parser.add_argument("--output", "-o", required=True, help="Base output directory")
    parser.add_argument("--name", "-n", help="Output file base name")
    parser.add_argument("--layout", action="store_true", help="Enable layout generation in GDSII")
    parser.add_argument("--svg", action="store_true", help="Enable SVG generation")
    parser.add_argument("--simulate", action="store_true", help="Enable simulation")
    parser.add_argument("--pack_sim", action="store_true", help="Package simulation results")
    parser.add_argument("--simulator", "--sim", choices=["emx", "openems", "empro"], help="Choose a simulator")
    parser.add_argument("--config", "-c", help="Simulator configuration file", default=None)
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    artworkData = load_json_data(args.artwork)
    sweepData = load_json_data(args.sweep)
    config = load_json_data(args.config) if args.config else None
    
    # Optional: run any environment setup commands.
    env_command = 'source /projects/bitstream/emon/projects/conure/simulator/TSMC65nmRF_session_IC618'
    process = subprocess.Popen(env_command, shell=True, executable='/bin/bash')
    process.communicate()
    
    sweep(args.simulator, artworkData, sweepData, args.config,
          args.output, args.name,
          enableLayoutGeneration=args.layout,
          generateSVG=args.svg,
          enableSimulation=args.simulate,
          packSimulationResults=args.pack_sim)

if __name__ == "__main__":
    main()




# import argparse
# import os
# import shlex
# import json
# import sys
# import itertools
# import copy
# import subprocess
# import time
# import json
# import numpy as np
# import skrf as rf
# import glob




# #CONURE_PATH = os.environ.get('CONURE_PATH')
# CONURE_PATH = "/home/emon/projects/Conure"


# if CONURE_PATH is None:
#     print("CONURE_PATH is not set!")
# else:
#     print(f"CONURE_PATH is set to: {CONURE_PATH}")

# ARTWORK_GENERATOR_PATH = os.path.join(CONURE_PATH, "artwork_generator", "artwork_generator.py")
# SIMULATOR_PATH = os.path.join(CONURE_PATH, "simulator", "simulate.py")



# def sweep(simulator, artworkData, sweepParam, simulatorConfig, outputDir, outputName, enableLayoutGeneration, generateSVG, enableSimulation, packSimulationResults):

#     sweepPar = []
#     sweepData = []
#     for param, paramSweepData in sweepParam["parameters"].items():
#         sweepPar.append(param)
#         sweepData.append(paramSweepData)

#     permutations = itertools.product(*sweepData)

#     # Calculate and print the total number of permutations
#     total_permutations = len(list(itertools.product(*sweepData)))
#     print("Total number of permutations:", total_permutations)

#     status = {
#         "total_permutations": total_permutations,
#         "completed_runs": 0,
#         "status_message": ''
#     }

#     STATUS_FILE_PATH = os.path.join(outputDir, "status.json")

#     RunID = 0
#     completedRuns = 0
#     for permutation in permutations:

#         InductorDataX = copy.deepcopy(artworkData)
#         InductorDataX["parameters"]["outputDir"] = outputDir + \
#             "/RunID_" + "{:04d}".format(RunID)
#         # InductorDataX["parameters"]["outputDir"] +=  "/RunID_" + "{:04d}".format(RunID)

#         if outputName == None:
#             InductorDataX["parameters"]["name"] += "_RunID_" + \
#                 "{:04d}".format(RunID)
#         else:
#             InductorDataX["parameters"]["name"] = outputName
#             InductorDataX["parameters"]["name"] += "_RunID_" + \
#                 "{:04d}".format(RunID)

#         print(InductorDataX["parameters"]["name"] + "\r\nRUN ID: " +
#               str(RunID) + "\r\n" + str(permutation) + "\r\n")

#         if os.path.exists(InductorDataX["parameters"]["outputDir"] + "/parameters.json"):
#             RunID += 1

#         else:
#             runData = {
#                 "runID": RunID,
#                 "parameters": {},
#             }

#             TotalRuns = len(permutation)
#             # print(TotalRuns)
#             for i in range(TotalRuns):
#                 InductorDataX["parameters"][sweepPar[i]] = permutation[i]
#                 # used to just write as a text file of the parameter value
#                 runData["parameters"][sweepPar[i]] = permutation[i]

#             runData["parameters"]["rings"] = InductorDataX["parameters"]["rings"]
#             runDataJSON = json.dumps(runData)

#             if not os.path.exists(InductorDataX["parameters"]["outputDir"]):
#                 os.makedirs(InductorDataX["parameters"]["outputDir"])

#             with open(InductorDataX["parameters"]["outputDir"] + "/parameters.json", "w") as parfile:
#                 parfile.write(runDataJSON)

#             RunID += 1

#         portCount = len(InductorDataX["ports"]["config"]["simulatingPorts"])
#         gdsPath = InductorDataX["parameters"]["outputDir"] + \
#             "/" + InductorDataX["parameters"]["name"] + ".gds"
#         sParamPath = InductorDataX["parameters"]["outputDir"] + "/" + \
#             InductorDataX["parameters"]["name"] + ".s" + str(portCount) + "p"
#         yParamPath = InductorDataX["parameters"]["outputDir"] + "/" + \
#             InductorDataX["parameters"]["name"] + ".s" + str(portCount) + "p"

#         if (enableLayoutGeneration or enableSimulation) and not os.path.exists(gdsPath):

#             status["status_message"] = f"Generating Artwork for RunID: {RunID}"
#             with open(STATUS_FILE_PATH, "w") as status_file:
#                 json.dump(status, status_file, indent=4)

#             print("Generating layout for RunID ", RunID)
#             # Define the command as a list of arguments, including the JSON content

#             command = [
#                 "python",
#                 ARTWORK_GENERATOR_PATH,
#                 # Pass the JSON content directly
#                 "-a", json.dumps(InductorDataX),
#                 "-o", InductorDataX["parameters"]["outputDir"],
#                 "-n", InductorDataX["parameters"]["name"],
#             ]

#             if (generateSVG):
#                 command.append("--svg")

#             # print(command)
#             process = subprocess.run(command)
#             # command_list = shlex.split(command)
#             # print(command_list)

#             # Use subprocess to run the command
#             # process = subprocess.Popen(
#             #    command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

#             # # Capture the output and error
#             # stdout, stderr = process.communicate()

#             # Check the return code to see if the process was successful
#             return_code = process.returncode

#             if return_code == 0:
#                 print("Layout generation completed successfully.")
#             else:
#                 print(f"Script failed with return code {return_code}")
#                 print("Error output:")
#                 # print(stderr.decode('utf-8'))

#         if enableSimulation and os.path.exists(gdsPath) and not os.path.exists(sParamPath):

#             status["status_message"] = f"Performing EM simulation for RunID: {
#                 RunID}"
#             with open(STATUS_FILE_PATH, "w") as status_file:
#                 json.dump(status, status_file, indent=4)

#             print("Performing EM simulation for RunID ", RunID)
#             json_content = json.dumps(InductorDataX)

#             command = [
#                 "python",
#                 SIMULATOR_PATH,
#                 "-f", gdsPath,
#                 "-a", json.dumps(InductorDataX),
#                 "-c", simulatorConfig,
#                 "--sim", simulator,
#                 "-o", InductorDataX["parameters"]["outputDir"],
#                 "-n", InductorDataX["parameters"]["name"]
#             ]

#             process = subprocess.run(command)

#             # process = subprocess.Popen(
#             #     command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

#             # # Capture the output and error
#             # stdout, stderr = process.communicate()

#             # Check the return code to see if the process was successful
#             return_code = process.returncode

#             if return_code == 0:
#                 print("EM simulation completed successfully.")
#                 if os.path.exists(sParamPath):
#                     print("S parameter file found")
#                 else:
#                     pass
#                     print("S parameter file NOT found")
#                     # simulate(InductorDataX, emxConfig)
#             else:
#                 print(f"Script failed with return code {return_code}")
#                 print("Error output:")
#                 # print(stderr.decode('utf-8'))





#         completedRuns = completedRuns + 1
#         status["completed_runs"] = completedRuns
#         with open(STATUS_FILE_PATH, "w") as status_file:
#             json.dump(status, status_file, indent=4)

#         pass
    

#     if packSimulationResults:
#         print("PACKING RESULTS ", outputDir, " (***) " ,outputName)
#         pack(outputDir)
#     pass





# def pack(sweep_dir):

#     data_dir = sweep_dir
#     print(f"Data directory: {data_dir}")
#     features_list = []
#     targets_list = []
#     feature_names = None  # Initialize to store feature names
#     target_names = None   # Initialize to store target (S-parameter) names
#     frequency_points = None  # Initialize to store frequency points

#     # Loop through each run folder
#     for run_folder in os.listdir(data_dir):
#         if run_folder.startswith('RunID'):
#             run_id = run_folder
            
#             # Load the parameters from parameters.json
#             with open(os.path.join(data_dir, run_folder, 'parameters.json'), 'r') as param_file:
#                 params = json.load(param_file)
#                 params_values = list(params['parameters'].values())
                
#                 # Save feature names only once
#                 if feature_names is None:
#                     feature_names = list(params['parameters'].keys())
                
#                 features_list.append(params_values)
            
#             # Find any touchstone file (e.g., .s2p, .s4p, .sNp) in the folder
#             touchstone_files = glob.glob(os.path.join(data_dir, run_folder, f"*.s*p"))

#             if touchstone_files:  # Check if there's at least one file found
#                 touchstone_path = touchstone_files[0]  # Take the first matching file
#                 print(f"Touchstone file found: {touchstone_path}")  # Print the path of the touchstone file
#                 network = rf.Network(touchstone_path)
                
#                 # Get the number of frequency points
#                 num_freqs = network.frequency.npoints
#                 num_ports = network.s.shape[1]  # Number of ports (shape: [freqs, ports, ports])
                
#                 # Save the frequency points only once
#                 if frequency_points is None:
#                     frequency_points = network.f  # Frequency points in Hz
                
#                 # Save target names (S-parameter keys) only once
#                 if target_names is None:
#                     target_names = []
#                     for i in range(num_ports):
#                         for j in range(num_ports):
#                             target_names.append(f"S{i+1}{j+1}_real")
#                             target_names.append(f"S{i+1}{j+1}_imag")

#                 # Prepare real and imaginary parts for all S-parameters at each frequency
#                 s_real_imag = []
#                 for i in range(num_ports):
#                     for j in range(num_ports):
#                         s_real_imag.append(network.s[:, i, j].real)  # Append real part
#                         s_real_imag.append(network.s[:, i, j].imag)  # Append imaginary part

#                 # Stack the real and imaginary parts in alternating order
#                 s_real_imag = np.stack(s_real_imag, axis=0)  # Shape: [2*num_ports^2, num_freqs]

#                 # Append this run's target data, keeping the shape [2*num_ports^2, num_freqs]
#                 targets_list.append(s_real_imag)
#             else:
#                 print(f"TOUCHSTONE FILE NOT FOUND for {run_id}")

#     # Convert lists to arrays
#     features_array = np.array(features_list)
#     targets_array = np.array(targets_list)  # Shape: [num_runs, 2*num_ports^2, num_freqs]

#     # Save the data in npz format, including feature names, target names, and frequency points
#     np.savez(os.path.join(data_dir, 's_parameters_data.npz'), 
#              features=features_array, 
#              targets=targets_array, 
#              feature_names=feature_names, 
#              target_names=target_names,
#              frequency_points=frequency_points)  # Store frequency points


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(
#         description="Your script description here")

#     # Add command-line argument for JSON input file
#     parser.add_argument("--artwork", "-a", required=True,
#                         help="JSON data or file path to JSON data")
#     parser.add_argument("--sweep", required=True, help="JSON file path")
#     # Add command-line arguments for output path and file name
#     parser.add_argument("--output", "-o", required=True, help="Output path")
#     parser.add_argument("--name", "-n", help="Output file name")
#     # Add the --layout flag to enable layout generation in GDSII
#     parser.add_argument("--layout", action="store_true",
#                         help="Enable generation of layout in GDSII")

#     parser.add_argument("--svg", action="store_true",
#                         help="Enable generation of layout in SVG")

#     # Add the --simulate flag to enable simulation
#     parser.add_argument("--simulate", action="store_true",
#                         help="Enable simulation")
    
#     # Add the --pack_sim flag to enable simulation
#     parser.add_argument("--pack_sim", action="store_true",
#                         help="Package the simulated results")

#     # Add the --simulator or -s argument with choices
#     parser.add_argument("--simulator", "--sim",
#                         choices=["emx", "openems", "empro"], help="Choose a simulator")

#     # Add the --config or -c argument for the JSON file (optional)
#     parser.add_argument(
#         "--config", "-c", help="Simulator configuration file", default=None)

#     args = parser.parse_args()

#     artworkData = []
#     sweepData = []
#     enableLayoutGeneration = 0
#     enableSimulation = 0
#     packSimRes = 0

#     if args.layout:
#         enableLayoutGeneration = 1
#     else:
#         enableLayoutGeneration = 0

#     if args.simulate:
#         enableSimulation = 1
#     else:
#         enableSimulation = 0

#     if args.pack_sim:
#         packSimRes = 1
#     else:
#         packSimRes = 0


#     if args.svg:
#         generateSVG = 1
#     else:
#         generateSVG = 0

#     # Check if the --artwork argument is provided
#     if args.artwork:
#         try:
#             # Try to load the input as a JSON string
#             artworkData = json.loads(args.artwork)
#         except json.JSONDecodeError:
#             # If loading as JSON string fails, assume it's a file path and load the file
#             try:
#                 with open(args.artwork, "r") as json_file:
#                     artworkData = json.load(json_file)
#             except FileNotFoundError:
#                 print(f"Error: File '{args.artwork}' not found.")
#                 exit(1)
#             except json.JSONDecodeError:
#                 print(
#                     f"Error: The file '{args.artwork}' does not contain valid JSON.")
#                 exit(1)
#     else:
#         print("Error: --artwork argument is required.")
#         exit(1)

#     # Check if the --sweep argument is provided
#     if args.sweep:
#         try:
#             # Try to load the input as a JSON string
#             sweepData = json.loads(args.sweep)
#         except json.JSONDecodeError:
#             # If loading as JSON string fails, assume it's a file path and load the file
#             try:
#                 with open(args.sweep, "r") as json_file:
#                     sweepData = json.load(json_file)
#             except FileNotFoundError:
#                 print(f"Error: File '{args.sweep}' not found.")
#                 exit(1)
#             except json.JSONDecodeError:
#                 print(
#                     f"Error: The file '{args.sweep}' does not contain valid JSON.")
#                 exit(1)
#     else:
#         print("Error: --sweep argument is required.")
#         exit(1)

#     if args.simulator:
#         if args.simulator == "emx":
#             print("Simulator available")

#     config = None
#     if args.config:
#         try:
#             # Try to load the input as a JSON string
#             config = json.loads(args.config)
#         except json.JSONDecodeError:
#             # If loading as JSON string fails, assume it's a file path and load the file
#             try:
#                 with open(args.config, "r") as config_file:
#                     config = json.load(config_file)
#             except FileNotFoundError:
#                 print(f"Error: Configuration file '{args.config}' not found.")
#                 config = None
#         except json.JSONDecodeError as e:
#             print(f"Error: Invalid JSON in the configuration file: {e}")
#             config = None

#     # Run the source command
#     command = 'source /projects/bitstream/emon/projects/conure/simulator/TSMC65nmRF_session_IC618'
#     process = subprocess.Popen(command, shell=True, executable='/bin/bash')
#     process.communicate()

#     sweep(args.simulator, artworkData, sweepData, args.config,
#           args.output, args.name, enableLayoutGeneration, generateSVG, enableSimulation, packSimRes)

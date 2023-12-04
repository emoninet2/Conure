import argparse
import os
import json
import sys
import itertools
import copy
import subprocess



def sweep(simulator, artworkData, sweepParam, simulatorConfig, outputDir, outputName, enableLayoutGeneration,enableSimulation):


    sweepPar = []
    sweepData = []
    for param, paramSweepData in sweepParam["parameters"].items():
        sweepPar.append(param)
        sweepData.append(paramSweepData)

    permutations = itertools.product(*sweepData)

    # Calculate and print the total number of permutations
    total_permutations = len(list(itertools.product(*sweepData)))
    print("Total number of permutations:", total_permutations)


    RunID = 0
    successfulRuns = 0
    for permutation in permutations:
        InductorDataX = copy.deepcopy(artworkData)
        InductorDataX["parameters"]["outputDir"] = outputDir+  "/RunID_" + "{:04d}".format(RunID)
        #InductorDataX["parameters"]["outputDir"] +=  "/RunID_" + "{:04d}".format(RunID)

        if outputName == None:
            InductorDataX["parameters"]["name"] +=  "_RunID_" + "{:04d}".format(RunID)
        else:
            InductorDataX["parameters"]["name"] =  outputName
            InductorDataX["parameters"]["name"] +=  "_RunID_" + "{:04d}".format(RunID)


        print(InductorDataX["parameters"]["name"] + "\r\nRUN ID: " + str(RunID) + "\r\n" + str(permutation) + "\r\n")


        if os.path.exists(InductorDataX["parameters"]["outputDir"] + "/parameters.json"):
            RunID += 1
        else:
            runData = {
                "runID" : None,
                "parameters" : {},
            }

            TotalRuns = len(permutation)
            #print(TotalRuns)
            for i in range(TotalRuns):
                InductorDataX["parameters"][sweepPar[i]] = permutation[i]
                runData["parameters"][sweepPar[i]] = permutation[i] #used to just write as a text file of the parameter value

            runData["parameters"]["rings"] = InductorDataX["parameters"]["rings"]
            runDataJSON = json.dumps(runData)


            if not os.path.exists(InductorDataX["parameters"]["outputDir"]):
                os.makedirs(InductorDataX["parameters"]["outputDir"])

            with open(InductorDataX["parameters"]["outputDir"] + "/parameters.json", "w") as parfile:
                parfile.write(runDataJSON)


            RunID += 1

        portCount = len(InductorDataX["ports"]["config"]["simulatingPorts"])
        gdsPath = InductorDataX["parameters"]["outputDir"] + "/" + InductorDataX["parameters"]["name"] + ".gds"
        sParamPath = InductorDataX["parameters"]["outputDir"] + "/" + InductorDataX["parameters"]["name"] + ".s" + str(portCount) +"p"
        yParamPath = InductorDataX["parameters"]["outputDir"] + "/" + InductorDataX["parameters"]["name"] + ".s" + str(portCount) +"p"


        if (enableLayoutGeneration or enableSimulation) and not os.path.exists( gdsPath):
            print("Generating layout for RunID ", RunID)
            # Define the command as a list of arguments, including the JSON content
            command = [
                "python",
                "artwork_generator/artwork_generator.py",
                "-a", json.dumps(InductorDataX),  # Pass the JSON content directly
                "-o", InductorDataX["parameters"]["outputDir"],
                "-n", InductorDataX["parameters"]["name"]
            ]

            # Use subprocess to run the command
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Capture the output and error
            stdout, stderr = process.communicate()

            # Check the return code to see if the process was successful
            return_code = process.returncode

            if return_code == 0:
                print("Layout generation completed successfully.")
            else:
                print(f"Script failed with return code {return_code}")
                print("Error output:")
                print(stderr.decode('utf-8'))

        if enableSimulation and os.path.exists( gdsPath) and not os.path.exists(sParamPath):
            print("Performing EM simulation for RunID ", RunID)
            json_content = json.dumps(InductorDataX)

            command = [
                "python",
                "simulator/simulate.py",
                "-f", gdsPath,
                "-a", json.dumps(InductorDataX),
                "-c", simulatorConfig,
                "--sim", simulator,
                "-o", InductorDataX["parameters"]["outputDir"],
                "-n", InductorDataX["parameters"]["name"]
            ]


            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Capture the output and error
            stdout, stderr = process.communicate()

            # Check the return code to see if the process was successful
            return_code = process.returncode

            if return_code == 0:
                print("EM simulation completed successfully.")
                if os.path.exists( sParamPath):
                    print("S parameter file found")
                else:
                    pass
                    print("S parameter file NOT found")
                    #simulate(InductorDataX, emxConfig)
            else:
                print(f"Script failed with return code {return_code}")
                print("Error output:")
                print(stderr.decode('utf-8'))

        pass

    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Your script description here")

    # Add command-line argument for JSON input file
    parser.add_argument("--artwork", "-a", required=True, help="JSON file path")
    parser.add_argument("--sweep", required=True, help="JSON file path")
    # Add command-line arguments for output path and file name
    parser.add_argument("--output", "-o", required=True, help="Output path")
    parser.add_argument("--name", "-n", help="Output file name")
    # Add the --layout flag to enable layout generation in GDSII
    parser.add_argument("--layout", action="store_true", help="Enable generation of layout in GDSII")

    # Add the --simulate flag to enable simulation
    parser.add_argument("--simulate", action="store_true", help="Enable simulation")

    # Add the --simulator or -s argument with choices
    parser.add_argument("--simulator", "--sim", choices=["emx", "openems", "empro"], help="Choose a simulator")

    # Add the --config or -c argument for the JSON file (optional)
    parser.add_argument("--config", "-c", help="Simulator configuration file", default=None)

    args = parser.parse_args()

    artworkData = []
    sweepData = []
    enableLayoutGeneration = 0
    enableSimulation = 0

    if args.layout:
        enableLayoutGeneration = 1
    else:
        enableLayoutGeneration = 0
    

    if args.simulate:
        enableSimulation = 1
    else:
        enableSimulation = 0



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
    else:
        print("Error: --artwork argument is required.")
        exit(1)

    if args.sweep:
        try:
            with open(args.sweep, "r") as json_file:
                sweepData = json.load(json_file)
        except FileNotFoundError:
            print(f"Error: File '{args.sweep}' not found.")
            exit(1)
    else:
        print("Error: --sweep argument is required.")
        exit(1)


    # if args.simulator:
    #     if args.simulator == "emx":
    #         print("Simulator available")
 


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

     

    sweep(args.simulator, artworkData, sweepData, args.config, args.output, args.name, enableLayoutGeneration,enableSimulation)
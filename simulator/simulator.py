import argparse
import os
import json
import sys
import logging
import emx

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)


def simulate(gds_file, simulator, artworkData, config, outputDir, outputName):
    logger.info(f"Simulating {gds_file} using {simulator}")
    if config is None:
        logger.error("No configuration file provided.")
    else:
        logger.debug(f"Simulator config: {config}")

    if simulator == "emx":
        try:
            emx.simulate(gds_file, artworkData, config["emx_config"], outputDir, outputName)
        except Exception as error:
            logger.error(f"Error during simulation: {error}")
            sys.exit(1)
    else:
        logger.error(f"Simulator '{simulator}' is not supported in this script.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Simulation Script for EMX")
    parser.add_argument("--gds_file", "-f", required=True, help="GDSII file path")
    parser.add_argument("--artwork", "-a", required=True, help="Artwork JSON file path or JSON string")
    parser.add_argument("--output", "-o", required=True, help="Output path")
    parser.add_argument("--name", "-n", required=True, help="Output file name")
    parser.add_argument("--simulator", "--sim", choices=["emx", "openems", "empro"], required=True,
                        help="Choose a simulator")
    parser.add_argument("--config", "-c", help="JSON configuration file path or JSON string", default=None)

    args = parser.parse_args()

    # Validate GDS file existence and extension
    if not os.path.exists(args.gds_file):
        logger.error(f"GDS file '{args.gds_file}' does not exist.")
        sys.exit(1)
    if not args.gds_file.lower().endswith((".gds", ".gdsii")):
        logger.error("Error: Not a valid GDS file.")
        sys.exit(1)
    else:
        logger.debug("GDS file verified.")

    # Load artwork data from file or as JSON string
    artworkData = None
    try:
        try:
            artworkData = json.loads(args.artwork)
        except json.JSONDecodeError:
            with open(args.artwork, "r") as json_file:
                artworkData = json.load(json_file)
    except Exception as error:
        logger.error(f"Error loading artwork JSON: {error}")
        sys.exit(1)

    # Load configuration from file or JSON string (if provided)
    config = None
    if args.config:
        try:
            try:
                config = json.loads(args.config)
            except json.JSONDecodeError:
                with open(args.config, "r") as config_file:
                    config = json.load(config_file)
        except Exception as error:
            logger.error(f"Error loading configuration JSON: {error}")
            config = None

    if args.simulator == "emx":
        logger.info("Simulator 'emx' selected.")
    else:
        logger.error(f"Simulator '{args.simulator}' is not currently implemented.")
        sys.exit(1)

    simulate(args.gds_file, args.simulator, artworkData, config, args.output, args.name)


if __name__ == "__main__":
    main()


# import argparse
# import os
# import json
# import sys
# import emx

# def simulate(gds_file, simulator, artworkData, config, outputDir, outputName):
#     # Your simulation code here
#     print(f"Simulating {gds_file} using {simulator} ")
#     if config == None:
#         print("No config file given")
#     else:
#         print(f"simulator with config: {config}")

#     if simulator=="emx":
#         emx.simulate(gds_file, artworkData, config["emx_config"], outputDir, outputName)

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Your script description here")

#     # Add command-line argument for JSON input file
#     parser.add_argument("--gds_file", "-f", help="GDSII file path")
#     parser.add_argument("--artwork", "-a", help="JSON file path")
#     # Add command-line arguments for output path and file name
#     parser.add_argument("--output", "-o", help="Output path")
#     parser.add_argument("--name", "-n", help="Output file name")

#     # Add the --simulator or -s argument with choices
#     parser.add_argument("--simulator", "--sim", choices=["emx", "openems", "empro"], help="Choose a simulator")

#     # Add the --config or -c argument for the JSON file or JSON string (optional)
#     parser.add_argument("--config", "-c", help="JSON configuration file or JSON string", default=None)

#     args = parser.parse_args()

#     artworkData = None
#     if args.gds_file:
#         # Check if the file exists
#         if os.path.exists(args.gds_file):
#             # Check if the file has a GDS extension
#             if args.gds_file.lower().endswith((".gds", ".gdsii")):
#                 # It appears to be a GDS file, you can proceed with further processing
#                 with open(args.gds_file, "r") as gds_file:
#                     print("gds file ok")
#             else:
#                 print("Error: Not a valid GDS file.")
#                 sys.exit(1)  # Quit the script with a non-zero exit code
#         else:
#             print(f"Error: File '{args.gds_file}' does not exist.")
#             sys.exit(1)  # Quit the script with a non-zero exit code

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
#     else:
#         print("Error: --artwork argument is required.")
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

#     simulate(args.gds_file, args.simulator, artworkData, config, args.output, args.name)
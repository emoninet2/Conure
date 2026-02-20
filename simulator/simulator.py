import argparse
import os
import json
import sys
import logging
import emx


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[94m",     # Blue
        logging.INFO: "\033[92m",      # Green
        logging.WARNING: "\033[93m",   # Yellow
        logging.ERROR: "\033[91m",     # Red
        logging.CRITICAL: "\033[95m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        timestamp = self.formatTime(record, self.datefmt)
        msg = super().format(record)
        return f"{timestamp} [SIM] {color}{msg}{self.RESET}"



# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter('%(levelname)s - %(message)s'))
    logger.addHandler(handler)
    
def simulate(gds_file, simulator, artworkData, config, outputDir, outputName):

    logger.info(f"Simulating {gds_file} using {simulator}")
    if config is None:
        logger.error("No configuration file provided.")
    else:
        logger.debug(f"Simulator config: {config}")

    if simulator.lower() == "emx":
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
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Set the logging level"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose (debug) output"
    )

    # ✅ Now parse all arguments
    args = parser.parse_args()

    # Set log level based on --log-level
    log_levels = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    # Start with logging disabled
    logger.setLevel(logging.CRITICAL + 1)

    # If --log-level is provided
    if args.log_level:
        logger.setLevel(log_levels[args.log_level])

    # If --verbose is used, override
    if args.verbose:
        logger.setLevel(logging.DEBUG)

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

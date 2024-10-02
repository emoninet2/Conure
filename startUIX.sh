#!/bin/bash

# Determine the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define the CONURE_PATH based on the script directory
#CONURE_PATH="$SCRIPT_DIR"
CONURE_PATH="/projects/bitstream/emon/projects/conure"


# Define the paths to the Python executable and the script to run
#PYTHON_EXECUTABLE="$CONURE_PATH/.venv/bin/python"
PYTHON_EXECUTABLE="/projects/bitstream/emon/anaconda/envs/.venv/bin/python"
SCRIPT_TO_RUN="$CONURE_PATH/uix/uix.py"

# Export CONURE_PATH so it's available to the Python script
export CONURE_PATH

# Check if the Python executable exists
if [ ! -f "$PYTHON_EXECUTABLE" ]; then
  echo "Python executable not found at $PYTHON_EXECUTABLE"
  exit 1
fi

# Check if the script to run exists
if [ ! -f "$SCRIPT_TO_RUN" ]; then
  echo "Script to run not found at $SCRIPT_TO_RUN"
  exit 1
fi

# Run the script
$PYTHON_EXECUTABLE $SCRIPT_TO_RUN

# Check if the script ran successfully
if [ $? -eq 0 ]; then
  echo "Project started successfully."
else
  echo "An error occurred while starting the project."
fi
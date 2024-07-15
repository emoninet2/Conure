#!/bin/bash

# Determine the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Define the paths to the Python executable and the script to run
PYTHON_EXECUTABLE="$SCRIPT_DIR/.venv/bin/python"
SCRIPT_TO_RUN="$SCRIPT_DIR/uix/uix.py"

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
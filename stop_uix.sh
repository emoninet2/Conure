#!/bin/bash

LOCK_FILE="./uix.lock"

# Check if the PID file exists
if [ ! -f "$LOCK_FILE" ]; then
  echo "PID file not found. Are the processes running?"
  exit 1
else
  echo "PID file found. Stopping existing processes..."
fi

# Read the PID file line by line and kill each process
while IFS=: read -r name pid; do
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "Stopping $name process with PID $pid..."
    kill "$pid"
    # Optionally wait a short while for graceful shutdown
    sleep 1
  else
    echo "Process $name with PID $pid not found."
  fi
done < "$LOCK_FILE"

# Remove the PID file once all processes have been terminated
rm "$LOCK_FILE"
echo "All processes have been terminated."

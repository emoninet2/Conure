#!/bin/bash

PID_FILE="./uix_pids.txt"

if [ ! -f "$PID_FILE" ]; then
  echo "PID file not found. Are the processes running?"
  exit 1
fi

while IFS=: read -r name pid; do
  if ps -p $pid > /dev/null; then
    echo "Stopping $name process with PID $pid..."
    kill $pid
  else
    echo "Process $name with PID $pid not found."
  fi
done < "$PID_FILE"

rm "$PID_FILE"
echo "All processes have been terminated."

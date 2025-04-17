#!/bin/bash
set -e

# Load .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Use defaults if not set
VITE_BACKEND_PORT=${VITE_BACKEND_PORT:-5000}
FRONTEND_PORT=${FRONTEND_PORT:-5173}

# Define directories
BACKEND_DIR="./uix/backend"
FRONTEND_DIR="./uix/frontend"
VENV_DIR="./.venv"

# Define PID file with absolute path so it is always created in a fixed location (project root)
LOCK_FILE="$(pwd)/uix.lock"

# Colors for display messages
GREEN="\033[0;32m"
BLUE="\033[0;34m"
NC="\033[0m"

# Check if PID file exists and whether the processes it lists are still running.
if [ -f "$LOCK_FILE" ]; then
  echo -e "${BLUE}PID file exists. Checking if processes are still active...${NC}"
  RUNNING=0
  while IFS=: read -r name pid; do
    if ps -p "$pid" > /dev/null 2>&1; then
      echo -e "${BLUE}${name} process with PID $pid is still running.${NC}"
      RUNNING=1
    fi
  done < "$LOCK_FILE"

  if [ $RUNNING -eq 1 ]; then
    echo -e "${BLUE}Existing UIX processes detected. Aborting start.${NC}"
    exit 1
  else
    echo -e "${GREEN}No active processes found. Removing stale PID file.${NC}"
    rm "$LOCK_FILE"
  fi
fi

# Activate the global virtual environment (from project root)
if [ -d "$VENV_DIR" ]; then
  echo -e "${GREEN}Activating virtual environment from $VENV_DIR...${NC}"
  source "$VENV_DIR/bin/activate"
else
  echo "❌ Virtual environment not found at $VENV_DIR"
  exit 1
fi

# Just in case, clear the PID file if it exists
if [ -f "$LOCK_FILE" ]; then
  rm "$LOCK_FILE"
fi

# Start Flask backend
echo -e "${GREEN}Starting Flask backend on port $VITE_BACKEND_PORT...${NC}"
cd "$BACKEND_DIR"
export FLASK_APP=app.py
export FLASK_ENV=development
export BACKEND_PORT=$VITE_BACKEND_PORT
#flask run --port=$VITE_BACKEND_PORT &
flask run --host=0.0.0.0 --port=$VITE_BACKEND_PORT &
BACKEND_PID=$!
echo "backend:$BACKEND_PID" >> "$LOCK_FILE"
cd - > /dev/null

# Start React frontend (Vite)
echo -e "${GREEN}Starting React frontend (Vite) on port $FRONTEND_PORT...${NC}"
cd "$FRONTEND_DIR"
npm install
npm run dev -- --port $FRONTEND_PORT &
FRONTEND_PID=$!
echo "frontend:$FRONTEND_PID" >> "$LOCK_FILE"
cd - > /dev/null

# Display a summary with URLs
echo -e "${GREEN}UIX is now running!${NC}"
echo -e "${BLUE}📦 Flask Backend PID:   $BACKEND_PID${NC}"
echo -e "${BLUE}🌐 React Frontend PID:  $FRONTEND_PID${NC}"
echo ""
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "Backend : http://localhost:$VITE_BACKEND_PORT"

# Wait for both processes to prevent the script from exiting immediately
wait $BACKEND_PID
wait $FRONTEND_PID

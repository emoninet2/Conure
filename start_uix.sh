#!/bin/bash
set -e

# Load .env file if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Use defaults if not set
BACKEND_PORT=${BACKEND_PORT:-5001}
FRONTEND_PORT=${FRONTEND_PORT:-5173}

# Define directories
BACKEND_DIR="./uix/backend"
FRONTEND_DIR="./uix/frontend"
VENV_DIR="./.venv"

# PID file
PID_FILE="./uix_pids.txt"

# Colors
GREEN="\033[0;32m"
BLUE="\033[0;34m"
NC="\033[0m"

# Activate global venv (from root)
if [ -d "$VENV_DIR" ]; then
  echo -e "${GREEN}Activating virtual environment from $VENV_DIR...${NC}"
  source "$VENV_DIR/bin/activate"
else
  echo "❌ Virtual environment not found at $VENV_DIR"
  exit 1
fi

# Clear PID file if exists
if [ -f "$PID_FILE" ]; then
  rm "$PID_FILE"
fi

# Start Flask backend
echo -e "${GREEN}Starting Flask backend on port $BACKEND_PORT...${NC}"
cd "$BACKEND_DIR"
export FLASK_APP=app.py
export FLASK_ENV=development
export BACKEND_PORT=$BACKEND_PORT
flask run --port=$BACKEND_PORT &
BACKEND_PID=$!
echo "backend:$BACKEND_PID" >> "../$PID_FILE"
cd - > /dev/null

# Start React frontend
echo -e "${GREEN}Starting React frontend (Vite) on port $FRONTEND_PORT...${NC}"
cd "$FRONTEND_DIR"
npm install
npm run dev -- --port $FRONTEND_PORT &
FRONTEND_PID=$!
echo "frontend:$FRONTEND_PID" >> "../$PID_FILE"
cd - > /dev/null

# Summary
echo -e "${GREEN}UIX is now running!${NC}"
echo -e "${BLUE}📦 Flask Backend PID:   $BACKEND_PID${NC}"
echo -e "${BLUE}🌐 React Frontend PID:  $FRONTEND_PID${NC}"
echo ""
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo "Backend : http://localhost:$BACKEND_PORT"

# Wait for both processes
wait $BACKEND_PID
wait $FRONTEND_PID

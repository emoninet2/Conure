#!/bin/bash

# Name of the virtual environment directory
VENV_DIR=".venv"

# Default Python version (change this if you want a different default)
DEFAULT_PYTHON_VERSION="3.11"

# Use argument if provided, otherwise use default
PYTHON_VERSION="${1:-$DEFAULT_PYTHON_VERSION}"
PYTHON_BIN="python${PYTHON_VERSION}"

# Check if requested Python version exists
if ! command -v "$PYTHON_BIN" &> /dev/null; then
    echo "❌ $PYTHON_BIN is not installed or not in PATH."
    echo "👉 Install it or run the script with a different version:"
    echo "   ./setup.sh 3.10"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creating virtual environment using $PYTHON_BIN in ./$VENV_DIR ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    echo "✅ Virtual environment created with $PYTHON_BIN."
else
    echo "⚠️  Virtual environment already exists in ./$VENV_DIR"
fi

# Final instructions
echo ""
echo "🚀 All set!"
echo "💡 To activate the virtual environment, run:"
echo "    source $VENV_DIR/bin/activate"
echo ""
echo "🧼 To deactivate, just run: deactivate"



# Optional: install dependencies
if [ -f "requirements.txt" ]; then
    echo ""
    echo "📦 Installing dependencies from requirements.txt ..."
    source $VENV_DIR/bin/activate
    pip install --upgrade pip > /dev/null
    pip install -r requirements.txt
    echo "✅ Dependencies installed."
    deactivate
fi


# Check if nvidia-smi exists and returns a 0 exit code
if command -v nvidia-smi &> /dev/null; then
    echo "GPU detected. Installing TensorFlow with CUDA support..."
    pip install "tensorflow[and-cuda]"
else
    echo "No GPU detected. Installing standard TensorFlow..."
    pip install tensorflow
fi



#!/bin/bash
set -e

# Name of the virtual environment directory
VENV_DIR=".venv"

# Default Python version
DEFAULT_PYTHON_VERSION="3.12"

# Use argument if provided, otherwise use default
PYTHON_VERSION="${1:-$DEFAULT_PYTHON_VERSION}"
PYTHON_BIN="python${PYTHON_VERSION}"

# Check if requested Python version exists
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
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

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# Upgrade pip inside the venv
echo ""
echo "⬆️ Upgrading pip in the virtual environment ..."
"$VENV_PIP" install --upgrade pip

# Optional: install dependencies
if [ -f "requirements.txt" ]; then
    echo ""
    echo "📦 Installing dependencies from requirements.txt ..."
    "$VENV_PIP" install -r requirements.txt
    echo "✅ Dependencies installed."
fi


# Install TensorFlow inside the venv
echo ""
if command -v nvidia-smi >/dev/null 2>&1; then
    echo "🖥️ GPU detected. Installing TensorFlow with CUDA support..."
    "$VENV_PIP" install "tensorflow[and-cuda]"
else
    echo "💻 No GPU detected. Installing standard TensorFlow..."
    "$VENV_PIP" install tensorflow
fi

# Final instructions
echo ""
echo "🚀 All set!"
echo "💡 To activate the virtual environment, run:"
echo "    source $VENV_DIR/bin/activate"
echo ""
echo "🧼 To deactivate, just run:"
echo "    deactivate"



#!/bin/bash
# Install system-level dependencies
sudo apt-get update
sudo apt-get install -y graphviz

# Install python dependencies
pip install -r requirements.txt
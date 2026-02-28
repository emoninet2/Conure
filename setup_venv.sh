#!/bin/bash

# Name of the virtual environment directory
VENV_DIR=".venv"

# Check for python3
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 is not installed or not in PATH."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creating virtual environment in ./$VENV_DIR ..."
    python3 -m venv $VENV_DIR
    echo "✅ Virtual environment created."
else
    echo "⚠️  Virtual environment already exists in ./$VENV_DIR"
fi

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


# Final instructions
echo ""
echo "🚀 All set!"
echo "💡 To activate the virtual environment, run:"
echo "    source $VENV_DIR/bin/activate"
echo ""
echo "🧼 To deactivate, just run: deactivate"

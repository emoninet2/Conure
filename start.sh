#!/bin/bash

# Function to check if python3-venv is installed and install it if not
check_and_install_python3_venv() {
    if dpkg -s python3-venv &> /dev/null; then
        echo "python3-venv is already installed."
    else
        echo "python3-venv is not installed. Installing..."
        sudo apt update
        sudo apt install -y python3-venv
    fi
}

# Function to check if a virtual environment exists, create if not
check_and_create_venv() {
    if [ -d ".venv" ]; then
        echo "Virtual environment '.venv' already exists."
    else
        echo "Virtual environment '.venv' does not exist. Creating it..."
        python3 -m venv .venv
        echo "Virtual environment '.venv' created."
    fi

    # Activate the virtual environment
    source .venv/bin/activate
    echo "Virtual environment '.venv' activated."

    # Check if pip is available in the virtual environment, and install it if missing
    if [ ! -f ".venv/bin/pip" ]; then
        echo "pip not found in the virtual environment. Installing pip..."
        python3 -m ensurepip --upgrade
        .venv/bin/pip install --upgrade pip
        echo "pip installed successfully."
    fi
}

# Function to check if pip3 is installed on the system
check_pip3() {
    if command -v pip3 &> /dev/null; then
        echo "pip3 is already installed."
    else
        echo "pip3 is not installed. Installing pip3..."
        sudo apt update
        sudo apt install -y python3-pip
    fi
}

# List of required packages
packages=("gdspy" "numpy" "flask" "datetime")

# Function to check if a package is installed in the virtual environment
check_and_install() {
    package=$1
    # Check if the package is installed
    if python3 -c "import $package" &> /dev/null; then
        echo "$package is already installed."
    else
        echo "$package is not installed. Installing..."
        pip install $package
    fi
}

# Step 1: Ensure python3-venv is installed
check_and_install_python3_venv

# Step 2: Ensure pip3 is installed on the system
check_pip3

# Step 3: Check if virtual environment exists, create and activate it if not
check_and_create_venv

# Step 4: Loop through the packages and check/install them in the virtual environment
for package in "${packages[@]}"; do
    check_and_install $package
done

echo "All packages are installed in the virtual environment '.venv'."


./startUIX.sh

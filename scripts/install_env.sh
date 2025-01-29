#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Check if the virtual environment already exists
if [ ! -d ".venv" ]; then
    echo "Creating a virtual environment..."
    python3.10 -m venv .venv
else
    echo "Virtual environment already exists. Skipping creation."
fi

# Activate the virtual environment
source .venv/bin/activate

# Install required packages without using cache
echo "Installing requirements..."
pip install -r requirements.txt --no-cache

# Install the subnet library in editable mode
echo "Installing subnet library..."
pip install -e .

# Notify the user that the setup is complete
echo "Environment setup complete."

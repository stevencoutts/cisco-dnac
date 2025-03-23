#!/bin/bash
# Run script for the Cisco Catalyst Centre CLI Tools
# Author: Steven Coutts

# Set the PYTHONPATH to include the current directory
export PYTHONPATH=$(pwd)

# Add debug output
echo "Starting Cisco Catalyst Centre CLI Tools..."
echo "PYTHONPATH: $PYTHONPATH"
echo "Current directory: $(pwd)"
echo "Python version: $(python3 --version)"

# Check for duplicate files in scripts directories
echo "Checking for module conflicts..."
find ./dnac/scripts -name "*.py.bak" 2>/dev/null || echo "No backup files found"

# Validate main file exists
if [ ! -f main.py ]; then
  echo "Error: main.py file not found!"
  exit 1
fi

echo "Running main.py..."

# Run the main application
python3 main.py --verbose 

# Add exit code information
exit_code=$?
echo "Application exited with code: $exit_code"

exit $exit_code 
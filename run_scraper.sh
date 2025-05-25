#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install or upgrade required packages
echo "Installing/upgrading required packages..."
# Configure pip to use public PyPI
pip config --user set global.index-url https://pypi.org/simple
pip install --upgrade pip
pip install --no-cache-dir python-dotenv requests beautifulsoup4 pandas python-telegram-bot

# Set Python path to include the project root
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Run the scraper with any provided arguments
echo "Running scraper..."
"$VIRTUAL_ENV/bin/python" src/main.py "$@"

# Log the run time
echo "Scraper run completed at $(date)" >> scraper.log

# Deactivate virtual environment without running the deactivate script
if [ -n "$VIRTUAL_ENV" ]; then
    # Clear VIRTUAL_ENV variable
    VIRTUAL_ENV=""
    # Remove the virtual environment's bin from PATH
    PATH=$(echo "$PATH" | tr ':' '\n' | grep -v "venv/bin" | tr '\n' ':' | sed 's/:$//')
    # Restore the original PS1 if it was modified by the virtual environment
    if [ -n "$_OLD_VIRTUAL_PS1" ]; then
        PS1="$_OLD_VIRTUAL_PS1"
        unset _OLD_VIRTUAL_PS1
    fi
fi 

# List all excluded listings
echo "Listing all excluded listings..."
"$SCRIPT_DIR/venv/bin/python" src/main.py exclusions list 
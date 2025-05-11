#!/bin/bash

echo "Starting Yad2 Scraper Worker..."

# Show debug info
echo "Current directory: $(pwd)"
echo "System time: $(date)"

# Setup Python environment
export PATH="/usr/local/bin:$PATH"
# If using virtualenv
if [ -d "/app/venv" ]; then
    echo "Activating virtual environment..."
    source /app/venv/bin/activate
fi

echo "Python location: $(which python3)"
echo "Python version: $(python3 --version)"

# Create data directory if it doesn't exist
mkdir -p /app/data

# Verify Python packages are installed
echo "Installing/Verifying required packages..."
pip3 install -r requirements.txt

echo "Installed Python packages:"
pip3 list

# Add cron job with tee to show logs in both file and stdout
# Use the Python from our environment
PYTHON_PATH=$(which python3)
echo "Using Python from: $PYTHON_PATH"

echo "0 * * * * cd /app && $PYTHON_PATH -m src.main 2>&1 | tee -a /app/data/cron.log" | crontab -

echo "Installed crontab:"
crontab -l

# Monitor cron.log and echo to stdout (this will show in Render.com logs)
tail -f /app/data/cron.log &

# Start cron daemon in foreground
cron -f
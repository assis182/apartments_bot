#!/bin/bash

echo "Starting Yad2 Scraper Worker..."

# Show debug info
echo "Current directory: $(pwd)"
echo "System time: $(date)"
echo "Python location: $(which python3)"

# Create data directory if it doesn't exist
mkdir -p /app/data

# Add cron job with tee to show logs in both file and stdout
# Use full path to python3 and ensure we're in the correct directory
echo "0 * * * * cd /app && /usr/local/bin/python3 -m src.main 2>&1 | tee -a /app/data/cron.log" | crontab -

echo "Installed crontab:"
crontab -l

# Test Python setup
echo "Testing Python setup:"
python3 --version
pip3 list | grep -E "requests|beautifulsoup4|python-dotenv"

# Monitor cron.log and echo to stdout (this will show in Render.com logs)
tail -f /app/data/cron.log &

# Start cron daemon in foreground
cron -f
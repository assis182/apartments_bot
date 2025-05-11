#!/bin/bash

echo "Starting Yad2 Scraper Worker..."

# Show debug info
echo "Current directory: $(pwd)"
echo "System time: $(date)"

# Create data directory if it doesn't exist
mkdir -p /app/data

# Add cron job with tee to show logs in both file and stdout
echo "0 * * * * cd /app && python -m src.main 2>&1 | tee -a /app/data/cron.log" | crontab -

echo "Installed crontab:"
crontab -l

# Monitor cron.log and echo to stdout (this will show in Render.com logs)
tail -f /app/data/cron.log &

# Start cron daemon in foreground
cron -f
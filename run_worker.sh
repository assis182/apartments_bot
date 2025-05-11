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

# Create a wrapper script that will be called by cron
cat > /app/run_scraper.sh << 'EOF'
#!/bin/bash
export PATH="/usr/local/bin:$PATH"
cd /app

# Setup Python environment
if [ -d "/app/venv" ]; then
    source /app/venv/bin/activate
fi

# Run the scraper
/usr/local/bin/python3 -m src.main 2>&1 | tee -a /app/data/cron.log
EOF

# Make the wrapper script executable
chmod +x /app/run_scraper.sh

# Add cron job to run the wrapper script
echo "0 * * * * /app/run_scraper.sh" | crontab -

echo "Installed crontab:"
crontab -l

# Test run the script directly
echo "Testing scraper script directly..."
/app/run_scraper.sh

# Monitor cron.log and echo to stdout (this will show in Render.com logs)
tail -f /app/data/cron.log &

# Start cron daemon in foreground
cron -f
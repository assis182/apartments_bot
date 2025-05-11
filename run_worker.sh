#!/bin/bash

# Add cron job
echo "0 * * * * cd /app && python -m src.main >> /app/data/cron.log 2>&1" | crontab -

# Start cron daemon in foreground
cron -f
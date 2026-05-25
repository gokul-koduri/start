#!/bin/bash
# Startup Research Report - Weekly Deep Collection
#
# Schedule with crontab:
#   0 3 * * 0 /Users/kodurigokul/Desktop/Startup_Research_Report/scripts/weekly_collect.sh >> /Users/kodurigokul/Desktop/Startup_Research_Report/data/logs/cron.log 2>&1
#
# This runs weekly on Sunday at 3 AM:
# - Scrapes Failory for new startup failure profiles (slow, ~30 min)
# - Runs RSS collectors for recent news
# - Generates the updated report

PROJECT_DIR="/Users/kodurigokul/Desktop/Startup_Research_Report"
cd "$PROJECT_DIR"

export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"

# Run all collectors (includes Failory which takes ~30 min at 3s delay)
python3 run_collectors.py --all

# Generate report
python3 run_report.py

echo "[$(date)] Weekly deep collection complete"

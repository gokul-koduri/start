#!/bin/bash
# Startup Research Report - Weekly Agent Pipeline
#
# Schedule with crontab:
#   0 3 * * 0 /Users/kodurigokul/Desktop/Startup_Research_Report/scripts/weekly_agent.sh >> /Users/kodurigokul/Desktop/Startup_Research_Report/data/logs/cron.log 2>&1
#
# This runs weekly on Sunday at 3 AM:
# - Searches the web for new data sources (DuckDuckGo)
# - Runs ALL collectors (including slow Failory scraping)
# - Generates the full markdown report
# - Builds the interactive HTML dashboard
# - Publishes to GitHub Pages (if git_publisher is enabled)

PROJECT_DIR="/Users/kodurigokul/Desktop/Startup_Research_Report"
cd "$PROJECT_DIR"

# Activate path
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run the weekly agent pipeline
python3 run_agent.py --pipeline weekly

echo "[$(date)] Weekly agent pipeline complete"

#!/bin/bash
# Startup Research Report - Daily Agent Pipeline
#
# Schedule with crontab:
#   0 8 * * * /Users/kodurigokul/Desktop/Startup_Research_Report/scripts/daily_agent.sh >> /Users/kodurigokul/Desktop/Startup_Research_Report/data/logs/cron.log 2>&1
#
# This runs daily at 8 AM:
# - Collects new articles from Google News and TechCrunch RSS (fast)
# - Generates the updated markdown report
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

# Run the daily agent pipeline
python3 run_agent.py --pipeline daily

echo "[$(date)] Daily agent pipeline complete"

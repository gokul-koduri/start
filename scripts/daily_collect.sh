#!/bin/bash
# Startup Research Report - Daily Data Collection + Report Generation
#
# Schedule with crontab:
#   0 8 * * * /Users/kodurigokul/Desktop/Startup_Research_Report/scripts/daily_collect.sh >> /Users/kodurigokul/Desktop/Startup_Research_Report/data/logs/cron.log 2>&1
#
# This runs daily at 8 AM:
# - Collects new articles from Google News and TechCrunch RSS
# - Generates the updated markdown report

PROJECT_DIR="/Users/kodurigokul/Desktop/Startup_Research_Report"
cd "$PROJECT_DIR"

# Activate path
export PATH="$HOME/.local/bin:$HOME/.bun/bin:$PATH"

# Run RSS collectors (fast, daily)
python3 run_collectors.py --collector google_news_rss
python3 run_collectors.py --collector techcrunch_rss

# Generate report
python3 run_report.py

echo "[$(date)] Daily collection complete"

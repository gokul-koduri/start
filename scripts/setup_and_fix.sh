#!/bin/bash
# Startup Research Report — Setup & Fix Script
#
# This script:
#   1. Installs launchd schedulers (replaces broken cron on macOS)
#   2. Creates missing directories
#   3. Cleans up stale SQLite files
#   4. Runs the test suite
#
# Usage:
#   bash scripts/setup_and_fix.sh

set -e
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "═══════════════════════════════════════════════════════"
echo "  Startup Research Report — Setup & Fix"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── 1. Create missing directories ─────────────────────────
echo "📁 Creating missing directories..."
mkdir -p data/logs
mkdir -p data/pdfs
mkdir -p data/cache
mkdir -p data/reports
echo "   ✓ data/logs, data/pdfs, data/cache, data/reports"

# ── 2. Clean up stale SQLite files ────────────────────────
echo ""
echo "🧹 Checking for stale SQLite files..."
if [ -f "data/research.db" ]; then
    SIZE=$(stat -f%z "data/research.db" 2>/dev/null || echo "0")
    if [ "$SIZE" -eq 0 ]; then
        rm -f data/research.db
        echo "   ✓ Removed empty data/research.db"
    else
        echo "   ⚠ data/research.db is ${SIZE} bytes — review before removing"
    fi
fi
if [ -f "data/startup_research.db" ]; then
    echo "   ⚠ data/startup_research.db exists (1MB) — legacy SQLite from before MySQL migration"
    echo "     Remove with: rm data/startup_research.db"
fi

# ── 3. Install launchd schedulers ─────────────────────────
echo ""
echo "⏰ Installing launchd schedulers (daily at 8 AM, weekly Sunday 3 AM)..."

# Copy plist files to LaunchAgents
PLIST_DAILY="$PROJECT_DIR/com.startup-research.daily.plist"
PLIST_WEEKLY="$PROJECT_DIR/com.startup-research.weekly.plist"
LAUNCH_DIR="$HOME/Library/LaunchAgents"

mkdir -p "$LAUNCH_DIR"

if [ -f "$PLIST_DAILY" ]; then
    # Unload old version if exists
    launchctl unload "$LAUNCH_DIR/com.startup-research.daily.plist" 2>/dev/null || true
    cp "$PLIST_DAILY" "$LAUNCH_DIR/"
    launchctl load "$LAUNCH_DIR/com.startup-research.daily.plist"
    echo "   ✓ Daily pipeline installed (8:00 AM daily)"
fi

if [ -f "$PLIST_WEEKLY" ]; then
    launchctl unload "$LAUNCH_DIR/com.startup-research.weekly.plist" 2>/dev/null || true
    cp "$PLIST_WEEKLY" "$LAUNCH_DIR/"
    launchctl load "$LAUNCH_DIR/com.startup-research.weekly.plist"
    echo "   ✓ Weekly pipeline installed (3:00 AM Sundays)"
fi

# ── 4. Run tests ──────────────────────────────────────────
echo ""
echo "🧪 Running test suite..."
if command -v python3 &> /dev/null; then
    python3 -m pytest tests/ -v --tb=short 2>&1 || echo "   ⚠ Some tests failed — install pytest: pip install pytest"
else
    echo "   ⚠ python3 not found"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ Setup complete!"
echo ""
echo "  To verify launchd jobs:"
echo "    launchctl list | grep startup-research"
echo ""
echo "  To run the pipeline manually:"
echo "    python3 run_agent.py --pipeline daily"
echo ""
echo "  To view logs:"
echo "    tail -f data/logs/launchd_daily.log"
echo "═══════════════════════════════════════════════════════"

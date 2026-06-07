#!/usr/bin/env python3
"""Weekly feedback report generator.

Usage:
    python scripts/weekly_report.py
    python scripts/weekly_report.py --output data/reports/weekly_feedback.md
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def generate_report(output_path=None):
    """Generate weekly feedback summary as markdown."""
    from db.connection import get_connection
    from db import schema

    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    now = datetime.now(timezone.utc)
    week_str = now.strftime("%G-W%V")

    # --- Feedback Analysis (latest row) ---
    cursor.execute(
        "SELECT * FROM feedback_analysis ORDER BY analyzed_at DESC LIMIT 1"
    )
    analysis = cursor.fetchone()

    # --- Raw stats ---
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM query_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    )
    queries_week = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM chat_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    )
    chats_week = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM score_feedback "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    )
    feedback_week = cursor.fetchone()["cnt"]

    # --- Top queries ---
    cursor.execute(
        "SELECT query, COUNT(*) as count FROM query_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
        "GROUP BY query ORDER BY count DESC LIMIT 10"
    )
    top_queries = cursor.fetchall()

    # --- Top feature requests ---
    cursor.execute(
        "SELECT feature, upvotes, status FROM feature_requests "
        "WHERE status = 'open' ORDER BY upvotes DESC LIMIT 10"
    )
    top_features = cursor.fetchall()

    # --- Error summary ---
    error_count = 0
    try:
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM error_log "
            "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
        )
        error_count = cursor.fetchone()["cnt"]
    except Exception:
        pass  # Table may not exist yet

    cursor.close()
    conn.close()

    # --- Build Markdown ---
    lines = [
        f"# Weekly Feedback Report: {week_str}",
        "",
        f"**Generated**: {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Search Queries | {queries_week:,} |",
        f"| Chat Questions | {chats_week:,} |",
        f"| Score Feedback | {feedback_week:,} |",
        f"| Errors | {error_count:,} |",
        "",
    ]

    if analysis:
        avg = analysis.get("avg_rating", 0) or 0
        lines.append(f"**Average Score Rating**: {avg:.1f} / 5.0")
        lines.append("")

    # Top queries table
    lines.append("## Top 10 Search Queries")
    lines.append("")
    if top_queries:
        lines.append("| Rank | Query | Count |")
        lines.append("|------|-------|-------|")
        for i, q in enumerate(top_queries, 1):
            lines.append(f"| {i} | {q['query'][:60]} | {q['count']} |")
    else:
        lines.append("_No search queries this week._")
    lines.append("")

    # Feature requests
    lines.append("## Top Feature Requests")
    lines.append("")
    if top_features:
        lines.append("| Feature | Upvotes | Status |")
        lines.append("|---------|---------|--------|")
        for f in top_features:
            lines.append(f"| {f['feature'][:60]} | {f['upvotes']} | {f['status']} |")
    else:
        lines.append("_No feature requests._")
    lines.append("")

    if error_count > 0:
        lines.append(f"## Errors ({error_count} this week)")
        lines.append("")
        lines.append("_See error_log table for details._")
        lines.append("")

    report = "\n".join(lines)

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report)

    return report


def main():
    output = None
    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i + 1 < len(sys.argv):
            output = sys.argv[i + 1]

    report = generate_report(output)
    print(report)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run sentiment agent in various modes."""

import sys
import time

sys.path.insert(0, "/Users/kodurigokul/Desktop/Startup_Research_Report")

from agents.sentiment_agent import SentimentAgent
from db.connection import get_connection

# Test 1: Fast mode (VADER)
print("=" * 60)
print("Test 1: Fast mode (VADER)")
print("=" * 60)
agent = SentimentAgent({"mode": "fast", "batch_size": 20})
start = time.time()
result = agent.execute()
elapsed = time.time() - start
print(f"Status: {result.status}")
print(f"Result data: {result.data}")
print(f"Time: {elapsed:.2f}s")

# Test 2: Check scored count after fast mode
conn = get_connection()
cursor = conn.cursor()
cursor.execute(
    "SELECT COUNT(*) as cnt FROM news_articles WHERE sentiment_score IS NULL"
)
remaining = cursor.fetchone()["cnt"]
print(f"Remaining unscored: {remaining}")

# Reset for deep mode test (optional)
# cursor.execute('UPDATE news_articles SET sentiment_score = NULL')
# conn.commit()

conn.close()

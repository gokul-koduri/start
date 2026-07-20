#!/usr/bin/env python3
"""Setup schema and run sentiment agent test."""

import sys

sys.path.insert(0, "/Users/kodurigokul/Desktop/Startup_Research_Report")

from db.connection import get_connection
from db import schema

# Initialize schema
conn = get_connection()
try:
    schema.init_schema(conn)
    print("Schema initialized")

    # Add sentiment columns
    cursor = conn.cursor()
    try:
        cursor.execute("""
            ALTER TABLE news_articles
            ADD COLUMN sentiment_score FLOAT DEFAULT NULL,
            ADD COLUMN sentiment_label VARCHAR(20) DEFAULT NULL,
            ADD COLUMN sentiment_model VARCHAR(100) DEFAULT NULL,
            ADD COLUMN sentiment_analyzed_at DATETIME DEFAULT NULL
        """)
        conn.commit()
        print("Added sentiment columns")
    except Exception as e:
        if "Duplicate" in str(e) or "already exists" in str(e).lower():
            print("Columns already exist")
        else:
            print(f"Error adding columns: {e}")

    # Check count
    cursor.execute("SELECT COUNT(*) as cnt FROM news_articles")
    result = cursor.fetchone()
    print(f'Total articles: {result["cnt"]}')

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM news_articles WHERE sentiment_score IS NULL"
    )
    result = cursor.fetchone()
    print(f'Unscored: {result["cnt"]}')

    conn.close()
except Exception as e:
    print(f"Error: {e}")

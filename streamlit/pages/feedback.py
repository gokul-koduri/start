"""Streamlit Feedback Analytics Page."""

import json


def _query_db(sql, params=None):
    """Execute a query and return list of dicts."""
    try:
        import pymysql
        from pymysql.cursors import DictCursor
        import os
        from contextlib import closing

        conn = pymysql.connect(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            port=int(os.environ.get("MYSQL_PORT", "3306")),
            user=os.environ.get("MYSQL_USER", "root"),
            password=os.environ.get("MYSQL_PASSWORD", ""),
            database=os.environ.get("MYSQL_DATABASE", "startup_research"),
            charset="utf8mb4",
            cursorclass=DictCursor,
            connect_timeout=5,
            autocommit=False,
        )
        with closing(conn.cursor()) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def render():
    """Render the feedback analytics page."""
    import streamlit as st
    import pandas as pd

    st.title("Feedback Analytics")
    st.caption("User feedback, search patterns, and feature requests")

    # --- KPI Row ---
    queries = _query_db(
        "SELECT COUNT(*) as cnt FROM query_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    )
    chats = _query_db(
        "SELECT COUNT(*) as cnt FROM chat_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    )
    feedback = _query_db(
        "SELECT COUNT(*) as cnt, AVG(rating) as avg_rating FROM score_feedback "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    )
    features = _query_db(
        "SELECT COUNT(*) as cnt FROM feature_requests WHERE status = 'open'"
    )

    q_cnt = queries[0]["cnt"] if queries else 0
    c_cnt = chats[0]["cnt"] if chats else 0
    f_cnt = feedback[0]["cnt"] if feedback else 0
    f_avg = (
        float(feedback[0]["avg_rating"])
        if feedback and feedback[0].get("avg_rating")
        else 0.0
    )
    fr_cnt = features[0]["cnt"] if features else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Searches (7d)", f"{q_cnt:,}")
    col2.metric("Chat Questions (7d)", f"{c_cnt:,}")
    col3.metric("Score Feedback (7d)", f"{f_cnt:,}")
    col4.metric("Open Features", f"{fr_cnt:,}")

    st.divider()

    # --- Top Searches ---
    st.subheader("Top Searches (Last 7 Days)")
    top_queries = _query_db(
        "SELECT query, COUNT(*) as count FROM query_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
        "GROUP BY query ORDER BY count DESC LIMIT 20"
    )
    if top_queries:
        st.dataframe(pd.DataFrame(top_queries), use_container_width=True, hide_index=True)
    else:
        st.info("No search queries recorded yet.")

    # --- Chat Questions ---
    st.subheader("Recent Chat Questions")
    recent_chats = _query_db(
        "SELECT user_message, created_at FROM chat_log "
        "ORDER BY created_at DESC LIMIT 20"
    )
    if recent_chats:
        st.dataframe(
            pd.DataFrame(recent_chats), use_container_width=True, hide_index=True
        )
    else:
        st.info("No chat questions recorded yet.")

    st.divider()

    # --- Score Ratings + Feedback Analysis ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Score Rating Distribution")
        ratings = _query_db(
            "SELECT rating, COUNT(*) as count FROM score_feedback "
            "GROUP BY rating ORDER BY rating"
        )
        if ratings:
            st.dataframe(pd.DataFrame(ratings), use_container_width=True, hide_index=True)
        else:
            st.info("No score feedback yet.")

    with col2:
        st.subheader("Feedback Analysis")
        analysis = _query_db(
            "SELECT * FROM feedback_analysis ORDER BY analyzed_at DESC LIMIT 1"
        )
        if analysis:
            a = analysis[0]
            st.metric("Avg Rating", f"{a.get('avg_rating', 0):.1f} / 5")
            st.metric("Queries Analyzed", f"{a.get('total_queries', 0):,}")
            gaps = json.loads(a.get("calibration_gaps", "[]") or "[]")
            st.metric("Calibration Gaps", len(gaps))
        else:
            st.info("No analysis yet. Run: `python run_agent.py --pipeline weekly`")

    st.divider()

    # --- Feature Requests by Upvotes ---
    st.subheader("Feature Requests by Upvotes")
    feature_reqs = _query_db(
        "SELECT feature, category, upvotes, status, created_at "
        "FROM feature_requests ORDER BY upvotes DESC LIMIT 30"
    )
    if feature_reqs:
        st.dataframe(
            pd.DataFrame(feature_reqs), use_container_width=True, hide_index=True
        )
    else:
        st.info("No feature requests submitted yet.")

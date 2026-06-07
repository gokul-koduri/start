"""Streamlit Performance Dashboard Page."""


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
    """Render the performance dashboard page."""
    import streamlit as st
    import pandas as pd

    st.title("Performance Dashboard")
    st.caption("System performance, latency metrics, and error tracking")

    # --- KPI Row ---
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    queries = _query_db(
        "SELECT COUNT(*) as cnt FROM query_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
    )
    query_count = queries[0]["cnt"] if queries else 0
    kpi1.metric("Queries (24h)", f"{query_count:,}")

    avg_resp = _query_db(
        "SELECT AVG(response_ms) as avg_ms FROM query_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) "
        "AND response_ms > 0"
    )
    avg_ms = round(avg_resp[0]["avg_ms"], 1) if avg_resp and avg_resp[0]["avg_ms"] else 0
    kpi2.metric("Avg Response (ms)", f"{avg_ms}")

    chats = _query_db(
        "SELECT COUNT(*) as cnt FROM chat_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
    )
    chat_count = chats[0]["cnt"] if chats else 0
    kpi3.metric("Chat Questions (24h)", f"{chat_count:,}")

    errors = _query_db(
        "SELECT COUNT(*) as cnt FROM error_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
    )
    error_count = errors[0]["cnt"] if errors else 0
    kpi4.metric("Errors (24h)", f"{error_count:,}")

    st.divider()

    # --- Response Time Histogram ---
    st.subheader("Response Time Distribution")
    response_data = _query_db(
        "SELECT response_ms FROM query_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
        "AND response_ms IS NOT NULL AND response_ms > 0 "
        "ORDER BY created_at DESC LIMIT 500"
    )
    if response_data:
        df = pd.DataFrame(response_data)
        st.bar_chart(df, y="response_ms")
    else:
        st.info("No response time data available yet.")

    # --- Error Types ---
    st.subheader("Error Types (7 days)")
    error_types = _query_db(
        "SELECT error_type, COUNT(*) as cnt FROM error_log "
        "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
        "GROUP BY error_type ORDER BY cnt DESC"
    )
    if error_types:
        st.dataframe(pd.DataFrame(error_types), use_container_width=True, hide_index=True)
    else:
        st.info("No errors recorded. System is healthy.")

    # --- Response Time Timeline ---
    st.subheader("Hourly Avg Response Time")
    timeline = _query_db(
        """SELECT DATE_FORMAT(created_at, '%Y-%m-%d %H:00') as hour,
                  AVG(response_ms) as avg_ms, COUNT(*) as cnt
           FROM query_log
           WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
             AND response_ms IS NOT NULL AND response_ms > 0
           GROUP BY hour ORDER BY hour"""
    )
    if timeline:
        df_tl = pd.DataFrame(timeline)
        st.line_chart(df_tl, x="hour", y="avg_ms")
    else:
        st.info("No timeline data available.")

    # --- Cache Stats ---
    st.subheader("Cache Statistics")
    try:
        import json
        import urllib.request
        req = urllib.request.Request(
            "http://localhost:8000/api/performance", method="GET"
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            perf_data = json.loads(resp.read().decode())
            cache_info = perf_data.get("cache", {})
            col1, col2 = st.columns(2)
            col1.metric("In-Memory Cache Entries", cache_info.get("in_memory_entries", "N/A"))
            col2.metric("Redis Available", "Yes" if cache_info.get("redis_available") else "No")
            if "redis_api_keys" in cache_info:
                st.metric("Redis API Keys", cache_info["redis_api_keys"])
    except Exception:
        st.info("API server not running — cache stats unavailable. Start with: python api_server.py")

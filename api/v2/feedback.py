"""Feedback API router — score ratings, feature requests, query/chat logs."""

import hashlib
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from db.connection import get_connection
from db import schema

router = APIRouter(prefix="/v2/feedback", tags=["feedback"])


def _hash_ip(request: Request) -> str:
    """Privacy-preserving IP hash for dedup and rate-limiting."""
    ip = request.client.host if request and request.client else "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


@router.post("/score")
def submit_score_feedback(request: Request, body: dict):
    """Submit feedback on a startup score.

    Body: {"entity_name": "Fisker", "rating": 4, "user_score": 55, "comment": "Pretty accurate"}
    """
    entity_name = body.get("entity_name", "").strip()
    rating = body.get("rating", 0)
    user_score = body.get("user_score")
    comment = body.get("comment", "")

    if not entity_name or rating not in (1, 2, 3, 4, 5):
        raise HTTPException(400, "entity_name and rating (1-5) required")

    ip_hash = _hash_ip(request)
    conn = get_connection()
    schema.init_schema(conn)
    try:
        with conn.cursor() as cursor:
            # Look up our score for this entity
            cursor.execute(
                "SELECT composite_score FROM opportunity_scores "
                "WHERE entity_name = %s ORDER BY scored_at DESC LIMIT 1",
                (entity_name,),
            )
            row = cursor.fetchone()
            score_given = float(row["composite_score"]) if row else None

            cursor.execute(
                "INSERT INTO score_feedback "
                "(entity_name, score_given, rating, user_score, comment, ip_hash) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (entity_name, score_given, rating, user_score, comment, ip_hash),
            )
        conn.commit()
        return {"status": "recorded", "entity_name": entity_name}
    finally:
        conn.close()


@router.post("/feature")
def submit_feature_request(request: Request, body: dict):
    """Submit or upvote a feature request.

    Body: {"feature": "Add Slack alerts for score changes", "category": "alerts"}
    """
    feature = body.get("feature", "").strip()
    category = body.get("category", "general").strip()
    ip_hash = _hash_ip(request)

    if not feature or len(feature) < 5:
        raise HTTPException(400, "feature description required (min 5 chars)")

    conn = get_connection()
    schema.init_schema(conn)
    try:
        with conn.cursor() as cursor:
            # Check for similar existing request → auto-upvote
            cursor.execute(
                "SELECT id, upvotes FROM feature_requests "
                "WHERE feature LIKE %s AND status = 'open' LIMIT 1",
                (f"%{feature[:50]}%",),
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    "UPDATE feature_requests SET upvotes = upvotes + 1 WHERE id = %s",
                    (existing["id"],),
                )
                conn.commit()
                return {
                    "status": "upvoted",
                    "id": existing["id"],
                    "upvotes": existing["upvotes"] + 1,
                }

            cursor.execute(
                "INSERT INTO feature_requests (feature, category, ip_hash) "
                "VALUES (%s, %s, %s)",
                (feature, category, ip_hash),
            )
        conn.commit()
        return {"status": "created", "feature": feature[:100]}
    finally:
        conn.close()


@router.get("/feature-requests")
def list_feature_requests(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List feature requests sorted by upvotes."""
    conn = get_connection()
    schema.init_schema(conn)
    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM feature_requests"
            params = []
            if status:
                query += " WHERE status = %s"
                params.append(status)
            query += " ORDER BY upvotes DESC, created_at DESC LIMIT %s"
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return {"feature_requests": rows, "count": len(rows)}
    finally:
        conn.close()


@router.get("/score-stats")
def get_score_feedback_stats():
    """Aggregate score feedback statistics."""
    conn = get_connection()
    schema.init_schema(conn)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) as total, AVG(rating) as avg_rating, "
                "rating, COUNT(*) as count FROM score_feedback "
                "GROUP BY rating ORDER BY rating"
            )
            by_rating = cursor.fetchall()

            cursor.execute(
                "SELECT COUNT(*) as total, AVG(rating) as avg_rating "
                "FROM score_feedback"
            )
            overall = cursor.fetchone()

            cursor.execute(
                "SELECT entity_name, COUNT(*) as feedback_count, AVG(rating) as avg_rating "
                "FROM score_feedback GROUP BY entity_name "
                "ORDER BY feedback_count DESC LIMIT 10"
            )
            top_entities = cursor.fetchall()

        return {
            "overall": overall,
            "by_rating": by_rating,
            "top_rated_entities": top_entities,
        }
    finally:
        conn.close()


@router.get("/dashboard")
def get_feedback_dashboard():
    """Full feedback dashboard data for admin view."""
    conn = get_connection()
    schema.init_schema(conn)
    try:
        with conn.cursor() as cursor:
            # Top search queries
            cursor.execute(
                "SELECT query, COUNT(*) as count FROM query_log "
                "GROUP BY query ORDER BY count DESC LIMIT 20"
            )
            top_queries = cursor.fetchall()

            # Recent chat questions
            cursor.execute(
                "SELECT user_message, created_at FROM chat_log "
                "ORDER BY created_at DESC LIMIT 20"
            )
            recent_chats = cursor.fetchall()

            # Score feedback summary
            cursor.execute(
                "SELECT COUNT(*) as total, AVG(rating) as avg_rating "
                "FROM score_feedback"
            )
            score_summary = cursor.fetchone()

            # Top feature requests
            cursor.execute(
                "SELECT * FROM feature_requests WHERE status = 'open' "
                "ORDER BY upvotes DESC LIMIT 20"
            )
            top_features = cursor.fetchall()

            # Daily counts (last 7 days)
            cursor.execute(
                "SELECT DATE(created_at) as day, COUNT(*) as queries "
                "FROM query_log WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
                "GROUP BY DATE(created_at) ORDER BY day"
            )
            daily_queries = cursor.fetchall()

        return {
            "top_queries": top_queries,
            "recent_chats": recent_chats,
            "score_feedback": score_summary,
            "top_feature_requests": top_features,
            "daily_query_counts": daily_queries,
        }
    finally:
        conn.close()

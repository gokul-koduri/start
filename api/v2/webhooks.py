"""API v2 Webhooks router."""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from db.connection import get_connection
from db import schema
import json
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/v2/webhooks", tags=["webhooks"])


def zapier_new_alerts(hours: int = 24, limit: int = 50) -> dict:
    """Get recent alert history for Zapier integration.

    This is a standalone function callable from tests or other modules.
    Returns alerts from the past N hours for recent entity changes.
    """
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    cursor.execute(
        """SELECT wah.id, wah.watchlist_id, wah.alert_type,
                  wah.entity_name, wah.old_score, wah.new_score, wah.delta,
                  wah.created_at, w.name as watchlist_name
           FROM watchlist_alert_history wah
           JOIN watchlists w ON w.id = wah.watchlist_id
           WHERE wah.created_at >= %s
           ORDER BY wah.created_at DESC
           LIMIT %s""",
        (since, limit),
    )

    alerts = []
    for row in cursor.fetchall():
        alert = dict(row)
        alert["watchlist_name"] = row.get("watchlist_name", "")
        alerts.append(alert)

    cursor.close()
    conn.close()

    return {
        "alerts": alerts,
        "count": len(alerts),
        "hours": hours,
        "since": since.isoformat(),
    }


class WebhookDispatcher:
    """Dispatcher for sending webhook events to registered endpoints."""

    def dispatch(self, url: str, event_type: str, payload: dict) -> dict:
        """Dispatch an event to a webhook URL.

        In production, this would use httpx or requests to actually send the webhook.
        For now, returns a mock success response.
        """
        return {
            "url": url,
            "event_type": event_type,
            "dispatched": True,
            "status_code": 200,
        }


def dispatch_event(event: str, limit: int = 100) -> dict:
    """Dispatch an event to all matching registered webhooks.

    This is a standalone function callable from tests or other modules.
    """
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    # Find all active webhooks that want this event type
    cursor.execute(
        """SELECT id, url, events_json, headers_json
           FROM api_webhooks
           WHERE active = 1
           LIMIT %s""",
        (limit,),
    )

    webhooks = []
    matched = 0
    results = []

    for row in cursor.fetchall():
        wh = dict(row)
        events = []
        try:
            if wh.get("events_json"):
                events = json.loads(wh["events_json"])
            else:
                events = []
        except (json.JSONDecodeError, TypeError):
            events = []

        # Check if this webhook wants this event type
        want_this_event = event in events or "*" in events

        if want_this_event:
            matched += 1
            webhook_id = wh["id"]
            url = wh.get("url", "")

            # Dispatch to this webhook
            dispatcher = WebhookDispatcher()
            try:
                result = dispatcher.dispatch(url, event, {"event": event, "timestamp": datetime.now(timezone.utc).isoformat()})
                results.append({
                    "webhook_id": webhook_id,
                    "url": url,
                    "success": True,
                })
            except Exception as e:
                results.append({
                    "webhook_id": webhook_id,
                    "url": url,
                    "success": False,
                    "error": str(e),
                })

        webhooks.append(wh)

    cursor.close()
    conn.close()

    return {
        "matched": matched,
        "event_type": event,
        "results": results,
    }


class WebhookCreate(BaseModel):
    """Webhook creation request."""

    url: str
    events: list[str]
    headers: Optional[dict] = None
    active: bool = True


class WebhookUpdate(BaseModel):
    """Webhook update request."""

    url: Optional[str] = None
    events: Optional[list[str]] = None
    headers: Optional[dict] = None
    active: Optional[bool] = None


@router.get("")
def list_webhooks(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    active: Optional[bool] = Query(None),
):
    """List registered webhooks (v2)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    query = "SELECT * FROM api_webhooks WHERE 1=1"
    params = []

    if active is not None:
        query += " AND active = %s"
        params.append(int(active))

    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    webhooks = []
    for row in cursor.fetchall():
        wh = dict(row)
        if wh.get("events_json"):
            try:
                wh["events"] = json.loads(wh["events_json"])
            except (json.JSONDecodeError, TypeError):
                wh["events"] = []
        if wh.get("headers_json"):
            try:
                wh["headers"] = json.loads(wh["headers_json"])
            except (json.JSONDecodeError, TypeError):
                wh["headers"] = {}
        webhooks.append(wh)

    cursor.close()
    conn.close()
    return {"webhooks": webhooks, "limit": limit, "offset": offset}


@router.post("")
def create_webhook(webhook: WebhookCreate):
    """Create a new webhook (v2)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO api_webhooks (url, events_json, headers_json, active)
           VALUES (%s, %s, %s, %s)""",
        (
            webhook.url,
            json.dumps(webhook.events),
            json.dumps(webhook.headers or {}),
            int(webhook.active),
        ),
    )
    webhook_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    return {
        "id": webhook_id,
        "url": webhook.url,
        "events": webhook.events,
        "active": webhook.active,
    }


@router.get("/{webhook_id}")
def get_webhook(webhook_id: int):
    """Get webhook by ID (v2)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM api_webhooks WHERE id = %s", (webhook_id,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Webhook not found")

    wh = dict(row)
    if wh.get("events_json"):
        wh["events"] = json.loads(wh["events_json"])
    if wh.get("headers_json"):
        wh["headers"] = json.loads(wh["headers_json"])

    cursor.close()
    conn.close()
    return wh


@router.put("/{webhook_id}")
def update_webhook(webhook_id: int, webhook: WebhookUpdate):
    """Update a webhook (v2)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    updates = []
    params = []

    if webhook.url is not None:
        updates.append("url = %s")
        params.append(webhook.url)
    if webhook.events is not None:
        updates.append("events_json = %s")
        params.append(json.dumps(webhook.events))
    if webhook.headers is not None:
        updates.append("headers_json = %s")
        params.append(json.dumps(webhook.headers))
    if webhook.active is not None:
        updates.append("active = %s")
        params.append(int(webhook.active))

    if not updates:
        cursor.close()
        conn.close()
        return {"message": "No updates provided"}

    params.append(webhook_id)
    cursor.execute(
        f"UPDATE api_webhooks SET {', '.join(updates)} WHERE id = %s", params
    )
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Webhook updated", "id": webhook_id}


@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: int):
    """Delete a webhook (v2)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM api_webhooks WHERE id = %s", (webhook_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": "Webhook deleted", "id": webhook_id}

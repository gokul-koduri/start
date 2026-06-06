"""API v2 Webhooks router."""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from db.connection import get_connection
from db import schema
import json

router = APIRouter(prefix="/v2/webhooks", tags=["webhooks"])


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
        )
    )
    webhook_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    return {"id": webhook_id, "url": webhook.url, "events": webhook.events, "active": webhook.active}


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
        f"UPDATE api_webhooks SET {', '.join(updates)} WHERE id = %s",
        params
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

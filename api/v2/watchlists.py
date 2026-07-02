"""API v2 Watchlists router — CRUD operations for user watchlists."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth.auth_middleware import get_current_user
from db.connection import get_connection
from db import schema

router = APIRouter(prefix="/v2/watchlists", tags=["watchlists"])


# ── Request models ──


class WatchlistCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class WatchlistItemAdd(BaseModel):
    entity_name: str
    entity_type: str = "company"
    notes: Optional[str] = None


class AlertConfigUpdate(BaseModel):
    min_delta: Optional[float] = None
    alert_on_trend_change: Optional[bool] = None
    channels: Optional[list[str]] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


# ── Helpers ──


def _verify_ownership(watchlist_id: int, user_id: int) -> dict:
    """Verify watchlist exists and belongs to user. Returns watchlist row."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM watchlists WHERE id = %s AND user_id = %s",
        (watchlist_id, user_id),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return dict(row)


def _parse_alert_config(raw: str | None) -> dict:
    """Parse alert_config_json, returning defaults if null."""
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    return {
        "min_delta": 5.0,
        "alert_on_trend_change": True,
        "channels": ["email"],
        "quiet_hours_start": None,
        "quiet_hours_end": None,
    }


# ── Watchlist CRUD ──


@router.get("")
def list_watchlists(
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List the current user's watchlists."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    user_id = user["user_id"]

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM watchlists WHERE user_id = %s", (user_id,)
    )
    total = cursor.fetchone()["cnt"]

    cursor.execute(
        """SELECT w.*,
                  (SELECT COUNT(*) FROM watchlist_items WHERE watchlist_id = w.id) as item_count
           FROM watchlists w
           WHERE w.user_id = %s
           ORDER BY w.updated_at DESC
           LIMIT %s OFFSET %s""",
        (user_id, limit, offset),
    )
    rows = [dict(r) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return {"watchlists": rows, "total": total, "limit": limit, "offset": offset}


@router.post("", status_code=201)
def create_watchlist(body: WatchlistCreate, user: dict = Depends(get_current_user)):
    """Create a new watchlist."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    user_id = user["user_id"]

    cursor.execute(
        "INSERT INTO watchlists (user_id, name, description) VALUES (%s, %s, %s)",
        (user_id, body.name, body.description),
    )
    watchlist_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM watchlists WHERE id = %s", (watchlist_id,))
    row = dict(cursor.fetchone())

    cursor.close()
    conn.close()

    return {"watchlist": row}


@router.get("/{watchlist_id}")
def get_watchlist(watchlist_id: int, user: dict = Depends(get_current_user)):
    """Get watchlist details with items."""
    wl = _verify_ownership(watchlist_id, user["user_id"])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM watchlist_items WHERE watchlist_id = %s ORDER BY added_at DESC",
        (watchlist_id,),
    )
    items = [dict(r) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    wl["items"] = items
    wl["alert_config"] = _parse_alert_config(wl.get("alert_config_json"))
    return {"watchlist": wl}


@router.put("/{watchlist_id}")
def update_watchlist(
    watchlist_id: int, body: WatchlistUpdate, user: dict = Depends(get_current_user)
):
    """Update watchlist name/description/active status."""
    _verify_ownership(watchlist_id, user["user_id"])

    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    params = []
    if body.name is not None:
        updates.append("name = %s")
        params.append(body.name)
    if body.description is not None:
        updates.append("description = %s")
        params.append(body.description)
    if body.is_active is not None:
        updates.append("is_active = %s")
        params.append(1 if body.is_active else 0)

    if not updates:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(watchlist_id)
    cursor.execute(f"UPDATE watchlists SET {', '.join(updates)} WHERE id = %s", params)
    conn.commit()

    cursor.execute("SELECT * FROM watchlists WHERE id = %s", (watchlist_id,))
    row = dict(cursor.fetchone())

    cursor.close()
    conn.close()

    return {"watchlist": row}


@router.delete("/{watchlist_id}")
def delete_watchlist(watchlist_id: int, user: dict = Depends(get_current_user)):
    """Delete a watchlist and all its items."""
    _verify_ownership(watchlist_id, user["user_id"])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM watchlists WHERE id = %s", (watchlist_id,))
    conn.commit()

    cursor.close()
    conn.close()

    return {"deleted": True, "watchlist_id": watchlist_id}


# ── Watchlist Items ──


@router.get("/{watchlist_id}/items")
def list_items(
    watchlist_id: int,
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List items in a watchlist."""
    _verify_ownership(watchlist_id, user["user_id"])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM watchlist_items WHERE watchlist_id = %s",
        (watchlist_id,),
    )
    total = cursor.fetchone()["cnt"]

    cursor.execute(
        """SELECT wi.*, os.composite_score, os.trend_direction
           FROM watchlist_items wi
           LEFT JOIN opportunity_scores os
             ON wi.entity_name = os.entity_name AND wi.entity_type = os.entity_type
           WHERE wi.watchlist_id = %s
           ORDER BY wi.added_at DESC
           LIMIT %s OFFSET %s""",
        (watchlist_id, limit, offset),
    )
    items = [dict(r) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("/{watchlist_id}/items", status_code=201)
def add_item(
    watchlist_id: int, body: WatchlistItemAdd, user: dict = Depends(get_current_user)
):
    """Add an entity to a watchlist."""
    _verify_ownership(watchlist_id, user["user_id"])

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """INSERT INTO watchlist_items (watchlist_id, entity_name, entity_type, notes)
               VALUES (%s, %s, %s, %s)""",
            (watchlist_id, body.entity_name, body.entity_type, body.notes),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        if "Duplicate" in str(e) or "uq_wl_item" in str(e):
            raise HTTPException(
                status_code=409,
                detail=f"Entity '{body.entity_name}' already in this watchlist",
            )
        raise HTTPException(status_code=500, detail=str(e))

    item_id = cursor.lastrowid
    cursor.execute("SELECT * FROM watchlist_items WHERE id = %s", (item_id,))
    row = dict(cursor.fetchone())

    cursor.close()
    conn.close()

    return {"item": row}


@router.delete("/{watchlist_id}/items/{item_id}")
def remove_item(
    watchlist_id: int, item_id: int, user: dict = Depends(get_current_user)
):
    """Remove an entity from a watchlist."""
    _verify_ownership(watchlist_id, user["user_id"])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM watchlist_items WHERE id = %s AND watchlist_id = %s",
        (item_id, watchlist_id),
    )
    deleted = cursor.rowcount
    conn.commit()

    cursor.close()
    conn.close()

    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")

    return {"deleted": True, "item_id": item_id}


# ── Alert History ──


@router.get("/{watchlist_id}/alerts")
def list_alerts(
    watchlist_id: int,
    user: dict = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get alert history for a watchlist."""
    _verify_ownership(watchlist_id, user["user_id"])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM watchlist_alert_history WHERE watchlist_id = %s",
        (watchlist_id,),
    )
    total = cursor.fetchone()["cnt"]

    cursor.execute(
        """SELECT * FROM watchlist_alert_history
           WHERE watchlist_id = %s
           ORDER BY created_at DESC
           LIMIT %s OFFSET %s""",
        (watchlist_id, limit, offset),
    )
    alerts = [dict(r) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return {"alerts": alerts, "total": total, "limit": limit, "offset": offset}


# ── Alert Configuration ──


@router.put("/{watchlist_id}/alert-config")
def update_alert_config(
    watchlist_id: int,
    body: AlertConfigUpdate,
    user: dict = Depends(get_current_user),
):
    """Update alert configuration for a watchlist."""
    _verify_ownership(watchlist_id, user["user_id"])

    conn = get_connection()
    cursor = conn.cursor()

    # Get current config
    cursor.execute(
        "SELECT alert_config_json FROM watchlists WHERE id = %s", (watchlist_id,)
    )
    row = cursor.fetchone()
    current = _parse_alert_config(row["alert_config_json"] if row else None)

    # Merge updates
    if body.min_delta is not None:
        current["min_delta"] = body.min_delta
    if body.alert_on_trend_change is not None:
        current["alert_on_trend_change"] = body.alert_on_trend_change
    if body.channels is not None:
        current["channels"] = body.channels
    if body.quiet_hours_start is not None:
        current["quiet_hours_start"] = body.quiet_hours_start
    if body.quiet_hours_end is not None:
        current["quiet_hours_end"] = body.quiet_hours_end

    cursor.execute(
        "UPDATE watchlists SET alert_config_json = %s WHERE id = %s",
        (json.dumps(current), watchlist_id),
    )
    conn.commit()

    cursor.close()
    conn.close()

    return {"alert_config": current}

"""API v2 Alert Preferences — per-user notification settings."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pydantic import Field

from auth.auth_middleware import get_current_user
from db.connection import get_connection
from db import schema

router = APIRouter(prefix="/v2/alert-preferences", tags=["alerts"])


class AlertPreferencesUpdate(BaseModel):
    """Fields the user can update. All optional for partial updates."""

    email_enabled: bool | None = None
    slack_enabled: bool | None = None
    discord_enabled: bool | None = None
    webhook_enabled: bool | None = None
    min_score_threshold: float | None = None
    quiet_hours_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    max_alerts_per_hour: int | None = None


_DEFAULTS = {
    "email_enabled": True,
    "slack_enabled": False,
    "discord_enabled": False,
    "webhook_enabled": False,
    "min_score_threshold": 80.0,
    "quiet_hours_start": None,
    "quiet_hours_end": None,
    "max_alerts_per_hour": 20,
}


@router.get("")
def get_preferences(user: dict = Depends(get_current_user)):
    """Get the current user's alert preferences.

    Returns defaults if the user has never saved preferences.
    """
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()
    user_id = user["user_id"]

    cursor.execute("SELECT * FROM alert_preferences WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if row:
        return {"preferences": _row_to_preferences(dict(row))}

    # Return sensible defaults
    return {"preferences": dict(_DEFAULTS)}


@router.put("", status_code=200)
def update_preferences(
    body: AlertPreferencesUpdate,
    user: dict = Depends(get_current_user),
):
    """Update the current user's alert preferences."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()
    user_id = user["user_id"]

    # Build dynamic UPDATE SET clause
    updates = []
    params = []

    def _add(field: str, value) -> None:
        updates.append(f"{field} = %s")
        params.append(value)

    if body.email_enabled is not None:
        _add("email_enabled", 1 if body.email_enabled else 0)
    if body.slack_enabled is not None:
        _add("slack_enabled", 1 if body.slack_enabled else 0)
    if body.discord_enabled is not None:
        _add("discord_enabled", 1 if body.discord_enabled else 0)
    if body.webhook_enabled is not None:
        _add("webhook_enabled", 1 if body.webhook_enabled else 0)
    if body.min_score_threshold is not None:
        _add("min_score_threshold", body.min_score_threshold)
    if body.quiet_hours_start is not None:
        _add("quiet_hours_start", body.quiet_hours_start)
    if body.quiet_hours_end is not None:
        _add("quiet_hours_end", body.quiet_hours_end)
    if body.max_alerts_per_hour is not None:
        _add("max_alerts_per_hour", body.max_alerts_per_hour)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Upsert: UPDATE if exists, INSERT if not
    cursor.execute("SELECT id FROM alert_preferences WHERE user_id = %s", (user_id,))
    exists = cursor.fetchone() is not None

    if exists:
        params.append(user_id)
        cursor.execute(
            f"UPDATE alert_preferences SET {', '.join(updates)} WHERE user_id = %s",
            params,
        )
    else:
        # Insert with defaults for omitted fields
        insert_fields = []
        insert_vals = []
        for field in [
            "email_enabled",
            "slack_enabled",
            "discord_enabled",
            "webhook_enabled",
            "min_score_threshold",
            "quiet_hours_start",
            "quiet_hours_end",
            "max_alerts_per_hour",
        ]:
            # Map the Pydantic field name to the actual DB column name
            val = getattr(body, field, None)
            if val is not None:
                insert_fields.append(field)
                if isinstance(val, bool):
                    insert_vals.append(1 if val else 0)
                else:
                    insert_vals.append(val)

        def _get_param(fld: str):
            v = getattr(body, fld, None)
            if v is None:
                return _DEFAULTS[fld]
            return 1 if isinstance(v, bool) else v

        cursor.execute(
            """INSERT INTO alert_preferences
               (user_id, email_enabled, slack_enabled, discord_enabled,
                webhook_enabled, min_score_threshold, quiet_hours_start,
                quiet_hours_end, max_alerts_per_hour)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                _get_param("email_enabled"),
                _get_param("slack_enabled"),
                _get_param("discord_enabled"),
                _get_param("webhook_enabled"),
                _get_param("min_score_threshold"),
                _get_param("quiet_hours_start"),
                _get_param("quiet_hours_end"),
                _get_param("max_alerts_per_hour"),
            ),
        )

    conn.commit()
    cursor.execute("SELECT * FROM alert_preferences WHERE user_id = %s", (user_id,))
    row = dict(cursor.fetchone())
    cursor.close()
    conn.close()

    return {"preferences": _row_to_preferences(row)}


def _row_to_preferences(row: dict) -> dict:
    """Convert DB row to API response (normalize int booleans)."""
    return {
        "id": row.get("id"),
        "email_enabled": bool(row.get("email_enabled", 1)),
        "slack_enabled": bool(row.get("slack_enabled", 0)),
        "discord_enabled": bool(row.get("discord_enabled", 0)),
        "webhook_enabled": bool(row.get("webhook_enabled", 0)),
        "min_score_threshold": row.get("min_score_threshold", 80.0),
        "quiet_hours_start": row.get("quiet_hours_start"),
        "quiet_hours_end": row.get("quiet_hours_end"),
        "max_alerts_per_hour": row.get("max_alerts_per_hour", 20),
    }

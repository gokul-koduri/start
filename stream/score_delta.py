"""Score delta calculation — computes and tracks score changes over time.

When a new score is computed for an entity, this module:
1. Reads the previous score from opportunity_scores
2. Calculates the delta (change) and signal-level breakdown
3. Stores the delta in score_deltas table for historical tracking
4. Returns a delta dict suitable for WebSocket broadcast

Usage:
    from stream.score_delta import calculate_and_store_delta

    delta = calculate_and_store_delta(conn, new_score_dict)
    # delta = {"entity_name": "Tesla", "old_score": 78.0, "new_score": 82.0,
    #          "change": 4.0, "signal_deltas": {"funding": +2, "market": +2}}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger(__name__)


def calculate_score_delta(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    """Calculate the delta between current and previous score.

    Args:
        current: New score dict from CompositeScorer with keys:
            entity_name, entity_type, composite_score, trend_direction, attribution
        previous: Previous score dict from opportunity_scores row, or None if
            this is the first score for this entity.

    Returns:
        Delta dict with keys:
            entity_name, entity_type, old_score, new_score, change,
            trend_previous, trend_current, signal_deltas, detected_at
    """
    new_score = current.get("composite_score", 0.0)
    entity_name = current.get("entity_name", "")
    entity_type = current.get("entity_type", "company")

    if previous is None:
        return {
            "entity_name": entity_name,
            "entity_type": entity_type,
            "old_score": None,
            "new_score": new_score,
            "change": new_score,
            "trend_previous": None,
            "trend_current": current.get("trend_direction", "stable"),
            "signal_deltas": _extract_signal_contributions(current.get("attribution", [])),
            "is_first_score": True,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }

    old_score = previous.get("composite_score", 0.0)
    change = round(new_score - old_score, 2)

    # Calculate signal-level deltas
    signal_deltas = _compute_signal_deltas(
        current.get("attribution", []),
        previous.get("attribution", []),
    )

    return {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "old_score": old_score,
        "new_score": new_score,
        "change": change,
        "trend_previous": previous.get("trend_direction", "stable"),
        "trend_current": current.get("trend_direction", "stable"),
        "signal_deltas": signal_deltas,
        "is_first_score": False,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


def calculate_and_store_delta(conn, current: dict[str, Any]) -> dict[str, Any] | None:
    """Calculate a score delta, store it in score_deltas, and return it.

    Reads the previous score from opportunity_scores, computes the delta,
    and inserts into score_deltas. Returns None if no change detected.

    Args:
        conn: MySQL connection with DictCursor.
        current: New score dict from CompositeScorer.

    Returns:
        Delta dict, or None if this is a duplicate (no change).
    """
    entity_name = current.get("entity_name", "")
    entity_type = current.get("entity_type", "company")
    new_score = current.get("composite_score", 0.0)

    try:
        cursor = conn.cursor()

        # Fetch previous score
        cursor.execute(
            """SELECT composite_score, trend_direction, attribution_json
               FROM opportunity_scores
               WHERE entity_name = %s AND entity_type = %s""",
            (entity_name, entity_type),
        )
        row = cursor.fetchone()
        previous = None
        if row:
            previous = {
                "composite_score": row["composite_score"],
                "trend_direction": row.get("trend_direction", "stable"),
                "attribution": json.loads(row.get("attribution_json", "[]")),
            }

        delta = calculate_score_delta(current, previous)

        # Skip if no meaningful change (first score or same value)
        if delta["is_first_score"]:
            _store_delta(cursor, delta)
            cursor.close()
            return delta

        if abs(delta["change"]) < 0.01:
            cursor.close()
            return None

        _store_delta(cursor, delta)
        cursor.close()
        return delta

    except Exception as e:
        _logger.error("Failed to calculate delta for %s: %s", entity_name, e)
        return None


def _store_delta(cursor, delta: dict[str, Any]):
    """Insert a score delta into the score_deltas table."""
    signal_json = json.dumps(delta.get("signal_deltas", {}))
    cursor.execute(
        """INSERT INTO score_deltas
           (entity_name, entity_type, old_score, new_score, delta,
            trend_previous, trend_current, signal_breakdown_json, detected_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            delta["entity_name"],
            delta["entity_type"],
            delta.get("old_score"),
            delta["new_score"],
            delta["change"],
            delta.get("trend_previous"),
            delta["trend_current"],
            signal_json,
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )


def _extract_signal_contributions(attribution: list) -> dict[str, float]:
    """Extract signal type → contribution from attribution list."""
    result = {}
    for item in attribution:
        if isinstance(item, dict):
            sig_type = item.get("signal_type", "unknown")
            contribution = item.get("contribution_pct", 0.0)
            result[sig_type] = contribution
    return result


def _compute_signal_deltas(
    current_attribution: list,
    previous_attribution: list,
) -> dict[str, float]:
    """Compute per-signal contribution changes between current and previous.

    Returns:
        Dict mapping signal_type to change in contribution_pct.
    """
    current_map = _extract_signal_contributions(current_attribution)
    previous_map = _extract_signal_contributions(previous_attribution)

    all_signals = set(current_map.keys()) | set(previous_map.keys())
    deltas = {}
    for signal in all_signals:
        curr = current_map.get(signal, 0.0)
        prev = previous_map.get(signal, 0.0)
        change = round(curr - prev, 2)
        if abs(change) > 0.01:
            deltas[signal] = change

    return deltas


def format_delta_message(delta: dict[str, Any]) -> str:
    """Format a score delta into a human-readable string.

    Example: "Tesla 78→82 (+4): Funding +2, Market +2"
    """
    entity = delta.get("entity_name", "Unknown")
    old = delta.get("old_score")
    new = delta.get("new_score", 0)
    change = delta.get("change", 0)

    if old is None:
        return f"{entity} → {new:.0f} (new)"

    sign = "+" if change >= 0 else ""
    parts = [f"{entity} {old:.0f}→{new:.0f} ({sign}{change:.1f})"]

    signal_deltas = delta.get("signal_deltas", {})
    if signal_deltas:
        signal_parts = []
        for sig, val in sorted(signal_deltas.items(), key=lambda x: abs(x[1]), reverse=True)[:3]:
            s = "+" if val >= 0 else ""
            signal_parts.append(f"{sig} {s}{val:.1f}")
        parts.append(": " + ", ".join(signal_parts))

    return "".join(parts)

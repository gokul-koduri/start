"""Ollama usage tracking — reads local inference data and computes cost equivalence.

This is a utility module (not a BaseAgent) that:
- Tracks token usage from Ollama /api/chat responses via a rolling JSON file
- Computes cost equivalence across external LLM providers
- Takes periodic snapshots stored in the database for trend analysis
"""

import json
import logging
from datetime import datetime, timezone

from config import get_project_root
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

TRACKER_FILE = get_project_root() / "data" / "cache" / "ollama_token_tracker.json"
MAX_TRACKER_ENTRIES = 10_000


def _track_inference(model_name: str, prompt_tokens: int, completion_tokens: int) -> None:
    """Append inference data to the rolling tracker file.

    This is called by the dashboard's ``_ollama_api()`` helper whenever a
    ``/api/chat`` response includes token counts.
    """
    tracker: dict = {"entries": [], "totals": {}}
    if TRACKER_FILE.exists():
        try:
            tracker = json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
    tracker["entries"].append(entry)

    # Keep only the most recent entries to prevent unbounded growth
    tracker["entries"] = tracker["entries"][-MAX_TRACKER_ENTRIES:]

    # Recompute cumulative totals
    tracker["totals"] = {
        "total_prompt_tokens": sum(e["prompt_tokens"] for e in tracker["entries"]),
        "total_completion_tokens": sum(e["completion_tokens"] for e in tracker["entries"]),
        "total_tokens": sum(e["total_tokens"] for e in tracker["entries"]),
        "inference_count": len(tracker["entries"]),
    }

    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRACKER_FILE.write_text(json.dumps(tracker, indent=2), encoding="utf-8")


def compute_cost_equivalence(
    prompt_tokens: int, completion_tokens: int, pricing_data: list[dict]
) -> dict[str, float]:
    """Compute what the given tokens would cost across external providers.

    Args:
        prompt_tokens: number of input tokens consumed
        completion_tokens: number of output tokens generated
        pricing_data: list of pricing rows from the ``llm_pricing`` table
            (each dict must have ``provider``, ``model_name``,
            ``input_price_per_1m``, ``output_price_per_1m``)

    Returns:
        dict mapping display names (e.g. ``"OpenAI — GPT-4o"``) to estimated USD cost
    """
    costs: dict[str, float] = {}
    seen_providers: set[str] = set()

    # Use one model per provider for a clean comparison
    for row in sorted(pricing_data, key=lambda r: (r["provider"], r["input_price_per_1m"])):
        provider = row["provider"]
        if provider in seen_providers:
            continue
        seen_providers.add(provider)

        input_cost = (prompt_tokens / 1_000_000) * row["input_price_per_1m"]
        output_cost = (completion_tokens / 1_000_000) * row["output_price_per_1m"]
        costs[f"{provider.title()} — {row['model_name']}"] = round(input_cost + output_cost, 4)

    return costs


def take_usage_snapshot(conn=None) -> dict:
    """Take a snapshot of current Ollama usage and store in the database.

    Reads the tracker file for cumulative totals, computes delta from the
    last DB snapshot, estimates cost equivalence, and inserts a new row.

    Returns the snapshot dict with current totals and cost equivalence.
    """
    snapshot: dict = {
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_tokens": 0,
        "inference_count": 0,
        "cost_equivalence": {},
        "delta_prompt_tokens": 0,
        "delta_completion_tokens": 0,
    }

    # Read tracker file
    if not TRACKER_FILE.exists():
        return snapshot
    try:
        tracker = json.loads(TRACKER_FILE.read_text(encoding="utf-8"))
        totals = tracker.get("totals", {})
        snapshot["total_prompt_tokens"] = totals.get("total_prompt_tokens", 0)
        snapshot["total_completion_tokens"] = totals.get("total_completion_tokens", 0)
        snapshot["total_tokens"] = totals.get("total_tokens", 0)
        snapshot["inference_count"] = totals.get("inference_count", 0)
    except (json.JSONDecodeError, OSError):
        return snapshot

    # Open DB connection if not provided
    own_conn = conn is None
    if own_conn:
        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            _logger.warning("ollama_usage_tracker: Could not connect to DB: %s", e)
            return snapshot

    try:
        cursor = conn.cursor()

        # Read the last snapshot for delta
        cursor.execute(
            "SELECT prompt_tokens, completion_tokens FROM ollama_usage_snapshots "
            "ORDER BY snapshot_at DESC LIMIT 1"
        )
        last = cursor.fetchone()

        if last:
            snapshot["delta_prompt_tokens"] = snapshot["total_prompt_tokens"] - last["prompt_tokens"]
            snapshot["delta_completion_tokens"] = snapshot["total_completion_tokens"] - last["completion_tokens"]
        else:
            snapshot["delta_prompt_tokens"] = snapshot["total_prompt_tokens"]
            snapshot["delta_completion_tokens"] = snapshot["total_completion_tokens"]

        # Read pricing data for cost equivalence
        cursor.execute(
            "SELECT provider, model_name, input_price_per_1m, output_price_per_1m "
            "FROM llm_pricing ORDER BY provider, input_price_per_1m"
        )
        pricing_rows = [dict(r) for r in cursor.fetchall()]

        costs = compute_cost_equivalence(
            snapshot["delta_prompt_tokens"],
            snapshot["delta_completion_tokens"],
            pricing_rows,
        )
        snapshot["cost_equivalence"] = costs

        # Determine model name from the most recent tracker entry
        entries = tracker.get("entries", [])
        model_name = entries[-1]["model"] if entries else "unknown"

        # Determine VRAM from Ollama
        vram_usage = 0
        try:
            import urllib.request
            with urllib.request.urlopen("http://localhost:11434/api/ps", timeout=5) as resp:
                ps = json.loads(resp.read().decode())
                vram_usage = sum(m.get("vram", 0) for m in ps.get("models", []))
        except Exception:
            pass

        # Insert snapshot
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            """INSERT INTO ollama_usage_snapshots
               (snapshot_at, model_name, prompt_tokens, completion_tokens,
                total_tokens, inference_count, vram_usage_bytes, cost_equivalence_json)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                now,
                model_name,
                snapshot["total_prompt_tokens"],
                snapshot["total_completion_tokens"],
                snapshot["total_tokens"],
                snapshot["inference_count"],
                vram_usage,
                json.dumps(costs) if costs else None,
            ),
        )
        conn.commit()
        cursor.close()

    except Exception as e:
        _logger.warning("ollama_usage_tracker: Snapshot failed: %s", e)
    finally:
        if own_conn:
            conn.close()

    return snapshot

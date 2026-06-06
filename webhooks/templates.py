"""Webhook event payload templates."""

from typing import Dict, Any


TEMPLATES: Dict[str, Dict[str, Any]] = {
    "opportunity_scored": {
        "description": "An opportunity was scored or updated",
        "payload_schema": {
            "event": "opportunity_scored",
            "timestamp": "ISO 8601 datetime",
            "data": {
                "entity_name": "string",
                "entity_type": "company|technology|market",
                "composite_score": "float 0-100",
                "trend_direction": "rising|falling|stable",
                "signal_count": "int",
            }
        }
    },
    "signal_collected": {
        "description": "A raw signal was collected",
        "payload_schema": {
            "event": "signal_collected",
            "timestamp": "ISO 8601 datetime",
            "data": {
                "signal_type": "string",
                "source_name": "string",
                "entity_name": "string (optional)",
                "title": "string",
            }
        }
    },
    "pipeline_completed": {
        "description": "A pipeline execution completed",
        "payload_schema": {
            "event": "pipeline_completed",
            "timestamp": "ISO 8601 datetime",
            "data": {
                "pipeline_name": "string",
                "status": "success|partial|failed",
                "duration_seconds": "float",
                "agents_run": "int",
            }
        }
    },
    "agent_failed": {
        "description": "An agent execution failed",
        "payload_schema": {
            "event": "agent_failed",
            "timestamp": "ISO 8601 datetime",
            "data": {
                "agent_name": "string",
                "pipeline_name": "string",
                "error_message": "string",
            }
        }
    },
}


def build_payload(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a webhook payload from event data.

    Args:
        event_type: Event type
        data: Event data

    Returns:
        Complete payload dictionary
    """
    from datetime import datetime, timezone

    template = TEMPLATES.get(event_type, {})
    return {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }

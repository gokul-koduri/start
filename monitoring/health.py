"""Health check endpoints."""

import datetime
import logging
import shutil
from typing import Dict

_logger = logging.getLogger(__name__)


def check_database_health() -> Dict:
    """Check database connectivity."""
    try:
        from db.connection import get_connection

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy", "message": "Database connected"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


def check_redis_health() -> Dict:
    """Check Redis connectivity."""
    try:
        import redis

        r = redis.from_url("redis://localhost:6379/0", socket_connect_timeout=2)
        r.ping()
        r.close()
        return {"status": "healthy", "message": "Redis connected"}
    except Exception as e:
        return {"status": "unhealthy", "message": str(e)}


def check_disk_space() -> Dict:
    """Check available disk space."""
    try:
        usage = shutil.disk_usage("/")
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        usage_pct = (usage.used / usage.total) * 100

        if usage_pct > 90:
            status = "critical"
        elif usage_pct > 75:
            status = "warning"
        else:
            status = "healthy"

        return {
            "status": status,
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "usage_percent": round(usage_pct, 2),
        }
    except Exception as e:
        return {"status": "unknown", "message": str(e)}


def get_health_status() -> Dict:
    """Get overall health status."""
    return {
        "database": check_database_health(),
        "redis": check_redis_health(),
        "disk": check_disk_space(),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

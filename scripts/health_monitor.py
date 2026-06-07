#!/usr/bin/env python3
"""Health monitor — run as a cron job to check platform health.

Usage:
    python scripts/health_monitor.py           # Human-readable summary
    python scripts/health_monitor.py --json     # JSON output for logging

Exit codes: 0 = healthy, 1 = degraded, 2 = critical.

Cron setup (every 5 minutes):
    */5 * * * * cd /path/to/project && python scripts/health_monitor.py --json >> data/logs/health.log 2>&1
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_mysql() -> dict:
    """Check MySQL connectivity and basic stats."""
    try:
        from db.connection import get_connection
        from contextlib import closing
        with closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.execute("SELECT COUNT(*) as cnt FROM signal_events")
            signal_count = cursor.fetchone()["cnt"]
            cursor.execute(
                "SELECT MAX(collected_at) as latest FROM signal_events"
            )
            row = cursor.fetchone()
            latest = str(row["latest"]) if row and row["latest"] else "never"
            cursor.close()
        return {"status": "healthy", "signals": signal_count, "latest_signal": latest}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_redis() -> dict:
    """Check Redis connectivity (graceful if not installed)."""
    try:
        import redis
        r = redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            socket_connect_timeout=2,
        )
        r.ping()
        info = r.info("memory")
        r.close()
        return {"status": "healthy", "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 1)}
    except ImportError:
        return {"status": "not_installed", "error": "redis-py not installed"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_disk() -> dict:
    """Check disk space."""
    try:
        usage = shutil.disk_usage(str(PROJECT_ROOT))
        free_gb = round(usage.free / (1024**3), 2)
        total_gb = round(usage.total / (1024**3), 2)
        pct = round((usage.used / usage.total) * 100, 1)

        if pct > 90:
            status = "critical"
        elif pct > 75:
            status = "warning"
        else:
            status = "healthy"

        return {"status": status, "free_gb": free_gb, "total_gb": total_gb, "usage_percent": pct}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def check_api(port: int = 8000) -> dict:
    """Check if API server is responding."""
    try:
        url = f"http://localhost:{port}/api/health"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                return {"status": "healthy", "url": url}
            return {"status": "unhealthy", "http_status": resp.status}
    except urllib.error.URLError:
        return {"status": "not_running", "error": f"API not reachable on port {port}"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_docker() -> dict:
    """Check Docker Compose service status."""
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            return {"status": "not_available", "error": result.stderr.strip()[:200]}

        services = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                svc = json.loads(line)
                services.append({
                    "name": svc.get("Name", svc.get("Service", "unknown")),
                    "state": svc.get("State", "unknown"),
                    "health": svc.get("Health", "unknown"),
                })
            except json.JSONDecodeError:
                continue

        running = [s for s in services if s["state"] == "running"]
        unhealthy = [s for s in running if s.get("health") == "unhealthy"]

        if unhealthy:
            return {"status": "degraded", "unhealthy": [s["name"] for s in unhealthy], "running": len(running)}
        return {"status": "healthy", "running": len(running), "total": len(services)}
    except FileNotFoundError:
        return {"status": "not_installed", "error": "docker compose not found"}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "docker compose ps timed out"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_pipeline_freshness() -> dict:
    """Check that the pipeline has run recently."""
    try:
        from db.connection import get_connection
        from contextlib import closing
        with closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(started_at) as latest FROM pipeline_runs"
            )
            row = cursor.fetchone()
            cursor.close()
        if not row or not row["latest"]:
            return {"status": "warning", "message": "No pipeline runs recorded"}
        latest = row["latest"]
        if isinstance(latest, str):
            latest = datetime.fromisoformat(latest.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
        if age_hours > 48:
            return {"status": "critical", "hours_since_last_run": round(age_hours, 1)}
        elif age_hours > 24:
            return {"status": "warning", "hours_since_last_run": round(age_hours, 1)}
        return {"status": "healthy", "hours_since_last_run": round(age_hours, 1)}
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def check_errors() -> dict:
    """Check recent error rate from error_log table (T-049)."""
    try:
        from db.connection import get_connection
        from contextlib import closing
        with closing(get_connection()) as conn:
            cursor = conn.cursor()
            # Errors in last hour
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM error_log "
                "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)"
            )
            hourly_errors = cursor.fetchone()["cnt"]
            # Errors in last 24 hours
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM error_log "
                "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)"
            )
            daily_errors = cursor.fetchone()["cnt"]
            # Most common error types
            cursor.execute(
                "SELECT error_type, COUNT(*) as cnt FROM error_log "
                "WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) "
                "GROUP BY error_type ORDER BY cnt DESC LIMIT 5"
            )
            top_errors = [dict(r) for r in cursor.fetchall()]
            cursor.close()

        if hourly_errors > 50:
            status = "critical"
        elif hourly_errors > 10:
            status = "warning"
        elif daily_errors > 100:
            status = "warning"
        else:
            status = "healthy"

        return {
            "status": status,
            "hourly_errors": hourly_errors,
            "daily_errors": daily_errors,
            "top_error_types": top_errors,
        }
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def run_all_checks() -> dict:
    """Run all health checks and return combined report."""
    checks = {
        "mysql": check_mysql(),
        "redis": check_redis(),
        "disk": check_disk(),
        "api": check_api(),
        "docker": check_docker(),
        "pipeline": check_pipeline_freshness(),
        "errors": check_errors(),
    }

    # Determine overall status
    statuses = []
    for result in checks.values():
        s = result.get("status", "unknown")
        if s in ("critical", "unhealthy", "not_running"):
            statuses.append(2)
        elif s in ("warning", "degraded", "not_installed"):
            statuses.append(1)
        else:
            statuses.append(0)

    overall = max(statuses) if statuses else 1
    overall_label = {0: "healthy", 1: "degraded", 2: "critical"}.get(overall, "unknown")

    return {
        "overall": overall_label,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


def main():
    """Run checks and print report."""
    report = run_all_checks()
    json_mode = "--json" in sys.argv

    if json_mode:
        print(json.dumps(report, indent=2, default=str))
    else:
        print("=" * 55)
        print(f"  Health Monitor  —  {report['overall'].upper()}")
        print("=" * 55)
        for name, result in report["checks"].items():
            status = result.get("status", "unknown")
            icon = {"healthy": "+", "degraded": "~", "warning": "?",
                    "unhealthy": "X", "critical": "!", "not_running": "X",
                    "not_installed": "-", "not_available": "-", "unknown": "?", "timeout": "!"}
            color = {"healthy": "\033[92m", "degraded": "\033[93m", "warning": "\033[93m",
                     "unhealthy": "\033[91m", "critical": "\033[91m", "not_running": "\033[91m",
                     "not_installed": "\033[90m", "not_available": "\033[90m", "unknown": "\033[93m",
                     "timeout": "\033[91m"}
            i = icon.get(status, "?")
            c = color.get(status, "\033[0m")
            r = "\033[0m"
            detail = ""
            for key in ("error", "signals", "free_gb", "running", "hours_since_last_run"):
                if key in result:
                    detail = f" ({key}: {result[key]})"
                    break
            print(f"  [{i}] {c}{name:10s}{r}  {status}{detail}")
        print("=" * 55)

    exit_code = {"healthy": 0, "degraded": 1, "critical": 2}.get(report["overall"], 1)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

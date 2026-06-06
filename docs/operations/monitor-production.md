# 📊 Monitor Production — Logs, Errors, Performance, Business Metrics

> "You can't improve what you don't measure."
> — Peter Drucker (adapted for software)

---

## Why This Document Exists

Your platform is 83% built. You have 207 Python files, 62 agents, 34 API endpoints, 11 Docker services. When you deploy, things will break. The only question is: **will you know when they break, and will you know why?**

**Current monitoring audit:**

| What | Status | Gap |
|---|---|---|
| Health endpoint (`/api/health`) | ✅ Checks MySQL | Only MySQL, not Redis/Kafka/Ollama/Qdrant |
| Stream metrics (`stream/metrics.py`) | ✅ 11 counters in Redis | Not visualized, no alerting |
| Prometheus registry (`monitoring/metrics.py`) | ✅ 5 metrics defined | `prometheus_client` not in requirements.txt |
| Health module (`monitoring/health.py`) | ✅ DB + Redis + disk | Not wired to `/api/health` endpoint |
| Agent run tracking | ✅ `agent_runs` table | No dashboard, no failure alerting |
| Collector run tracking | ✅ `collection_runs` table | No dashboard, no failure alerting |
| Log files | ⚠️ `data/logs/collector.log` | Only collector logs, no API logs |
| Docker logs | ⚠️ Docker default (json) | No centralized logging |
| Error tracking | ❌ None | No Sentry, no error aggregation |
| Performance monitoring | ❌ None | No APM, no response time tracking |
| Business metrics | ❌ None | No user counts, no query counts, no conversion |
| Alerting | ❌ None | No PagerDuty, no Slack alerts |
| Uptime monitoring | ❌ None | No external ping check |
| Dashboard | ✅ Streamlit (11 pages) | No monitoring page |

**Verdict**: You have the *infrastructure* for monitoring (metrics, health, runs tables) but nothing is wired together. No alerting. No dashboards. No error tracking.

---

## Part 1: Track Logs — Centralized, Structured, Searchable

---

### 1.1 Current Logging State

```
✅ 120 modules use _logger = logging.getLogger(__name__)
✅ Collector logs go to data/logs/collector.log
✅ LOG_LEVEL env var controls verbosity

❌ API server logs go to stdout only (no file)
❌ No structured logging (plain text, not JSON)
❌ No log rotation (collector.log grows forever)
❌ No centralized logging across 11 Docker services
❌ No request correlation (no request ID)
❌ No log retention policy
```

### 1.2 Logging Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│                  LOGGING ARCHITECTURE                                │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ FastAPI  │  │ Stream   │  │ Collector│  │ 26 Agents│           │
│  │ Access   │  │ Pipeline │  │ Scheduler│  │          │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
│       │              │              │              │                  │
│       v              v              v              v                  │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │           Python logging (structured JSON)              │       │
│  │   Every log entry: {timestamp, level, logger,           │       │
│  │    message, request_id, user_id, extra}                 │       │
│  └──────────────────────┬──────────────────────────────────┘       │
│                          │                                           │
│              ┌───────────┼───────────┐                              │
│              v           v           v                               │
│      ┌──────────┐ ┌──────────┐ ┌──────────┐                       │
│      │ Stdout   │ │ File     │ │ Docker   │                       │
│      │ (dev)    │ │ (prod)   │ │ json-file│                       │
│      └──────────┘ └──────────┘ └──────────┘                       │
│                          │                                           │
│                          v                                           │
│              ┌───────────────────────┐                              │
│              │ Docker logging driver │                              │
│              │ json-file + max-size  │                              │
│              │ + max-file rotation   │                              │
│              └───────────────────────┘                              │
│                                                                      │
│  FUTURE (Stage 2): Loki + Grafana for search                        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.3 Structured Logging — JSON Format

```python
# ═══ NEW FILE: config/logging_config.py ═══

"""Structured logging configuration for production monitoring."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging.

    Output format:
        {
            "timestamp": "2026-06-05T12:34:56.789Z",
            "level": "INFO",
            "logger": "agents.failure_pattern_agent",
            "message": "Analyzed 150 records",
            "request_id": "abc-123",
            "user_id": 42,
            "extra": {"agent": "failure_pattern", "records": 150}
        }
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if present (set by middleware)
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        # Add user ID if present
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id

        # Add any extra fields
        extra = {}
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord(
                "", 0, "", 0, "", (), None
            ).__dict__ and key not in ("message", "asctime"):
                try:
                    json.dumps(value)  # Test serializability
                    extra[key] = value
                except (TypeError, ValueError):
                    extra[key] = str(value)
        if extra:
            log_entry["extra"] = extra

        # Add exception info
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, default=str)


def configure_logging():
    """Configure structured logging for the application.

    - Development: human-readable format to stdout
    - Production: JSON format to stdout + file
    """
    env = os.environ.get("ENVIRONMENT", "development")
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    if env == "production":
        # ── Production: JSON to stdout ──
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        root_logger.addHandler(handler)

        # ── Also log to file with rotation ──
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                "data/logs/app.log",
                maxBytes=50 * 1024 * 1024,  # 50 MB
                backupCount=10,             # Keep 10 files = 500 MB max
                encoding="utf-8",
            )
            file_handler.setFormatter(JSONFormatter())
            root_logger.addHandler(file_handler)
        except (OSError, PermissionError):
            pass  # Can't write to file — stdout is sufficient

        # ── Quiet down noisy libraries ──
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("pymysql").setLevel(logging.WARNING)

    else:
        # ── Development: human-readable to stdout ──
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        root_logger.addHandler(handler)

    return root_logger


# ── Call at app startup ──
# from config.logging_config import configure_logging
# configure_logging()
```

### 1.4 Request ID Middleware — Correlate Logs

```python
# ═══ NEW FILE: api/middleware/request_id.py ═══

"""Add a unique request ID to every request for log correlation."""

import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique X-Request-ID to every request and log entry."""

    async def dispatch(self, request, call_next):
        # Use existing request ID from header, or generate one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Attach to request state
        request.state.request_id = request_id

        # Attach to all log entries in this request
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id
            return record

        logging.setLogRecordFactory(record_factory)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            logging.setLogRecordFactory(old_factory)
```

### 1.5 Request Logging Middleware — Access Logs

```python
# ═══ NEW FILE: api/middleware/access_log.py ═══

"""Log every API request with method, path, status, duration, user."""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware

_logger = logging.getLogger("api.access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Log request method, path, status code, and response time."""

    async def dispatch(self, request, call_next):
        # Skip health checks (too noisy)
        if request.url.path == "/api/health":
            return await call_next(request)

        start = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000

            _logger.info(
                "%s %s → %d (%.1fms)",
                method,
                path,
                response.status_code,
                duration_ms,
                extra={
                    "method": method,
                    "path": path,
                    "status": response.status_code,
                    "duration_ms": round(duration_ms, 1),
                },
            )

            # Add timing header
            response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            _logger.error(
                "%s %s → 500 (%.1fms) %s: %s",
                method,
                path,
                duration_ms,
                type(e).__name__,
                str(e),
                extra={
                    "method": method,
                    "path": path,
                    "status": 500,
                    "duration_ms": round(duration_ms, 1),
                    "exception": type(e).__name__,
                },
            )
            raise
```

### 1.6 Docker Logging — Rotation + Size Limits

```yaml
# ═══ Add to docker-compose.yml — all services ═══

services:
  api:
    # ... existing config ...
    logging:
      driver: json-file
      options:
        max-size: "50m"     # Rotate at 50 MB
        max-file: "5"       # Keep 5 files per service
        tag: "oip-{{.Name}}"  # Tag with container name

  mysql:
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"

  redis:
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  # Apply same to all 11 services
```

### 1.7 Log Retention Policy

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  LOG SOURCE           RETENTION    ROTATION       TOTAL SIZE        │
│  ──────────           ─────────    ────────       ──────────        │
│  app.log              10 files     50 MB each     500 MB            │
│  collector.log        10 files     50 MB each     500 MB            │
│  Docker json-file     5 files     50 MB each     250 MB/service    │
│  access logs          In app.log  (same file)     —                 │
│  cron.log             30 days     daily rotate    ~1 MB             │
│  ────────────────────────────────────────────────────               │
│  TOTAL per service    ~750 MB                                        │
│  TOTAL all services   ~2 GB                                         │
│                                                                      │
│  CLEANUP: Add to scripts/cleanup_logs.sh (weekly cron):             │
│  find data/logs/ -name "*.log.*" -mtime +30 -delete                 │
│  find data/logs/ -name "*.log" -size +100M -exec truncate -s 0 {} \;│
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Monitor Errors — Catch Them Before Users Report Them

---

### 2.1 Current Error State

```
❌ No error tracking service (no Sentry, no Rollbar)
❌ No error aggregation (same error logged 100 times, no dedup)
❌ No error alerting (nobody knows when API returns 500)
❌ No stack trace collection
❌ No error rate monitoring
⚠️ 250 broad except Exception blocks silently swallow errors
```

### 2.2 Error Tracking Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│              ERROR TRACKING FLOW                                     │
│                                                                      │
│  Unhandled Exception                                                 │
│       │                                                              │
│       v                                                              │
│  FastAPI Exception Handler                                           │
│       │                                                              │
│       ├── Log to structured logger (JSON)                            │
│       │                                                              │
│       ├── Write to error_log MySQL table                             │
│       │   (for dashboard + historical analysis)                      │
│       │                                                              │
│       └── Send to alert channel                                      │
│           ├── Email (for CRITICAL)                                   │
│           ├── Slack webhook (for ERROR+)                             │
│           └── /api/alerts (for in-app display)                       │
│                                                                      │
│  Stage 1 (Now):      MySQL error_log + email alerts                 │
│  Stage 2 (100 users): Add Sentry for stack traces + dedup           │
│  Stage 3 (1000 users): Add PagerDuty for on-call rotation           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3 Error Log Table

```sql
-- ═══ Add to db/schema.py (schema v17) ═══

CREATE TABLE IF NOT EXISTS error_log (
    id              BIGINT PRIMARY KEY AUTO_INCREMENT,
    timestamp       DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    level           VARCHAR(10) NOT NULL DEFAULT 'ERROR'
                    COMMENT 'ERROR, CRITICAL, WARNING',
    source          VARCHAR(50) NOT NULL
                    COMMENT 'api, stream, collector, agent, scheduler',
    error_type      VARCHAR(100) NOT NULL COMMENT 'Exception class name',
    error_message   TEXT NOT NULL,
    stack_trace     TEXT,
    request_id      VARCHAR(100),
    endpoint        VARCHAR(200),
    user_id         INT,
    request_data    TEXT COMMENT 'Sanitized request body (no secrets)',
    occurrence_count INT DEFAULT 1 COMMENT 'Dedup: increment if same error',
    first_seen_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    resolved_at     DATETIME COMMENT 'NULL if unresolved',
    INDEX idx_error_timestamp (timestamp),
    INDEX idx_error_level (level),
    INDEX idx_error_source (source),
    INDEX idx_error_type (error_type(50)),
    INDEX idx_error_unresolved (resolved_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.4 Error Tracking Middleware

```python
# ═══ NEW FILE: monitoring/error_tracker.py ═══

"""Centralized error tracking — log, store, alert."""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


def track_error(
    error: Exception,
    source: str = "api",
    endpoint: str = "",
    request_id: str = "",
    user_id: int | None = None,
    request_data: dict | None = None,
) -> int:
    """Track an error: log it, store it, optionally alert.

    Args:
        error: The exception that occurred.
        source: Where it happened (api, stream, collector, agent, scheduler).
        endpoint: API endpoint (if applicable).
        request_id: Correlation ID.
        user_id: Authenticated user ID.
        request_data: Sanitized request body.

    Returns:
        error_log ID.
    """
    error_type = type(error).__name__
    error_message = str(error)[:2000]
    stack = traceback.format_exc()

    # Determine severity
    level = "ERROR"
    if isinstance(error, (MemoryError, SystemError)):
        level = "CRITICAL"
    elif isinstance(error, (ConnectionError, TimeoutError)):
        level = "WARNING"

    # Log it
    _logger.error(
        "[%s] %s in %s: %s (request_id=%s)",
        level,
        error_type,
        source,
        error_message,
        request_id,
        extra={
            "error_type": error_type,
            "source": source,
            "endpoint": endpoint,
            "request_id": request_id,
        },
    )

    # Sanitize request data (remove secrets)
    safe_data = None
    if request_data:
        safe_data = {
            k: v for k, v in request_data.items()
            if k not in ("password", "token", "secret", "api_key", "credit_card")
        }
        safe_data = json.dumps(safe_data)[:5000]

    # Store in error_log table
    try:
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        # Check for duplicate (same error_type + message in last hour)
        cursor.execute(
            "SELECT id, occurrence_count FROM error_log "
            "WHERE error_type = %s AND error_message = %s AND source = %s "
            "AND timestamp > DATE_SUB(NOW(), INTERVAL 1 HOUR) "
            "AND resolved_at IS NULL "
            "ORDER BY timestamp DESC LIMIT 1",
            (error_type, error_message[:200], source),
        )
        existing = cursor.fetchone()

        if existing:
            # Dedup: increment occurrence count
            cursor.execute(
                "UPDATE error_log SET occurrence_count = occurrence_count + 1, "
                "last_seen_at = NOW() WHERE id = %s",
                (existing["id"],),
            )
            error_id = existing["id"]
        else:
            # New error
            cursor.execute(
                "INSERT INTO error_log "
                "(level, source, error_type, error_message, stack_trace, "
                " request_id, endpoint, user_id, request_data) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (level, source, error_type, error_message, stack,
                 request_id, endpoint, user_id, safe_data),
            )
            error_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as db_error:
        # Can't track error in DB — at least log it
        _logger.critical("Cannot write to error_log: %s", db_error)
        return 0

    # Alert on CRITICAL errors
    if level == "CRITICAL":
        _send_critical_alert(error_type, error_message, source, error_id)

    return error_id


def _send_critical_alert(error_type: str, message: str, source: str, error_id: int):
    """Send alert for critical errors.

    Stage 1: Log prominently (always).
    Stage 2: Send email (when SMTP configured).
    Stage 3: Send Slack webhook (when configured).
    """
    _logger.critical(
        "🚨 CRITICAL ERROR #%d: %s in %s: %s",
        error_id, error_type, source, message,
    )
    # TODO: Add email/Slack notification when channels are configured


def get_error_summary(hours: int = 24) -> list[dict]:
    """Get error summary for the monitoring dashboard.

    Args:
        hours: Look back period.

    Returns:
        List of error summaries grouped by type.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT error_type, source, level, "
            "COUNT(*) as total_errors, "
            "MAX(last_seen_at) as last_seen, "
            "SUM(occurrence_count) as total_occurrences, "
            "MIN(error_message) as sample_message "
            "FROM error_log "
            "WHERE timestamp > DATE_SUB(NOW(), INTERVAL %s HOUR) "
            "GROUP BY error_type, source, level "
            "ORDER BY total_occurrences DESC "
            "LIMIT 50",
            (hours,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def resolve_errors(error_type: str, source: str) -> int:
    """Mark all unresolved errors of a type as resolved.

    Returns:
        Number of errors resolved.
    """
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE error_log SET resolved_at = NOW() "
            "WHERE error_type = %s AND source = %s AND resolved_at IS NULL",
            (error_type, source),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        cursor.close()
        conn.close()
```

### 2.5 FastAPI Exception Handlers

```python
# ═══ Add to api_server.py ═══

from monitoring.error_tracker import track_error


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch all unhandled exceptions — track, log, return 500."""
    request_id = getattr(request.state, "request_id", "unknown")
    error_id = track_error(
        error=exc,
        source="api",
        endpoint=str(request.url.path),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "error_id": error_id,  # For support lookup
            },
            "meta": {"request_id": request_id},
        },
    )


@app.exception_handler(ValueError)
async def validation_exception_handler(request, exc):
    """Handle ValueError from input validation."""
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
            },
            "meta": {"request_id": request_id},
        },
    )
```

---

## Part 3: Measure Performance — Know Your Speed

---

### 3.1 Performance Metrics to Track

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  METRIC                    TARGET    CRITICAL   SOURCE              │
│  ───────                   ──────    ─────────  ──────              │
│                                                                      │
│  API response time (p50)    <200ms    >1s        Access log         │
│  API response time (p99)    <1s       >5s        Access log         │
│  API error rate             <1%       >5%        Access log         │
│  Chat response time         <10s      >30s       Ollama timing      │
│  Score computation time     <2s       >10s       Scorer timing      │
│  Collector cycle time       <5min     >30min     collection_runs    │
│  Agent execution time       <30s      >5min      agent_runs         │
│  Stream processing lag      <30s      >5min      stream:metrics     │
│  MySQL query time (p95)     <100ms    >500ms     Slow query log     │
│  Redis hit rate             >80%      <50%       Redis INFO         │
│  Qdrant search time         <50ms     >200ms     Qdrant metrics     │
│  Ollama tokens/sec          >10       <5         Model manager      │
│  WebSocket message lag      <1s       >10s       WS metrics         │
│  Disk usage                 <70%      >90%       Disk check         │
│  Memory usage               <80%      >95%       OS metrics         │
│  CPU usage                  <70%      >90%       OS metrics         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 Performance Monitoring Implementation

```python
# ═══ NEW FILE: monitoring/performance.py ═══

"""Performance monitoring — response times, throughput, resource usage."""

import os
import time
import threading
import logging
from collections import deque
from dataclasses import dataclass, field

_logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """In-memory performance metrics with sliding window.

    Stores the last 10,000 request durations for percentile calculation.
    Thread-safe for concurrent FastAPI workers.
    """

    # Sliding window of response times (milliseconds)
    _response_times: deque = field(default_factory=lambda: deque(maxlen=10000))
    _error_count: int = 0
    _request_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_request(self, duration_ms: float, status_code: int):
        """Record a completed request."""
        with self._lock:
            self._response_times.append(duration_ms)
            self._request_count += 1
            if status_code >= 500:
                self._error_count += 1

    def get_summary(self) -> dict:
        """Get current performance summary.

        Returns:
            Dict with p50, p95, p99, error_rate, request_count.
        """
        with self._lock:
            if not self._response_times:
                return {
                    "p50_ms": 0, "p95_ms": 0, "p99_ms": 0,
                    "error_rate": 0.0, "request_count": 0,
                    "avg_ms": 0,
                }

            times = sorted(self._response_times)
            n = len(times)
            return {
                "p50_ms": round(times[int(n * 0.50)], 1),
                "p95_ms": round(times[int(n * 0.95)], 1),
                "p99_ms": round(times[min(int(n * 0.99), n - 1)], 1),
                "avg_ms": round(sum(times) / n, 1),
                "error_rate": round(self._error_count / max(1, self._request_count) * 100, 2),
                "request_count": self._request_count,
                "error_count": self._error_count,
            }


# Global instance
perf_metrics = PerformanceMetrics()
```

### 3.3 MySQL Slow Query Log

```sql
-- ═══ Enable in MySQL (add to my.cnf or docker-compose command) ═══

-- Log queries slower than 500ms
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.5;  -- seconds
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
SET GLOBAL log_queries_not_using_indexes = 'ON';

-- ═══ Docker compose: add to mysql service ═══
-- command: >
--   --slow-query-log=1
--   --long-query-time=0.5
--   --slow-query-log-file=/var/log/mysql/slow.log
--   --log-queries-not-using-indexes=1
```

### 3.4 Health Check Enhancement — Check All Services

```python
# ═══ REPLACE: monitoring/health.py ═══

"""Comprehensive health check — all 11 Docker services."""

import os
import time
import shutil
import logging
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger(__name__)


def check_database() -> dict[str, Any]:
    """Check MySQL connectivity and query speed."""
    start = time.perf_counter()
    try:
        from db.connection import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return {
            "status": "healthy" if latency_ms < 500 else "degraded",
            "latency_ms": latency_ms,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_redis() -> dict[str, Any]:
    """Check Redis connectivity and measure ping latency."""
    start = time.perf_counter()
    try:
        import redis
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(url, socket_connect_timeout=2)
        r.ping()
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        info = r.info("memory")
        r.close()
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 1),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_kafka() -> dict[str, Any]:
    """Check Kafka/Redpanda connectivity."""
    try:
        from kafka import KafkaConsumer
        brokers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        consumer = KafkaConsumer(
            bootstrap_servers=brokers,
            request_timeout_ms=3000,
        )
        topics = consumer.topics()
        consumer.close()
        return {
            "status": "healthy",
            "topics_count": len(topics),
            "has_raw_signals": "raw.signals" in topics,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_ollama() -> dict[str, Any]:
    """Check Ollama LLM service."""
    start = time.perf_counter()
    try:
        import requests
        url = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
        base_url = url.replace("/api/chat", "")
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "models_loaded": len(models),
                "models": [m.get("name") for m in models],
            }
        return {"status": "unhealthy", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_qdrant() -> dict[str, Any]:
    """Check Qdrant vector database."""
    try:
        import requests
        resp = requests.get("http://localhost:6333/collections", timeout=3)
        if resp.status_code == 200:
            collections = resp.json().get("result", {}).get("collections", [])
            return {
                "status": "healthy",
                "collections": len(collections),
            }
        return {"status": "unhealthy", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_elasticsearch() -> dict[str, Any]:
    """Check Elasticsearch."""
    try:
        import requests
        resp = requests.get("http://localhost:9200/_cluster/health", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "status": "healthy" if data.get("status") in ("green", "yellow") else "unhealthy",
                "cluster_status": data.get("status"),
                "nodes": data.get("number_of_nodes"),
            }
        return {"status": "unhealthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_disk() -> dict[str, Any]:
    """Check disk space."""
    try:
        usage = shutil.disk_usage("/")
        free_gb = usage.free / (1024 ** 3)
        usage_pct = (usage.used / usage.total) * 100
        return {
            "status": "critical" if usage_pct > 90 else "warning" if usage_pct > 75 else "healthy",
            "free_gb": round(free_gb, 1),
            "usage_percent": round(usage_pct, 1),
        }
    except Exception as e:
        return {"status": "unknown", "error": str(e)}


def get_full_health() -> dict[str, Any]:
    """Run all health checks and return comprehensive status."""
    checks = {
        "mysql": check_database(),
        "redis": check_redis(),
        "kafka": check_kafka(),
        "ollama": check_ollama(),
        "qdrant": check_qdrant(),
        "elasticsearch": check_elasticsearch(),
        "disk": check_disk(),
    }

    # Overall status: unhealthy if ANY service is unhealthy
    any_unhealthy = any(c.get("status") == "unhealthy" for c in checks.values())
    any_degraded = any(c.get("status") in ("degraded", "warning") for c in checks.values())

    overall = "unhealthy" if any_unhealthy else "degraded" if any_degraded else "healthy"

    return {
        "status": overall,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

### 3.5 Enhanced `/api/health` Endpoint

```python
# ═══ REPLACE in api_server.py ═══

@app.get("/api/health")
def health(detailed: bool = Query(False)):
    """Health check — all services.

    Query params:
        detailed: If true, shows per-service details.
    """
    from monitoring.health import get_full_health
    from monitoring.performance import perf_metrics

    result = get_full_health()

    if detailed:
        result["performance"] = perf_metrics.get_summary()

    status_code = 200 if result["status"] == "healthy" else 503
    return JSONResponse(content=result, status_code=status_code)
```

---

## Part 4: Watch Business Metrics — Know If You're Winning

---

### 4.1 Business Metrics Dashboard

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│              BUSINESS METRICS TO TRACK                               │
│                                                                      │
│  ACQUISITION                                                        │
│  ├── Total registered users          (daily + cumulative)           │
│  ├── New users today                 (trend line)                   │
│  ├── GitHub stars                    (weekly)                       │
│  ├── HN upvotes                      (per launch post)             │
│  └── Referral source breakdown       (HN, Reddit, Google, Direct)  │
│                                                                      │
│  ACTIVATION                                                         │
│  ├── Users who ran first search      (% of registered)             │
│  ├── Users who used chat             (% of registered)             │
│  ├── Users who scored a startup      (% of registered)             │
│  └── Time to first value             (minutes from signup)         │
│                                                                      │
│  ENGAGEMENT                                                         │
│  ├── Daily Active Users (DAU)                                       │
│  ├── Weekly Active Users (WAU)                                      │
│  ├── DAU/MAU ratio                   (stickiness, target >20%)     │
│  ├── Avg sessions per user/week                                      │
│  ├── Avg queries per session                                         │
│  ├── Top 10 search queries                                           │
│  ├── Score feedback (thumbs up/down ratio)                          │
│  └── Watchlist items per user                                        │
│                                                                      │
│  RETENTION                                                          │
│  ├── Day-1 retention                 (% return next day)           │
│  ├── Day-7 retention                 (% return within 7 days)      │
│  ├── Day-30 retention                (% return within 30 days)     │
│  └── Churn rate                      (% inactive >30 days)         │
│                                                                      │
│  REVENUE                                                            │
│  ├── Free → Pro conversion rate     (target >3%)                   │
│  ├── Monthly Recurring Revenue      (MRR)                          │
│  ├── Average Revenue Per User       (ARPU)                         │
│  ├── Pro subscribers                (count + trend)                │
│  ├── Enterprise leads               (count)                        │
│  └── API key usage                  (calls per key per day)        │
│                                                                      │
│  SYSTEM HEALTH (business-impacting)                                 │
│  ├── Uptime percentage              (target >99.5%)                │
│  ├── Mean time to recovery          (MTTR, target <30 min)         │
│  ├── Error rate                     (target <1%)                   │
│  └── P95 response time              (target <500ms)                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Business Metrics Tables

```sql
-- ═══ Add to db/schema.py (schema v17) ═══

-- Track daily business metrics (one row per day)
CREATE TABLE IF NOT EXISTS daily_metrics (
    id              INT PRIMARY KEY AUTO_INCREMENT,
    metric_date     DATE NOT NULL,
    -- Acquisition
    total_users     INT DEFAULT 0,
    new_users       INT DEFAULT 0,
    -- Activation
    users_searched  INT DEFAULT 0 COMMENT 'Users who ran ≥1 search',
    users_chatted   INT DEFAULT 0 COMMENT 'Users who used chat ≥1',
    users_scored    INT DEFAULT 0 COMMENT 'Users who scored ≥1 startup',
    -- Engagement
    dau             INT DEFAULT 0 COMMENT 'Daily Active Users',
    total_queries   INT DEFAULT 0,
    total_chat_msgs INT DEFAULT 0,
    total_scores    INT DEFAULT 0,
    avg_session_min FLOAT DEFAULT 0,
    -- Retention
    day1_retention  FLOAT DEFAULT 0 COMMENT '% who returned next day',
    day7_retention  FLOAT DEFAULT 0 COMMENT '% who returned within 7d',
    -- Revenue
    pro_subscribers INT DEFAULT 0,
    mrr_cents       INT DEFAULT 0 COMMENT 'Monthly Recurring Revenue in cents',
    -- System
    error_count     INT DEFAULT 0,
    p95_response_ms INT DEFAULT 0,
    uptime_pct      FLOAT DEFAULT 100.0,
    -- Metadata
    computed_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_daily_metrics_date (metric_date),
    INDEX idx_metrics_date (metric_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 4.3 Business Metrics Computation — Daily Cron

```python
# ═══ NEW FILE: scripts/compute_daily_metrics.py ═══

"""Compute daily business metrics — run via cron at 00:05 UTC."""

import os
import sys
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import get_connection
from db import schema


def compute_metrics(yesterday: date) -> dict:
    """Compute all business metrics for a given date.

    Args:
        yesterday: The date to compute metrics for.

    Returns:
        Dict of metric values.
    """
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    date_str = yesterday.isoformat()

    metrics = {}

    # ── Acquisition ──
    cursor.execute("SELECT COUNT(*) as cnt FROM users WHERE created_at < %s", (date_str,))
    metrics["total_users"] = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE DATE(created_at) = %s",
        (date_str,),
    )
    metrics["new_users"] = cursor.fetchone()["cnt"]

    # ── Engagement ──
    cursor.execute(
        "SELECT COUNT(DISTINCT user_id) as cnt FROM query_log "
        "WHERE DATE(created_at) = %s AND user_id IS NOT NULL",
        (date_str,),
    )
    metrics["dau"] = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM query_log WHERE DATE(created_at) = %s",
        (date_str,),
    )
    metrics["total_queries"] = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(*) as cnt FROM chat_log WHERE DATE(created_at) = %s",
        (date_str,),
    )
    metrics["total_chat_msgs"] = cursor.fetchone()["cnt"]

    cursor.execute(
        "SELECT COUNT(DISTINCT user_id) as cnt FROM query_log "
        "WHERE DATE(created_at) = %s AND user_id IS NOT NULL",
        (date_str,),
    )
    metrics["users_searched"] = cursor.fetchone()["cnt"]

    # ── Revenue ──
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE tier = 'pro' AND is_active = 1"
    )
    metrics["pro_subscribers"] = cursor.fetchone()["cnt"]

    # ── System ──
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM error_log WHERE DATE(timestamp) = %s",
        (date_str,),
    )
    metrics["error_count"] = cursor.fetchone()["cnt"]

    cursor.close()
    conn.close()
    return metrics


def store_metrics(metric_date: date, metrics: dict):
    """Upsert daily metrics into database."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    columns = ["metric_date"] + list(metrics.keys())
    values = [metric_date] + list(metrics.values())
    placeholders = ", ".join(["%s"] * len(values))
    col_str = ", ".join(columns)

    updates = ", ".join(f"{c} = VALUES({c})" for c in metrics.keys())
    sql = f"INSERT INTO daily_metrics ({col_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}"

    cursor.execute(sql, values)
    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    print(f"Computing metrics for {yesterday}...")
    metrics = compute_metrics(yesterday)
    store_metrics(yesterday, metrics)
    print(f"✓ Stored metrics: {metrics}")
```

### 4.4 Business Metrics API Endpoint

```python
# ═══ Add to api_server.py ═══

@app.get("/api/metrics/business")
def business_metrics(days: int = Query(30, ge=1, le=365)):
    """Business metrics for the last N days. Admin only."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM daily_metrics "
        "WHERE metric_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY) "
        "ORDER BY metric_date",
        (days,),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {"data": rows, "days": days}
```

### 4.5 Monitoring Dashboard — Add to Streamlit

```python
# ═══ Add page to streamlit_app.py ═══

elif page == "📈 Monitoring":
    st.header("📈 Production Monitoring")

    col1, col2, col3, col4 = st.columns(4)

    # ── Health Check ──
    with st.spinner("Checking services..."):
        health = get_full_health()  # from monitoring.health

    status_emoji = {"healthy": "🟢", "degraded": "🟡", "unhealthy": "🔴"}

    with col1:
        st.metric("Overall", value=health["status"].upper(),
                  delta=None)
    with col2:
        db_status = health["checks"]["mysql"]["status"]
        st.metric("MySQL", value=f"{status_emoji[db_status]} {db_status}")
    with col3:
        redis_status = health["checks"]["redis"]["status"]
        st.metric("Redis", value=f"{status_emoji.get(redis_status, '⚪')} {redis_status}")
    with col4:
        ollama_status = health["checks"]["ollama"]["status"]
        st.metric("Ollama", value=f"{status_emoji.get(ollama_status, '⚪')} {ollama_status}")

    st.divider()

    # ── Error Summary ──
    st.subheader("🔴 Recent Errors (24h)")
    errors = get_error_summary(hours=24)
    if errors:
        st.dataframe(errors, use_container_width=True)
    else:
        st.success("No errors in the last 24 hours 🎉")

    st.divider()

    # ── Business Metrics ──
    st.subheader("📊 Business Metrics (30 days)")
    metrics_df = query_db(
        "SELECT metric_date, new_users, dau, total_queries, pro_subscribers "
        "FROM daily_metrics ORDER BY metric_date DESC LIMIT 30"
    )
    if metrics_df is not None and len(metrics_df) > 0:
        import plotly.express as px
        import pandas as pd

        fig1 = px.line(metrics_df, x="metric_date", y=["new_users", "dau"],
                       title="Users: New vs Active")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.line(metrics_df, x="metric_date", y="total_queries",
                       title="Daily Queries")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No business metrics data yet.")
```

---

## Part 5: Alerting — Know Immediately When Things Break

---

### 5.1 Alert Rules

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ALERT ID   CONDITION                          SEVERITY  CHANNEL    │
│  ────────   ─────────                          ────────  ───────    │
│                                                                      │
│  A-001      API error rate > 5% (5 min)        CRITICAL  Slack      │
│  A-002      API error rate > 1% (15 min)       WARNING   Email      │
│  A-003      Health check fails (any service)   CRITICAL  Slack      │
│  A-004      Disk usage > 90%                   CRITICAL  Slack      │
│  A-005      Disk usage > 75%                   WARNING   Email      │
│  A-006      MySQL unavailable                  CRITICAL  Slack      │
│  A-007      Ollama unavailable > 5 min         WARNING   Email      │
│  A-008      Collector fails 3x in a row        WARNING   Email      │
│  A-009      Agent execution > 5 min            WARNING   Log        │
│  A-010      No new signals in 2 hours          WARNING   Email      │
│  A-011      Score drift > 20% from baseline    WARNING   Log        │
│  A-012      User signup spike (10x normal)     INFO      Slack      │
│  A-013      Pro subscription created           INFO      Slack      │
│  A-014      Daily backup failed                CRITICAL  Slack      │
│  A-015      TLS certificate expiring <7 days   WARNING   Email      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 Simple Alert Dispatcher — Slack Webhook

```python
# ═══ NEW FILE: monitoring/alerts.py ═══

"""Lightweight alerting via Slack webhook (no external service needed)."""

import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum

import requests

_logger = logging.getLogger(__name__)


class Severity(Enum):
    INFO = "ℹ️"
    WARNING = "⚠️"
    CRITICAL = "🚨"


def send_alert(
    title: str,
    message: str,
    severity: Severity = Severity.WARNING,
    details: dict | None = None,
):
    """Send an alert to the configured channel.

    Stage 1: Slack webhook (if SLACK_WEBHOOK_URL set)
    Stage 2: Email (if SMTP configured)
    Stage 3: PagerDuty (if needed for on-call)
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

    # Always log
    _logger.log(
        logging.CRITICAL if severity == Severity.CRITICAL else logging.WARNING,
        "%s %s: %s",
        severity.value,
        title,
        message,
    )

    # Send to Slack if configured
    if not webhook_url:
        _logger.debug("No SLACK_WEBHOOK_URL set — alert logged only")
        return

    color = {
        Severity.INFO: "#36a64f",      # green
        Severity.WARNING: "#f2c744",   # yellow
        Severity.CRITICAL: "#ff0000",  # red
    }[severity]

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{severity.value} {title}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": message},
        },
    ]

    if details:
        detail_lines = "\n".join(f"• *{k}*: {v}" for k, v in details.items())
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": detail_lines},
        })

    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": f"_Opportunity Intelligence Platform • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        }],
    })

    try:
        requests.post(
            webhook_url,
            json={
                "attachments": [{"color": color, "blocks": blocks}],
            },
            timeout=5,
        )
    except Exception as e:
        _logger.error("Failed to send Slack alert: %s", e)
```

### 5.3 Alert Evaluation Cron — Every 5 Minutes

```python
# ═══ NEW FILE: scripts/check_alerts.py ═══

"""Check alert conditions and fire alerts. Run via cron every 5 minutes.

Usage:
    */5 * * * * cd /path/to/project && python scripts/check_alerts.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from monitoring.health import get_full_health
from monitoring.alerts import send_alert, Severity


def check_health_alerts():
    """A-003: Check all service health."""
    health = get_full_health()

    if health["status"] == "unhealthy":
        failed = [
            name for name, check in health["checks"].items()
            if check.get("status") == "unhealthy"
        ]
        send_alert(
            title="Service Unhealthy",
            message=f"Services DOWN: {', '.join(failed)}",
            severity=Severity.CRITICAL,
            details=health["checks"],
        )
    elif health["status"] == "degraded":
        degraded = [
            name for name, check in health["checks"].items()
            if check.get("status") in ("degraded", "warning")
        ]
        send_alert(
            title="Service Degraded",
            message=f"Services degraded: {', '.join(degraded)}",
            severity=Severity.WARNING,
        )

    # A-004/A-005: Disk check
    disk = health["checks"].get("disk", {})
    if disk.get("usage_percent", 0) > 90:
        send_alert(
            title="Disk Space Critical",
            message=f"Disk usage at {disk['usage_percent']}% ({disk['free_gb']} GB free)",
            severity=Severity.CRITICAL,
        )


if __name__ == "__main__":
    check_health_alerts()
```

### 5.4 External Uptime Monitoring — Free

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SERVICE         FREE TIER           WHAT IT DOES                    │
│  ───────         ─────────           ────────────                    │
│  UptimeRobot     50 monitors free    Pings /api/health every 5 min  │
│                  (https://uptimerobot.com)                           │
│                                                                      │
│  Better Stack    1 monitor free      Pings + status page            │
│                  (https://betterstack.com)                           │
│                                                                      │
│  SETUP (5 minutes):                                                  │
│  1. Sign up for UptimeRobot (free)                                  │
│  2. Add monitor: HTTPS yourdomain.com/api/health                    │
│  3. Set check interval: 5 minutes                                    │
│  4. Add alert contact: your email                                    │
│  5. Optional: Add Slack integration                                  │
│                                                                      │
│  RECOMMENDED MONITORS:                                               │
│  • https://yourdomain.com/api/health          (API health)          │
│  • https://yourdomain.com/                     (Dashboard)          │
│  • https://yourdomain.com/api/health?detailed=1  (All services)    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 6: Monitoring Stack — What to Add and When

---

### 6.1 Stage 1: Day 1 (Free, Zero New Infrastructure)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WHAT                         TOOL              COST                │
│  ────                         ────              ────                │
│  Structured JSON logs         Python logging    $0 (built in)       │
│  Log rotation                 RotatingFileHandler $0               │
│  Request ID correlation       Custom middleware  $0                 │
│  Access logging               Custom middleware  $0                 │
│  Error tracking               MySQL error_log   $0                 │
│  Health checks (7 services)   monitoring/health  $0                │
│  Performance percentiles      In-memory deque    $0                 │
│  Business metrics table       MySQL daily_metrics $0               │
│  Slack alerts                 Incoming webhook   $0                 │
│  Uptime monitoring            UptimeRobot free   $0                 │
│  Docker log rotation          json-file driver   $0                 │
│                                                                      │
│  TOTAL COST: $0                                                      │
│  SETUP TIME: ~4 hours                                                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 Stage 2: 100 Users (Low Cost, Big Value)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ADD                              TOOL              COST            │
│  ────                             ────              ────            │
│  Error tracking with stack traces Sentry free tier  $0             │
│  Log aggregation + search         Grafana Loki      $0 (self-host) │
│  Metrics dashboards               Grafana           $0 (self-host) │
│  Grafana MySQL datasource         Grafana plugin    $0             │
│  Grafana alerting                 Grafana           $0             │
│                                                                      │
│  TOTAL COST: $0                                                      │
│  SETUP TIME: ~8 hours                                                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.3 Stage 3: 1,000 Users (Professional)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ADD                              TOOL              COST            │
│  ────                             ────              ────            │
│  APM (Application Performance)   Grafana + Pyroscope $0 (self-host)│
│  On-call rotation                PagerDuty free     $0             │
│  Distributed tracing             Grafana Tempo      $0 (self-host) │
│  Real User Monitoring            Grafana Faro       $0             │
│                                                                      │
│  TOTAL COST: $0 (all self-hosted)                                   │
│  SETUP TIME: ~16 hours                                               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  4 AREAS COVERED          WHAT WE BUILT                              │
│  ──────────────           ──────────────                             │
│                                                                      │
│  TRACK LOGS               Structured JSON logging, request ID       │
│                           middleware, access log middleware,         │
│                           log rotation (50MB × 10 files),           │
│                           Docker json-file rotation, cleanup cron   │
│                                                                      │
│  MONITOR ERRORS           MySQL error_log table with dedup,         │
│                           FastAPI exception handlers, error          │
│                           summary API, CRITICAL alert routing        │
│                                                                      │
│  MEASURE PERFORMANCE      16 performance targets with thresholds,   │
│                           in-memory percentile calculator (p50/p95/ │
│                           p99), enhanced health checks for 7        │
│                           services, MySQL slow query log config      │
│                                                                      │
│  WATCH BUSINESS METRICS   daily_metrics table, 25 business KPIs,    │
│                           daily cron computation script,             │
│                           /api/metrics/business endpoint,            │
│                           Streamlit monitoring page                  │
│                                                                      │
│  ALERTING                 15 alert rules (A-001 to A-015),          │
│                           Slack webhook dispatcher,                  │
│                           5-minute alert evaluation cron,            │
│                           UptimeRobot external monitoring            │
│                                                                      │
│  TOTAL NEW FILES: 8 (logging_config, request_id, access_log,        │
│  error_tracker, performance, alerts, compute_daily_metrics,         │
│  check_alerts) + 3 SQL tables (error_log, daily_metrics, audit_log) │
│                                                                      │
│  TOTAL COST: $0 (all free tools, self-hosted)                       │
│  SETUP TIME: Stage 1 = 4 hours, Stage 2 = 8 hours, Stage 3 = 16h  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*
*Cross-references: SECURITY_FROM_DAY_ONE.md, DESIGN_BEFORE_CODING.md, WORK_PLAN.md, MAINTENANCE_PLAN.md, PROGRESS_MONITORING_TOOLS.md*

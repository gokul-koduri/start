# 📏 Coding Standards — Naming, Structure, Reuse, Comments

> "Any fool can write code that a computer can understand.
>  Good programmers write code that **humans** can understand."
> — Martin Fowler

---

## Why This Document Exists

A 207-file, 62-agent, 76-table codebase with **1 contributor** and **bus factor = 1** needs rules.
Not because rules are fun — because without them, every file becomes a snowflake.

**The audit found:**

| Metric | Value | Status |
|---|---|---|
| Total Python functions | 1,601 | — |
| Functions ≤ 20 lines | 1,128 (70%) | ✅ Good |
| Functions > 100 lines | 47 (3%) | ⚠️ Fix 20 of these |
| Type annotation coverage | 62% | ⚠️ Raise to 90% |
| Repeated DB boilerplate | 57 identical blocks | ❌ Extract to helper |
| `except Exception` catches | 250 | ⚠️ Use specific exceptions |
| Longest function | 257 lines (`seed_data.py`) | ❌ Break up |
| Largest file | 3,273 lines (`dashboard.py`) | ❌ Split |
| camelCase functions | 8 (all in tests) | ✅ Acceptable |
| Module-level constants | 120 with `_UPPER_CASE` | ✅ Good |

---

## Part 1: Naming Conventions

---

### 1.1 The Rule: Follow PEP 8, No Exceptions

Python has one naming standard: **PEP 8**. Every file, class, function, and variable follows it.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ELEMENT              CONVENTION          EXAMPLE                    │
│  ────────             ──────────          ────────                  │
│  Files                snake_case.py       hn_live_collector.py      │
│  Packages             snake_case/         stream/ ingestion/        │
│  Classes              PascalCase          FailurePatternAgent       │
│  Functions            snake_case          get_connection()          │
│  Methods              snake_case          def execute(self)         │
│  Variables            snake_case          entity_name = "Tesla"     │
│  Constants            UPPER_SNAKE         MAX_RETRIES = 3           │
│  Private              _leading_underscore _get_mysql_params()       │
│  Module constants     UPPER_SNAKE         _SCHEMA_VERSION = 16      │
│  Boolean variables    is_/has_/should_    is_loaded, has_api_key    │
│  Type variables       PascalCase          T = TypeVar("T")          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Naming Patterns by Layer

#### Files

```python
# ✅ CORRECT — snake_case, descriptive
collectors/hn_live_collector.py
agents/failure_pattern_agent.py
scoring/composite_scorer.py
db/connection.py
stream/operators.py

# ❌ WRONG — inconsistent, abbreviated, mixed
collectors/reshoring_pdf.py      # OK but could be reshoring_collector.py
agents/git_publisher.py          # OK but could be git_publisher_agent.py
collectors/crunchbase.py         # Missing _collector suffix
agents/dashboard.py              # OK but could be dashboard_agent.py
```

**Rule**: Collector files end in `_collector.py`. Agent files end in `_agent.py`.
Current exceptions (`crunchbase.py`, `dashboard.py`, `git_publisher.py`) are grandfathered.

#### Classes

```python
# ✅ CORRECT — PascalCase, descriptive noun
class FailurePatternAgent(BaseAgent): ...
class CompositeScorer: ...
class SignalEnvelope: ...
class VectorStore: ...
class JWTHandler: ...

# ✅ CORRECT — Agent classes end in "Agent"
class RiskScorerAgent(BaseAgent): ...
class EmailDigestAgent(BaseAgent): ...

# ❌ WRONG — snake_case, abbreviated, vague
class risk_scorer(BaseAgent): ...     # Not PascalCase
class RSA(BaseAgent): ...             # Abbreviated
class Handler: ...                    # Too vague — Handler of what?
```

#### Functions

```python
# ✅ CORRECT — snake_case, verb_first, descriptive
def get_connection() -> pymysql.Connection: ...
def normalize_signal(signal_type: str, ...) -> SignalEnvelope: ...
def sanitize_input(value: str) -> str: ...
def write_score_to_mysql(scored: dict) -> dict: ...
def build_attribution(scores, weights, decay) -> list: ...

# ✅ CORRECT — Private helpers start with _
def _get_mysql_params() -> dict: ...
def _parse_datetime(value: Any) -> datetime | None: ...
def _compute_trend(attribution: list) -> str: ...

# ❌ WRONG — vague, abbreviated, camelCase
def process(data): ...               # Process what?
def get_conn(): ...                  # Abbreviated
def getData(): ...                   # camelCase
def run2(): ...                      # Numbered
```

**Verb conventions for functions:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  VERB          USE FOR                          EXAMPLE              │
│  ────          ────────                          ────────            │
│  get_          Read from DB/API                  get_connection()    │
│  fetch_        Read from external source          fetch_stories()    │
│  load_         Load from disk/config              load_config()      │
│  save_         Write to disk                      save_report()      │
│  write_        Write to DB                        write_score()      │
│  create_       Make a new thing                   create_token()     │
│  build_        Construct complex object           build_pipeline()   │
│  parse_        Convert format                     parse_signal()     │
│  normalize_    Standardize format                 normalize_signal() │
│  validate_     Check correctness                  validate_token()   │
│  sanitize_     Clean unsafe input                 sanitize_input()   │
│  compute_      Calculate a value                  compute_score()    │
│  enrich_       Add metadata                       enrich_signal()    │
│  aggregate_    Combine multiple → one             aggregate_scores() │
│  emit_         Produce an event                   emit_alert()       │
│  publish_      Send to Kafka                      publish_signal()   │
│  is_/has_      Return boolean                     is_loaded()        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

#### Variables

```python
# ✅ CORRECT — snake_case, descriptive
entity_name = "Tesla"
composite_score = 78.5
total_signals = 1500
is_active = True
has_api_key = False

# ❌ WRONG — single letter (except in comprehensions), camelCase
en = "Tesla"                    # Abbreviated
compositeScore = 78.5           # camelCase
x = get_connection()            # Single letter (not in comprehension)
data1 = fetch()                 # Numbered
thing = process(input)          # Vague

# ✅ ACCEPTABLE — single letters in these contexts:
for i, row in enumerate(rows): ...          # Loop counter
[x.name for x in entities]                  # Comprehension
except Exception as e: ...                  # Exception
conn = get_connection()                     # Well-known short form
cursor = conn.cursor()                      # Well-known short form
df = pd.DataFrame(...)                      # pandas convention
```

#### Constants

```python
# ✅ CORRECT — UPPER_SNAKE_CASE at module level
SCHEMA_VERSION = 16
MAX_RETRIES = 3
DEFAULT_PORT = 8000
VALID_SIGNAL_TYPES = {"sec_filing", "job_posting_spike", ...}
ANOMALY_Z_THRESHOLD = 2.0

# ✅ CORRECT — Private constants with leading _
_SCHEMA_VERSION = 16
_GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
_LOGGER = logging.getLogger(__name__)

# ❌ WRONG
schemaVersion = 16              # camelCase
version = 16                    # Not UPPER_CASE for constant
```

---

## Part 2: Clean Code Structure

---

### 2.1 File Structure — Every Python File Follows This Order

```python
"""Module docstring — what this file does, how to use it.

Usage:
    python -m stream.pipeline                # Start stream processor
    python -m stream.pipeline --test         # Test mode

Design choices:
    - Stateless operators for horizontal scaling
    - Graceful Kafka fallback (MySQL-only mode)
"""

# ── Standard library imports (alphabetical) ──
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Third-party imports (alphabetical) ──
import pymysql
from fastapi import FastAPI, HTTPException

# ── Local imports (alphabetical by package) ──
from agents.base import AgentResult, BaseAgent
from config import load_config
from db import schema
from db.connection import get_connection

# ── Module-level constants ──
_LOGGER = logging.getLogger(__name__)
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# ── Module-level private helpers ──
def _parse_datetime(value: str) -> datetime | None:
    ...

# ── Public classes ──
class MyAgent(BaseAgent):
    ...

# ── Public functions ──
def build_pipeline() -> Any:
    ...

# ── Main entry point (if applicable) ──
if __name__ == "__main__":
    main()
```

**The order is:**

```
1. Module docstring (triple-quote)
2. Standard library imports (sorted alphabetically)
3. Third-party imports (sorted alphabetically)
4. Local imports (sorted by package name)
5. Module constants (UPPER_SNAKE_CASE)
6. Private helpers (_leading_underscore)
7. Public classes
8. Public functions
9. if __name__ == "__main__": block
```

### 2.2 Function Size Rules

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  RULES:                                                              │
│  • Functions should be ≤ 50 lines.                                   │
│  • If > 50 lines, extract helpers.                                   │
│  • Hard limit: 100 lines. Refactor anything above this.             │
│  • The 257-line seed_data.py::seed() → 5 functions of ~50 lines.   │
│  • The 224-line orchestrator::_get_agent_class() → auto-discovery.  │
│                                                                      │
│  CURRENT DISTRIBUTION:                                               │
│  1-20 lines:  1,128 (70%)  ✅                                        │
│  21-50 lines:   300 (19%)  ✅                                        │
│  51-100 lines:  126 (8%)   ⚠️  Review each                          │
│  100+ lines:     47 (3%)   ❌  Must refactor top 20                 │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**How to break up a long function — the `dashboard.py::execute()` example:**

```python
# ❌ BEFORE: 176 lines doing everything
def execute(self, upstream_results=None):
    # 30 lines of HTML header
    # 40 lines of chart 1
    # 40 lines of chart 2
    # 30 lines of chart 3
    # 36 lines of footer + return
    ...

# ✅ AFTER: 5 functions of ~35 lines each
def execute(self, upstream_results=None):
    html = self._build_header()
    html += self._build_score_chart(conn)
    html += self._build_trend_chart(conn)
    html += self._build_failure_chart(conn)
    html += self._build_footer()
    return AgentResult(agent_name=self.name, status="success", ...)

def _build_header(self) -> str:
    ...

def _build_score_chart(self, conn) -> str:
    ...

def _build_trend_chart(self, conn) -> str:
    ...

def _build_failure_chart(self, conn) -> str:
    ...
```

### 2.3 Function Structure — The 4-Part Pattern

Every function should follow this structure:

```python
def function_name(param1: type, param2: type) -> return_type:
    """One-line description of what this does.

    Optional: More detail if the function is complex.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is invalid.
    """
    # 1. Validate inputs
    if not param1:
        raise ValueError("param1 is required")

    # 2. Do the work
    result = _compute_something(param1, param2)

    # 3. Return the result
    return result
```

### 2.4 Error Handling

```python
# ❌ WRONG — bare except, too broad
try:
    conn = get_connection()
except Exception:
    pass  # Swallows ALL errors silently

# ❌ WRONG — catches too much
try:
    result = complex_operation()
except Exception as e:
    _logger.error("Error: %s", e)
    return None  # Hides the real error

# ✅ CORRECT — specific exception, specific action
try:
    conn = get_connection()
except pymysql.OperationalError as e:
    _logger.error("Database connection failed: %s", e)
    raise HTTPException(status_code=503, detail="Database unavailable")
except pymysql.ProgrammingError as e:
    _logger.error("SQL error: %s", e)
    raise HTTPException(status_code=500, detail="Internal error")

# ✅ CORRECT — cleanup in finally
cursor = None
conn = None
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
    result = cursor.fetchall()
    conn.commit()
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
```

**Current state**: 250 `except Exception` catches. Target: ≤ 50 (only at API boundary).

### 2.5 Import Rules

```python
# ✅ CORRECT — grouped, sorted, no wildcards
import json                    # stdlib
import logging
from datetime import datetime, timezone

import pymysql                 # third-party
from fastapi import FastAPI

from agents.base import BaseAgent     # local
from db.connection import get_connection

# ❌ WRONG
from agents.base import *      # Wildcard import
import os, sys, json           # Multiple imports on one line
from db import *                # Wildcard
import pymysql, requests       # Multiple on one line
```

**Rule**: No `import *`. No multiple imports on one line. Use `isort` to auto-sort.

### 2.6 Max Line Length

```
Limit: 120 characters (not PEP 8's 79)

Why 120?
  • Modern monitors are wide (120+ chars visible in split pane)
  • 79 chars wastes horizontal space
  • ruff defaults to 88, but 120 is readable

Configure in pyproject.toml:
  [tool.ruff]
  line-length = 120
```

---

## Part 3: Reusable Components

---

### 3.1 The Biggest Duplication: DB Boilerplate

**Found 57 identical blocks of:**

```python
conn = get_connection()
schema.init_schema(conn)
cursor = conn.cursor()
```

**And 35 identical blocks of:**

```python
conn.commit()
cursor.close()
conn.close()
```

**Solution**: Extract a `db_query` helper:

```python
# ═══ NEW FILE: db/helpers.py ═══

"""Database helper functions — eliminate boilerplate across agents and API."""

from contextlib import contextmanager
from typing import Any, Generator

from db import schema
from db.connection import get_connection


@contextmanager
def db_connection(init_schema: bool = True) -> Generator:
    """Context manager for MySQL connections with auto-cleanup.

    Usage:
        with db_connection() as (conn, cursor):
            cursor.execute("SELECT * FROM startups")
            rows = cursor.fetchall()

    Handles:
        - Connection opening/closing
        - Cursor creation/closing
        - Schema initialization (optional)
        - Commit on success, rollback on error
    """
    conn = get_connection()
    if init_schema:
        schema.init_schema(conn)
    cursor = conn.cursor()
    try:
        yield conn, cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def db_execute(query: str, params: tuple = (), fetch: str = "all") -> list[dict]:
    """Execute a query and return results. Auto-handles connection lifecycle.

    Args:
        query: SQL query with %s placeholders.
        params: Tuple of parameter values.
        fetch: "all", "one", or "none".

    Returns:
        List of dicts (fetch="all"), single dict (fetch="one"),
        or empty list (fetch="none").

    Usage:
        rows = db_execute("SELECT * FROM startups WHERE sector = %s", ("fintech",))
        row = db_execute("SELECT * FROM startups WHERE id = %s", (1,), fetch="one")
        db_execute("INSERT INTO startups (name) VALUES (%s)", ("Tesla",), fetch="none")
    """
    with db_connection() as (conn, cursor):
        cursor.execute(query, params)
        if fetch == "all":
            return cursor.fetchall()
        elif fetch == "one":
            return cursor.fetchone()
        else:
            return []


def db_insert(table: str, data: dict) -> int:
    """Insert a row into a table and return the new ID.

    Args:
        table: Table name.
        data: Column name → value mapping.

    Returns:
        Last insert ID.
    """
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    with db_connection() as (conn, cursor):
        cursor.execute(
            f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
            tuple(data.values()),
        )
        return cursor.lastrowid


def db_upsert(table: str, data: dict, unique_key: str) -> int:
    """Insert or update a row based on a unique key.

    Args:
        table: Table name.
        data: Column name → value mapping.
        unique_key: Column name that defines uniqueness.

    Returns:
        Last insert ID.
    """
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["%s"] * len(data))
    updates = ", ".join(f"{k} = VALUES({k})" for k in data if k != unique_key)
    query = (
        f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {updates}"
    )
    with db_connection() as (conn, cursor):
        cursor.execute(query, tuple(data.values()))
        return cursor.lastrowid
```

**Impact**: Replace 57 × 5-line boilerplate blocks with 1-line calls:

```python
# BEFORE (5 lines, repeated 57 times):
conn = get_connection()
schema.init_schema(conn)
cursor = conn.cursor()
cursor.execute("SELECT ...")
conn.commit(); cursor.close(); conn.close()

# AFTER (1 line):
rows = db_execute("SELECT ...")
```

### 3.2 Reusable Component: Pagination Helper

```python
# ═══ NEW FILE: utils/pagination.py ═══

"""Pagination helper for list API endpoints."""

from dataclasses import dataclass
from typing import Any


@dataclass
class PaginationParams:
    page: int = 1
    per_page: int = 20
    max_per_page: int = 100

    def __post_init__(self):
        self.page = max(1, self.page)
        self.per_page = min(max(1, self.per_page), self.max_per_page)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    def to_sql(self) -> str:
        return f"LIMIT {self.per_page} OFFSET {self.offset}"


def paginated_response(
    data: list[Any],
    total: int,
    page: int,
    per_page: int,
) -> dict[str, Any]:
    """Build a standard paginated response.

    Returns:
        {"data": [...], "pagination": {"page": 1, "per_page": 20,
         "total": 150, "total_pages": 8}}
    """
    total_pages = max(1, (total + per_page - 1) // per_page)
    return {
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
    }
```

**Usage in every list endpoint:**

```python
# BEFORE (repeated in 12 endpoints):
page = max(1, int(request.args.get("page", 1)))
per_page = min(100, max(1, int(request.args.get("per_page", 20))))
offset = (page - 1) * per_page
total = cursor.fetchone()["cnt"]
total_pages = (total + per_page - 1) // per_page

# AFTER (2 lines):
pag = PaginationParams(page=page, per_page=per_page)
return paginated_response(rows, total, pag.page, pag.per_page)
```

### 3.3 Reusable Component: Error Response Helper

```python
# ═══ NEW FILE: utils/errors.py ═══

"""Standard error responses for the API."""

from uuid import uuid4
from fastapi import HTTPException
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Structured API error with error code."""

    def __init__(self, code: str, message: str, status: int = 400, details: dict | None = None):
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}
        super().__init__(message)


def error_response(code: str, message: str, status: int = 400, details: dict | None = None) -> JSONResponse:
    """Build a standard error response.

    Returns:
        {"error": {"code": "...", "message": "...", "details": {}},
         "meta": {"request_id": "...", "timestamp": "..."}}
    """
    from datetime import datetime, timezone
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
            "meta": {
                "request_id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )


# Pre-built error helpers
def not_found(entity: str, name: str) -> JSONResponse:
    return error_response("NOT_FOUND", f"{entity} '{name}' not found", 404)

def validation_error(message: str, field: str = "", value: str = "") -> JSONResponse:
    return error_response("VALIDATION_ERROR", message, 422, {"field": field, "value": value})

def unauthorized(message: str = "Authentication required") -> JSONResponse:
    return error_response("UNAUTHORIZED", message, 401)

def rate_limited(retry_after: int = 60) -> JSONResponse:
    return error_response("RATE_LIMITED", f"Retry after {retry_after} seconds", 429, {"retry_after": retry_after})

def service_unavailable(service: str) -> JSONResponse:
    return error_response("SERVICE_UNAVAILABLE", f"{service} is unavailable", 503)
```

### 3.4 Reusable Component: Input Validation

```python
# ═══ NEW FILE: utils/validation.py ═══

"""Input validation helpers — sanitize all user input."""

import re
from typing import Any


def sanitize_string(value: str, max_length: int = 500) -> str:
    """Strip HTML tags, null bytes, and limit length.

    Args:
        value: Raw user input.
        max_length: Maximum allowed length.

    Returns:
        Cleaned string.

    Raises:
        ValueError: If input is not a string or is empty after cleaning.
    """
    if not isinstance(value, str):
        raise ValueError("Input must be a string")
    # Strip whitespace
    value = value.strip()
    # Remove null bytes
    value = value.replace("\x00", "")
    # Remove HTML tags
    value = re.sub(r"<[^>]*>", "", value)
    # Limit length
    value = value[:max_length]
    return value


def validate_entity_name(name: str) -> str:
    """Validate and clean an entity name for search/score.

    Args:
        name: Raw entity name.

    Returns:
        Cleaned entity name.

    Raises:
        ValueError: If name is empty or contains only special characters.
    """
    name = sanitize_string(name, max_length=255)
    if not name:
        raise ValueError("Entity name is required")
    if re.match(r'^[\s\.;\'"\\\-]+$', name):
        raise ValueError("Entity name contains only special characters")
    return name


def validate_score(score: Any) -> float:
    """Validate a numeric score value.

    Returns:
        Float between 0 and 100.

    Raises:
        ValueError: If score is not a valid number.
    """
    try:
        score = float(score)
    except (TypeError, ValueError):
        raise ValueError("Score must be a number")
    if not 0 <= score <= 100:
        raise ValueError("Score must be between 0 and 100")
    return score


def validate_page_params(page: Any, per_page: Any) -> tuple[int, int]:
    """Validate and normalize pagination parameters.

    Returns:
        (page, per_page) as integers within bounds.
    """
    try:
        page = max(1, int(page))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = min(100, max(1, int(per_page)))
    except (TypeError, ValueError):
        per_page = 20
    return page, per_page


def validate_email(email: str) -> str:
    """Basic email validation.

    Returns:
        Lowercased, stripped email.

    Raises:
        ValueError: If email format is invalid.
    """
    email = sanitize_string(email, max_length=255).lower()
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError("Invalid email format")
    return email


def validate_password(password: str) -> str:
    """Validate password meets minimum requirements.

    Raises:
        ValueError: If password is too short.
    """
    if not isinstance(password, str):
        raise ValueError("Password must be a string")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password) > 128:
        raise ValueError("Password must be at most 128 characters")
    return password
```

### 3.5 Reusable Component: Agent Auto-Discovery

Replace the 224-line `_get_agent_class()` with auto-discovery:

```python
# ═══ REPLACE IN: agents/orchestrator.py ═══

import importlib
import pkgutil
from pathlib import Path

# Auto-discover all agent classes
_agent_registry: dict[str, type] = {}


def _discover_agents() -> dict[str, type]:
    """Auto-discover all BaseAgent subclasses in the agents/ package."""
    from agents.base import BaseAgent

    agents_dir = Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(agents_dir)]):
        if module_name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"agents.{module_name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                    and issubclass(attr, BaseAgent)
                    and attr is not BaseAgent
                    and not attr_name.startswith("_")):
                    # Register by class name minus "Agent" suffix
                    key = attr_name.replace("Agent", "").lower()
                    _agent_registry[key] = attr
                    _logger.debug("Registered agent: %s → %s", key, attr_name)
        except ImportError as e:
            _logger.warning("Failed to import agent module %s: %s", module_name, e)

    return _agent_registry


def _get_agent_class(name: str):
    """Get agent class by name. Auto-discovers on first call."""
    if not _agent_registry:
        _discover_agents()
    if name in _agent_registry:
        return _agent_registry[name]
    raise ValueError(f"Unknown agent: {name}. Available: {list(_agent_registry.keys())}")
```

**Impact**: 224 lines → 35 lines. New agents are auto-registered by existing in `agents/`.

### 3.6 Component Inventory — What to Extract

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  REPEATED PATTERN         TIMES    EXTRACT TO          LINES SAVED  │
│  ────────────────         ─────    ──────────           ───────────  │
│  DB open/query/close      57       db/helpers.py        228         │
│  Pagination logic         12       utils/pagination.py  48          │
│  Error response building  15       utils/errors.py      60          │
│  Input validation         20       utils/validation.py  40          │
│  Schema init + conn       34       db/helpers.py        102         │
│  JSON serialize result    25       utils/serialize.py   50          │
│  Paginated response dict  12       utils/pagination.py  48          │
│  ──────────────────────────────────────────────────────             │
│  TOTAL                    177 patterns → 7 helpers     576 lines    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: Proper Comments

---

### 4.1 Comment Rules

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  RULE 1: Comments explain WHY, not WHAT.                             │
│  RULE 2: Code should be self-documenting.                            │
│  RULE 3: Every module has a docstring.                               │
│  RULE 4: Every public function has a docstring.                      │
│  RULE 5: Every class has a docstring.                                │
│  RULE 6: Inline comments are rare and explain non-obvious logic.     │
│  RULE 7: No commented-out code (use git to remember).               │
│  RULE 8: Section comments use ── delimiters for scanning.            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Module Docstrings — Every File Gets One

```python
"""Composite Opportunity Scorer — the central scoring engine.

Combines multiple signal sources into a single explainable opportunity score
using time-weighted decay, anomaly detection, and confidence factors.

Formula:
  Composite_Score(entity, t) =
      SUM( w_i * signal_score_i * decay(t - t_i) )
      / SUM( w_i * decay(t - t_i) )
      * anomaly_multiplier
      * confidence_factor

Usage:
    scorer = CompositeScorer()
    result = scorer.score(
        entity_name="Neuromorphic Labs",
        entity_type="company",
        signal_scores={
            "funding_round": {"raw_score": 90, "published_at": datetime(...)},
            "sec_filing":    {"raw_score": 75, "published_at": datetime(...)},
        },
    )
    print(result.composite_score)  # 78.5

Design choices:
    - Stateless by design (all state passed per-call)
    - Time decay uses exponential function with per-signal lambda
    - Anomaly detection uses Z-score with configurable threshold
"""
```

**Good module docstrings include:**
1. One-line summary
2. What the module does (2-3 sentences)
3. Usage example
4. Design choices (why, not what)

### 4.3 Function Docstrings — Google Style

```python
def score(
    self,
    entity_name: str,
    entity_type: str = "company",
    signal_scores: dict[str, dict[str, Any]] | None = None,
    historical_values: dict[str, list[float]] | None = None,
) -> ScoreResult:
    """Compute the composite opportunity score for an entity.

    Combines weighted signal scores with time decay, applies anomaly
    detection, and adjusts for confidence based on signal coverage.

    Args:
        entity_name: Name of the entity (company, technology, market).
        entity_type: Entity type ("company", "technology", "market").
        signal_scores: Map of signal_type → {raw_score, published_at}.
            raw_score is 0-100. published_at is when the signal was detected.
        historical_values: Optional map of signal_type → historical values
            for anomaly detection (chronological, oldest first).

    Returns:
        ScoreResult with composite_score, attribution, trend, confidence.

    Raises:
        ValueError: If signal_scores contains invalid types.

    Examples:
        >>> scorer = CompositeScorer()
        >>> result = scorer.score("Tesla", signal_scores={
        ...     "funding_round": {"raw_score": 90, "published_at": now},
        ... })
        >>> result.composite_score > 0
        True
    """
```

**Good function docstrings include:**
1. One-line summary (imperative mood: "Compute", not "Computes")
2. Detailed description (if complex)
3. `Args:` — every parameter named and described
4. `Returns:` — what comes back
5. `Raises:` — exceptions that can be thrown
6. `Examples:` — doctest-style usage (optional but valuable)

### 4.4 Inline Comments — Only for Non-Obvious Logic

```python
# ✅ CORRECT — explains WHY
# Z-score > 2.0 means this signal is 2 standard deviations above the mean.
# We boost these because sudden spikes often precede major events.
if anomaly_result.is_anomaly:
    anomaly_multiplier = self._anomaly_boost

# ✅ CORRECT — explains a business rule
# Kafka key = entity_name so all signals for one entity go to same partition.
# This enables efficient per-entity windowed aggregation.
return self.entity_name.lower().strip() or "unknown"

# ✅ CORRECT — explains a workaround
# Ollama returns 404 during model pull — retry after delay
if response.status_code == 404:
    time.sleep(5)
    continue

# ❌ WRONG — states the obvious
# Increment counter by 1
counter += 1

# ❌ WRONG — restates the code
# Set score to 85.3
score = 85.3

# ❌ WRONG — commented-out code
# old_scoring_method()
# score = raw_score * 0.8
```

### 4.5 Section Comments — Use ── Delimiters

```python
# ── Stage 1: Ingest from Kafka ──
flow.input("kafka_in", source)

# ── Stage 2: Enrich with fast sentiment ──
flow.map(_op_enrich)

# ── Stage 3: Aggregate by entity (tumbling window) ──
flow.reduce_window(_collect_signals, clock)

# ── Stage 4: Score aggregated signals ──
flow.map(_op_score)

# ── Stage 5: Write to MySQL + publish to Kafka ──
flow.map(_op_write_mysql)
```

This pattern lets you scan a file and jump to sections quickly.

### 4.6 TODO Comments — Use a Standard Format

```python
# TODO(gokul): Add connection pooling — currently opens new conn per request. [R2]
# TODO(gokul): Rate limiting needed before public launch. [T-059]
# FIXME: test_semantic_search.py — 12 tests fail due to dict ordering. [R1]
# HACK: Using sleep(5) because Ollama pull is async — replace with polling.
# DEPRECATED: datetime.utcnow() — use datetime.now(timezone.utc) instead. [R15]
```

**Format**: `TAG(author): Description. [Cross-reference]`

**Tags:**
- `TODO` — needs to be done
- `FIXME` — broken, needs fixing
- `HACK` — works but is ugly, should improve
- `DEPRECATED` — still works but will be removed

---

## Part 5: Configuration & Tooling

---

### 5.1 `pyproject.toml` — Project Configuration

```toml
[project]
name = "opportunity-intelligence-platform"
version = "1.0.0"
requires-python = ">=3.12"

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "TCH",  # flake8-type-checking
]
ignore = [
    "E501",   # line too long (handled by formatter)
    "B008",   # function call in default argument
    "SIM108", # ternary operator (sometimes if/else is clearer)
]

[tool.ruff.lint.isort]
known-first-party = ["agents", "collectors", "config", "db", "ingestion", "nlp", "scoring", "stream", "auth", "utils", "monitoring", "webhooks", "report"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Enable later when coverage > 80%
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

### 5.2 `Makefile` — Common Commands

```makefile
.PHONY: lint format test check run clean

lint:
	ruff check . --statistics

format:
	ruff format . && ruff check --fix .

test:
	python -m pytest tests/ -v --tb=short

check: lint test
	@echo "✅ All checks passed"

run:
	python api_server.py --host 0.0.0.0 --port 8000

dashboard:
	streamlit run streamlit_app.py --server.port 8501

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
	find . -type f -name "*.pyc" -delete
	rm -rf .mypy_cache .pytest_cache .ruff_cache

coverage:
	python -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

types:
	mypy agents/ collectors/ scoring/ stream/ db/ api_server.py --ignore-missing-imports
```

### 5.3 Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: no-commit-to-branch
        args: [--branch, main]
```

---

## Part 6: The Standards Checklist

---

### Before Every Commit, Check:

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  □ ruff check . passes (0 errors)                                   │
│  □ ruff format . applied (consistent formatting)                    │
│  □ All functions ≤ 50 lines (extract if longer)                     │
│  □ No commented-out code                                            │
│  □ No hardcoded secrets or magic numbers                            │
│  □ New functions have type annotations                              │
│  □ New public functions have docstrings                             │
│  □ New files have module docstrings                                 │
│  □ Names follow PEP 8 (snake_case, PascalCase, UPPER_SNAKE)        │
│  □ No bare except Exception (be specific)                           │
│  □ Uses db/helpers.py instead of raw get_connection()               │
│  □ Tests pass: python -m pytest tests/ -q                          │
│  □ Commit message follows Conventional Commits                      │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
```
feat:      New feature (agent, endpoint, collector)
fix:       Bug fix
docs:      Documentation only
style:     Formatting (no code change)
refactor:  Code restructure (no behavior change)
test:      Adding or updating tests
chore:     Build, CI, dependencies
perf:      Performance improvement
```

**Examples:**
```
feat(api): add /api/watchlist CRUD endpoints
fix(scoring): handle empty signal_scores gracefully
docs(agents): add docstrings to 12 agent files
refactor(db): extract db helpers to eliminate 57 boilerplate blocks
test(api): add 68 endpoint tests for api_server.py
chore(deps): update pymysql to 1.1.1
```

---

## Part 7: Refactoring Priority — Standards Compliance

---

### 20 Files to Fix First (by impact)

```
┌────┬──────────────────────────────────┬────────────────┬──────────────┐
│ #  │ File                             │ Issue          │ Fix          │
├────┼──────────────────────────────────┼────────────────┼──────────────┤
│ S1 │ agents/dashboard.py (3,273 lines)│ Too large      │ Split into 5 │
│ S2 │ agents/orchestrator.py           │ 224-line elif  │ Auto-discover│
│ S3 │ api_server.py                    │ 1,500+ lines   │ Split routers│
│ S4 │ db/schema.py                     │ 1,000+ lines   │ Split tables │
│ S5 │ seed_data.py                     │ 257-line func  │ Break up     │
│ S6 │ 57 files with DB boilerplate     │ Copy-paste     │ db/helpers   │
│ S7 │ 12 list endpoints               │ Pagination     │ utils/pag    │
│ S8 │ 15 error responses              │ Inconsistent   │ utils/errors │
│ S9 │ 20 user input endpoints         │ No validation  │ utils/valid  │
│S10 │ 250 except Exception catches    │ Too broad      │ Be specific  │
├────┼──────────────────────────────────┼────────────────┼──────────────┤
│S11 │ agents/opportunity_pipeline_agent│ 209 lines      │ Extract 4    │
│S12 │ agents/nlp_enrichment_agent.py  │ 204 lines      │ Extract 4    │
│S13 │ agents/span_agent.py            │ 186 lines      │ Extract 3    │
│S14 │ collectors/job_postings.py       │ 165 lines      │ Extract 4    │
│S15 │ collectors/github_deep.py        │ 161 lines      │ Extract 4    │
│S16 │ collectors/sec_edgar.py          │ 148 lines      │ Extract 3    │
│S17 │ collectors/github_trends.py      │ 145 lines      │ Extract 3    │
│S18 │ agents/semantic_search_agent.py  │ 145 lines      │ Extract 3    │
│S19 │ agents/revival_opportunity_agent │ 139 lines      │ Extract 3    │
│S20 │ agents/ml_predictor.py           │ 138 lines      │ Extract 3    │
└────┴──────────────────────────────────┴────────────────┴──────────────┘
```

### Schedule

```
SPRINT 1: S6 (db helpers), S9 (validation)           — Standards foundation
SPRINT 2: S10 (specific exceptions), S8 (errors)     — Error handling
SPRINT 3: S7 (pagination)                             — API consistency
SPRINT 4: S2 (auto-discover), S3 (split api_server)  — Architecture
SPRINT 5: S1 (split dashboard), S4 (split schema)    — File size
SPRINT 6: S5 (seed_data), S11-S20 (long functions)   — Function size
```

---

## Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  NAMING:     PEP 8 everywhere. snake_case functions, PascalCase     │
│              classes, UPPER_SNAKE constants. Verb-first functions.   │
│                                                                      │
│  STRUCTURE:  Imports (stdlib → 3rd → local). Functions ≤ 50 lines.  │
│              Files ≤ 500 lines. Section comments with ──.            │
│              Standard file layout (docstring → imports → code).      │
│                                                                      │
│  REUSE:      db/helpers.py (57 → 1 line per query).                 │
│              utils/pagination.py (12 endpoints simplified).          │
│              utils/errors.py (15 error builders unified).            │
│              utils/validation.py (20 endpoints secured).             │
│              agents/orchestrator auto-discovery (224 → 35 lines).    │
│              Total: 576 lines of boilerplate eliminated.             │
│                                                                      │
│  COMMENTS:   Module docstring on every file.                         │
│              Google-style docstrings on every public function.       │
│              Inline comments explain WHY, not WHAT.                  │
│              Section delimiters with ── for scanning.                │
│              Standard TODO/FIXME/HACK format with author + ref.      │
│                                                                      │
│  TOOLING:    ruff (lint + format), mypy (types), pytest (tests),    │
│              pre-commit hooks, Makefile for common commands.         │
│              pyproject.toml as single config source.                 │
│                                                                      │
│  BEFORE EACH COMMIT:                                                 │
│  ruff check → ruff format → pytest → no hardcoded secrets →         │
│  docstrings → type hints → conventional commit message              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*
*Cross-references: DESIGN_BEFORE_CODING.md, WORK_PLAN.md, VERSION_CONTROL.md, TESTING_STRATEGY.md*

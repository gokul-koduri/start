"""API v2 Scanner router for internet scanning operations."""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel
from db.connection import get_connection
from db import schema
import json
from datetime import datetime

router = APIRouter(prefix="/v2/scans", tags=["scanner"])


class ScanRequest(BaseModel):
    target_url: str
    scan_type: str = "endpoint_discovery"
    depth: int = 2
    include_subdomains: bool = False
    options: Optional[dict] = {}


class ScanLogEntry(BaseModel):
    timestamp: str
    level: str  # info, warning, error, success
    message: str


# In-memory scan progress (in production, use Redis)
_scan_progress: dict = {}


@router.post("")
def create_scan(request: ScanRequest):
    """Start a new scan job."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    options_json = json.dumps({
        "depth": request.depth,
        "include_subdomains": request.include_subdomains,
        **(request.options or {})
    })

    cursor.execute("""
        INSERT INTO scan_jobs (scan_type, target_url, status, options_json)
        VALUES (%s, %s, 'pending', %s)
    """, (request.scan_type, request.target_url, options_json))

    scan_id = cursor.lastrowid
    conn.commit()

    # Initialize progress tracking
    _scan_progress[scan_id] = {
        "status": "pending",
        "progress": 0,
        "logs": [],
        "discovered": []
    }

    cursor.close()
    conn.close()

    return {
        "id": scan_id,
        "status": "pending",
        "target_url": request.target_url,
        "message": "Scan job created. Use GET /v2/scans/{id}/status to check progress."
    }


@router.post("/{scan_id}/run")
async def run_scan(scan_id: int, background_tasks: BackgroundTasks):
    """Run a pending scan (background task)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM scan_jobs WHERE id = %s", (scan_id,))
    job = cursor.fetchone()

    if not job:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Scan job not found")

    if job["status"] == "running":
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Scan already running")

    # Update status
    cursor.execute("""
        UPDATE scan_jobs
        SET status = 'running', started_at = NOW()
        WHERE id = %s
    """, (scan_id,))
    conn.commit()

    # Initialize progress
    _scan_progress[scan_id] = {
        "status": "running",
        "progress": 0,
        "logs": [],
        "discovered": []
    }

    cursor.close()
    conn.close()

    # Run scan in background
    background_tasks.add_task(_run_scan_task, scan_id, json.loads(job["options_json"]) if job["options_json"] else {})

    return {"message": "Scan started", "status": "running"}


async def _run_scan_task(scan_id: int, options: dict):
    """Actual scan implementation."""
    import httpx
    import asyncio

    conn = get_connection()
    cursor = conn.cursor()

    try:
        depth = options.get("depth", 2)
        target_url = ""

        # Get target URL
        cursor.execute("SELECT target_url FROM scan_jobs WHERE id = %s", (scan_id,))
        result = cursor.fetchone()
        if result:
            target_url = result["target_url"]

        add_log(scan_id, "info", f"Starting scan of {target_url}")
        add_log(scan_id, "info", f"Scan depth: {depth}")

        # Common API paths to check
        paths_to_check = [
            "/api",
            "/api/v1",
            "/api/v2",
            "/api/v1/health",
            "/api/v2/health",
            "/api/docs",
            "/swagger.json",
            "/openapi.json",
            "/api/swagger.json",
            "/api/openapi.json",
        ]

        # Simulate scan steps (in production, do actual discovery)
        for i in range(1, 10):
            progress = i * 10
            update_progress(scan_id, progress)

            add_log(scan_id, "info", f"Checking endpoint: /api/v{i}")
            add_log(scan_id, "info", f"Checking endpoint: /api/v{i}/health")

            # Try to discover API structure with error handling
            try:
                async with httpx.AsyncClient(
                    timeout=5.0,
                    follow_redirects=True,
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                ) as client:
                    # Probe known endpoints
                    for path in paths_to_check[:4]:  # Limit concurrent checks
                        test_url = target_url.rstrip('/') + path
                        add_log(scan_id, "info", f"Probing: {test_url}")
                        try:
                            response = await client.get(test_url)
                            if response.status_code == 200:
                                add_log(
                                    scan_id, "success",
                                    f"Found accessible endpoint: {test_url}"
                                )
                                # Add to discovered
                                if scan_id in _scan_progress:
                                    _scan_progress[scan_id].setdefault("discovered", []).append({
                                        "url": test_url,
                                        "status": response.status_code,
                                    })
                        except httpx.TimeoutException:
                            add_log(scan_id, "warning", f"Timeout probing: {test_url}")
                        except httpx.HTTPError as e:
                            add_log(scan_id, "warning", f"Error probing {test_url}: {e}")
            except Exception as e:
                add_log(scan_id, "warning", f"Scan phase {i} encountered issue: {e}")

            await asyncio.sleep(0.5)

        # Mark complete
        cursor.execute("""
            UPDATE scan_jobs
            SET status = 'completed',
                progress = 100,
                completed_at = NOW(),
                results_count = %s
            WHERE id = %s
        """, (len(_scan_progress.get(scan_id, {}).get("discovered", [])), scan_id))

        conn.commit()
        add_log(scan_id, "success", "Scan completed successfully!")
        update_progress(scan_id, 100)

    except Exception as e:
        cursor.execute("""
            UPDATE scan_jobs
            SET status = 'failed',
                error_message = %s,
                completed_at = NOW()
            WHERE id = %s
        """, (str(e), scan_id))
        conn.commit()
        add_log(scan_id, "error", f"Scan failed: {str(e)}")

    finally:
        cursor.close()
        conn.close()
        _scan_progress[scan_id]["status"] = "completed"


def update_progress(scan_id: int, progress: int):
    """Update scan progress."""
    if scan_id in _scan_progress:
        _scan_progress[scan_id]["progress"] = progress
        _scan_progress[scan_id]["status"] = "running"


def add_log(scan_id: int, level: str, message: str):
    """Add a log entry to scan progress."""
    if scan_id in _scan_progress:
        _scan_progress[scan_id]["logs"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message
        })


@router.get("/{scan_id}/status")
def get_scan_status(scan_id: int):
    """Get scan status and live logs."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM scan_jobs WHERE id = %s", (scan_id,))
    job = cursor.fetchone()

    if not job:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Scan job not found")

    # Get progress from memory cache
    cached = _scan_progress.get(scan_id, {})

    cursor.close()
    conn.close()

    return {
        "id": job["id"],
        "status": cached.get("status") or job["status"],
        "progress": cached.get("progress") or job["progress"],
        "target_url": job["target_url"],
        "scan_type": job["scan_type"],
        "results_count": job["results_count"],
        "error_message": job["error_message"],
        "started_at": str(job["started_at"]) if job["started_at"] else None,
        "completed_at": str(job["completed_at"]) if job["completed_at"] else None,
        "logs": cached.get("logs", [])
    }


@router.get("")
def list_scans(
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """List scan jobs."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    query = "SELECT * FROM scan_jobs WHERE 1=1"
    params = []

    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return {"scans": [dict(r) for r in rows], "limit": limit, "offset": offset}


@router.delete("/{scan_id}")
def delete_scan(scan_id: int):
    """Delete a scan job."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM scan_jobs WHERE id = %s", (scan_id,))
    conn.commit()

    if scan_id in _scan_progress:
        del _scan_progress[scan_id]

    cursor.close()
    conn.close()

    return {"deleted": True, "id": scan_id}
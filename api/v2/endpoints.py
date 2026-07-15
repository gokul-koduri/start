"""API v2 Endpoints router for managing individual API endpoints."""

from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from db.connection import get_connection
from db import schema
import json
import httpx
import asyncio
from datetime import datetime

router = APIRouter(prefix="/v2/endpoints", tags=["endpoints"])


class EndpointTestRequest(BaseModel):
    method: str = "GET"
    url: str
    headers: Optional[dict] = {}
    body: Optional[str] = None
    auth_type: Optional[str] = None
    auth_value: Optional[str] = None


class EndpointTestResponse(BaseModel):
    status_code: int
    headers: dict
    body: str
    latency_ms: int
    errors: Optional[List[str]] = []
    timestamp: str


# Block private IP ranges for security
BLOCKED_PREFIXES = [
    "10.", "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.", "127.", "localhost", "0.0.0.0"
]


def is_blocked_url(url: str) -> bool:
    """Check if URL points to internal/private network."""
    lower_url = url.lower()
    return any(lower_url.startswith(prefix) for prefix in BLOCKED_PREFIXES)


@router.get("")
def list_endpoints(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    registry_id: Optional[int] = None,
    method: Optional[str] = None,
    auth_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """List all API endpoints with filtering."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    query = """
        SELECT e.*, r.name as registry_name, r.base_url as registry_base_url
        FROM api_endpoints e
        JOIN api_registries r ON e.registry_id = r.id
        WHERE 1=1
    """
    params = []

    if registry_id:
        query += " AND e.registry_id = %s"
        params.append(registry_id)
    if method:
        query += " AND e.method = %s"
        params.append(method.upper())
    if auth_type:
        query += " AND e.auth_type = %s"
        params.append(auth_type)
    if status:
        query += " AND e.status = %s"
        params.append(status)
    if search:
        query += " AND (e.path LIKE %s OR e.summary LIKE %s OR r.name LIKE %s)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])

    # Count total
    count_query = query.replace("SELECT e.*, r.name as registry_name, r.base_url as registry_base_url", "SELECT COUNT(*) as total")
    cursor.execute(count_query, params)
    total = cursor.fetchone()["total"]

    # Add pagination
    query += " ORDER BY e.popularity_score DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    endpoints = []
    for row in rows:
        ep = dict(row)
        if ep.get("tags_json"):
            try:
                ep["tags"] = json.loads(ep["tags_json"])
            except (json.JSONDecodeError, TypeError):
                ep["tags"] = []
        endpoints.append(ep)

    cursor.close()
    conn.close()

    return {
        "endpoints": endpoints,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(endpoints) < total
    }


@router.get("/methods")
def get_methods():
    """Get list of supported HTTP methods."""
    return {
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
    }


@router.get("/{endpoint_id}")
def get_endpoint(endpoint_id: int):
    """Get a specific endpoint by ID."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.*, r.name as registry_name, r.base_url as registry_base_url,
               r.documentation_url, o.name as org_name
        FROM api_endpoints e
        JOIN api_registries r ON e.registry_id = r.id
        LEFT JOIN api_organizations o ON r.organization_id = o.id
        WHERE e.id = %s
    """, (endpoint_id,))

    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Endpoint with ID {endpoint_id} not found")

    endpoint = dict(row)
    if endpoint.get("tags_json"):
        try:
            endpoint["tags"] = json.loads(endpoint["tags_json"])
        except (json.JSONDecodeError, TypeError):
            endpoint["tags"] = []

    # Get request schema
    cursor.execute("""
        SELECT * FROM endpoint_requests WHERE endpoint_id = %s
    """, (endpoint_id,))
    schema_row = cursor.fetchone()
    if schema_row:
        req = dict(schema_row)
        for key in ["headers_json", "body_schema_json", "query_params_json", "path_params_json", "response_codes_json"]:
            if req.get(key):
                try:
                    req[key.replace("_json", "")] = json.loads(req[key])
                except (json.JSONDecodeError, TypeError):
                    pass
        endpoint["request_schema"] = req

    # Get technologies
    cursor.execute("""
        SELECT technology, category, version, confidence
        FROM endpoint_technologies
        WHERE endpoint_id = %s
        ORDER BY confidence DESC
    """, (endpoint_id,))
    endpoint["technologies"] = [dict(t) for t in cursor.fetchall()]

    # Get security analyses
    cursor.execute("""
        SELECT check_type, severity, finding, recommendation, analyzed_at
        FROM security_analyses
        WHERE endpoint_id = %s
        ORDER BY analyzed_at DESC
    """, (endpoint_id,))
    endpoint["security_checks"] = [dict(s) for s in cursor.fetchall()]

    cursor.close()
    conn.close()

    return endpoint


@router.post("/test")
async def test_endpoint(request: EndpointTestRequest):
    """
    Test an API endpoint by making a real HTTP request.

    Security features:
    - Blocks private/internal IP addresses
    - 10 second timeout
    - Max 5MB response size
    """
    # Security check
    if is_blocked_url(request.url):
        return JSONResponse(
            status_code=400,
            content={
                "error": "URL blocked",
                "detail": "Cannot make requests to private/internal networks"
            }
        )

    # Build headers
    headers = dict(request.headers) if request.headers else {}
    headers["User-Agent"] = "API-Explorer/1.0"

    # Add auth header if provided
    if request.auth_type and request.auth_value:
        if request.auth_type.lower() == "bearer":
            headers["Authorization"] = f"Bearer {request.auth_value}"
        elif request.auth_type.lower() == "apikey":
            headers["X-API-Key"] = request.auth_value
        elif request.auth_type.lower() == "basic":
            import base64
            headers["Authorization"] = f"Basic {base64.b64encode(request.auth_value.encode()).decode()}"

    errors = []
    start_time = asyncio.get_event_loop().time()

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, limits=httpx.Limits(max_bytes=5_242_880)) as client:
            request_kwargs = {
                "method": request.method.upper(),
                "url": request.url,
                "headers": headers,
            }

            if request.body and request.method in ["POST", "PUT", "PATCH"]:
                request_kwargs["content"] = request.body.encode()
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"

            response = await client.request(**request_kwargs)
            latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            # Parse response body
            try:
                response_body = response.text[:10000]  # Limit to 10KB for display
            except Exception:
                response_body = "[Binary or unreadable response]"

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "latency_ms": latency_ms,
                "errors": errors if errors else None,
                "timestamp": datetime.utcnow().isoformat(),
                "success": True
            }

    except httpx.TimeoutException:
        return JSONResponse(
            status_code=408,
            content={
                "error": "Request timeout",
                "detail": "The request took too long to complete (max 10s)",
                "latency_ms": 10000,
                "timestamp": datetime.utcnow().isoformat(),
                "success": False
            }
        )
    except httpx.InvalidURL as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid URL",
                "detail": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "success": False
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Request failed",
                "detail": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "success": False
            }
        )


@router.get("/{endpoint_id}/test")
async def test_saved_endpoint(
    endpoint_id: int,
    mock: bool = Query(False, description="Return mock response instead of making real request")
):
    """Test a saved endpoint by its ID."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT e.*, r.base_url as registry_base_url
        FROM api_endpoints e
        JOIN api_registries r ON e.registry_id = r.id
        WHERE e.id = %s
    """, (endpoint_id,))

    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Endpoint with ID {endpoint_id} not found")

    endpoint = dict(row)

    if mock:
        # Return mock response based on saved schema
        cursor.execute("SELECT * FROM endpoint_requests WHERE endpoint_id = %s", (endpoint_id,))
        schema_row = cursor.fetchone()
        cursor.close()
        conn.close()

        return {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "body": schema_row.get("example_response", '{"message": "Mock response"}') if schema_row else '{"message": "Mock response"}',
            "latency_ms": endpoint.get("latency_ms", 150),
            "errors": None,
            "timestamp": datetime.utcnow().isoformat(),
            "success": True,
            "mock": True
        }

    # Build full URL
    base_url = endpoint.get("registry_base_url", "")
    path = endpoint.get("path", "")
    full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    return await test_endpoint(EndpointTestRequest(
        method=endpoint.get("method", "GET"),
        url=full_url,
        auth_type=endpoint.get("auth_type")
    ))
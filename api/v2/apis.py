"""API v2 Registry router for managing API collections."""

from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from db.connection import get_connection
from db import schema
import json

router = APIRouter(prefix="/v2/apis", tags=["apis"])


class APIRegistryResponse(BaseModel):
    id: int
    name: str
    organization_id: Optional[int]
    description: Optional[str]
    documentation_url: Optional[str]
    base_url: Optional[str]
    is_public: int
    popularity_score: int
    api_version: Optional[str]
    category: Optional[str]
    tags_json: Optional[str]
    logo_url: Optional[str]
    created_at: str
    updated_at: str


@router.get("")
def list_apis(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    organization_id: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("popularity_score", pattern="^(popularity_score|created_at|name)$"),
    order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
):
    """List API registries with filtering and pagination."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    query = """
        SELECT r.*, o.name as organization_name, o.logo_url as org_logo_url
        FROM api_registries r
        LEFT JOIN api_organizations o ON r.organization_id = o.id
        WHERE 1=1
    """
    params = []

    if category:
        query += " AND r.category = %s"
        params.append(category)
    if organization_id:
        query += " AND r.organization_id = %s"
        params.append(organization_id)
    if search:
        query += " AND (r.name LIKE %s OR r.description LIKE %s)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])

    # Count total
    count_query = query.replace("SELECT r.*, o.name as organization_name, o.logo_url as org_logo_url", "SELECT COUNT(*) as total")
    cursor.execute(count_query, params)
    total = cursor.fetchone()["total"]

    # Add sorting and pagination
    order_dir = "DESC" if order == "desc" else "ASC"
    query += f" ORDER BY r.{sort_by} {order_dir} LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    apis = []
    for row in rows:
        api = dict(row)
        if api.get("tags_json"):
            try:
                api["tags"] = json.loads(api["tags_json"])
            except (json.JSONDecodeError, TypeError):
                api["tags"] = []
        apis.append(api)

    cursor.close()
    conn.close()

    return {
        "apis": apis,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(apis) < total
    }


@router.get("/search")
def search_apis(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=50),
):
    """Quick search for APIs (autocomplete style)."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    search_term = f"%{q}%"
    cursor.execute("""
        SELECT id, name, base_url, category, logo_url
        FROM api_registries
        WHERE name LIKE %s OR base_url LIKE %s
        ORDER BY popularity_score DESC
        LIMIT %s
    """, (search_term, search_term, limit))

    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return {"results": [dict(r) for r in results]}


@router.get("/stats")
def get_api_stats():
    """Get overall API statistics for dashboard."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    stats = {}

    # Total APIs
    cursor.execute("SELECT COUNT(*) as count FROM api_registries")
    stats["total_apis"] = cursor.fetchone()["count"]

    # Total endpoints
    cursor.execute("SELECT COUNT(*) as count FROM api_endpoints")
    stats["total_endpoints"] = cursor.fetchone()["count"]

    # Total organizations
    cursor.execute("SELECT COUNT(*) as count FROM api_organizations")
    stats["total_organizations"] = cursor.fetchone()["count"]

    # Total technologies detected
    cursor.execute("SELECT COUNT(DISTINCT technology) as count FROM endpoint_technologies")
    stats["total_technologies"] = cursor.fetchone()["count"]

    # API categories breakdown
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM api_registries
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY count DESC
        LIMIT 10
    """)
    stats["categories"] = [dict(r) for r in cursor.fetchall()]

    # Method distribution
    cursor.execute("""
        SELECT method, COUNT(*) as count
        FROM api_endpoints
        GROUP BY method
        ORDER BY count DESC
    """)
    stats["method_distribution"] = [dict(r) for r in cursor.fetchall()]

    # Top technologies
    cursor.execute("""
        SELECT technology, category, COUNT(*) as count
        FROM endpoint_technologies
        GROUP BY technology, category
        ORDER BY count DESC
        LIMIT 10
    """)
    stats["top_technologies"] = [dict(r) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return stats


@router.get("/{api_id}")
def get_api(api_id: int):
    """Get a specific API registry by ID."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*, o.name as organization_name, o.logo_url as org_logo_url, o.website as org_website
        FROM api_registries r
        LEFT JOIN api_organizations o ON r.organization_id = o.id
        WHERE r.id = %s
    """, (api_id,))

    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"API with ID {api_id} not found")

    api = dict(row)
    if api.get("tags_json"):
        try:
            api["tags"] = json.loads(api["tags_json"])
        except (json.JSONDecodeError, TypeError):
            api["tags"] = []

    # Get endpoint count
    cursor.execute("SELECT COUNT(*) as count FROM api_endpoints WHERE registry_id = %s", (api_id,))
    api["endpoint_count"] = cursor.fetchone()["count"]

    cursor.close()
    conn.close()

    return api


@router.get("/{api_id}/endpoints")
def get_api_endpoints(
    api_id: int,
    method: Optional[str] = None,
    auth_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get all endpoints for a specific API registry."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    # Verify API exists
    cursor.execute("SELECT COUNT(*) as count FROM api_registries WHERE id = %s", (api_id,))
    if not cursor.fetchone()["count"]:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"API with ID {api_id} not found")

    query = "SELECT * FROM api_endpoints WHERE registry_id = %s"
    params = [api_id]

    if method:
        query += " AND method = %s"
        params.append(method)
    if auth_type:
        query += " AND auth_type = %s"
        params.append(auth_type)

    query += " ORDER BY popularity_score DESC LIMIT %s OFFSET %s"
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

    return {"endpoints": endpoints, "limit": limit, "offset": offset}


@router.post("")
def create_api(
    name: str,
    base_url: Optional[str] = None,
    organization_id: Optional[int] = None,
    description: Optional[str] = None,
    documentation_url: Optional[str] = None,
    api_version: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
):
    """Create a new API registry."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    tags_json = json.dumps(tags) if tags else None

    cursor.execute("""
        INSERT INTO api_registries
        (name, base_url, organization_id, description, documentation_url, api_version, category, tags_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (name, base_url, organization_id, description, documentation_url, api_version, category, tags_json))

    api_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    return {"id": api_id, "name": name, "created": True}
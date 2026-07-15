"""API v2 Organizations router."""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from db.connection import get_connection
from db import schema
import json

router = APIRouter(prefix="/v2/organizations", tags=["organizations"])


@router.get("")
def list_organizations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    country: Optional[str] = None,
    search: Optional[str] = None,
):
    """List API organizations."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    query = """
        SELECT o.*,
               COUNT(r.id) as api_count,
               SUM(e.popularity_score) as total_endpoint_score
        FROM api_organizations o
        LEFT JOIN api_registries r ON o.id = r.organization_id
        LEFT JOIN api_endpoints e ON r.id = e.registry_id
        WHERE 1=1
    """
    params = []

    if country:
        query += " AND o.country = %s"
        params.append(country)
    if search:
        query += " AND o.name LIKE %s"
        params.append(f"%{search}%")

    query += " GROUP BY o.id"

    # Count
    count_query = f"""
        SELECT COUNT(*) as total FROM (
            {query.replace("SELECT o.*,\n               COUNT(r.id) as api_count,\n               SUM(e.popularity_score) as total_endpoint_score", "SELECT COUNT(DISTINCT o.id) as total")}
        ) as subq
    """
    cursor.execute(count_query.replace(" AND o.country = %s", "").replace(" AND o.name LIKE %s", "").replace("AND 1=1", "SELECT COUNT(DISTINCT o.id) as total FROM api_organizations o"), [] if not country and not search else ([country] if country else []) + ([f"%{search}%"] if search else []))
    total = cursor.fetchone()["total"]

    query += " ORDER BY api_count DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()

    orgs = []
    for row in rows:
        org = dict(row)
        if org.get("social_links_json"):
            try:
                org["social_links"] = json.loads(org["social_links_json"])
            except (json.JSONDecodeError, TypeError):
                org["social_links"] = {}
        orgs.append(org)

    cursor.close()
    conn.close()

    return {
        "organizations": orgs,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/countries")
def get_countries():
    """Get list of unique countries."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT country, COUNT(*) as count
        FROM api_organizations
        WHERE country IS NOT NULL
        GROUP BY country
        ORDER BY count DESC
    """)

    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return {"countries": [dict(r) for r in results]}


@router.get("/{org_id}")
def get_organization(org_id: int):
    """Get organization details with its APIs."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM api_organizations WHERE id = %s", (org_id,))
    row = cursor.fetchone()

    if not row:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail=f"Organization with ID {org_id} not found")

    org = dict(row)
    if org.get("social_links_json"):
        try:
            org["social_links"] = json.loads(org["social_links_json"])
        except (json.JSONDecodeError, TypeError):
            org["social_links"] = {}

    # Get APIs
    cursor.execute("""
        SELECT id, name, base_url, api_version, category, popularity_score
        FROM api_registries
        WHERE organization_id = %s
        ORDER BY popularity_score DESC
    """, (org_id,))
    org["apis"] = [dict(r) for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return org
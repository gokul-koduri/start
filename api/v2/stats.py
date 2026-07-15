"""API v2 Dashboard Stats router."""

from fastapi import APIRouter
from db.connection import get_connection
from db import schema

router = APIRouter(prefix="/v2/stats", tags=["stats"])


@router.get("/dashboard")
def get_dashboard_stats():
    """Get dashboard statistics and KPIs."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    stats = {}

    # Basic counts
    tables = [
        ("api_registries", "total_apis"),
        ("api_endpoints", "total_endpoints"),
        ("api_organizations", "total_organizations"),
    ]

    for table, key in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[key] = cursor.fetchone()["count"]
        except:
            stats[key] = 0

    # Active endpoints (last 7 days)
    try:
        cursor.execute("""
            SELECT COUNT(*) as count FROM api_endpoints
            WHERE updated_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        stats["active_endpoints_7d"] = cursor.fetchone()["count"]
    except:
        stats["active_endpoints_7d"] = 0

    # Public APIs
    try:
        cursor.execute("SELECT COUNT(*) as count FROM api_registries WHERE is_public = 1")
        stats["public_apis"] = cursor.fetchone()["count"]
    except:
        stats["public_apis"] = 0

    # Recently updated (last 7 days)
    try:
        cursor.execute("""
            SELECT COUNT(*) as count FROM api_registries
            WHERE updated_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        stats["recently_updated"] = cursor.fetchone()["count"]
    except:
        stats["recently_updated"] = 0

    # Technologies count
    try:
        cursor.execute("SELECT COUNT(DISTINCT technology) as count FROM endpoint_technologies")
        stats["technologies_detected"] = cursor.fetchone()["count"]
    except:
        stats["technologies_detected"] = 0

    # Average security score
    try:
        cursor.execute("SELECT AVG(security_score) as avg FROM api_endpoints WHERE security_score > 0")
        result = cursor.fetchone()
        stats["avg_security_score"] = round(result["avg"], 1) if result["avg"] else 0
    except:
        stats["avg_security_score"] = 0

    # Average latency
    try:
        cursor.execute("SELECT AVG(latency_ms) as avg FROM api_endpoints WHERE latency_ms > 0")
        result = cursor.fetchone()
        stats["avg_latency_ms"] = round(result["avg"], 0) if result["avg"] else 0
    except:
        stats["avg_latency_ms"] = 0

    # Method distribution
    try:
        cursor.execute("""
            SELECT method, COUNT(*) as count
            FROM api_endpoints
            GROUP BY method
            ORDER BY count DESC
        """)
        stats["method_distribution"] = [dict(r) for r in cursor.fetchall()]
    except:
        stats["method_distribution"] = []

    # Authentication distribution
    try:
        cursor.execute("""
            SELECT auth_type, COUNT(*) as count
            FROM api_endpoints
            WHERE auth_type IS NOT NULL
            GROUP BY auth_type
            ORDER BY count DESC
        """)
        stats["auth_distribution"] = [dict(r) for r in cursor.fetchall()]
    except:
        stats["auth_distribution"] = []

    # Top categories
    try:
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM api_registries
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
            LIMIT 10
        """)
        stats["top_categories"] = [dict(r) for r in cursor.fetchall()]
    except:
        stats["top_categories"] = []

    # Top technologies
    try:
        cursor.execute("""
            SELECT technology, category, COUNT(*) as count
            FROM endpoint_technologies
            GROUP BY technology, category
            ORDER BY count DESC
            LIMIT 10
        """)
        stats["top_technologies"] = [dict(r) for r in cursor.fetchall()]
    except:
        stats["top_technologies"] = []

    # Top organizations by API count
    try:
        cursor.execute("""
            SELECT o.name, o.logo_url, COUNT(r.id) as api_count
            FROM api_organizations o
            JOIN api_registries r ON o.id = r.organization_id
            GROUP BY o.id, o.name, o.logo_url
            ORDER BY api_count DESC
            LIMIT 10
        """)
        stats["top_organizations"] = [dict(r) for r in cursor.fetchall()]
    except:
        stats["top_organizations"] = []

    # Security status breakdown
    try:
        cursor.execute("""
            SELECT
                SUM(CASE WHEN security_score >= 80 THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN security_score >= 50 AND security_score < 80 THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN security_score > 0 AND security_score < 50 THEN 1 ELSE 0 END) as low,
                SUM(CASE WHEN security_score = 0 OR security_score IS NULL THEN 1 ELSE 0 END) as unrated
            FROM api_endpoints
        """)
        result = cursor.fetchone()
        stats["security_breakdown"] = {
            "high": result.get("high", 0) or 0,
            "medium": result.get("medium", 0) or 0,
            "low": result.get("low", 0) or 0,
            "unrated": result.get("unrated", 0) or 0,
        }
    except:
        stats["security_breakdown"] = {"high": 0, "medium": 0, "low": 0, "unrated": 0}

    cursor.close()
    conn.close()

    return stats


@router.get("/trends")
def get_trends(
    period: str = "30d"  # 7d, 30d, 90d, 1y
):
    """Get trend data for charts."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    # Determine interval based on period
    intervals = {
        "7d": ("DAY", 7, "%Y-%m-%d"),
        "30d": ("DAY", 30, "%Y-%m-%d"),
        "90d": ("WEEK", 13, "%Y-%u"),
        "1y": ("MONTH", 12, "%Y-%m")
    }

    interval_type, num_periods, date_format = intervals.get(period, ("DAY", 30, "%Y-%m-%d"))

    trends = {}

    # API growth over time (simulated - in production, track created_at)
    try:
        cursor.execute(f"""
            SELECT
                DATE_FORMAT(created_at, '{date_format}') as date,
                COUNT(*) as count
            FROM api_registries
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL {num_periods} {interval_type})
            GROUP BY DATE_FORMAT(created_at, '{date_format}')
            ORDER BY date
        """)
        trends["api_growth"] = [{"date": r["date"], "count": r["count"]} for r in cursor.fetchall()]
    except:
        trends["api_growth"] = []

    cursor.close()
    conn.close()

    return {"period": period, "trends": trends}


@router.get("/technologies")
def get_technology_breakdown():
    """Get technology stack breakdown."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    results = {}

    categories = [
        ("backend", ["node.js", "express", "django", "flask", "fastapi", "rails", "spring", "laravel", "asp.net", ".net"]),
        ("frontend", ["react", "vue", "angular", "next.js", "nuxt", "svelte"]),
        ("database", ["postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite"]),
        ("infrastructure", ["nginx", "apache", "aws", "azure", "gcp", "docker", "kubernetes", "cloudflare"]),
    ]

    for category, keywords in categories:
        try:
            placeholders = ", ".join(["%s"] * len(keywords))
            cursor.execute(f"""
                SELECT technology, COUNT(*) as count
                FROM endpoint_technologies
                WHERE LOWER(technology) IN ({placeholders})
                GROUP BY technology
                ORDER BY count DESC
            """, keywords)
            results[category] = [dict(r) for r in cursor.fetchall()]
        except:
            results[category] = []

    cursor.close()
    conn.close()

    return results


@router.get("/data-quality")
def get_data_quality():
    """Get data quality metrics and inventory for all tables."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    # Key tables to monitor
    tables_to_check = {
        "Core Startup Data": [
            ("failed_startups", "Failed Startups"),
            ("failure_reasons_taxonomy", "Failure Reasons Taxonomy"),
            ("manufacturing_failure_categories", "Manufacturing Failure Categories"),
            ("failure_idea_patterns", "Failure Idea Patterns"),
        ],
        "Pipeline Operations": [
            ("pipeline_companies", "Pipeline Companies"),
            ("pipeline_opportunities", "Pipeline Opportunities"),
            ("pipeline_funding_events", "Pipeline Funding Events"),
            ("pipeline_failure_analysis", "Pipeline Failure Analysis"),
        ],
        "Intelligence & Signals": [
            ("news_articles", "News Articles"),
            ("raw_signals", "Raw Signals"),
            ("opportunity_scores", "Opportunity Scores"),
            ("funding_events", "Funding Events"),
            ("patent_filings", "Patent Filings"),
            ("github_trends", "GitHub Trends"),
            ("job_postings", "Job Postings"),
        ],
        "Analysis & Research": [
            ("analysis_global_market_viability", "GMV Analysis"),
            ("analysis_failure_patterns", "Failure Pattern Analysis"),
            ("analysis_revival_opportunities", "Revival Analysis"),
            ("analysis_survival_trends", "Survival Trends"),
            ("analysis_opportunity_pipeline", "Opportunity Pipeline Research"),
        ],
        "Knowledge Graph": [
            ("kg_entity_types", "Entity Types"),
            ("kg_entities", "Entities"),
            ("kg_relationships", "Relationships"),
            ("kg_entity_aliases", "Entity Aliases"),
        ],
        "Reshoring & Market": [
            ("reshoring_data", "Reshoring Data"),
            ("reshoring_summary_stats", "Reshoring Summary"),
            ("revival_industries", "Revival Industries"),
            ("geographic_hotspots", "Geographic Hotspots"),
            ("bls_survival_rates", "BLS Survival Rates"),
        ],
        "LLM & Models": [
            ("llm_pricing", "LLM Pricing"),
            ("llm_benchmarks", "LLM Benchmarks"),
            ("llm_portfolio", "LLM Portfolio"),
            ("ollama_usage_snapshots", "Ollama Usage"),
        ],
    }

    results = {
        "timestamp": "",  # Will be set below
        "summary": {
            "total_records": 0,
            "tables_with_data": 0,
            "tables_without_data": 0,
        },
        "categories": {},
        "gaps": [],
        "recommendations": [],
    }

    import time
    results["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    all_counts = []

    for category, tables in tables_to_check.items():
        cat_result = {}
        for table, display_name in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                count = cursor.fetchone()["cnt"]

                # Get last insert time (approximate via max id or max date)
                last_seen = None
                try:
                    # Try to get last collected/created timestamp
                    date_cols = ["collected_at", "created_at", "analyzed_at",
                                "collected_at", "published_at", "created_at"]
                    for col in date_cols:
                        cursor.execute(f"SELECT MAX({col}) as last_seen FROM {table}")
                        row = cursor.fetchone()
                        if row and row["last_seen"]:
                            last_seen = str(row["last_seen"])[:19]
                            break
                except:
                    pass

                cat_result[table] = {
                    "display_name": display_name,
                    "count": count,
                    "status": "populated" if count > 0 else "empty",
                    "last_updated": last_seen,
                }

                all_counts.append(count)

                if count == 0:
                    results["gaps"].append(f"{display_name} ({table}) has no data")

            except Exception as e:
                cat_result[table] = {
                    "display_name": display_name,
                    "count": 0,
                    "status": "error",
                    "error": str(e)[:100],
                }
                results["gaps"].append(f"{display_name}: {str(e)[:50]}")

        results["categories"][category] = cat_result

    # Calculate summary
    results["summary"]["total_records"] = sum(all_counts)
    results["summary"]["tables_with_data"] = sum(1 for c in all_counts if c > 0)
    results["summary"]["tables_without_data"] = sum(1 for c in all_counts if c == 0)

    # Generate recommendations based on gaps
    critical_gaps = [
        ("raw_signals", "Run collection pipeline to populate signals"),
        ("opportunity_scores", "Run analysis pipeline to score opportunities"),
        ("kg_entities", "Expand knowledge graph with more seed data"),
        ("github_trends", "Enable GitHub trends collector in daily pipeline"),
    ]

    gap_tables = {item.split("(")[1].rstrip(")"): item
                  for item in results["gaps"] if "(" in item}

    for table, recommendation in critical_gaps:
        if gap_tables.get(table):
            results["recommendations"].append(recommendation)

    cursor.close()
    conn.close()

    return results
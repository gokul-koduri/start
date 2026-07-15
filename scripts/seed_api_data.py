"""Seed API endpoint data for the API Explorer."""

import json
from db.connection import get_connection
from db import schema
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample organizations
ORGANIZATIONS = [
    {"name": "Stripe", "slug": "stripe", "website": "https://stripe.com", "description": "Online payment processing", "country": "US", "social_links": {"twitter": "@stripe"}},
    {"name": "GitHub", "slug": "github", "website": "https://github.com", "description": "Code collaboration", "country": "US", "social_links": {"twitter": "@github"}},
    {"name": "Twilio", "slug": "twilio", "website": "https://twilio.com", "description": "Cloud communications", "country": "US", "social_links": {"twitter": "@twilio"}},
    {"name": "OpenAI", "slug": "openai", "website": "https://openai.com", "description": "AI research", "country": "US", "social_links": {"twitter": "@OpenAI"}},
    {"name": "AWS", "slug": "aws", "website": "https://aws.amazon.com", "description": "Cloud computing platform", "country": "US", "social_links": {"twitter": "@awscloud"}},
    {"name": "Slack", "slug": "slack", "website": "https://slack.com", "description": "Team collaboration", "country": "US", "social_links": {"twitter": "@SlackHQ"}},
    {"name": "SendGrid", "slug": "sendgrid", "website": "https://sendgrid.com", "description": "Email delivery", "country": "US", "social_links": {}},
    {"name": "Shopify", "slug": "shopify", "website": "https://shopify.com", "description": "E-commerce platform", "country": "CA", "social_links": {"twitter": "@Shopify"}},
]

# Sample APIs
APIS = [
    {"name": "Stripe API", "base_url": "https://api.stripe.com", "version": "v1", "category": "payment", "description": "Online payment processing", "popularity": 98},
    {"name": "GitHub API", "base_url": "https://api.github.com", "version": "v3", "category": "social", "description": "Build with the GitHub API", "popularity": 96},
    {"name": "Twilio API", "base_url": "https://api.twilio.com", "version": "2010-04-01", "category": "communication", "description": "Programmable voice, video, messaging", "popularity": 92},
    {"name": "OpenAI API", "base_url": "https://api.openai.com", "version": "v1", "category": "ai", "description": "Access AI models", "popularity": 99},
    {"name": "AWS Lambda", "base_url": "https://lambda.us-east-1.amazonaws.com", "version": "v1", "category": "devtools", "description": "Serverless compute", "popularity": 88},
    {"name": "Slack API", "base_url": "https://slack.com/api", "version": "v1", "category": "communication", "description": "Build with Slack", "popularity": 90},
]

# Sample endpoints per API
ENDPOINTS_TEMPLATE = {
    "payment": [
        {"method": "GET", "path": "/v1/charges", "summary": "List charges"},
        {"method": "POST", "path": "/v1/charges", "summary": "Create charge"},
        {"method": "GET", "path": "/v1/customers", "summary": "List customers"},
        {"method": "POST", "path": "/v1/customers", "summary": "Create customer"},
        {"method": "GET", "path": "/v1/subscriptions", "summary": "List subscriptions"},
        {"method": "POST", "path": "/v1/subscriptions", "summary": "Create subscription"},
    ],
    "ai": [
        {"method": "POST", "path": "/v1/chat/completions", "summary": "Create chat completion"},
        {"method": "POST", "path": "/v1/completions", "summary": "Create completion"},
        {"method": "POST", "path": "/v1/embeddings", "summary": "Create embeddings"},
        {"method": "GET", "path": "/v1/models", "summary": "List models"},
        {"method": "GET", "path": "/v1/models/{model}", "summary": "Retrieve model"},
    ],
}

# Sample technologies
TECHNOLOGIES = [
    ("Node.js", "backend"), ("Python", "backend"), ("Express", "backend"), ("FastAPI", "backend"),
    ("React", "frontend"), ("Vue.js", "frontend"), ("Next.js", "frontend"),
    ("PostgreSQL", "database"), ("MySQL", "database"), ("Redis", "database"), ("MongoDB", "database"),
    ("AWS", "infrastructure"), ("Docker", "infrastructure"), ("Kubernetes", "infrastructure"), ("Nginx", "infrastructure"),
]


def seed_api_data():
    """Seed the database with sample API data."""
    conn = get_connection()
    schema.init_schema(conn)
    cursor = conn.cursor()

    logger.info("Seeding API organizations...")

    # Insert organizations
    org_ids = {}
    for org in ORGANIZATIONS:
        try:
            cursor.execute("""
                INSERT INTO api_organizations (name, slug, website, description, country, social_links_json, employee_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE updated_at = NOW()
            """, (
                org["name"], org["slug"], org["website"], org["description"],
                org["country"], json.dumps(org["social_links"]), "1000-5000"
            ))
            cursor.execute("SELECT id FROM api_organizations WHERE slug = %s", (org["slug"],))
            result = cursor.fetchone()
            org_ids[org["name"]] = result["id"]
        except Exception as e:
            logger.warning(f"Organization {org['name']}: {e}")

    conn.commit()

    logger.info(f"Seeded {len(org_ids)} organizations")

    # Insert APIs
    api_ids = {}
    for api in APIS:
        org_name = next((o["name"] for o in ORGANIZATIONS if api["name"].lower() in o["name"].lower()), None)
        org_id = org_ids.get(org_name)

        try:
            cursor.execute("""
                INSERT INTO api_registries (name, base_url, api_version, category, description, organization_id, popularity_score, is_public, tags_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s)
                ON DUPLICATE KEY UPDATE updated_at = NOW()
            """, (
                api["name"], api["base_url"], api["version"], api["category"],
                api["description"], org_id, api["popularity"],
                json.dumps(["api", api["category"]])
            ))
            cursor.execute("SELECT id FROM api_registries WHERE base_url = %s", (api["base_url"],))
            result = cursor.fetchone()
            api_ids[api["name"]] = result["id"]
        except Exception as e:
            logger.warning(f"API {api['name']}: {e}")

    conn.commit()

    logger.info(f"Seeded {len(api_ids)} APIs")

    # Insert endpoints
    endpoint_count = 0
    for api_category, endpoints in ENDPOINTS_TEMPLATE.items():
        api_id = None
        for name, id in api_ids.items():
            # Match by category
            for api in APIS:
                if api["category"] == api_category and api["name"] in api_ids:
                    api_id = api_ids[api["name"]]
                    break

        if not api_id:
            continue

        for ep in endpoints:
            try:
                full_url = f"{APIS[0]['base_url']}{ep['path']}"  # Use Stripe as template
                cursor.execute("""
                    INSERT INTO api_endpoints (registry_id, method, path, full_url, summary, auth_type, security_score, latency_ms, popularity_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    api_id, ep["method"], ep["path"], full_url, ep["summary"],
                    "bearer", 85, 120, endpoints.index(ep) + 1
                ))
                endpoint_count += 1
            except Exception as e:
                logger.warning(f"Endpoint {ep['path']}: {e}")

    conn.commit()
    logger.info(f"Seeded {endpoint_count} endpoints")

    # Insert technologies
    tech_count = 0
    cursor.execute("SELECT id FROM api_endpoints LIMIT 5")
    endpoint_ids = [row["id"] for row in cursor.fetchall()]

    for tech, category in TECHNOLOGIES:
        for ep_id in endpoint_ids:
            try:
                cursor.execute("""
                    INSERT INTO endpoint_technologies (endpoint_id, technology, category, confidence)
                    VALUES (%s, %s, %s, %s)
                """, (ep_id, tech, category, 0.95))
                tech_count += 1
            except:
                pass

    conn.commit()
    logger.info(f"Seeded {tech_count} technology detections")

    cursor.close()
    conn.close()

    logger.info("Seed complete!")
    return {
        "organizations": len(org_ids),
        "apis": len(api_ids),
        "endpoints": endpoint_count,
        "technologies": tech_count,
    }


if __name__ == "__main__":
    result = seed_api_data()
    print(f"Successfully seeded: {result}")
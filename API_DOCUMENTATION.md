# 📡 Opportunity Intelligence Platform — API Documentation

> Complete REST API reference for v1 and v2 endpoints
> FastAPI | GraphQL | WebSocket | SSE

---

## Table of Contents

1. [Base URL & Authentication](#1-base-url--authentication)
2. [Core Endpoints](#2-core-endpoints)
3. [Startup Endpoints](#3-startup-endpoints)
4. [News & Signals](#4-news--signals)
5. [Opportunities & Scoring](#5-opportunities--scoring)
6. [Knowledge Graph](#6-knowledge-graph)
7. [Search](#7-search)
8. [Real-Time (SSE + WebSocket)](#8-real-time-sse--websocket)
9. [AI Chat](#9-ai-chat)
10. [License & Billing](#10-license--billing)
11. [Monitoring](#11-monitoring)
12. [Error Handling](#12-error-handling)
13. [Rate Limiting](#13-rate-limiting)
14. [Pagination](#14-pagination)

---

## 1. Base URL & Authentication

### Base URLs

| Environment | URL |
|---|---|
| **Local** | `http://localhost:8000` |
| **Docker** | `http://localhost:8000` |
| **Production** | `https://api.your-domain.com` |

### Authentication (Phase 6+)

```http
# Free tier: No auth needed

# Pro/Enterprise: Bearer token
Authorization: Bearer <jwt_token>

# API Key (alternative)
X-API-Key: <your_api_key>
```

### Get a Token

```http
POST /api/auth/token
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

## 2. Core Endpoints

### Health Check

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "ollama": "running",
  "redis": "connected",
  "kafka": "connected",
  "uptime_seconds": 86400,
  "last_pipeline_run": "2024-01-15T08:00:00Z"
}
```

### Statistics

```http
GET /api/stats
```

**Response:**
```json
{
  "startups": {
    "total": 1250,
    "failed": 890,
    "active": 360
  },
  "news_articles": 15420,
  "sectors": 42,
  "countries": 28,
  "opportunity_scores": {
    "total": 450,
    "high_score": 85,
    "avg_score": 52.3
  },
  "knowledge_graph": {
    "entities": 12500,
    "relationships": 45000
  },
  "last_updated": "2024-01-15T08:05:00Z"
}
```

---

## 3. Startup Endpoints

### List Startups

```http
GET /api/startups?page=1&limit=20&sector=Manufacturing&country=US&failure_category=market
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page (max 100) |
| `sector` | string | all | Filter by sector |
| `country` | string | all | Filter by country code |
| `region` | string | all | Filter by region |
| `failure_category` | string | all | Filter by failure category |
| `sort` | string | created_at | Sort field |
| `order` | string | desc | asc or desc |
| `search` | string | — | Full-text search |

**Response:**
```json
{
  "data": [
    {
      "id": 42,
      "name": "Example Manufacturing Co.",
      "sector": "Manufacturing",
      "sub_sector": "Electronics",
      "country": "US",
      "region": "Midwest",
      "founded_year": 2018,
      "failed_year": 2022,
      "failure_category": "market",
      "failure_reason": "Unable to compete with overseas pricing",
      "funding_total": 5000000,
      "employees_peak": 120,
      "description": "Electronics manufacturing startup...",
      "revival_potential": 0.72,
      "created_at": "2024-01-10T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 1250,
    "pages": 63,
    "has_next": true,
    "has_prev": false
  }
}
```

### Get Single Startup

```http
GET /api/startups/{id}
```

**Response:**
```json
{
  "id": 42,
  "name": "Example Manufacturing Co.",
  "sector": "Manufacturing",
  "sub_sector": "Electronics",
  "country": "US",
  "region": "Midwest",
  "city": "Columbus, OH",
  "founded_year": 2018,
  "failed_year": 2022,
  "failure_category": "market",
  "failure_reason": "Unable to compete with overseas pricing",
  "failure_details": "...",
  "funding_total": 5000000,
  "funding_rounds": [
    {"round": "Seed", "amount": 500000, "date": "2018-06"},
    {"round": "Series A", "amount": 4500000, "date": "2019-03"}
  ],
  "employees_peak": 120,
  "founders": ["John Doe", "Jane Smith"],
  "investors": ["VC Fund A", "Angel Investor B"],
  "technologies": ["IoT", "PCB Assembly"],
  "revival_potential": 0.72,
  "risk_score": 0.65,
  "opportunity_score": 78.5,
  "related_startups": [15, 67, 89],
  "news_mentions": 12,
  "created_at": "2024-01-10T00:00:00Z",
  "updated_at": "2024-01-15T08:05:00Z"
}
```

---

## 4. News & Signals

### News Articles

```http
GET /api/news?page=1&limit=20&category=failure&sector=Manufacturing
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page |
| `category` | string | all | failure, funding, m&a, product, layoff |
| `sector` | string | all | Filter by sector |
| `source` | string | all | techcrunch, google_news, reddit, hn |
| `date_from` | date | — | Start date (YYYY-MM-DD) |
| `date_to` | date | — | End date (YYYY-MM-DD) |

**Response:**
```json
{
  "data": [
    {
      "id": 1001,
      "title": "Manufacturing Startup Shuts Down After 3 Years",
      "source": "TechCrunch",
      "category": "failure",
      "sector": "Manufacturing",
      "url": "https://techcrunch.com/...",
      "published_date": "2024-01-12T10:30:00Z",
      "summary": "The Ohio-based startup struggled with...",
      "sentiment": -0.45,
      "entities_mentioned": ["Example Manufacturing Co."],
      "created_at": "2024-01-12T11:00:00Z"
    }
  ],
  "pagination": { "...": "..." }
}
```

### Raw Signals

```http
GET /api/signals?source=github&signal_type=trending&hours=24
```

**Response:**
```json
{
  "data": [
    {
      "id": "sig_001",
      "source": "github",
      "signal_type": "trending",
      "entity": "vercel/ai",
      "value": {
        "stars": 45000,
        "star_velocity": 500,
        "language": "TypeScript"
      },
      "score": 82.5,
      "captured_at": "2024-01-15T07:30:00Z"
    }
  ]
}
```

### Survival Rates

```http
GET /api/survival-rates?sector=Manufacturing&naics_code=33
```

**Response:**
```json
{
  "data": [
    {
      "naics_code": "33",
      "sector": "Manufacturing",
      "year": 2020,
      "births": 12500,
      "deaths": 8900,
      "survival_rate_1yr": 0.82,
      "survival_rate_3yr": 0.58,
      "survival_rate_5yr": 0.42
    }
  ]
}
```

---

## 5. Opportunities & Scoring

### List Opportunities

```http
GET /api/opportunities?min_score=70&sector=Manufacturing&sort=score&order=desc
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `min_score` | float | 0 | Minimum composite score |
| `max_score` | float | 100 | Maximum composite score |
| `sector` | string | all | Filter by sector |
| `country` | string | all | Filter by country |
| `sort` | string | score | score, created_at, updated_at |
| `order` | string | desc | asc or desc |

**Response:**
```json
{
  "data": [
    {
      "entity_name": "Neuromorphic Labs",
      "entity_type": "startup",
      "composite_score": 78.5,
      "attribution": [
        {
          "signal": "funding_round",
          "contribution": 18.2,
          "weight": 25,
          "freshness": 0.85,
          "details": "Series A $5M, Jan 2024"
        },
        {
          "signal": "sec_filing",
          "contribution": 14.1,
          "weight": 20,
          "freshness": 0.94,
          "details": "8-K filed Dec 2023"
        }
      ],
      "anomaly_detected": true,
      "anomaly_z_score": 3.2,
      "trend_direction": "rising",
      "confidence": 0.82,
      "sector": "AI/ML",
      "country": "US",
      "last_updated": "2024-01-15T08:00:00Z"
    }
  ]
}
```

### On-Demand Scoring

```http
POST /api/score
Content-Type: application/json

{
  "entity_name": "Example Startup",
  "entity_type": "startup",
  "sector": "Manufacturing",
  "country": "US"
}
```

**Response:**
```json
{
  "entity_name": "Example Startup",
  "composite_score": 65.2,
  "attribution": [
    {"signal": "funding_round", "contribution": 12.5, "weight": 25, "freshness": 0.50},
    {"signal": "news_mention", "contribution": 8.2, "weight": 10, "freshness": 0.82},
    {"signal": "github_trend", "contribution": 5.1, "weight": 10, "freshness": 0.90}
  ],
  "anomaly_detected": false,
  "trend_direction": "stable",
  "confidence": 0.65,
  "signals_found": 3,
  "signals_missing": ["sec_filing", "job_posting", "patent"],
  "scored_at": "2024-01-15T08:05:00Z"
}
```

### Risk Scores

```http
GET /api/risk-scores?min_risk=0.5&sector=SaaS
```

**Response:**
```json
{
  "data": [
    {
      "startup_id": 42,
      "startup_name": "Example Startup",
      "risk_score": 0.72,
      "risk_level": "high",
      "factors": {
        "funding_depletion": 0.85,
        "market_competition": 0.70,
        "team_stability": 0.45,
        "customer_concentration": 0.60
      },
      "comparable_failures": 5,
      "predicted_timeframe": "12-18 months",
      "scored_at": "2024-01-15T08:00:00Z"
    }
  ]
}
```

### Revival Opportunities

```http
GET /api/revival-opportunities?country=US&sector=Manufacturing
```

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "sector": "Electronics Manufacturing",
      "country": "US",
      "revival_score": 0.82,
      "failed_startups_count": 15,
      "market_gap": "PCB assembly for IoT devices",
      "policy_support": "CHIPS Act eligible",
      "funding_available": true,
      "similar_successes": 3,
      "best_geography": "Austin, TX",
      "estimated_tam": 500000000,
      "key_success_factors": [
        "Domestic supply chain",
        "Specialized workforce available",
        "Government subsidies"
      ]
    }
  ]
}
```

---

## 6. Knowledge Graph

### Entities & Relationships

```http
GET /api/knowledge-graph?entity_type=startup&limit=50
```

**Response:**
```json
{
  "entities": [
    {
      "id": 1,
      "name": "Example Startup",
      "type": "startup",
      "properties": {
        "sector": "Manufacturing",
        "country": "US",
        "founded": 2018,
        "status": "failed"
      }
    }
  ],
  "relationships": [
    {
      "source_id": 1,
      "target_id": 5,
      "type": "funded_by",
      "properties": {
        "amount": 5000000,
        "round": "Series A",
        "date": "2019-03"
      }
    }
  ],
  "stats": {
    "total_entities": 12500,
    "total_relationships": 45000,
    "entity_types": {
      "startup": 1250,
      "investor": 450,
      "person": 2800,
      "technology": 350,
      "industry": 42
    }
  }
}
```

### Entity Connections

```http
GET /api/entities/{name}/connections?depth=2&relationship_type=funded_by
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `depth` | int | 1 | Traversal depth (max 3) |
| `relationship_type` | string | all | Filter by relationship type |
| `limit` | int | 50 | Max connections |

**Response:**
```json
{
  "center": {
    "name": "Example Startup",
    "type": "startup"
  },
  "connections": [
    {
      "path": ["Example Startup", "funded_by", "VC Fund A"],
      "depth": 1,
      "relationship": "funded_by"
    },
    {
      "path": ["Example Startup", "funded_by", "VC Fund A", "funded", "Another Startup"],
      "depth": 2,
      "relationship": "funded_by -> funded"
    }
  ],
  "total_connections": 25,
  "unique_entities": 18
}
```

---

## 7. Search

### Semantic Search

```http
GET /api/search?mode=semantic&q=manufacturing+revival+opportunities+in+texas&limit=10
```

### Full-Text Search

```http
GET /api/search?mode=fulltext&q=startup+failure+electronics&limit=10
```

### Hybrid Search

```http
GET /api/search?mode=hybrid&q=best+sectors+for+manufacturing+revival&limit=10
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `q` | string | required | Search query |
| `mode` | string | hybrid | semantic, fulltext, hybrid |
| `limit` | int | 10 | Results per page |
| `filters` | string | — | JSON filter string |
| `min_score` | float | 0.5 | Minimum relevance score |

**Response:**
```json
{
  "query": "manufacturing revival opportunities in texas",
  "mode": "hybrid",
  "results": [
    {
      "id": 42,
      "type": "startup",
      "title": "Example Manufacturing Co.",
      "content": "Electronics manufacturing startup...",
      "score": 0.92,
      "highlights": ["Manufacturing revival", "Texas"],
      "metadata": {
        "sector": "Manufacturing",
        "country": "US"
      }
    }
  ],
  "total": 15,
  "search_time_ms": 45
}
```

---

## 8. Real-Time (SSE + WebSocket)

### Server-Sent Events (SSE)

```http
GET /api/signals/live
Accept: text/event-stream
```

**Event Stream:**
```
event: signal
data: {"source": "reddit", "entity": "OpenAI", "signal_type": "sentiment", "score": 0.85, "timestamp": "2024-01-15T08:00:00Z"}

event: signal
data: {"source": "sec", "entity": "Tesla", "signal_type": "filing", "filing_type": "8-K", "timestamp": "2024-01-15T08:01:00Z"}

event: alert
data: {"type": "opportunity", "entity": "Neuromorphic Labs", "score": 94, "message": "High opportunity detected", "timestamp": "2024-01-15T08:02:00Z"}

event: ping
data: {"timestamp": "2024-01-15T08:05:00Z"}
```

### WebSocket

```javascript
// Connect
const ws = new WebSocket('ws://localhost:8000/ws');

// Subscribe to signals
ws.send(JSON.stringify({
  action: 'subscribe',
  channels: ['signals', 'alerts', 'scores'],
  filters: {
    min_score: 70,
    sectors: ['Manufacturing', 'AI/ML']
  }
}));

// Receive messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
  // { channel: "signals", type: "funding", entity: "...", score: 85, ... }
};
```

---

## 9. AI Chat

### Natural Language Query

```http
POST /api/chat
Content-Type: application/json

{
  "message": "Which manufacturing sectors have the best revival opportunities in the US?",
  "context": {
    "sector": "Manufacturing",
    "country": "US"
  }
}
```

**Response:**
```json
{
  "response": "Based on the current analysis, the top manufacturing revival opportunities in the US are:\n\n1. **Semiconductor Manufacturing** (Score: 89/100)\n   - CHIPS Act funding available ($52B)\n   - 3 failed startups with revivable IP\n   - 85% policy support score\n\n2. **EV Battery Production** (Score: 85/100)\n   - Inflation Reduction Act subsidies\n   - Strong demand growth (40% YoY)\n   - 5 failed startups, 2 with viable technology\n\n3. **PCB Assembly for IoT** (Score: 78/100)\n   - Reshoring trend strong in Midwest\n   - Lower capital requirements\n   - 4 failed startups with revival potential\n\n...",
  "sources_used": [
    "failed_startups", "opportunity_scores", "bls_survival_rates", "news_articles"
  ],
  "agents_involved": [
    "revival_opportunity", "geographic_strategy", "market_viability"
  ],
  "confidence": 0.82,
  "follow_up_suggestions": [
    "Tell me more about semiconductor manufacturing revival",
    "Compare US vs Mexico for EV battery production",
    "Show me the failed startups with revivable IP"
  ]
}
```

---

## 10. License & Billing

### Validate License

```http
POST /api/license/validate
Content-Type: application/json

{
  "license_key": "OIP-PRO-XXXX-XXXX-XXXX"
}
```

**Response:**
```json
{
  "valid": true,
  "tier": "pro",
  "features": ["alerts", "webhooks", "ml_scoring", "api_full"],
  "expires_at": "2025-01-15T00:00:00Z",
  "seat_count": 5,
  "usage": {
    "api_calls_this_month": 1250,
    "api_call_limit": 10000
  }
}
```

### Generate License (Admin)

```http
POST /api/license/generate
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "tier": "pro",
  "duration_days": 365,
  "seat_count": 5,
  "email": "customer@example.com"
}
```

### Subscription Metrics

```http
GET /api/license/metrics
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total_licenses": 52,
  "by_tier": {
    "free": 500,
    "pro_starter": 15,
    "pro_professional": 25,
    "pro_team": 10,
    "enterprise": 2
  },
  "mrr": 7950,
  "churn_rate": 0.05,
  "active_subscriptions": 52,
  "expired_subscriptions": 8
}
```

---

## 11. Monitoring

### Pipeline Runs

```http
GET /api/pipeline-runs?limit=10
```

**Response:**
```json
{
  "data": [
    {
      "id": 150,
      "pipeline_type": "daily",
      "status": "completed",
      "started_at": "2024-01-15T08:00:00Z",
      "completed_at": "2024-01-15T08:12:34Z",
      "duration_seconds": 754,
      "agents_run": 35,
      "agents_succeeded": 34,
      "agents_failed": 1,
      "failed_agents": ["whale_investor"],
      "records_processed": 4520,
      "new_signals": 230,
      "new_scores": 15
    }
  ]
}
```

### Alerts

```http
GET /api/alerts?status=active&severity=high
```

**Response:**
```json
{
  "data": [
    {
      "id": 500,
      "type": "pipeline_failure",
      "severity": "high",
      "message": "Whale Investor agent failed: Crunchbase API timeout",
      "agent": "whale_investor",
      "status": "active",
      "created_at": "2024-01-15T08:10:00Z"
    },
    {
      "id": 501,
      "type": "data_freshness",
      "severity": "medium",
      "message": "BLS data is 35 days old (expected: 30 days)",
      "source": "bls",
      "status": "active",
      "created_at": "2024-01-14T00:00:00Z"
    }
  ]
}
```

### Prometheus Metrics

```http
GET /metrics
```

```
# HELP oip_pipeline_runs_total Total pipeline runs
# TYPE oip_pipeline_runs_total counter
oip_pipeline_runs_total{status="success"} 145
oip_pipeline_runs_total{status="failure"} 3

# HELP oip_agent_duration_seconds Agent execution duration
# TYPE oip_agent_duration_seconds histogram
oip_agent_duration_seconds_bucket{agent="failure_pattern",le="10"} 50
oip_agent_duration_seconds_bucket{agent="failure_pattern",le="30"} 140

# HELP oip_signals_processed_total Total signals processed
# TYPE oip_signals_processed_total counter
oip_signals_processed_total{source="reddit"} 15200
oip_signals_processed_total{source="github"} 8900

# HELP oip_opportunity_scores_total Opportunity scores calculated
# TYPE oip_opportunity_scores_total counter
oip_opportunity_scores_total 450
```

---

## 12. Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Startup with id 9999 not found",
    "details": null
  }
}
```

### HTTP Status Codes

| Code | Meaning | When |
|---|---|---|
| `200` | OK | Successful request |
| `201` | Created | Resource created (POST) |
| `400` | Bad Request | Invalid parameters |
| `401` | Unauthorized | Missing or invalid auth token |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Error | Server error |
| `503` | Service Unavailable | Database or LLM down |

### Common Errors

```json
// 400 - Bad Request
{
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Parameter 'limit' must be between 1 and 100",
    "details": {"parameter": "limit", "value": "500", "max": 100}
  }
}

// 401 - Unauthorized
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "JWT token has expired",
    "details": {"expired_at": "2024-01-15T07:00:00Z"}
  }
}

// 429 - Rate Limited
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded: 100 requests per minute",
    "details": {
      "limit": 100,
      "window": "60s",
      "remaining": 0,
      "reset_at": "2024-01-15T08:01:00Z"
    }
  }
}
```

---

## 13. Rate Limiting

| Tier | Limit | Window |
|---|---|---|
| **Free** | 60 requests/min | Per IP |
| **Pro** | 300 requests/min | Per API key |
| **Enterprise** | 1,000 requests/min | Per API key |

### Rate Limit Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 245
X-RateLimit-Reset: 1705305600
```

---

## 14. Pagination

### Request

```http
GET /api/startups?page=2&limit=20
```

### Response

```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 20,
    "total": 1250,
    "pages": 63,
    "has_next": true,
    "has_prev": true,
    "next_page": "/api/startups?page=3&limit=20",
    "prev_page": "/api/startups?page=1&limit=20"
  }
}
```

---

## SDK Examples

### Python

```python
import requests

class OIPClient:
    def __init__(self, base_url="http://localhost:8000", api_key=None):
        self.base_url = base_url
        self.session = requests.Session()
        if api_key:
            self.session.headers["Authorization"] = f"Bearer {api_key}"

    def get_startups(self, sector=None, country=None, page=1):
        params = {"page": page, "limit": 20}
        if sector: params["sector"] = sector
        if country: params["country"] = country
        return self.session.get(f"{self.base_url}/api/startups", params=params).json()

    def get_opportunities(self, min_score=70):
        return self.session.get(
            f"{self.base_url}/api/opportunities",
            params={"min_score": min_score, "sort": "score", "order": "desc"}
        ).json()

    def search(self, query, mode="hybrid"):
        return self.session.get(
            f"{self.base_url}/api/search",
            params={"q": query, "mode": mode}
        ).json()

    def chat(self, message):
        return self.session.post(
            f"{self.base_url}/api/chat",
            json={"message": message}
        ).json()

    def score_entity(self, name, sector=None, country=None):
        return self.session.post(
            f"{self.base_url}/api/score",
            json={"entity_name": name, "sector": sector, "country": country}
        ).json()

# Usage
client = OIPClient(api_key="your-key")

# Get startups
startups = client.get_startups(sector="Manufacturing", country="US")

# Get opportunities
opportunities = client.get_opportunities(min_score=75)

# Search
results = client.search("best manufacturing revival opportunities in Texas")

# AI Chat
response = client.chat("Why do hardware startups fail?")
print(response["response"])

# Score an entity
score = client.score_entity("Example Startup", sector="Manufacturing")
print(f"Score: {score['composite_score']}")
```

### JavaScript

```javascript
class OIPClient {
  constructor(baseUrl = 'http://localhost:8000', apiKey = null) {
    this.baseUrl = baseUrl;
    this.headers = apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {};
  }

  async getStartups(params = {}) {
    const query = new URLSearchParams(params).toString();
    const res = await fetch(`${this.baseUrl}/api/startups?${query}`, { headers: this.headers });
    return res.json();
  }

  async search(query, mode = 'hybrid') {
    const res = await fetch(`${this.baseUrl}/api/search?q=${encodeURIComponent(query)}&mode=${mode}`, { headers: this.headers });
    return res.json();
  }

  async chat(message) {
    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method: 'POST',
      headers: { ...this.headers, 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    return res.json();
  }

  // SSE stream
  streamSignals(onSignal) {
    const source = new EventSource(`${this.baseUrl}/api/signals/live`);
    source.onmessage = (event) => onSignal(JSON.parse(event.data));
    return source;
  }
}

// Usage
const client = new OIPClient('http://localhost:8000', 'your-key');
const startups = await client.getStartups({ sector: 'Manufacturing', limit: 10 });
const results = await client.search('manufacturing revival Texas');
const chatResponse = await client.chat('Why do startups fail?');

// Real-time stream
const source = client.streamSignals((signal) => {
  console.log('New signal:', signal);
});
```

### cURL

```bash
# List startups
curl -s "http://localhost:8000/api/startups?sector=Manufacturing&limit=5" | jq

# Search
curl -s "http://localhost:8000/api/search?q=manufacturing+revival&mode=hybrid" | jq

# AI Chat
curl -s -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Why do hardware startups fail?"}' | jq

# Score entity
curl -s -X POST "http://localhost:8000/api/score" \
  -H "Content-Type: application/json" \
  -d '{"entity_name": "Example Startup", "sector": "Manufacturing"}' | jq

# SSE stream
curl -N "http://localhost:8000/api/signals/live"
```

---

*Last updated: June 5, 2026*
*API Version: v1 (v2 planned for Phase 6)*

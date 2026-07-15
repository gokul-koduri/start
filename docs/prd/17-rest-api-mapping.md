# REST API Mapping — Opportunity Intelligence Platform

> Complete mapping of every user action to its corresponding API endpoint, request, and response.

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication APIs](#authentication-apis)
3. [Company APIs](#company-apis)
4. [Search APIs](#search-apis)
5. [Watchlist APIs](#watchlist-apis)
6. [Reports APIs](#reports-apis)
7. [Analysis APIs](#analysis-apis)
8. [User APIs](#user-apis)

---

## API Overview

### Base URL

```
Production: https://api.example.com/v2
Staging:    https://staging-api.example.com/v2
Local:      http://localhost:8000/api/v2
```

### Authentication

All authenticated endpoints require:
```
Authorization: Bearer <access_token>
```

### Rate Limits (by tier)

| Tier | Limit | Window |
|------|-------|--------|
| Free | 60 requests | 1 minute |
| Pro | 300 requests | 1 minute |
| Enterprise | 1000 requests | 1 minute |

---

## Authentication APIs

### Register

| Property | Value |
|----------|-------|
| Endpoint | `POST /auth/register` |
| Auth | None |
| Rate Limit | 3/hour |

**Request:**
```json
{
  "name": "Jane Smith",
  "email": "jane@company.com",
  "password": "SecurePass123!",
  "terms_accepted": true
}
```

**Response (201):**
```json
{
  "data": {
    "user_id": "uuid",
    "email": "jane@company.com",
    "name": "Jane Smith",
    "email_verified": false
  },
  "tokens": {
    "access_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

**Success UI:** Redirect to onboarding

---

### Login

| Property | Value |
|----------|-------|
| Endpoint | `POST /auth/login` |
| Auth | None |

**Request:**
```json
{
  "email": "jane@company.com",
  "password": "SecurePass123!",
  "remember_me": true
}
```

**Response (200):**
```json
{
  "data": {
    "user_id": "uuid",
    "name": "Jane Smith",
    "email": "jane@company.com",
    "email_verified": true,
    "onboarding_complete": true,
    "subscription_tier": "pro"
  },
  "tokens": { ... }
}
```

**Success UI:** Redirect to dashboard

---

### Refresh Token

| Property | Value |
|----------|-------|
| Endpoint | `POST /auth/refresh` |
| Auth | Refresh cookie |

**Success UI:** Auto-retry original request

---

### Logout

| Property | Value |
|----------|-------|
| Endpoint | `POST /auth/logout` |
| Auth | Access token |

**Success UI:** Redirect to landing page

---

## Company APIs

### Get Company

| Property | Value |
|----------|-------|
| Endpoint | `GET /companies/{id}` |
| Auth | Required |

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "name": "NovaTech AI",
    "slug": "nova-tech-ai",
    "logo_url": "https://...",
    "description": "...",
    "sector": { "slug": "ai-ml", "name": "AI & ML" },
    "stage": "series-a",
    "location": { "city": "San Francisco", "country": "US" },
    "opportunity_score": 82,
    "founded_year": 2021,
    "employee_count": 45,
    "is_watched": false,
    "last_funding": { "amount": 12000000, "date": "2024-01-15" }
  }
}
```

**Success UI:** Populate company profile page

---

### Get Company Timeline

| Property | Value |
|----------|-------|
| Endpoint | `GET /companies/{id}/timeline` |
| Auth | Required |
| Rate Limit | 60/min |

**Response (200):**
```json
{
  "data": [
    {
      "id": "event-uuid",
      "date": "2024-01-15",
      "type": "funding",
      "title": "Series A Funding",
      "description": "$12M raised",
      "source_url": "https://..."
    }
  ]
}
```

---

### Get Company Funding

| Property | Value |
|----------|-------|
| Endpoint | `GET /companies/{id}/funding` |
| Auth | Required |

**Response (200):**
```json
{
  "data": {
    "total_raised": 14500000,
    "rounds": [
      {
        "round": "series-a",
        "amount": 12000000,
        "date": "2024-01-15",
        "lead_investors": ["Sequoia", "a16z"]
      }
    ]
  }
}
```

---

## Search APIs

### Search Companies

| Property | Value |
|----------|-------|
| Endpoint | `GET /search/companies` |
| Auth | Required |

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| q | string | No | Search query |
| sector | string | No | Sector slug |
| country | string | No | Country code |
| stage | string[] | No | Funding stages |
| score_min | int | No | Min score |
| score_max | int | No | Max score |
| sort | string | No | score, name, created |
| order | string | No | asc, desc |
| page | int | No | Default 1 |
| limit | int | No | Default 20, max 100 |

**Response (200):**
```json
{
  "data": {
    "companies": [ /* array of company objects */ ],
    "facets": {
      "sectors": [{ "slug": "ai-ml", "name": "AI/ML", "count": 15420 }],
      "stages": [{ "value": "seed", "count": 8230 }]
    }
  },
  "meta": {
    "total": 1234,
    "page": 1,
    "per_page": 20,
    "total_pages": 62,
    "query_time_ms": 234
  }
}
```

**Success UI:** Display result cards

---

### Autocomplete

| Property | Value |
|----------|-------|
| Endpoint | `GET /search/autocomplete` |
| Auth | Required |
| Rate Limit | 120/min |

**Query:** `GET /search/autocomplete?q=nova&limit=5`

**Response (200):**
```json
{
  "data": {
    "companies": [{ "id": "...", "name": "NovaTech AI", "sector": "AI/ML" }],
    "sectors": [{ "slug": "ai-ml", "name": "AI & ML", "count": 15420 }],
    "investors": [],
    "locations": []
  }
}
```

---

### Save Search

| Property | Value |
|----------|-------|
| Endpoint | `POST /search/saved` |
| Auth | Required |

**Request:**
```json
{
  "name": "AI Startups SF",
  "query": "AI startups",
  "filters": { "sector": "ai-ml", "country": "US" },
  "alert_enabled": true,
  "alert_frequency": "daily"
}
```

---

## Watchlist APIs

### List Watchlists

| Property | Value |
|----------|-------|
| Endpoint | `GET /watchlists` |
| Auth | Required |

**Response (200):**
```json
{
  "data": [
    {
      "id": "uuid",
      "name": "My Portfolio",
      "company_count": 12,
      "alert_enabled": true,
      "created_at": "ISO8601"
    }
  ]
}
```

---

### Create Watchlist

| Property | Value |
|----------|-------|
| Endpoint | `POST /watchlists` |
| Auth | Required |

**Request:**
```json
{
  "name": "Investment Targets",
  "description": "Q2 investment targets"
}
```

---

### Get Watchlist

| Property | Value |
|----------|-------|
| Endpoint | `GET /watchlists/{id}` |
| Auth | Required |

**Response (200):**
```json
{
  "data": {
    "id": "uuid",
    "name": "My Portfolio",
    "description": null,
    "company_count": 12,
    "companies": [
      {
        "company": { "id": "...", "name": "NovaTech AI" },
        "added_at": "ISO8601",
        "latest_signal": { "type": "funding", "title": "Series A" }
      }
    ],
    "alert_settings": {
      "funding": { "enabled": true },
      "news": { "enabled": true }
    }
  }
}
```

---

### Add Company to Watchlist

| Property | Value |
|----------|-------|
| Endpoint | `POST /watchlists/{id}/companies` |
| Auth | Required |

**Request:**
```json
{
  "company_id": "company-uuid"
}
```

**Success UI:** Toast "Added to Watchlist", update count

---

### Remove Company from Watchlist

| Property | Value |
|----------|-------|
| Endpoint | `DELETE /watchlists/{id}/companies/{companyId}` |
| Auth | Required |

**Success UI:** Toast "Removed from Watchlist", update list

---

### Update Watchlist Alerts

| Property | Value |
|----------|-------|
| Endpoint | `PUT /watchlists/{id}/alerts` |
| Auth | Required |

**Request:**
```json
{
  "funding": { "enabled": true, "sensitivity": 3 },
  "news": { "enabled": true, "sensitivity": 3 },
  "score_change": { "enabled": true, "threshold": 10 },
  "frequency": "daily"
}
```

---

## Reports APIs

### List Reports

| Property | Value |
|----------|-------|
| Endpoint | `GET /reports` |
| Auth | Required |

---

### Create Report

| Property | Value |
|----------|-------|
| Endpoint | `POST /reports` |
| Auth | Required |

**Request:**
```json
{
  "type": "company-analysis",
  "company_id": "company-uuid",
  "depth": "standard",
  "include_sections": ["summary", "scores", "recommendations"]
}
```

**Response (202):**
```json
{
  "data": {
    "id": "report-uuid",
    "job_id": "job-uuid",
    "status": "initiated"
  }
}
```

**Success UI:** Show job progress

---

### Get Report

| Property | Value |
|----------|-------|
| Endpoint | `GET /reports/{id}` |
| Auth | Required |

---

### Export Report

| Property | Value |
|----------|-------|
| Endpoint | `GET /reports/{id}/export` |
| Auth | Required |

**Query:** `?format=pdf&include_charts=true`

**Response:** File download

---

## Analysis APIs

### Request Analysis

| Property | Value |
|----------|-------|
| Endpoint | `POST /companies/{id}/analyses` |
| Auth | Required |

**Request:**
```json
{
  "analysis_type": "standard"
}
```

**Response (202):**
```json
{
  "data": {
    "job_id": "job-uuid",
    "status": "initiated"
  }
}
```

---

### Get Analysis Status

| Property | Value |
|----------|-------|
| Endpoint | `GET /companies/{id}/analyses/{jobId}` |
| Auth | Required |

**Response (200):**
```json
{
  "data": {
    "job_id": "job-uuid",
    "status": "streaming",
    "progress": 0.65,
    "current_step": "generating_summary"
  }
}
```

---

### Get Completion

| Property | Value |
|----------|-------|
| Endpoint | `GET /companies/{id}/analyses/{jobId}` |
| Status | completed |

**Response (200):**
```json
{
  "data": {
    "status": "completed",
    "result": {
      "summary": "...",
      "overall_score": 82,
      "scores": {
        "market": { "value": 85 },
        "team": { "value": 78 }
      },
      "key_findings": ["..."],
      "risk_factors": ["..."],
      "recommendations": ["..."]
    }
  }
}
```

---

### SSE Stream

| Property | Value |
|----------|-------|
| Endpoint | `GET /companies/{id}/analyses/{jobId}/stream` |
| Auth | Required |
| Type | Server-Sent Events |

**Events:**
```
event: status
data: {"state": "running", "progress": 0.45}

event: token
data: {"delta": "company operates in"}

event: complete
data: {"analysis_id": "uuid"}
```

---

## User APIs

### Get Current User

| Property | Value |
|----------|-------|
| Endpoint | `GET /users/me` |
| Auth | Required |

---

### Update User

| Property | Value |
|----------|-------|
| Endpoint | `PUT /users/me` |
| Auth | Required |

**Request:**
```json
{
  "name": "Jane Smith",
  "avatar_url": "https://..."
}
```

---

### Update Preferences

| Property | Value |
|----------|-------|
| Endpoint | `PUT /users/me/preferences` |
| Auth | Required |

**Request:**
```json
{
  "onboarding_complete": true,
  "interests": {
    "sectors": ["ai-ml", "saas"],
    "stages": ["seed", "series-a"]
  },
  "notifications": {
    "method": "email",
    "frequency": "daily"
  }
}
```

---

### Delete Account

| Property | Value |
|----------|-------|
| Endpoint | `DELETE /users/me` |
| Auth | Required |

**Request:**
```json
{
  "confirmation": "DELETE",
  "reason": "No longer need the service"
}
```

---

## Error Codes Reference

| Code | HTTP | Description |
|------|------|-------------|
| `AUTH_INVALID_CREDENTIALS` | 401 | Wrong email/password |
| `AUTH_TOKEN_EXPIRED` | 401 | Refresh token expired |
| `RESOURCE_NOT_FOUND` | 404 | Company/Report not found |
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `PERMISSION_DENIED` | 403 | No access to resource |
| `JOB_FAILED` | 500 | Analysis/report failed |

---

## Cross-References

| Document | Topic |
|----------|-------|
| [16-backend-flows.md](./16-backend-flows.md) | System flow |
| [04-authentication.md](./04-authentication.md) | Auth details |
| [07-search.md](./07-search.md) | Search UI |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial API mapping |

---

*Part of the Opportunity Intelligence Platform PRD*
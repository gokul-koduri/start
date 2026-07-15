# Opportunity Intelligence Platform - REST API Specification

> Version 1.0 | Base URL: `/api/v1`

---

## Overview

The Opportunity Intelligence Platform provides a RESTful API for discovering startup opportunities, analyzing investment potential, and monitoring market trends.

**Base URL:**
```
https://api.example.com/api/v1
```

**Content-Type:**
All requests and responses use `application/json` unless specified.

---

## Authentication

### Bearer Token (JWT)
```
Authorization: Bearer <jwt_token>
```

### API Key (Header)
```
X-API-Key: <api_key>
```

---

## Standard Response Format

### Success
```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully",
  "timestamp": "2026-07-02T10:30:00Z",
  "request_id": "uuid-v4"
}
```

### Error
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {"field": "email", "message": "Invalid email format"}
    ]
  },
  "timestamp": "2026-07-02T10:30:00Z",
  "request_id": "uuid-v4"
}
```

### Pagination
```json
{
  "success": true,
  "data": [],
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total": 150,
    "has_more": true
  }
}
```

---

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limited |
| 500 | Internal Server Error |

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid input parameters |
| `AUTHENTICATION_REQUIRED` | 401 | Missing or invalid token |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource does not exist |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Resource Groups

### 1. Authentication (`/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login and get token |
| POST | `/auth/logout` | Invalidate token |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/forgot-password` | Request password reset |
| POST | `/auth/reset-password` | Reset password with token |
| GET | `/auth/verify-email` | Verify email address |

#### POST /auth/register

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response (201):**
```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  },
  "message": "Registration successful"
}
```

#### POST /auth/login

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "expires_in": 3600,
    "token_type": "Bearer"
  }
}
```

---

### 2. Users (`/users`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users/me` | Get current user profile |
| PATCH | `/users/me` | Update current user |
| DELETE | `/users/me` | Delete account |
| GET | `/users/me/preferences` | Get user preferences |
| PUT | `/users/me/preferences` | Update preferences |
| GET | `/users/me/api-keys` | List API keys |
| POST | `/users/me/api-keys` | Create API key |
| DELETE | `/users/me/api-keys/{key_id}` | Revoke API key |

#### GET /users/me

**Response (200):**
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "tier": "pro",
    "created_at": "2026-01-15T10:00:00Z",
    "last_login": "2026-07-02T09:00:00Z"
  }
}
```

#### POST /users/me/api-keys

**Request:**
```json
{
  "name": "Production API Key",
  "expires_in_days": 365
}
```

**Response (201):**
```json
{
  "success": true,
  "data": {
    "id": "key_uuid",
    "name": "Production API Key",
    "key": "sk_live_xxxxx...",
    "expires_at": "2027-07-02T00:00:00Z"
  },
  "message": "Store this key securely. It will not be shown again."
}
```

---

### 3. Organizations (`/organizations`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/organizations` | Create organization |
| GET | `/organizations/{org_id}` | Get organization |
| PATCH | `/organizations/{org_id}` | Update organization |
| POST | `/organizations/{org_id}/members` | Invite member |
| GET | `/organizations/{org_id}/members` | List members |
| DELETE | `/organizations/{org_id}/members/{user_id}` | Remove member |
| PUT | `/organizations/{org_id}/members/{user_id}/role` | Update role |

#### POST /organizations

**Request:**
```json
{
  "name": "Acme VC",
  "description": "Venture Capital Firm",
  "website": "https://acme.vc"
}
```

#### Role Types
- `owner` - Full control
- `admin` - Manage members, settings
- `analyst` - Read access, create reports
- `viewer` - Read-only access

---

### 4. Startups (`/startups`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/startups` | List startups (with filters) |
| POST | `/startups` | Create startup entry |
| GET | `/startups/{id}` | Get startup details |
| PATCH | `/startups/{id}` | Update startup |
| DELETE | `/startups/{id}` | Delete startup |
| GET | `/startups/{id}/funding` | Funding history |
| GET | `/startups/{id}/metrics` | Growth metrics |
| GET | `/startups/{id}/news` | News articles |
| GET | `/startups/{id}/score` | AI opportunity score |
| GET | `/startups/search` | Search startups |

#### GET /startups

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `offset` | int | Pagination offset |
| `limit` | int | Items per page (max 100) |
| `sector` | string | Filter by sector |
| `country` | string | Filter by country |
| `min_funding` | int | Minimum funding USD |
| `max_funding` | int | Maximum funding USD |
| `year_founded` | int | Year founded |
| `status` | string | `active`, `acquired`, `failed` |
| `sort` | string | `name`, `funding`, `score` |
| `order` | string | `asc`, `desc` |

**Response (200):**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "TechCorp",
      "sector": "AI/ML",
      "country": "USA",
      "funding_raised_usd": 5000000,
      "status": "active",
      "opportunity_score": 85.5,
      "founded_year": 2022
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total": 150,
    "has_more": true
  }
}
```

#### GET /startups/{id}/score

**Response (200):**
```json
{
  "success": true,
  "data": {
    "startup_id": 1,
    "composite_score": 85.5,
    "components": {
      "founder_quality": 92.0,
      "market_potential": 88.0,
      "product_maturity": 75.0,
      "traction": 82.0,
      "competitive_position": 85.0
    },
    "trend": "improving",
    "score_change_30d": 5.2,
    "risk_factors": ["limited market validation"],
    "strengths": ["strong team", "proprietary tech"],
    "analyzed_at": "2026-07-02T10:00:00Z"
  }
}
```

---

### 5. Investors (`/investors`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/investors/{id}` | Get investor profile |
| GET | `/investors/{id}/portfolio` | Portfolio companies |
| GET | `/investors/{id}/history` | Investment history |
| GET | `/investors/{id}/active` | Active investments |

#### GET /investors/{id}

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Sequoia Capital",
    "type": "VC Firm",
    "headquarters": "USA",
    "total_aum_usd": 80000000000,
    "portfolio_count": 300,
    "focus_sectors": ["AI", "SaaS", "Fintech"],
    "website": "https://sequoiacap.com"
  }
}
```

---

### 6. Funding Rounds (`/funding-rounds`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/funding-rounds` | Create funding round |
| GET | `/funding-rounds` | List funding rounds |
| GET | `/funding-rounds/{id}` | Get funding round |
| GET | `/startups/{id}/funding-timeline` | Company funding timeline |

#### POST /funding-rounds

```json
{
  "startup_id": 1,
  "round_type": "Series A",
  "amount_usd": 15000000,
  "valuation_usd": 75000000,
  "date": "2026-06-15",
  "investors": [1, 5, 12],
  "lead_investor_id": 1
}
```

---

### 7. AI Analysis (`/analysis`)

Long-running AI requests are asynchronous. Returns a Job ID.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analysis/startup` | Analyze startup |
| POST | `/analysis/industry` | Analyze industry |
| POST | `/analysis/compare` | Compare companies |
| POST | `/analysis/summary` | Generate executive summary |
| POST | `/analysis/investment-report` | Generate investment report |
| POST | `/analysis/risk-assessment` | Risk assessment |
| POST | `/analysis/market-opportunity` | Market opportunity analysis |
| GET | `/analysis/{job_id}` | Get analysis status/result |

#### POST /analysis/startup

**Request:**
```json
{
  "startup_id": 1,
  "analysis_types": ["risk", "opportunity", "competitive"],
  "depth": "detailed"
}
```

**Response (202):**
```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "pending",
    "estimated_completion": "2026-07-02T10:35:00Z"
  }
}
```

#### GET /analysis/{job_id}

**Response (200):**
```json
{
  "success": true,
  "data": {
    "job_id": "job_abc123",
    "status": "completed",
    "result": {
      "summary": "Strong investment opportunity...",
      "risk_score": 25,
      "opportunity_score": 88,
      "recommendation": "Consider investment"
    },
    "completed_at": "2026-07-02T10:32:00Z"
  }
}
```

---

### 8. Jobs (`/jobs`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/jobs/{job_id}` | Job status |
| GET | `/jobs/{job_id}/progress` | Job progress |
| GET | `/jobs/{job_id}/result` | Job result |
| POST | `/jobs/{job_id}/cancel` | Cancel job |
| POST | `/jobs/{job_id}/retry` | Retry failed job |

#### Job Status Values
- `pending` - Job queued
- `running` - Job in progress
- `completed` - Job finished successfully
- `failed` - Job failed
- `cancelled` - Job was cancelled

---

### 9. Search (`/search`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/search` | Full-text + semantic search |
| GET | `/search/autocomplete` | Autocomplete suggestions |

#### GET /search

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (required) |
| `type` | string | `all`, `startups`, `investors`, `news` |
| `limit` | int | Max results |
| `semantic` | bool | Enable semantic search |

**Example:**
```
GET /search?q=AI+healthcare+startups&type=startups&semantic=true
```

---

### 10. Watchlists (`/watchlists`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/watchlists` | List user's watchlists |
| POST | `/watchlists` | Create watchlist |
| GET | `/watchlists/{id}` | Get watchlist |
| PATCH | `/watchlists/{id}` | Update watchlist |
| DELETE | `/watchlists/{id}` | Delete watchlist |
| POST | `/watchlists/{id}/items` | Add startup to watchlist |
| DELETE | `/watchlists/{id}/items/{item_id}` | Remove startup |
| POST | `/watchlists/{id}/subscribe` | Subscribe to alerts |

#### POST /watchlists

```json
{
  "name": "Healthcare AI Opportunities",
  "description": "AI startups in healthcare sector",
  "filters": {
    "sectors": ["Healthcare", "AI/ML"],
    "min_score": 70,
    "countries": ["USA", "UK"]
  },
  "alert_preferences": {
    "score_changes": true,
    "new_funding": true,
    "news_mentions": true
  }
}
```

---

### 11. Alerts (`/alerts`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/alerts` | List alerts |
| GET | `/alerts/{id}` | Get alert details |
| PUT | `/alerts/{id}/read` | Mark as read |
| DELETE | `/alerts/{id}` | Delete alert |
| GET | `/alerts/digest` | Daily digest |
| WebSocket | `/ws/live` | Real-time alerts |

#### Alert Types
- `opportunity_score_change` - Score increased/decreased
- `new_funding` - Startup received funding
- `news_mention` - News article about watchlist item
- `price_milestone` - Valuation threshold reached
- `portfolio_update` - Investor activity

---

### 12. Reports (`/reports`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reports/generate` | Generate report |
| GET | `/reports/{id}` | Get report |
| GET | `/reports/{id}/pdf` | Download PDF |
| GET | `/reports/{id}/csv` | Download CSV |
| GET | `/reports/{id}/json` | Download JSON |
| POST | `/reports/{id}/share` | Share report |
| DELETE | `/reports/{id}` | Delete report |

#### POST /reports/generate

```json
{
  "report_type": "opportunity_analysis",
  "startup_ids": [1, 5, 12],
  "compare_to_market": true,
  "include_recommendations": true,
  "format": "detailed"
}
```

---

### 13. Feedback (`/feedback`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/feedback` | Submit feedback |
| POST | `/feedback/ai-error` | Report incorrect AI result |
| POST | `/feedback/rate` | Rate AI response |
| GET | `/feedback` | List submitted feedback |

#### POST /feedback/ai-error

```json
{
  "analysis_id": "job_abc123",
  "error_type": "incorrect_funding_data",
  "correct_value": "Series B instead of Series A",
  "comments": "The funding round was incorrect..."
}
```

---

### 14. Health (`/health`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Overall health check |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe |
| GET | `/health/metrics` | Prometheus metrics |
| GET | `/health/dependencies` | Dependency status |

#### GET /health

```json
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected",
  "version": "1.0.0",
  "uptime_seconds": 86400
}
```

#### GET /health/ready

Returns 200 if all dependencies are ready, 503 otherwise.

---

### 15. Admin (`/admin`)

Requires `admin` role.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/stats` | Dashboard statistics |
| GET | `/admin/agents` | AI agent status |
| GET | `/admin/collectors` | Collector status |
| GET | `/admin/queue` | Job queue status |
| GET | `/admin/logs` | System logs |
| POST | `/admin/maintenance` | Toggle maintenance mode |

#### GET /admin/stats

```json
{
  "total_users": 1250,
  "total_startups": 15000,
  "active_watchlists": 3400,
  "reports_generated_today": 245,
  "api_requests_today": 45000,
  "error_rate": 0.02
}
```

---

## Rate Limiting

| Tier | Requests/hour |
|------|---------------|
| Free | 60 |
| Pro | 1000 |
| Enterprise | 10000 |

Rate limit headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 55
X-RateLimit-Reset: 1656758400
```

---

## Webhooks

Configure webhooks for event notifications:

**Event Types:**
- `startup.score_changed`
- `startup.funding_received`
- `alert.triggered`
- `report.completed`

**Webhook Payload:**
```json
{
  "event": "startup.score_changed",
  "timestamp": "2026-07-02T10:30:00Z",
  "data": {
    "startup_id": 1,
    "old_score": 72.5,
    "new_score": 85.5
  }
}
```

---

## API Versioning

Current version: `v1`

Future deprecations will be announced with 6 months notice at:
```
GET /api/v1/deprecations
```

---

## SDKs

- **Python**: `pip install opportunity-intelligence`
- **JavaScript/TypeScript**: `npm install @opportunity-intelligence/sdk`

---

*Last updated: July 2, 2026*
*Version: 1.0.0*
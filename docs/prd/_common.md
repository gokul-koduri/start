# Common Definitions — Opportunity Intelligence Platform

> Shared definitions, API formats, error codes, and design tokens used across all PRD sections.

---

## Table of Contents

1. [API Response Format](#api-response-format)
2. [Error Codes](#error-codes)
3. [Design Tokens](#design-tokens)
4. [Common Terminology](#common-terminology)
5. [Conventions](#conventions)

---

## API Response Format

### Success Response

```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601",
    "page": 1,
    "per_page": 20,
    "total": 100
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": { ... },
    "request_id": "uuid"
  }
}
```

### Async Job Response

```json
{
  "data": {
    "job_id": "uuid",
    "status": "queued|running|completed|failed",
    "progress": 0.45,
    "result": null,
    "error": null
  }
}
```

---

## Error Codes

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (no/invalid auth) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 409 | Conflict (duplicate resource) |
| 422 | Unprocessable Entity |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

### Application Error Codes

| Code | Description |
|------|-------------|
| `AUTH_INVALID_CREDENTIALS` | Email or password incorrect |
| `AUTH_TOKEN_EXPIRED` | Access token has expired |
| `AUTH_TOKEN_INVALID` | Access token is malformed |
| `AUTH_MFA_REQUIRED` | Multi-factor authentication required |
| `AUTH_EMAIL_NOT_VERIFIED` | Email verification pending |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist |
| `RESOURCE_CONFLICT` | Resource already exists |
| `VALIDATION_ERROR` | Request validation failed |
| `PERMISSION_DENIED` | Insufficient permissions |
| `JOB_FAILED` | Async job processing failed |
| `SERVICE_UNAVAILABLE` | Dependent service is down |

---

## Design Tokens

### Spacing Scale

```css
--space-1:  4px;
--space-2:  8px;
--space-3:  12px;
--space-4:  16px;
--space-5:  20px;
--space-6:  24px;
--space-8:  32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
--space-20: 80px;
--space-24: 96px;
```

### Border Radius

```css
--radius-sm:   4px;
--radius-md:   8px;
--radius-lg:   12px;
--radius-xl:   16px;
--radius-2xl:  24px;
--radius-full: 9999px;
```

### Shadows

```css
--shadow-sm:  0 1px 2px rgba(0,0,0,0.05);
--shadow-md:  0 4px 6px -1px rgba(0,0,0,0.1);
--shadow-lg:  0 10px 15px -3px rgba(0,0,0,0.1);
--shadow-xl:  0 20px 25px -5px rgba(0,0,0,0.1);
--shadow-2xl: 0 25px 50px -12px rgba(0,0,0,0.25);
```

### Colors (Dark Mode)

```css
--color-bg-primary:   #0a0a0f;
--color-bg-secondary: #111118;
--color-bg-tertiary:  #1a1a24;
--color-bg-elevated:  #222230;

--color-text-primary:   #ffffff;
--color-text-secondary: #a1a1aa;
--color-text-muted:     #71717a;

--color-border:        #27272a;
--color-border-strong: #3f3f46;

--color-accent:        #3b82f6;
--color-accent-hover:  #2563eb;
--color-accent-muted:  rgba(59,130,246,0.15);

--color-success:       #22c55e;
--color-warning:       #f59e0b;
--color-error:         #ef4444;
--color-info:          #06b6d4;
```

### Typography

```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;

--text-xs:   0.75rem;   /* 12px */
--text-sm:   0.875rem;  /* 14px */
--text-base: 1rem;      /* 16px */
--text-lg:   1.125rem;  /* 18px */
--text-xl:   1.25rem;   /* 20px */
--text-2xl:  1.5rem;    /* 24px */
--text-3xl:  1.875rem;  /* 30px */
--text-4xl:  2.25rem;   /* 36px */
--text-5xl:  3rem;      /* 48px */

--font-normal:    400;
--font-medium:    500;
--font-semibold:  600;
--font-bold:      700;
```

### Animation

```css
--duration-fast:   100ms;
--duration-normal: 200ms;
--duration-slow:   300ms;
--duration-slower: 500ms;

--ease-default:    cubic-bezier(0.4, 0, 0.2, 1);
--ease-in:         cubic-bezier(0.4, 0, 1, 1);
--ease-out:        cubic-bezier(0, 0, 0.2, 1);
--ease-bounce:     cubic-bezier(0.68, -0.55, 0.265, 1.55);
```

---

## Common Terminology

| Term | Definition |
|------|------------|
| **Opportunity Score** | AI-calculated score (0-100) indicating startup potential |
| **Signal** | Market event related to a startup (funding, news, etc.) |
| **Watchlist** | User-curated list of companies they want to track |
| **Alert** | Notification triggered by specific events/thresholds |
| **Job** | Async processing task (AI analysis, report generation) |
| **Tenant** | Organization/account in multi-tenant system |

### Entity States

| Entity | States |
|--------|--------|
| Startup | `active`, `acquired`, `closed`, `ipo`, `bankruptcy` |
| Job | `initiated`, `queued`, `running`, `streaming`, `completed`, `failed` |
| User | `active`, `suspended`, `deleted` |
| Alert | `active`, `paused`, `fired`, `acknowledged` |
| Subscription | `trial`, `active`, `past_due`, `cancelled`, `expired` |

---

## Conventions

### Routes
- All routes use kebab-case: `/company-profile`, `/watchlist-alerts`
- API routes prefixed with `/api/v2/`
- WebSocket routes use `/ws/`

### Naming
- Components: PascalCase (`Button`, `SearchBar`)
- Functions: camelCase (`fetchCompanies`, `updateAlert`)
- Constants: SCREAMING_SNAKE_CASE (`MAX_RESULTS`, `API_TIMEOUT`)
- CSS classes: kebab-case (`btn-primary`, `card-content`)

### File Format
- Markdown files for documentation
- Use `###` for sub-sections, `####` for details
- Include Mermaid diagrams for flows
- Code examples use triple backticks with language

### Cross-References
- Link to other PRD sections: `[Section Name](./XX-section-name.md)`
- Link to API: Use backticks for endpoints like `/api/v2/startups`
- Link to components: Use code format `Button`

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial common definitions |

---

*Part of the Opportunity Intelligence Platform PRD*
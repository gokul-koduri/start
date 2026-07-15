# Backend Flows — Opportunity Intelligence Platform

> System integration diagrams showing request flows from frontend through backend services to database and response.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Flows](#core-flows)
3. [Search Flow](#search-flow)
4. [AI Analysis Flow](#ai-analysis-flow)
5. [Real-Time Updates](#real-time-updates)
6. [Data Model](#data-model)

---

## Architecture Overview

### System Components

```mermaid
flowchart TD
    subgraph Frontend
        N[Next.js App]
        W[WebSocket Client]
        S[SSE Client]
    end

    subgraph Gateway
        API[API Gateway]
        AUTH[JWT Auth]
        RATE[Rate Limiter]
    end

    subgraph Backend
        F[FastAPI Backend]
        O[Agent Orchestrator]
        Q[Job Queue]
    end

    subgraph Services
        C[Companies Service]
        SVC[Signals Service]
        RPT[Reports Service]
    end

    subgraph AI
        OLL[Ollama]
        AGENTS[40+ Agents]
    end

    subgraph Storage
        DB[(MySQL)]
        REDIS[(Redis Cache)]
        ES[Elasticsearch]
        QD[Qdrant]
        KAFKA[Kafka]
    end

    N --> API
    W --> API
    S --> API
    API --> AUTH
    AUTH --> RATE
    RATE --> F
    F --> O
    O --> Q
    Q --> OLL
    OLL --> AGENTS
    F --> C
    F --> SVC
    F --> RPT
    C --> DB
    C --> REDIS
    F --> ES
    F --> QD
    O --> KAFKA
    KAFKA --> SVC
```

---

## Core Flows

### Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as Auth API
    participant D as Database
    participant E as Email Service

    U->>F: Enter credentials
    F->>A: POST /auth/login
    A->>D: Validate credentials
    D->>A: User verified
    A->>A: Generate JWT tokens
    A->>F: Set refresh cookie + access token
    F->>U: Redirect to dashboard

    Note over A: Access token: 15min<br/>Refresh token: 7 days
```

### Token Refresh Flow

```mermaid
sequenceDiagram
    participant F as Frontend
    participant A as Auth API

    Note over F: Access token about to expire
    F->>A: POST /auth/refresh
    A->>A: Validate refresh token
    A->>A: Rotate refresh token
    A->>F: New access token<br/>New refresh cookie
    F->>F: Retry original request
```

---

## Search Flow

### Company Search

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant ES as Elasticsearch
    participant QD as Qdrant
    participant R as Redis
    participant D as Database

    U->>F: Enter search query
    F->>A: GET /search?q=AI+san+francisco

    A->>R: Check query cache
    R->>A: Cache hit?

    alt Cache Hit
        R->>A: Return cached results
        A->>F: Return results
    else Cache Miss
        A->>ES: Execute hybrid query
        ES->>A: Keyword matches

        A->>QD: Execute vector search
        QD->>A: Semantic matches

        A->>A: Merge & rerank results
        A->>D: Enrich with DB fields
        A->>R: Cache results (5 min)
        A->>F: Return results
    end

    F->>F: Render results
    F->>U: Display company cards
```

### Search Architecture Details

```
Frontend              API                     Services                    Storage
    │                  │                          │                          │
    │  GET /search?q=  │                          │                          │
    │─────────────────>│                          │                          │
    │                  │                          │                          │
    │                  │  Check Redis cache        │                          │
    │                  │────────────────────────>│                          │
    │                  │<─────────────────────────│                          │
    │                  │                          │                          │
    │                  │                  [Cache miss]                       │
    │                  │                          │                          │
    │                  │  Elasticsearch query     │                          │
    │                  │─────────────────────────>│                          │
    │                  │<─────────────────────────│                          │
    │                  │                          │                          │
    │                  │  Qdrant vector search    │                          │
    │                  │─────────────────────────>│                          │
    │                  │<─────────────────────────│                          │
    │                  │                          │                          │
    │                  │  Merge scores            │                          │
    │                  │────────────────          │                          │
    │                  │  Fetch from DB           │                          │
    │                  │────────────────>│<────────│                          │
    │                  │  Fetch from DB    │      │                          │
    │                  │────────────────>│        │                          │
    │                  │                          │                          │
    │  Response        │                          │                          │
    │<─────────────────│                          │                          │
```

---

## AI Analysis Flow

### Analysis Request Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant Q as Queue
    participant W as Worker
    participant O as Ollama
    participant D as Database
    participant SSE as SSE Server

    U->>F: Request analysis
    F->>A: POST /companies/[id]/analyses

    A->>D: Create job record
    D->>A: Job created
    A->>Q: Publish job

    A->>F: Return job ID
    F->>F: Open SSE connection

    Q->>W: Assign job to worker
    W->>O: Process with agents

    O-->>SSE: Stream tokens
    SSE-->>F: SSE events
    F->>U: Update UI live

    O->>W: Analysis complete
    W->>D: Store results
    D->>W: Results saved
    W->>Q: Mark complete

    SSE-->>F: Complete event
    F->>U: Show results
```

### Report Generation Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant Q as Queue
    participant W as Worker
    participant O as Ollama
    participant S3[S3 Storage]

    U->>F: Configure + Generate
    F->>A: POST /reports

    A->>Q: Create reporting job
    A->>F: Return job ID

    loop Progress
        F->>A: GET /reports/[id]/stream
        A-->>F: SSE events
    end

    Q->>W: Assign report job
    W->>O: Generate content
    O->>W: Content ready

    W->>S3: Upload report file
    W->>D: Update job status

    F->>A: GET /reports/[id]
    A->>D: Get report metadata
    D->>A: Report details
    A->>F: Display report
```

---

## Real-Time Updates

### Signal Broadcasting

```mermaid
sequenceDiagram
    participant Source as Data Source
    participant K as Kafka
    participant S as Signal Processor
    participant R as Redis Pub/Sub
    participant WS as WS Server
    participant F as Frontend

    Source->>K: Publish signal event
    K->>S: Consume event
    S->>S: Process & enrich

    S->>R: Publish signal
    R->>WS: Broadcast to subscribers
    WS->>F: WebSocket message

    alt Email digest (async)
        S->>E: Email Service
        E->>U: Send digest
    end
```

### WebSocket Connection

```mermaid
sequenceDiagram
    participant C as Client
    participant WS as WebSocket Server
    participant R as Redis

    C->>WS: Connect with token
    WS->>R: Validate+store connection
    R->>WS: Connection stored
    WS->>C: Connection ack

    loop Live data
        R->>WS: Publish event
        WS->>C: Send message
    end

    C->>WS: Disconnect
    WS->>R: Remove connection
```

---

## Data Model

### Key Entities

```
┌─────────────────┐       ┌─────────────────┐
│      User       │       │    Company      │
├─────────────────┤       ├─────────────────┤
│ id              │       │ id              │
│ email           │       │ name            │
│ name            │       │ slug            │
│ role            │       │ sector          │
│ preferences     │       │ stage           │
│ subscription    │       │ location        │
└────────┬────────┘       └────────┬────────┘
         │                         │
         │ 1:N                    │ 1:N
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│   Watchlist     │       │   Analysis      │
├─────────────────┤       ├─────────────────┤
│ id              │       │ id              │
│ user_id         │       │ company_id     │
│ name            │       │ job_id          │
│ alert_settings  │       │ status          │
└────────┬────────┘       │ scores          │
         │                │ content         │
         │                └─────────────────┘
         │ N:N
         ▼
┌─────────────────┐       ┌─────────────────┐
│ WatchlistItem   │       │     Signal      │
├─────────────────┤       ├─────────────────┤
│ watchlist_id    │       │ id              │
│ company_id      │       │ company_id     │
│ added_at        │       │ type            │
└─────────────────┘       │ data           │
                           │ published_at  │
                           └─────────────────┘
```

### API to Service Mapping

| API Layer | Service Layer | Database |
|-----------|---------------|----------|
| AuthController | AuthService | users |
| CompanyController | CompanyService | companies, funding |
| SearchController | SearchService | Elasticsearch |
| AnalysisController | AnalysisService | analyses, jobs |
| WatchlistController | WatchlistService | watchlists |
| SignalController | SignalService | signals |

---

## Error Flow

### Error Handling Pipeline

```mermaid
flowchart TD
    A[Request] --> B{Validate}
    B -->|Fail| E[Validation Error]
    B -->|Pass| C{Authenticate}
    C -->|Fail| F[Auth Error]
    C -->|Pass| D{Authorize}
    D -->|Fail| G[Forbidden]
    D -->|Pass| H{Rate Limit}
    H -->|Fail| I[Rate Limited]
    H -->|Pass| J[Business Logic]
    J -->|Fail| K[Business Error]
    J -->|Pass| L[Success]
```

### Error Response Format

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
      "retry_after": 60
    },
    "request_id": "uuid"
  }
}
```

---

## Cross-References

| Document | Topic |
|----------|-------|
| [07-search.md](./07-search.md) | Search UI flow |
| [09-ai-analysis.md](./09-ai-analysis.md) | Analysis UI flow |
| [17-rest-api-mapping.md](./17-rest-api-mapping.md) | API endpoints |
| [22-security.md](./22-security.md) | Security flows |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial backend flows |

---

*Part of the Opportunity Intelligence Platform PRD*
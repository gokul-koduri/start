# API Changelog

All notable changes to the Opportunity Intelligence Platform API.

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- POST /api/auth/register — User registration
- POST /api/auth/login — User login with JWT
- POST /api/auth/logout — Session invalidation
- GET /api/watchlist — List user's watchlist (auth required)
- POST /api/watchlist — Add to watchlist (auth required)
- DELETE /api/watchlist/{id} — Remove from watchlist (auth required)
- GET /api/health?detailed=1 — Extended health check (7 services)
- GET /api/metrics/business — Business metrics dashboard (admin)
- POST /api/feedback/score — Rate a score's accuracy
- POST /api/feedback/feature-request — Submit feature request

### Changed
- POST /api/score now validates input via Pydantic ScoreRequest
- POST /api/chat now validates input via Pydantic ChatRequest
- GET /api/health now checks MySQL, Redis, Kafka, Ollama, Qdrant, ES, disk
- CORS now uses CORS_ORIGINS env var whitelist (not wildcard)
- WebSocket /ws/live requires JWT token in query param

### Fixed
- 12 failing tests in test_semantic_search.py
- CORS misconfiguration (allow_origins=["*"])
- JWT secret no longer defaults to "change-me-in-production"

## [0.9.0] - 2026-06-05

### Added
- 34 API endpoints for search, score, chat, data access
- WebSocket /ws/live for real-time updates
- Prometheus metrics registry (monitoring/metrics.py)
- Stream metrics pipeline (stream/metrics.py → Redis)
- Health check endpoint (MySQL only)
- 26 data collectors (HN, Reddit, GitHub, SEC, etc.)
- 62 AI agents (scoring, analysis, NLP, reporting)
- Streamlit dashboard (11 pages)
- Docker Compose with 11 services

### Known Issues
- WebSocket polls MySQL instead of consuming Kafka
- No input validation on 6 POST endpoints (body: dict)
- CORS allows all origins (allow_origins=["*"])
- No rate limiting on any endpoint
- No user authentication system
- docker-compose.yml has hardcoded password fallback
- api_server.py has 0 tests

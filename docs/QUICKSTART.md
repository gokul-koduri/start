# Quickstart Guide

Get the Opportunity Intelligence Platform running in 5 minutes.

---

## Option 1: Docker (Recommended)

The fastest way to get started.

```bash
# Clone and start
git clone https://github.com/gokul-koduri/start.git
cd start

# Start all services
docker compose up -d

# Pull the LLM model (one-time)
docker compose exec ollama ollama pull llama3

# Initialize the database
docker compose exec api python seed_data.py

# Verify everything is running
docker compose ps
```

**Access the dashboard:**
- API: http://localhost:8000
- Dashboard: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Option 2: Local Development

For development with hot reload.

### Prerequisites

- Python 3.12+
- MySQL 8.0+
- Ollama with llama3

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/gokul-koduri/start.git
cd start

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 5. Create database
mysql -u root -p -e "CREATE DATABASE startup_research CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 6. Initialize database
python seed_data.py

# 7. Start Ollama
ollama pull llama3
ollama serve &

# 8. Run the API server
python api_server.py
```

---

## First Steps

### 1. Explore the API

```bash
# Health check
curl http://localhost:8000/api/health

# Get database stats
curl http://localhost:8000/api/stats

# List startups
curl http://localhost:8000/api/startups

# Search startups
curl "http://localhost:8000/api/search?q=manufacturing"
```

### 2. Try the Dashboard

Open http://localhost:8000 in your browser.

Features:
- Dark mode (click 🌙 in header)
- Mobile responsive
- Real-time search
- Collapsible sections

### 3. Run AI Analysis

```bash
# Run the agent pipeline
python run_agent.py --pipeline daily

# Ask the AI Analyst a question
python run_agent.py --chat "What are the key success factors for EV startups?"
```

### 4. Explore Data Sources

| Source | Endpoint | Purpose |
|--------|----------|---------|
| Startups | `/api/startups` | Failed startup data |
| News | `/api/news` | Recent articles |
| Survival Rates | `/api/survival-rates` | BLS data |
| Opportunities | `/api/v2/opportunities` | Scored opportunities |
| Knowledge Graph | `/api/knowledge-graph` | Entity relationships |

---

## Data Collection

### Run all collectors

```bash
python run_collectors.py --all
```

### Run specific collector

```bash
python run_collectors.py --collector google_news_rss
python run_collectors.py --collector bls_survival_rates
python run_collectors.py --collector failory_scraper
```

---

## Authentication

### Register a new user

```bash
curl -X POST http://localhost:8000/api/v2/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "securepassword123"}'
```

### Login and get JWT

```bash
curl -X POST http://localhost:8000/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "securepassword123"}'
```

### Use the token

```bash
curl http://localhost:8000/api/v2/watchlists \
  -H "Authorization: Bearer <your_jwt_token>"
```

---

## Watchlists & Alerts

### Create a watchlist

```bash
curl -X POST http://localhost:8000/api/v2/watchlists \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Favorites", "description": "Tracking interesting startups"}'
```

### Add item to watchlist

```bash
curl -X POST http://localhost:8000/api/v2/watchlists/1/items \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"entity_name": "Tesla", "entity_type": "startup"}'
```

---

## Export Data

### CSV Export

```bash
curl "http://localhost:8000/api/v2/export/csv?table=opportunities" \
  -o opportunities.csv
```

### PDF Report (Pro)

```bash
curl "http://localhost:8000/api/v2/export/pdf?type=weekly" \
  -o report.pdf
```

---

## WebSocket Connection

Connect to live updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/live?token=<your_jwt>');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.data);
};
```

Message types:
- `stats_update` — Dashboard statistics
- `score_update` — New opportunity scores
- `score_delta` — Score changes

---

## Troubleshooting

### "Connection refused" on /api/health

```bash
# Check if API is running
docker compose ps api

# View logs
docker compose logs api

# Restart services
docker compose restart api
```

### Ollama not responding

```bash
# Check Ollama status
docker compose ps ollama

# Pull model again
docker compose exec ollama ollama pull llama3
```

### Database errors

```bash
# Check MySQL logs
docker compose logs mysql

# Reinitialize database
docker compose exec api python seed_data.py
```

---

## Next Steps

- Read the [API Documentation](API_ENDPOINTS.md)
- Explore the [Architecture](ARCHITECTURE.md)
- Check out [Example Reports](site/data.json)
- Join discussions on GitHub

---

## Need Help?

- GitHub Issues: https://github.com/gokul-koduri/start/issues
- Documentation: See `docs/` folder
- API Docs: http://localhost:8000/docs
# 🚀 Opportunity Intelligence Platform — Deployment Guide

> How to deploy the platform locally, on a server, or in production
> Docker | Kubernetes | Manual | Cloud

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start (Local)](#2-quick-start-local)
3. [Docker Deployment](#3-docker-deployment)
4. [Manual Deployment](#4-manual-deployment)
5. [Production Deployment](#5-production-deployment)
6. [Cloud Deployment](#6-cloud-deployment)
7. [Environment Variables](#7-environment-variables)
8. [Database Setup](#8-database-setup)
9. [LLM Setup (Ollama)](#9-llm-setup-ollama)
10. [Monitoring & Health Checks](#10-monitoring--health-checks)
11. [Troubleshooting](#11-troubleshooting)
12. [Backup & Recovery](#12-backup--recovery)

---

## 1. Prerequisites

### Minimum Requirements

| Component | Minimum | Recommended |
|---|---|---|
| **CPU** | 2 cores | 4+ cores |
| **RAM** | 4 GB | 16+ GB |
| **Disk** | 20 GB | 100+ GB SSD |
| **OS** | Ubuntu 20.04+ / macOS 12+ | Ubuntu 22.04 LTS |
| **Python** | 3.12+ | 3.12 |
| **Docker** | 24.0+ | 27.0+ |
| **Docker Compose** | v2.20+ | v2.30+ |

### Required Accounts (Free Tier)

| Service | Purpose | Needed For |
|---|---|---|
| **Ollama** | Local LLM inference | All deployments |
| **Reddit API** | Reddit data collection | Optional (Reddit collector) |
| **GitHub API** | GitHub data collection | Optional (GitHub collector) |
| **SEC EDGAR** | Financial filings | Free, no account needed |

---

## 2. Quick Start (Local)

### Option A: Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/Startup_Research_Report.git
cd Startup_Research_Report

# 2. Copy environment variables
cp .env.example .env
# Edit .env with your settings

# 3. Start all services
docker compose up -d

# 4. Wait for services to be healthy
docker compose ps

# 5. Pull the LLM model
docker compose exec ollama ollama pull llama3

# 6. Seed the database (first time only)
docker compose exec api python seed_data.py

# 7. Run the collection pipeline
docker compose exec api python run_agent.py --pipeline daily

# 8. Access the services
# Dashboard:    http://localhost:8000
# API docs:     http://localhost:8000/docs
# Streamlit:    http://localhost:8501
```

### Option B: Manual (No Docker)

```bash
# 1. Clone and enter directory
git clone https://github.com/your-org/Startup_Research_Report.git
cd Startup_Research_Report

# 2. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install and start Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3

# 5. Install MySQL (if not installed)
# macOS:
brew install mysql && brew services start mysql
# Ubuntu:
sudo apt install mysql-server && sudo systemctl start mysql

# 6. Create database
mysql -u root -p -e "CREATE DATABASE startup_research CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 7. Configure environment
cp .env.example .env
# Edit .env:
#   DB_HOST=localhost
#   DB_PORT=3306
#   DB_USER=root
#   DB_PASSWORD=your_password
#   DB_NAME=startup_research
#   OLLAMA_HOST=http://localhost:11434

# 8. Run database migrations
python -c "from db.schema import SchemaManager; from db.connection import get_connection; SchemaManager(get_connection()).run_migrations()"

# 9. Seed data
python seed_data.py

# 10. Run collectors
python run_collectors.py

# 11. Run agent pipeline
python run_agent.py --pipeline daily

# 12. Start API server
python api_server.py

# 13. (Optional) Start Streamlit dashboard
streamlit run streamlit_app.py
```

---

## 3. Docker Deployment

### Services Overview (12 services)

```yaml
# docker-compose.yml services

services:
  mysql:          # MySQL 8.0 - operational database
  ollama:         # Local LLM inference (llama3)
  api:            # FastAPI REST + WebSocket server
  streamlit:      # Internal dashboard
  redis:          # Cache + pub/sub
  redpanda:       # Kafka-compatible event bus
  qdrant:         # Vector similarity search
  elasticsearch:  # Full-text search engine
  clickhouse:     # OLAP analytics
  timescaledb:    # Time-series database
  nextjs:         # Production Next.js dashboard
  nlp-worker:     # spaCy + SentenceTransformers
```

### Start Specific Services

```bash
# Start only core services (minimal)
docker compose up -d mysql ollama api

# Start with search
docker compose up -d mysql ollama api redis qdrant elasticsearch

# Start with streaming
docker compose up -d mysql ollama api redis redpanda

# Start everything
docker compose up -d

# Start with build (after code changes)
docker compose up -d --build
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f mysql

# Last 100 lines
docker compose logs --tail 100 api
```

### Resource Limits

```bash
# Check resource usage
docker stats

# Expected resource usage:
# MySQL:          ~500MB RAM
# Ollama:         ~4GB RAM (with llama3)
# FastAPI:        ~200MB RAM
# Redis:          ~50MB RAM
# Elasticsearch:  ~1GB RAM
# Qdrant:         ~200MB RAM
# ClickHouse:     ~500MB RAM
# TimescaleDB:    ~300MB RAM
# Total:          ~7-8GB RAM
```

---

## 4. Manual Deployment

### Systemd Service (Linux)

```ini
# /etc/systemd/system/oip-api.service

[Unit]
Description=Opportunity Intelligence Platform API
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=oip
Group=oip
WorkingDirectory=/opt/oip/Startup_Research_Report
Environment="PATH=/opt/oip/venv/bin"
ExecStart=/opt/oip/venv/bin/python api_server.py --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable oip-api
sudo systemctl start oip-api
sudo systemctl status oip-api

# View logs
sudo journalctl -u oip-api -f
```

### Pipeline Scheduler (Cron)

```bash
# Edit crontab
crontab -e

# Daily pipeline at 8 AM UTC
0 8 * * * /opt/oip/venv/bin/python /opt/oip/Startup_Research_Report/run_agent.py --pipeline daily >> /opt/oip/data/logs/cron.log 2>&1

# Weekly deep analysis (Sundays 6 AM UTC)
0 6 * * 0 /opt/oip/venv/bin/python /opt/oip/Startup_Research_Report/run_agent.py --pipeline weekly >> /opt/oip/data/logs/cron.log 2>&1

# Collector refresh every 4 hours
0 */4 * * * /opt/oip/venv/bin/python /opt/oip/Startup_Research_Report/run_collectors.py >> /opt/oip/data/logs/cron.log 2>&1
```

---

## 5. Production Deployment

### Architecture

```
                    ┌─────────────┐
                    │   Nginx     │ (SSL termination, reverse proxy)
                    │  (Port 443) │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴────┐ ┌────┴────┐ ┌────┴─────┐
        │ FastAPI  │ │ FastAPI │ │ Next.js  │
        │ (Worker  │ │ (Worker │ │Dashboard │
        │   #1)    │ │   #2)   │ │          │
        └─────┬────┘ └────┬────┘ └────┬─────┘
              │            │            │
              └────────────┼────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
  ┌─────┴─────┐    ┌──────┴──────┐    ┌──────┴──────┐
  │   MySQL   │    │  ClickHouse │    │ Elasticsearch│
  │ (Primary  │    │   (OLAP)    │    │   (Search)   │
  │ + Replica)│    │             │    │              │
  └───────────┘    └─────────────┘    └──────────────┘
        │
  ┌─────┴─────┐    ┌─────────────┐    ┌──────────────┐
  │  Qdrant   │    │ TimescaleDB │    │    Redis     │
  │ (Vectors) │    │ (Time-      │    │ (Cache +     │
  │           │    │  Series)    │    │  Pub/Sub)    │
  └───────────┘    └─────────────┘    └──────────────┘
        │
  ┌─────┴─────┐
  │  Ollama   │ (LLM inference, GPU recommended)
  │ (llama3)  │
  └───────────┘
```

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/oip

upstream api_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
}

upstream dashboard {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Dashboard
    location / {
        proxy_pass http://dashboard;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # API
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # SSE
    location /api/events/stream {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding off;
    }
}
```

### SSL (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renew (certbot adds this automatically)
sudo certbot renew --dry-run
```

---

## 6. Cloud Deployment

### AWS

```yaml
# Recommended AWS Architecture

Compute:
  - ECS Fargate (API + Dashboard)     # $30-100/mo
  - EC2 g4dn.xlarge (Ollama + GPU)    # $0.526/hr spot = ~$380/mo

Database:
  - RDS MySQL 8.0 (db.t3.medium)      # $50/mo
  - ElastiCache Redis (cache.t3.micro) # $15/mo

Search:
  - OpenSearch (t3.small)             # $30/mo
  - Qdrant Cloud (free tier)          # $0

Storage:
  - S3 (reports + PDFs)               # $1-5/mo
  - EBS (database volumes)            # $10/mo

Networking:
  - ALB (Application Load Balancer)   # $25/mo
  - CloudFront (CDN)                  # $5/mo

Total estimated: ~$550-700/mo
```

### Google Cloud

```yaml
Compute:
  - Cloud Run (API + Dashboard)       # $20-50/mo
  - GCE with L4 GPU (Ollama)          # $300/mo

Database:
  - Cloud SQL MySQL                   # $50/mo
  - Memorystore Redis                 # $15/mo

Total estimated: ~$400-500/mo
```

### Hetzner (Budget)

```yaml
# Most cost-effective option

Server: Dedicated AX42 (~$50/mo)
  - AMD Ryzen 9, 64GB RAM, 2x NVMe
  - Runs everything on one machine
  - Ollama runs on CPU (slower but works)

Total estimated: ~$55/mo
```

---

## 7. Environment Variables

### Core (.env)

```bash
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_secure_password
DB_NAME=startup_research

# Ollama (Local LLM)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Kafka (Redpanda)
KAFKA_BROKERS=localhost:9092
KAFKA_TOPIC_PREFIX=oip

# Qdrant (Vector Search)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Elasticsearch
ES_HOST=http://localhost:9200

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123

# TimescaleDB
TIMESCALE_HOST=localhost
TIMESCALE_PORT=5432

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RELOAD=false

# Stripe (Pro tier)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email Alerts
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_TO=team@your-domain.com

# GitHub API (optional)
GITHUB_TOKEN=ghp_...

# Reddit API (optional)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=OIP/1.0

# Monitoring
SENTRY_DSN=
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
```

---

## 8. Database Setup

### MySQL Configuration

```ini
# /etc/mysql/mysql.conf.d/oip.cnf

[mysqld]
# Performance
innodb_buffer_pool_size = 2G
innodb_log_file_size = 512M
innodb_flush_method = O_DIRECT

# Connections
max_connections = 200
wait_timeout = 600

# Character set
character_set_server = utf8mb4
collation_server = utf8mb4_unicode_ci

# Slow query log
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
```

### Backup Script

```bash
#!/bin/bash
# scripts/backup_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/oip/backups"
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# MySQL backup
mysqldump -u root -p$DB_PASSWORD startup_research \
    --single-transaction --routines --triggers \
    | gzip > "$BACKUP_DIR/mysql_$DATE.sql.gz"

# Keep only last 30 days
find $BACKUP_DIR -name "mysql_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: mysql_$DATE.sql.gz"
```

### Cron Backup

```bash
# Daily backup at 2 AM
0 2 * * * /opt/oip/Startup_Research_Report/scripts/backup_db.sh >> /opt/oip/data/logs/backup.log 2>&1
```

---

## 9. LLM Setup (Ollama)

### Install Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Start service
ollama serve
```

### Pull Models

```bash
# Primary model (recommended)
ollama pull llama3

# Lighter model (for low RAM)
ollama pull llama3:8b

# Alternative models
ollama pull mistral
ollama pull phi3
```

### GPU Setup (NVIDIA)

```bash
# Install NVIDIA drivers
sudo apt install nvidia-driver-535

# Install NVIDIA Container Toolkit (for Docker)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Docker Compose with GPU

```yaml
# docker-compose.yml — Ollama with GPU

ollama:
  image: ollama/ollama:latest
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  volumes:
    - ollama_data:/root/.ollama
  ports:
    - "11434:11434"
```

---

## 10. Monitoring & Health Checks

### Health Check Endpoints

```bash
# API health
curl http://localhost:8000/api/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "ollama": "running",
  "redis": "connected",
  "kafka": "connected",
  "last_pipeline_run": "2024-01-15T08:00:00Z",
  "uptime_seconds": 86400
}
```

### Pipeline Health Monitoring

```bash
# Check pipeline runs
curl http://localhost:8000/api/pipeline-runs

# Check agent health
curl http://localhost:8000/api/stats
```

### Docker Health Checks

```bash
# Check all service health
docker compose ps

# Check specific service health
docker inspect --format='{{.State.Health.Status}}' oip-api-1
```

---

## 11. Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|---|---|---|
| `Connection refused` (MySQL) | MySQL not started | `docker compose restart mysql` or `sudo systemctl start mysql` |
| `Ollama connection error` | Ollama not running | `ollama serve` or `docker compose restart ollama` |
| `Model not found` | llama3 not pulled | `ollama pull llama3` |
| `Out of memory` | RAM < 4GB | Add swap or use lighter model |
| `Kafka connection failed` | Redpanda not ready | Wait 30s after `docker compose up` |
| `Slow API responses` | Missing indexes | Run `python -c "from db.schema import ...; create_indexes()"` |
| ` collectors rate limited` | Too many requests | Reduce frequency in `config/settings.yaml` |
| `Docker build fails` | Dependency conflict | `docker compose build --no-cache` |

### Logs

```bash
# Application logs
tail -f data/logs/app.log

# Docker logs
docker compose logs -f api --tail 100

# MySQL slow queries
tail -f /var/log/mysql/slow.log

# Ollama logs
docker compose logs -f ollama
```

### Reset Everything

```bash
# ⚠️ DESTROYS ALL DATA
docker compose down -v    # Stop + remove volumes
docker compose up -d      # Start fresh
docker compose exec api python seed_data.py  # Re-seed
```

---

## 12. Backup & Recovery

### Backup Strategy

| What | Frequency | Tool | Retention |
|---|---|---|---|
| MySQL database | Daily | `mysqldump` | 30 days |
| ClickHouse data | Weekly | `clickhouse-backup` | 4 weeks |
| Qdrant vectors | Weekly | Snapshot API | 4 weeks |
| Config files | On change | Git | Forever |
| Elasticsearch indices | Weekly | Snapshot API | 4 weeks |
| LLM model | Once | `ollama pull` | N/A |

### Recovery

```bash
# Restore MySQL
gunzip < backup/mysql_20240115.sql.gz | mysql -u root -p startup_research

# Restore from Docker volume
docker compose down
docker volume rm oip_mysql_data
docker volume create --name oip_mysql_data -d local
# Copy backup to volume, then:
docker compose up -d
```

---

*Last updated: June 5, 2026*

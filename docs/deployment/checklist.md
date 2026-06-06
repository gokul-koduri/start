# Deployment Checklist

## Pre-Deploy (30 minutes before)

- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] Security scan clean: `bash scripts/security_scan.sh`
- [ ] Database backup completed: `bash scripts/backup_db.sh`
- [ ] Review git diff since last deploy: `git log --oneline v0.9.0..HEAD`
- [ ] Check for new environment variables in .env.example
- [ ] Verify .env has all required variables
- [ ] Check disk space: `df -h` (need >20% free)
- [ ] Notify users if there will be downtime

## Deploy

- [ ] `git pull origin main`
- [ ] `git checkout v1.x.x` (use tag)
- [ ] `pip install -r requirements.txt`
- [ ] Run database migrations if any
- [ ] `docker compose down && docker compose up -d`
- [ ] Wait 30 seconds for services to start
- [ ] `curl http://localhost:8000/api/health?detailed=1`

## Post-Deploy

- [ ] Verify API: `curl http://localhost:8000/api/health`
- [ ] Verify dashboard: `curl http://localhost:8501`
- [ ] Check MySQL: `docker exec oip-mysql mysql -e "SELECT 1"`
- [ ] Check Redis: `docker exec oip-redis redis-cli ping`
- [ ] Check Ollama: `curl http://localhost:11434/api/tags`
- [ ] Watch logs for 5 min: `docker compose logs -f --tail=100`
- [ ] Run smoke test: search, chat, score
- [ ] Check error_log: `SELECT * FROM error_log WHERE timestamp > NOW() - INTERVAL 10 MINUTE`
- [ ] Tag release: `git tag -a v1.x.x -m "Release v1.x.x"`

## Rollback (if something goes wrong)

- [ ] `docker compose down`
- [ ] `git checkout v0.9.0` (previous tag)
- [ ] `docker compose up -d`
- [ ] Restore DB if migration ran: `bash scripts/restore_db.sh <backup>`
- [ ] Verify: `curl http://localhost:8000/api/health`
- [ ] Post-mortem within 24 hours

.PHONY: install test run api docker-up docker-down clean lint

# ── Setup ───────────────────────────────────────────────
install:
	pip install -r requirements.txt
	cp -n .env.example .env || true

# ── Development ─────────────────────────────────────────
run:
	python run_agent.py --pipeline daily

run-weekly:
	python run_agent.py --pipeline weekly

run-full:
	python run_agent.py --pipeline full

collect:
	python run_collectors.py --all

report:
	python run_report.py

# ── API Server ──────────────────────────────────────────
api:
	python api_server.py --reload

# ── Chat ────────────────────────────────────────────────
chat:
	@read -p "Ask: " q && python run_agent.py --chat "$$q"

# ── Testing ─────────────────────────────────────────────
test:
	python -m pytest tests/ -v --tb=short

test-verbose:
	python -m pytest tests/ -v -s --tb=long

# ── Docker ──────────────────────────────────────────────
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api

docker-pipeline:
	docker compose exec pipeline python run_agent.py --pipeline daily

docker-seed:
	docker compose exec api python seed_data.py

docker-pull-llama:
	docker compose exec ollama ollama pull llama3

# ── Setup ───────────────────────────────────────────────
setup:
	bash scripts/setup_and_fix.sh

# ── Cleanup ─────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache/

# ── Schedule (macOS launchd) ────────────────────────────
schedule:
	bash scripts/setup_and_fix.sh

unschedule:
	launchctl unload $(HOME)/Library/LaunchAgents/com.startup-research.daily.plist 2>/dev/null || true
	launchctl unload $(HOME)/Library/LaunchAgents/com.startup-research.weekly.plist 2>/dev/null || true
	@echo "Schedulers removed."

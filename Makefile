.PHONY: install test run api docker-up docker-down clean lint \
	sprint-status sprint-plan sprint-gate sprint-review sprint-retro standup backlog-refine \
	pr lint-fix

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
api: ## Start the FastAPI REST API server
	/opt/anaconda3/bin/python api_server.py --host 127.0.0.1 --port 8000 --reload

# ── Chat ────────────────────────────────────────────────
chat:
	@read -p "Ask: " q && python run_agent.py --chat "$$q"

# ── Streamlit Dashboard ─────────────────────────────────
streamlit: ## Launch the interactive Streamlit dashboard
	streamlit run streamlit_app.py --server.port 8501

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

# ── Linting ─────────────────────────────────────────────
lint:
	ruff check .

lint-fix:
	ruff check . --fix
	ruff format .

# ── Agile / Sprint ─────────────────────────────────────
sprint-status: ## Show current sprint status
	@python scripts/sprint_validator.py --sprint $$(python -c "import yaml; print(yaml.safe_load(open('docs/sprints/sprint-tracker.yaml')).get('current_sprint', 1))") -d || python scripts/sprint_validator.py

sprint-plan: ## Sprint planning ceremony
	@python scripts/agile_cli.py planning

sprint-gate: ## Run sprint gate check (exit 0=pass, 1=fail)
	@python scripts/sprint_validator.py --gate

sprint-review: ## Generate sprint review report
	@python scripts/agile_cli.py review

sprint-retro: ## Generate retrospective template
	@python scripts/agile_cli.py retrospective

standup: ## Generate daily standup template
	@python scripts/agile_cli.py standup

backlog-refine: ## Show product backlog for refinement
	@python scripts/agile_cli.py backlog

sprint-metrics: ## Show velocity & metrics
	@python scripts/agile_cli.py metrics

sprint-burndown: ## Show burndown chart
	@python scripts/agile_cli.py burndown

sprint-labels: ## Print GitHub label creation commands
	@python scripts/agile_cli.py labels

sprint-all: ## Show all sprint statuses
	@python scripts/sprint_validator.py --all

# ── PR Helper ──────────────────────────────────────────
pr: ## Create a PR (interactive)
	@read -p "Branch name (e.g., feature/T-001-desc): " branch && \
	git checkout -b $$branch develop && \
	@echo "✅ Branch created. Push and open PR when ready."
	@echo "Template: .github/pull_request_template.md"

# Contributing to Opportunity Intelligence Platform

Thank you for considering contributing! 🎉

## Report a Bug
1. Search [existing issues](https://github.com/gokul-koduri/start/issues) first
2. Click **New Issue** → **Bug Report**
3. Fill in: description, steps to reproduce, expected behavior
4. Add the `bug` label

## Request a Feature
1. Click **New Issue** → **Feature Request**
2. Describe the **problem** it solves (not just the solution)
3. Explain your proposed solution
4. Add the `enhancement` label

## Submit a Fix
1. Fork the repository
2. Create a branch: `git checkout -b fix/your-fix-name`
3. Make your change (smallest possible change)
4. Add a test that verifies the fix
5. Run all tests: `python -m pytest tests/ -q`
6. Commit: `git commit -m "fix: description of fix"`
7. Push: `git push origin fix/your-fix-name`
8. Create a Pull Request

## Submit a Feature
1. Fork the repository
2. Create a branch: `git checkout -b feat/your-feature-name`
3. Build the feature + add tests + update docs
4. Run all tests: `python -m pytest tests/ -q`
5. Commit: `git commit -m "feat: description of feature"`
6. Push and create a Pull Request

## Development Setup

```bash
git clone https://github.com/gokul-koduri/start.git
cd start
pip install -r requirements.txt
docker compose up -d
python -m pytest tests/ -v       # Run tests
python api_server.py             # Start API
streamlit run streamlit_app.py   # Start dashboard
```

## Code Style
- Python 3.12+
- Follow PEP 8 (use `ruff check .` to lint)
- Write docstrings for all public functions
- Max line length: 120 characters

## Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat: add new scoring factor`
- `fix: resolve search crash on empty query`
- `docs: update API documentation`
- `test: add tests for scoring engine`
- `chore: update dependencies`

## Questions?
Open a [GitHub Discussion](https://github.com/gokul-koduri/start/discussions). We respond within 24 hours.

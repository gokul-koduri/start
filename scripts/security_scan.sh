#!/bin/bash
# Security Scanner — run weekly or before releases

echo "=== Security Scan — $(date) ==="
cd "$(git rev-parse --show-toplevel)"

# 1. Python dependency CVEs
echo ""
echo ">>> Checking Python packages for CVEs..."
pip install pip-audit -q 2>/dev/null
pip-audit --desc 2>&1 | tail -20

# 2. Python code security
echo ""
echo ">>> Scanning Python code..."
pip install bandit -q 2>/dev/null
bandit -r . -ll --exclude "./tests,./.git,./venv" 2>&1 | tail -20

# 3. Docker images
echo ""
echo ">>> Scanning Docker images..."
if command -v trivy &> /dev/null; then
    trivy image --severity HIGH,CRITICAL mysql:8.0 2>&1 | tail -10
else
    echo "Trivy not installed. Install: brew install trivy"
fi

# 4. Hardcoded secrets
echo ""
echo ">>> Checking for secrets..."
if command -v gitleaks &> /dev/null; then
    gitleaks detect --source . --verbose 2>&1 | tail -10
else
    grep -rn "password\s*=" . --include="*.py" --include="*.yml" \
        | grep -v ".env" | grep -v "test" || echo "No obvious hardcoded passwords"
fi

# 5. .gitignore check
echo ""
if grep -q ".env" .gitignore 2>/dev/null; then
    echo "✅ .env is in .gitignore"
else
    echo "🔴 CRITICAL: .env is NOT in .gitignore!"
fi

echo ""
echo "=== Scan complete ==="

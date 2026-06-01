#!/bin/bash
# One-time setup script to create a GitHub repository and configure GitHub Pages.
#
# Prerequisites:
#   - GitHub CLI (gh) installed and authenticated: https://cli.github.com/
#   - Run: gh auth login
#
# Usage:
#   ./scripts/setup_github.sh [REPO_NAME]
#
# Example:
#   ./scripts/setup_github.sh startup-research-report

set -euo pipefail

REPO_NAME="${1:-startup-research-report}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== GitHub Repository Setup ==="
echo "Project: $PROJECT_DIR"
echo "Repo name: $REPO_NAME"
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "ERROR: GitHub CLI (gh) not found."
    echo "Install it from: https://cli.github.com/"
    echo "Then run: gh auth login"
    exit 1
fi

# Check if already authenticated
if ! gh auth status &> /dev/null; then
    echo "ERROR: Not authenticated with GitHub."
    echo "Run: gh auth login"
    exit 1
fi

# Get GitHub username
GH_USER=$(gh api user --jq '.login')
echo "GitHub user: $GH_USER"
FULL_REPO="${GH_USER}/${REPO_NAME}"
echo "Full repo: $FULL_REPO"
echo ""

# Create the repository
echo "--- Creating repository ---"
if gh repo view "$FULL_REPO" &> /dev/null; then
    echo "Repository already exists: $FULL_REPO"
else
    gh repo create "$REPO_NAME" --public --description "Automated Startup Research Report - Manufacturing failures & revival opportunities"
    echo "Repository created: https://github.com/$FULL_REPO"
fi

# Add remote if not already present
cd "$PROJECT_DIR"
if git remote get-url origin &> /dev/null; then
    echo "Remote 'origin' already configured: $(git remote get-url origin)"
else
    git remote add origin "https://github.com/$FULL_REPO.git"
    echo "Remote 'origin' added: https://github.com/$FULL_REPO.git"
fi

# Enable GitHub Pages
echo ""
echo "--- Enabling GitHub Pages ---"
gh api "repos/$FULL_REPO/pages" \
    --method POST \
    --field "source[branch]=main" \
    --field "source[path]=/site" \
    2>/dev/null || echo "Pages may already be enabled or needs manual setup in repo Settings > Pages"

# Initial commit and push
echo ""
echo "--- Pushing to GitHub ---"
BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
if [ "$BRANCH" != "main" ]; then
    echo "Current branch is '$BRANCH'. Consider renaming to 'main'."
fi

git push -u origin "$BRANCH" 2>/dev/null || echo "Push may have already been done."

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Your live dashboard will be available at:"
echo "  https://${GH_USER}.github.io/${REPO_NAME}/"
echo ""
echo "It may take 1-3 minutes after the first push for the site to become available."
echo ""
echo "To enable automated publishing, set these in your .env:"
echo "  GITHUB_TOKEN=ghp_your_personal_access_token"
echo "  GITHUB_REPO=${FULL_REPO}"
echo ""
echo "Then update config/settings.yaml:"
echo "  agents.git_publisher.enabled: true"

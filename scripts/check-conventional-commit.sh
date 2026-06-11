#!/usr/bin/env bash
# Validate conventional commit format: type(scope)?: description
# Types: feat, fix, docs, test, refactor, chore, ci, perf, build, style

COMMIT_MSG_FILE="$1"
FIRST_LINE=$(head -1 "$COMMIT_MSG_FILE")
if ! echo "$FIRST_LINE" | grep -qE "^(feat|fix|docs|test|refactor|chore|ci|perf|build|style)(\(.+\))?: .+"; then
    echo "ERROR: Commit message must follow Conventional Commits: type(scope): description"
    echo "  Example: feat(auth): add JWT login endpoint"
    echo "  Types: feat, fix, docs, test, refactor, chore, ci, perf, build, style"
    exit 1
fi

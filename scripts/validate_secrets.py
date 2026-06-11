#!/usr/bin/env python3
"""Startup secrets validation — run before deployment.

Checks that required secrets are set and not using default/weak values.
Exit codes: 0 = all pass, 1 = failures found.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# Known weak/default values that must not be used in production
WEAK_PASSWORDS = {"startup2024", "password", "root", "admin", "changeme", "1234", ""}
WEAK_SECRETS = {"change-me-in-production", "secret", "jwt-secret", "my-secret", ""}


def load_env_file() -> dict[str, str]:
    """Load .env file as key-value pairs (without exporting to os.environ)."""
    env_path = PROJECT_ROOT / ".env"
    env_vars = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip().strip("\"'")
    return env_vars


def check_env_exists() -> tuple[str, str, str]:
    """Check that .env file exists."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        return ("PASS", ".env file exists", "")
    return (
        "FAIL",
        ".env file missing",
        "Create .env from .env.example: cp .env.example .env",
    )


def check_env_gitignored() -> tuple[str, str, str]:
    """Check that .env is in .gitignore."""
    gitignore_path = PROJECT_ROOT / ".gitignore"
    if not gitignore_path.exists():
        return ("WARN", ".gitignore not found", "Create .gitignore and add .env")
    content = gitignore_path.read_text()
    if ".env" in content:
        return ("PASS", ".env is in .gitignore", "")
    return (
        "FAIL",
        ".env NOT in .gitignore",
        "Add .env to .gitignore to prevent secret leaks",
    )


def check_jwt_secret(env_vars: dict) -> tuple[str, str, str]:
    """Check JWT_SECRET is set and not default."""
    val = env_vars.get("JWT_SECRET", "")
    if not val:
        return (
            "WARN",
            "JWT_SECRET not set",
            'Set JWT_SECRET in .env (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")',
        )
    if val in WEAK_SECRETS:
        return (
            "FAIL",
            f"JWT_SECRET is weak ('{val}')",
            'Generate a strong secret: python -c "import secrets; print(secrets.token_urlsafe(32))"',
        )
    return ("PASS", "JWT_SECRET is set and non-default", "")


def check_mysql_password(env_vars: dict) -> tuple[str, str, str]:
    """Check MYSQL_PASSWORD is set and not weak."""
    val = env_vars.get("MYSQL_PASSWORD", "")
    if val in WEAK_PASSWORDS:
        return (
            "FAIL",
            "MYSQL_PASSWORD is weak or empty",
            "Set a strong database password in .env",
        )
    if len(val) < 12:
        return (
            "WARN",
            f"MYSQL_PASSWORD is short ({len(val)} chars)",
            "Use at least 12 characters",
        )
    return ("PASS", "MYSQL_PASSWORD is set and strong enough", "")


def check_docker_env_secrets() -> tuple[str, str, str]:
    """Check .env.docker doesn't use default passwords."""
    docker_env = PROJECT_ROOT / ".env.docker"
    if not docker_env.exists():
        return (
            "WARN",
            ".env.docker not found",
            "Create .env.docker for Docker Compose",
        )
    content = docker_env.read_text()
    if "startup2024" in content:
        return (
            "FAIL",
            ".env.docker uses default password 'startup2024'",
            "Change MYSQL_PASSWORD in .env.docker",
        )
    return ("PASS", ".env.docker does not use default passwords", "")


def check_no_hardcoded_secrets() -> tuple[str, str, str]:
    """Check key files for hardcoded default secrets."""
    issues = []
    jwt_path = PROJECT_ROOT / "auth" / "jwt_handler.py"
    if jwt_path.exists():
        content = jwt_path.read_text()
        if '"change-me-in-production"' in content:
            # Only flag if it's used as a runtime default (not just docs)
            if "auth_config.get" not in content and "self.config.get" not in content:
                issues.append("jwt_handler.py has hardcoded default secret")
    if issues:
        return (
            "WARN",
            "Possible hardcoded secrets: " + "; ".join(issues),
            "Move secrets to .env and read from environment",
        )
    return ("PASS", "No obvious hardcoded secrets in source files", "")


def main():
    """Run all checks and print report."""
    print("=" * 60)
    print("  Startup Secrets Validation")
    print("=" * 60)
    print()

    env_vars = load_env_file()

    checks = [
        check_env_exists(),
        check_env_gitignored(),
        check_jwt_secret(env_vars),
        check_mysql_password(env_vars),
        check_docker_env_secrets(),
        check_no_hardcoded_secrets(),
    ]

    fails = 0
    warns = 0
    passes = 0

    for status, desc, fix in checks:
        icon = {"PASS": "+", "WARN": "?", "FAIL": "X"}[status]
        label_color = {"PASS": "\033[92m", "WARN": "\033[93m", "FAIL": "\033[91m"}[
            status
        ]
        reset = "\033[0m"
        print(f"  [{icon}] {label_color}{status:4s}{reset}  {desc}")
        if fix:
            print(f"         -> {fix}")
        if status == "FAIL":
            fails += 1
        elif status == "WARN":
            warns += 1
        else:
            passes += 1

    print()
    print("-" * 60)
    print(f"  Results: {passes} passed, {warns} warnings, {fails} failures")
    print("=" * 60)

    if fails > 0:
        print("\n  BLOCKED: Fix FAIL items before deploying to production.\n")
        sys.exit(1)
    elif warns > 0:
        print("\n  CAUTION: Review WARN items before deploying.\n")
        sys.exit(0)
    else:
        print("\n  READY: All checks passed.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

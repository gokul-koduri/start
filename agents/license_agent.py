"""License Management Agent — generates and validates license keys.

Manages the Pro/Enterprise tier system for the Opportunity Intelligence Platform.
Generates license keys, embeds them in the site build as hashed allowlists,
and tracks subscription metrics.

Runs as part of the ``publish-only`` pipeline, before the dashboard agent.
"""

import hashlib
import json
import logging
import secrets
import string
from datetime import datetime, timezone, timedelta

from agents.base import AgentResult, BaseAgent
from config import get_project_root
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

# Tier feature definitions — what each tier gets access to
TIER_FEATURES = {
    "free": [
        "failure_database",
        "news_monitoring",
        "manufacturing_survival",
        "llm_pricing",
        "basic_search",
        "public_reports",
    ],
    "pro": [
        "ai_analyst",
        "unlimited_search",
        "opportunity_reports",
        "opportunity_deep_dives",
        "industry_intelligence",
        "llm_portfolio",
        "llm_benchmarks",
        "llm_cost_optimizer",
        "alert_system",
    ],
    "enterprise": [
        "api_access",
        "custom_monitoring",
        "internal_reports",
        "consulting_support",
        "priority_support",
        "white_label",
        "bulk_export",
    ],
}

# Tier pricing configuration (display only — actual payments via Stripe)
TIER_PRICING = {
    "free": {"price": 0, "currency": "USD", "period": "forever", "label": "Free"},
    "pro": {"price": 49, "currency": "USD", "period": "month", "label": "Pro"},
    "enterprise": {
        "price": 1000,
        "currency": "USD",
        "period": "month",
        "label": "Enterprise",
    },
}

# License key prefix per tier
TIER_PREFIXES = {
    "pro": "PRO",
    "enterprise": "ENT",
}


def _generate_license_key(tier: str) -> str:
    """Generate a human-readable license key: PRO-XXXX-XXXX-XXXX or ENT-XXXX-XXXX-XXXX."""
    prefix = TIER_PREFIXES.get(tier, "OPL")
    chars = string.ascii_uppercase + string.digits
    groups = ["".join(secrets.choice(chars) for _ in range(4)) for _ in range(3)]
    return f"{prefix}-{'-'.join(groups)}"


def _hash_key(key: str) -> str:
    """SHA-256 hash of a license key for safe storage in licenses.json."""
    return hashlib.sha256(key.encode()).hexdigest()


class LicenseAgent(BaseAgent):
    """Agent that manages license keys and builds the client-side allowlist.

    Config options:
        generate_keys: int — number of new keys to generate per run (default: 0)
        default_tier: str — tier for generated keys (default: 'pro')
        key_expiry_days: int — days until keys expire (default: 365)
        stripe_pro_url: str — Stripe checkout URL for Pro tier
        stripe_enterprise_url: str — Stripe checkout URL for Enterprise tier
    """

    @property
    def name(self) -> str:
        return "license_manager"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        generate_count = self.config.get("generate_keys", 0)
        default_tier = self.config.get("default_tier", "pro")
        expiry_days = self.config.get("key_expiry_days", 365)

        _logger.info("LicenseAgent: Starting license management")

        try:
            conn = get_connection()
            schema.init_schema(conn)
            cursor = conn.cursor()
        except Exception as e:
            _logger.error("LicenseAgent: DB connection failed: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        generated_keys = []
        total_active = 0

        try:
            # 1. Generate new keys if configured
            if generate_count > 0:
                for _ in range(generate_count):
                    key = _generate_license_key(default_tier)
                    expires = (
                        datetime.now(timezone.utc) + timedelta(days=expiry_days)
                    ).strftime("%Y-%m-%d %H:%M:%S")
                    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

                    cursor.execute(
                        """INSERT INTO user_licenses
                           (license_key, tier, expires_at, status, created_at)
                           VALUES (%s, %s, %s, 'active', %s)
                           ON DUPLICATE KEY UPDATE status = 'active'""",
                        (key, default_tier, expires, now),
                    )
                    generated_keys.append(key)
                    _logger.info(
                        "LicenseAgent: Generated key %s...%s for tier %s",
                        key[:8],
                        key[-4:],
                        default_tier,
                    )

            # 2. Expire old keys
            cursor.execute(
                "UPDATE user_licenses SET status = 'expired' "
                "WHERE status = 'active' AND expires_at IS NOT NULL "
                "AND expires_at < NOW()"
            )
            expired_count = cursor.rowcount
            if expired_count:
                _logger.info("LicenseAgent: Expired %d keys", expired_count)

            # 3. Read all active non-free keys for the allowlist
            cursor.execute(
                "SELECT license_key, tier FROM user_licenses "
                "WHERE status = 'active' AND tier != 'free'"
            )
            active_licenses = cursor.fetchall()

            # 4. Count metrics
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM user_licenses WHERE status = 'active' AND tier = 'free'"
            )
            free_count = cursor.fetchone()["cnt"]
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM user_licenses WHERE status = 'active' AND tier = 'pro'"
            )
            pro_count = cursor.fetchone()["cnt"]
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM user_licenses WHERE status = 'active' AND tier = 'enterprise'"
            )
            ent_count = cursor.fetchone()["cnt"]
            total_active = free_count + pro_count + ent_count

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            _logger.error("LicenseAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()

        # 5. Build the licenses.json file (hashed keys only)
        site_dir = get_project_root() / self.config.get("site_dir", "site")
        licenses = {
            "keys": [_hash_key(row["license_key"]) for row in active_licenses],
            "tier_features": TIER_FEATURES,
            "tier_pricing": TIER_PRICING,
            "stripe_urls": {
                "pro": self.config.get("stripe_pro_url", ""),
                "enterprise": self.config.get("stripe_enterprise_url", ""),
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "licenses.json").write_text(
            json.dumps(licenses, indent=2), encoding="utf-8"
        )

        _logger.info(
            "LicenseAgent: Done — %d generated, %d active keys (%d pro, %d enterprise)",
            len(generated_keys),
            total_active,
            pro_count,
            ent_count,
        )

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "keys_generated": len(generated_keys),
                "active_licenses": total_active,
                "pro_users": pro_count,
                "enterprise_users": ent_count,
                "free_users": free_count,
                "records_affected": len(generated_keys),
            },
        )


def generate_license(tier: str = "pro", expiry_days: int = 365) -> str:
    """Utility function to generate a single license key.

    Can be called from scripts or the CLI for manual key creation.
    Returns the generated key string.
    """
    key = _generate_license_key(tier)

    try:
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        expires = (datetime.now(timezone.utc) + timedelta(days=expiry_days)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            """INSERT INTO user_licenses
               (license_key, tier, expires_at, status, created_at)
               VALUES (%s, %s, %s, 'active', %s)""",
            (key, tier, expires, now),
        )
        conn.commit()
        cursor.close()
        conn.close()

        _logger.info(
            "Generated license key: %s (tier=%s, expires=%dd)", key, tier, expiry_days
        )
    except Exception as e:
        _logger.error("Failed to store license key: %s", e)

    return key

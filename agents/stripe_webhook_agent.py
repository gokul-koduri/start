"""Stripe Payment Agent — polls Stripe API for completed checkout sessions.

Since the Opportunity Intelligence Platform is a static site on GitHub Pages,
it cannot receive webhook events directly. This agent polls the Stripe API
to retrieve completed checkout sessions and auto-generates license keys.

Architecture:
    GET /v1/checkout/sessions?created[gte]={24h_ago} (Bearer auth)
    -> for each completed session:
       -> check if stripe_session_id exists in payment_events
       -> if new: insert payment_event + generate license key
       -> update subscription_metrics

Also provides an optional Flask webhook server for local development:
    python -c "from agents.stripe_webhook_agent import create_flask_app; create_flask_app().run(port=5000)"

Config options:
    stripe_secret_key: str — Stripe API secret key (${STRIPE_SECRET_KEY})
    poll_hours_back: int — hours to look back for sessions (default: 24)
"""

import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

from agents.base import AgentResult, BaseAgent
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

# Stripe API base URL
STRIPE_API_BASE = "https://api.stripe.com/v1"


class StripePaymentAgent(BaseAgent):
    """Polls Stripe for completed payments and auto-generates license keys.

    Config options:
        stripe_secret_key: str — Stripe API secret key
        poll_hours_back: int — lookback window in hours (default: 24)
    """

    @property
    def name(self) -> str:
        return "stripe_payments"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        secret_key = self.config.get("stripe_secret_key", "")
        poll_hours = self.config.get("poll_hours_back", 24)

        if not secret_key:
            _logger.info("StripePaymentAgent: No Stripe key configured, skipping")
            return AgentResult(
                agent_name=self.name,
                status="success",
                data={"sessions_processed": 0, "new_payments": 0, "records_affected": 0},
            )

        _logger.info("StripePaymentAgent: Polling Stripe for sessions (last %dh)", poll_hours)

        try:
            conn = get_connection()
            schema.init_schema(conn)
        except Exception as e:
            _logger.error("StripePaymentAgent: Cannot connect to DB: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])

        try:
            cursor = conn.cursor()
            sessions = self._fetch_stripe_sessions(secret_key, poll_hours)

            new_payments = 0
            total_amount = 0.0

            for session in sessions:
                session_id = session.get("id")
                if not session_id:
                    continue

                # Check if already processed
                cursor.execute(
                    "SELECT id FROM payment_events WHERE stripe_session_id = %s", (session_id,)
                )
                if cursor.fetchone():
                    continue

                # Determine tier from metadata or amount
                tier = self._determine_tier(session)
                amount = self._session_amount(session)
                email = session.get("customer_details", {}).get("email", "")
                status = "completed" if session.get("payment_status") == "paid" else "pending"

                # Generate license key
                license_key = None
                if status == "completed":
                    try:
                        from agents.license_agent import generate_license
                        license_key = generate_license(tier, 365)
                        _logger.info("StripePaymentAgent: Generated license %s for %s", license_key, email)
                    except Exception as e:
                        _logger.error("StripePaymentAgent: License generation failed: %s", e)

                # Insert payment event
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """INSERT INTO payment_events
                       (stripe_session_id, customer_email, tier, amount_usd, status,
                        license_key, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (session_id, email, tier, amount, status, license_key, now),
                )

                # Link license to Stripe session if we have both
                if license_key:
                    cursor.execute(
                        "UPDATE user_licenses SET stripe_session_id = %s, email = %s WHERE license_key = %s",
                        (session_id, email, license_key),
                    )

                new_payments += 1
                total_amount += amount

            # Update subscription metrics
            self._update_subscription_metrics(conn, cursor)

            conn.commit()

            _logger.info(
                "StripePaymentAgent: Done — %d sessions, %d new payments, $%.2f",
                len(sessions), new_payments, total_amount,
            )

            return AgentResult(
                agent_name=self.name,
                status="success",
                data={
                    "sessions_polled": len(sessions),
                    "new_payments": new_payments,
                    "total_amount_usd": total_amount,
                    "records_affected": new_payments,
                },
            )

        except Exception as e:
            _logger.error("StripePaymentAgent: Error: %s", e)
            return AgentResult(agent_name=self.name, status="failed", errors=[str(e)])
        finally:
            conn.close()

    # ── Stripe API ──

    def _fetch_stripe_sessions(self, secret_key: str, poll_hours: int) -> list[dict]:
        """Fetch completed checkout sessions from Stripe API."""
        created_gte = int(
            (datetime.now(timezone.utc) - timedelta(hours=poll_hours)).timestamp()
        )
        url = f"{STRIPE_API_BASE}/checkout/sessions?created[gte]={created_gte}&limit=100&expand[]=data.customer_details"

        try:
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {secret_key}")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            sessions = data.get("data", [])
            _logger.info("StripePaymentAgent: Fetched %d sessions from Stripe", len(sessions))
            return sessions

        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode()
            except Exception:
                pass
            _logger.error("StripePaymentAgent: Stripe API error %d: %s", e.code, body[:200])
            return []
        except Exception as e:
            _logger.error("StripePaymentAgent: Stripe API request failed: %s", e)
            return []

    def _determine_tier(self, session: dict) -> str:
        """Determine subscription tier from session metadata or amount."""
        # Check metadata first
        metadata = session.get("metadata", {})
        if metadata.get("tier"):
            return metadata["tier"].lower()

        # Fallback: determine by amount
        amount = self._session_amount(session)
        if amount >= 500:
            return "enterprise"
        elif amount >= 20:
            return "pro"
        return "pro"

    def _session_amount(self, session: dict) -> float:
        """Extract payment amount in USD from a Stripe session."""
        amount_total = session.get("amount_total", 0)
        currency = session.get("currency", "usd")
        # Stripe amounts are in cents
        return amount_total / 100.0 if currency == "usd" else amount_total / 100.0

    def _update_subscription_metrics(self, conn, cursor):
        """Update daily subscription_metrics from current license state."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        cursor.execute("SELECT COUNT(*) as cnt FROM user_licenses WHERE tier = 'free' AND status = 'active'")
        free_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM user_licenses WHERE tier = 'pro' AND status = 'active'")
        pro_count = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM user_licenses WHERE tier = 'enterprise' AND status = 'active'")
        ent_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM payment_events WHERE status = 'completed'")
        revenue = cursor.fetchone()[0]

        cursor.execute(
            """INSERT INTO subscription_metrics
               (metric_date, free_users, pro_users, enterprise_users, revenue_usd)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               free_users = VALUES(free_users),
               pro_users = VALUES(pro_users),
               enterprise_users = VALUES(enterprise_users),
               revenue_usd = VALUES(revenue_usd)""",
            (today, free_count, pro_count, ent_count, revenue),
        )


# ── Optional Flask webhook server (for local development) ──

def create_flask_app(stripe_webhook_secret: str = ""):
    """Create a Flask app for receiving Stripe webhook events locally.

    Usage:
        python -c "from agents.stripe_webhook_agent import create_flask_app; \\
                   create_flask_app('whsec_...').run(port=5000)"

    Requires Flask: pip install flask
    """
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        _logger.error("Flask not installed. Run: pip install flask")
        raise

    app = Flask(__name__)

    @app.route("/webhook/stripe", methods=["POST"])
    def stripe_webhook():
        """Handle Stripe checkout.session.completed webhook."""
        payload = request.data
        sig_header = request.headers.get("Stripe-Signature", "")

        if stripe_webhook_secret:
            try:
                import stripe
                event = stripe.Webhook.construct_event(
                    payload, sig_header, stripe_webhook_secret
                )
            except (ImportError, Exception) as e:
                _logger.error("Webhook signature verification failed: %s", e)
                return jsonify({"error": str(e)}), 400
        else:
            event = json.loads(payload)
            _logger.warning("No webhook secret configured — skipping signature verification")

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            _logger.info("Webhook: Processing checkout.session.completed: %s", session.get("id"))

            try:
                conn = get_connection()
                schema.init_schema(conn)
                cursor = conn.cursor()

                session_id = session.get("id")
                cursor.execute("SELECT id FROM payment_events WHERE stripe_session_id = %s", (session_id,))
                if cursor.fetchone():
                    return jsonify({"status": "already_processed"}), 200

                agent = StripePaymentAgent(config={"stripe_secret_key": "", "poll_hours_back": 24})
                tier = agent._determine_tier(session)
                amount = agent._session_amount(session)
                email = session.get("customer_details", {}).get("email", "")

                license_key = None
                try:
                    from agents.license_agent import generate_license
                    license_key = generate_license(tier, 365)
                except Exception:
                    pass

                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    """INSERT INTO payment_events
                       (stripe_session_id, customer_email, tier, amount_usd, status,
                        license_key, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (session_id, email, tier, amount, "completed", license_key, now),
                )

                if license_key:
                    cursor.execute(
                        "UPDATE user_licenses SET stripe_session_id = %s, email = %s WHERE license_key = %s",
                        (session_id, email, license_key),
                    )

                conn.commit()
                cursor.close()
                conn.close()

            except Exception as e:
                _logger.error("Webhook handler error: %s", e)
                return jsonify({"error": str(e)}), 500

        return jsonify({"status": "received"}), 200

    return app

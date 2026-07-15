"""Sprint 7 tests for billing, entitlements, and usage quota endpoints."""

import unittest
import json
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


class _MockConn:
    def __init__(self):
        self._cursor = MagicMock()

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def close(self):
        pass


class TestSprint7Billing(unittest.TestCase):
    """Validate Sprint 7 billing API behaviors with mocked DB access."""

    @patch("api.v2.billing.schema.init_schema")
    @patch("api.v2.billing.get_connection")
    def test_get_tier_defaults_free(self, mock_conn, _mock_schema):
        from api.v2.billing import get_tier

        conn = _MockConn()
        conn._cursor.fetchone.return_value = None
        conn._cursor.fetchall.return_value = []
        mock_conn.return_value = conn

        result = get_tier(current_user={"user_id": 99})
        self.assertEqual(result["tier"], "free")
        self.assertIn("features", result)

    @patch("api.v2.billing.schema.init_schema")
    @patch("api.v2.billing.get_connection")
    def test_get_subscription_returns_latest_payment(self, mock_conn, _mock_schema):
        from api.v2.billing import get_subscription

        conn = _MockConn()
        conn._cursor.fetchone.side_effect = [
            {"email": "pro@example.com"},
            {"license_key": "PRO-XXXX-XXXX-XXXX", "tier": "pro", "status": "active"},
            {
                "stripe_session_id": "cs_test_1",
                "tier": "pro",
                "amount_usd": 49.0,
                "status": "completed",
            },
        ]
        conn._cursor.fetchall.return_value = []
        mock_conn.return_value = conn

        result = get_subscription(current_user={"user_id": 1})
        self.assertEqual(result["email"], "pro@example.com")
        self.assertEqual(result["latest_payment"]["tier"], "pro")

    def test_checkout_session_payload(self):
        from api.v2.billing import create_checkout_session, CheckoutSessionCreate

        body = CheckoutSessionCreate(tier="pro")
        result = create_checkout_session(
            body=body, current_user={"user_id": 1, "email": "x@y.com"}
        )
        self.assertEqual(result["tier"], "pro")
        self.assertIn("checkout_url", result)
        self.assertIn("price", result)

    @patch("api.v2.billing.urllib.request.urlopen")
    @patch("api.v2.billing.os.environ.get")
    def test_checkout_session_stripe_success(self, mock_env_get, mock_urlopen):
        from api.v2.billing import create_checkout_session, CheckoutSessionCreate

        def _env(key, default=""):
            values = {
                "STRIPE_SECRET_KEY": "sk_test_123",
                "STRIPE_PRO_PRICE_ID": "price_pro_123",
                "STRIPE_ENTERPRISE_PRICE_ID": "",
                "STRIPE_PRO_URL": "",
                "STRIPE_ENTERPRISE_URL": "",
            }
            return values.get(key, default)

        mock_env_get.side_effect = _env
        stripe_resp = MagicMock()
        stripe_resp.read.return_value = json.dumps(
            {
                "id": "cs_live_123",
                "url": "https://checkout.stripe.com/c/pay/cs_live_123",
                "mode": "subscription",
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = stripe_resp

        result = create_checkout_session(
            body=CheckoutSessionCreate(tier="pro"),
            current_user={"user_id": 1, "email": "pro@example.com"},
        )

        self.assertEqual(result["provider"], "stripe")
        self.assertEqual(result["session_id"], "cs_live_123")
        self.assertTrue(result["checkout_url"].startswith("https://checkout.stripe.com"))

    @patch("api.v2.billing.os.environ.get")
    def test_checkout_session_fallback_when_stripe_unconfigured(self, mock_env_get):
        from api.v2.billing import create_checkout_session, CheckoutSessionCreate

        mock_env_get.return_value = ""
        result = create_checkout_session(
            body=CheckoutSessionCreate(tier="enterprise"),
            current_user={"user_id": 5, "email": "ent@example.com"},
        )

        self.assertEqual(result["provider"], "fallback")
        self.assertIsNone(result["session_id"])
        self.assertIn("/enterprise", result["checkout_url"])

    @patch("api.v2.billing.schema.init_schema")
    @patch("api.v2.billing.get_connection")
    def test_check_feature_access_denied_for_free(self, mock_conn, _mock_schema):
        from api.v2.billing import check_feature_access

        conn = _MockConn()
        conn._cursor.fetchone.return_value = {"email": "free@example.com"}
        conn._cursor.fetchall.return_value = []
        mock_conn.return_value = conn

        with self.assertRaises(HTTPException) as ctx:
            check_feature_access(
                feature="opportunity_reports", current_user={"user_id": 1}
            )
        self.assertEqual(ctx.exception.status_code, 403)

    @patch("api.v2.billing.schema.init_schema")
    @patch("api.v2.billing.get_connection")
    def test_record_usage_event_success(self, mock_conn, _mock_schema):
        from api.v2.billing import record_usage_event, UsageEventCreate

        conn = _MockConn()
        conn._cursor.fetchone.side_effect = [
            {"email": "free@example.com"},
            {"used": 10},
        ]
        conn._cursor.fetchall.return_value = []
        conn._cursor.lastrowid = 123
        mock_conn.return_value = conn

        body = UsageEventCreate(endpoint="/api/v2/opportunities", units=5)
        result = record_usage_event(body=body, current_user={"user_id": 1})
        self.assertEqual(result["event_id"], 123)
        self.assertEqual(result["used"], 15)

    @patch("api.v2.billing.schema.init_schema")
    @patch("api.v2.billing.get_connection")
    def test_record_usage_event_quota_exceeded(self, mock_conn, _mock_schema):
        from api.v2.billing import record_usage_event, UsageEventCreate

        conn = _MockConn()
        conn._cursor.fetchone.side_effect = [
            {"email": "free@example.com"},
            {"used": 999},
        ]
        conn._cursor.fetchall.return_value = []
        mock_conn.return_value = conn

        body = UsageEventCreate(endpoint="/api/v2/opportunities", units=10)
        with self.assertRaises(HTTPException) as ctx:
            record_usage_event(body=body, current_user={"user_id": 1})
        self.assertEqual(ctx.exception.status_code, 429)

    @patch("api.v2.billing.schema.init_schema")
    @patch("api.v2.billing.get_connection")
    def test_get_quota(self, mock_conn, _mock_schema):
        from api.v2.billing import get_quota

        conn = _MockConn()
        conn._cursor.fetchone.side_effect = [
            {"email": "free@example.com"},
            {"used": 100},
        ]
        conn._cursor.fetchall.return_value = []
        mock_conn.return_value = conn

        result = get_quota(current_user={"user_id": 1})
        self.assertEqual(result["tier"], "free")
        self.assertEqual(result["used"], 100)
        self.assertEqual(result["quota"], 1000)

    @patch("api.v2.billing.schema.init_schema")
    @patch("api.v2.billing.get_connection")
    def test_cancel_subscription(self, mock_conn, _mock_schema):
        from api.v2.billing import cancel_subscription, SubscriptionCancelRequest

        conn = _MockConn()
        conn._cursor.fetchone.return_value = {"email": "pro@example.com"}
        conn._cursor.rowcount = 1
        conn._cursor.fetchall.return_value = []
        mock_conn.return_value = conn

        result = cancel_subscription(
            body=SubscriptionCancelRequest(reason="No longer needed"),
            current_user={"user_id": 1},
        )
        self.assertEqual(result["status"], "canceled")
        self.assertEqual(result["revoked_licenses"], 1)

    @patch("api.v2.billing.generate_license", return_value="PRO-ABCD-EFGH-IJKL")
    @patch("api.v2.billing.schema.init_schema")
    @patch("api.v2.billing.get_connection")
    def test_ingest_stripe_subscription_event_completed(
        self, mock_conn, _mock_schema, _mock_license
    ):
        from api.v2.billing import ingest_stripe_subscription_event, StripeSubscriptionEvent

        conn = _MockConn()
        conn._cursor.fetchone.side_effect = [
            {"email": "pro@example.com"},
            None,
        ]
        conn._cursor.fetchall.return_value = []
        mock_conn.return_value = conn

        body = StripeSubscriptionEvent(
            stripe_session_id="cs_test_sprint7",
            status="completed",
            tier="pro",
            amount_usd=49.0,
        )
        result = ingest_stripe_subscription_event(body=body, current_user={"user_id": 1})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["license_key"], "PRO-ABCD-EFGH-IJKL")


if __name__ == "__main__":
    unittest.main()

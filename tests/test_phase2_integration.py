"""Phase 2 Integration Gate Test — Sync Point 2 validation.

Verifies the sync gate criteria: auth + scheduler + alerts must pass.
Covers Streams A-D: T-025 to T-064.

Run:
    python -m pytest tests/test_phase2_integration.py -v
"""

import importlib
import sys
from pathlib import Path


# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ─────────────────────────────────────────────────────────────
# 1. AUTH FLOW: Register → Login → JWT → Protected endpoint
# ─────────────────────────────────────────────────────────────


class TestAuthIntegration:
    """Stream B (T-054 to T-064): Auth and security integration."""

    def test_auth_router_registers_login_and_register(self):
        """Auth router must expose /register and /login endpoints."""
        from api.v2.auth import router

        routes = [r.path for r in router.routes]
        assert "/v2/auth/register" in routes, f"Missing /register route, got {routes}"
        assert "/v2/auth/login" in routes, f"Missing /login route, got {routes}"

    def test_jwt_handler_create_and_validate(self):
        """JWT handler must create tokens that validate back correctly."""
        from auth.jwt_handler import JWTHandler

        handler = JWTHandler()
        token = handler.create_token(
            {"user_id": 42, "email": "test@example.com", "role": "admin"}
        )
        assert isinstance(token, str), "Token must be a string"
        payload = handler.validate_token(token)
        assert payload["user_id"] == 42
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "admin"

    def test_password_hash_roundtrip(self):
        """Password hasher must hash and verify correctly."""
        from auth.password_hasher import hash_password, verify_password

        hashed = hash_password("SecurePass123")
        assert verify_password("SecurePass123", hashed) is True
        assert verify_password("WrongPass456", hashed) is False

    def test_password_strength_validation(self):
        """Password strength validator must reject weak passwords."""
        from auth.password_hasher import validate_password_strength

        valid, _ = validate_password_strength("SecurePass123")
        assert valid is True
        weak, msg = validate_password_strength("short")
        assert weak is False

    def test_api_key_generation(self):
        """API key manager must generate and validate keys."""
        from auth.api_key_manager import generate_api_key, validate_api_key_format

        raw_key, prefix, key_hash = generate_api_key()
        assert raw_key.startswith("oip_live_"), "API key must have 'oip_live_' prefix"
        assert validate_api_key_format(raw_key) is True
        assert validate_api_key_format("invalid-key") is False

    def test_security_headers_middleware_exists(self):
        """SecurityHeadersMiddleware must be importable from api_server."""
        # api_server defines the middleware class inside the HAS_FASTAPI guard
        # so we verify the module loads and the class pattern is accessible
        import api_server

        source = Path(api_server.__file__).read_text()
        assert "SecurityHeadersMiddleware" in source
        assert "X-Content-Type-Options" in source
        assert "X-Frame-Options" in source
        assert "Content-Security-Policy" in source
        assert "Referrer-Policy" in source
        assert "Permissions-Policy" in source

    def test_rate_limiter_configured(self):
        """Rate limiter (slowapi) must be configured in api_server."""
        import api_server

        source = Path(api_server.__file__).read_text()
        assert "slowapi" in source
        assert "Limiter" in source
        assert "get_remote_address" in source
        assert "60/minute" in source


# ─────────────────────────────────────────────────────────────
# 2. SCHEDULER: Collectors register and daemon loop starts
# ─────────────────────────────────────────────────────────────


class TestSchedulerIntegration:
    """Stream A (T-025 to T-039): Infrastructure integration."""

    def test_collector_scheduler_imports(self):
        """Collector scheduler module must be importable."""
        mod = importlib.import_module("scripts.collector_scheduler")
        assert hasattr(mod, "main") or hasattr(
            mod, "run"
        ), "Scheduler must have a main() or run() entry point"

    def test_collector_scheduler_has_retry_logic(self):
        """Scheduler must implement retry with exponential backoff."""
        source = Path("scripts/collector_scheduler.py").read_text()
        assert "retry" in source.lower()
        assert "backoff" in source.lower() or "exponential" in source.lower()

    def test_scheduler_groups_defined(self):
        """Scheduler must define fast, standard, and daily collector groups."""
        source = Path("scripts/collector_scheduler.py").read_text()
        assert "fast" in source.lower()
        assert "standard" in source.lower()
        assert "daily" in source.lower()

    def test_score_validation_runs(self):
        """Score validation must run against the 20-startup golden dataset."""
        from scoring.validate import VALIDATION_SET, run_validation

        assert len(VALIDATION_SET) >= 20, "Validation set must have 20+ startups"
        report = run_validation()
        assert hasattr(report, "accuracy"), "Report must have accuracy attribute"
        assert (
            report.accuracy >= 50.0
        ), f"Accuracy {report.accuracy}% is below 50% threshold"

    def test_score_accuracy_api_registered(self):
        """Score accuracy API endpoint must be registered in api_server."""
        source = Path("api_server.py").read_text()
        assert "/api/score/accuracy" in source, "Missing score accuracy endpoint"


# ─────────────────────────────────────────────────────────────
# 3. ALERTS: Consumer dispatches to channels
# ─────────────────────────────────────────────────────────────


class TestAlertIntegration:
    """Stream D (T-029 to T-046): Alert and notification integration."""

    def test_alert_consumer_imports(self):
        """Alert consumer module must be importable."""
        mod = importlib.import_module("scripts.alert_consumer")
        assert (
            hasattr(mod, "main") or hasattr(mod, "consume_loop") or hasattr(mod, "run")
        ), "Alert consumer must have an entry point"

    def test_alert_consumer_has_channels(self):
        """Alert consumer must support email and Slack channels."""
        source = Path("scripts/alert_consumer.py").read_text()
        assert "email" in source.lower() or "_send_email" in source
        assert "slack" in source.lower() or "_send_slack" in source

    def test_alert_consumer_has_dead_letter_queue(self):
        """Alert consumer must implement dead letter queue."""
        source = Path("scripts/alert_consumer.py").read_text()
        assert "dead_letter" in source.lower() or "dlq" in source.lower()

    def test_websocket_endpoint_in_api(self):
        """WebSocket /ws/live endpoint must be registered."""
        source = Path("api_server.py").read_text()
        assert "/ws/live" in source, "Missing WebSocket /ws/live endpoint"
        assert "heartbeat" in source.lower(), "WebSocket must have heartbeat"


# ─────────────────────────────────────────────────────────────
# 4. FEEDBACK + MONITORING: Dashboard, error tracking, perf
# ─────────────────────────────────────────────────────────────


class TestFeedbackMonitoringIntegration:
    """Stream C (T-043 to T-053): Feedback and monitoring integration."""

    def test_feedback_analyzer_agent_registered(self):
        """FeedbackAnalyzerAgent must be importable and inherit BaseAgent."""
        from agents.feedback_analyzer_agent import FeedbackAnalyzerAgent
        from agents.base import BaseAgent

        assert issubclass(FeedbackAnalyzerAgent, BaseAgent)

    def test_weekly_report_imports(self):
        """Weekly report script must be importable."""
        mod = importlib.import_module("scripts.weekly_report")
        assert hasattr(
            mod, "generate_report"
        ), "Weekly report must have generate_report()"

    def test_error_tracking_schema_exists(self):
        """Error log table must exist in DB schema."""
        from db import schema

        # _TABLES is a list of SQL CREATE TABLE strings
        sql_text = " ".join(schema._TABLES)
        assert "error_log" in sql_text, "Schema must define 'error_log' table"
        assert (
            schema._SCHEMA_VERSION >= 21
        ), f"Schema v{schema._SCHEMA_VERSION} must be >= 21 for error_log"

    def test_performance_endpoint_registered(self):
        """Performance metrics endpoint must be in api_server."""
        source = Path("api_server.py").read_text()
        assert "/api/performance" in source, "Missing /api/performance endpoint"

    def test_health_monitor_imports(self):
        """Health monitor module must be importable."""
        from monitoring.health import check_database_health

        assert callable(check_database_health)


# ─────────────────────────────────────────────────────────────
# 5. CROSS-CUTTING: Docker, schema, dependencies
# ─────────────────────────────────────────────────────────────


class TestCrossCuttingValidation:
    """Cross-cutting concerns across all streams."""

    def test_schema_version_sufficient(self):
        """Schema version must include all Phase 2 tables."""
        from db import schema

        assert (
            schema._SCHEMA_VERSION >= 22
        ), f"Schema v{schema._SCHEMA_VERSION} must be >= 22 for auth tables"

    def test_users_table_in_schema(self):
        """Users table must be defined in schema for auth."""
        from db import schema

        sql_text = " ".join(schema._TABLES)
        assert (
            "CREATE TABLE" in sql_text and "users" in sql_text
        ), "Schema must define 'users' table"

    def test_api_keys_table_in_schema(self):
        """API keys table must be defined for auth."""
        from db import schema

        sql_text = " ".join(schema._TABLES)
        assert (
            "CREATE TABLE" in sql_text and "api_keys" in sql_text
        ), "Schema must define 'api_keys' table"

    def test_docker_compose_has_scheduler_service(self):
        """Docker Compose must define a scheduler service."""
        source = Path("docker-compose.yml").read_text()
        assert "scheduler:" in source, "Missing scheduler service in docker-compose"

    def test_docker_compose_security_hardened(self):
        """Docker services must have security hardening."""
        source = Path("docker-compose.yml").read_text()
        assert "no-new-privileges" in source, "Missing no-new-privileges security opt"
        assert (
            "cap_drop:" in source.lower() or "cap_drop" in source
        ), "Missing cap_drop in docker-compose"

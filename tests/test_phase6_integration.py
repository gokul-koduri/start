"""Phase 6 integration tests — verify all components exist."""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPhase6Integration(unittest.TestCase):
    """Test that all Phase 6 components are present."""

    def test_auth_package_exists(self):
        """Test auth package exists."""
        self.assertTrue((Path(__file__).parent.parent / "auth" / "__init__.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "auth" / "jwt_handler.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "auth" / "rbac.py").exists())

    def test_tenant_manager_exists(self):
        """Test tenant manager exists."""
        self.assertTrue((Path(__file__).parent.parent / "auth" / "tenant_manager.py").exists())

    def test_api_v2_exists(self):
        """Test API v2 routers exist."""
        self.assertTrue((Path(__file__).parent.parent / "api" / "v2" / "__init__.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "api" / "v2" / "opportunities.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "api" / "v2" / "signals.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "api" / "v2" / "webhooks.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "api" / "v2" / "export.py").exists())

    def test_webhooks_package_exists(self):
        """Test webhooks package exists."""
        self.assertTrue((Path(__file__).parent.parent / "webhooks" / "__init__.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "webhooks" / "dispatcher.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "webhooks" / "templates.py").exists())

    def test_monitoring_package_exists(self):
        """Test monitoring package exists."""
        self.assertTrue((Path(__file__).parent.parent / "monitoring" / "__init__.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "monitoring" / "metrics.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "monitoring" / "health.py").exists())

    def test_phase6_agents_exist(self):
        """Test Phase 6 agents exist."""
        self.assertTrue((Path(__file__).parent.parent / "agents" / "slack_integration_agent.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "agents" / "email_digest_agent.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "agents" / "export_agent.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "agents" / "feed_generator_agent.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "agents" / "data_quality_agent.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "agents" / "pipeline_health_agent.py").exists())
        self.assertTrue((Path(__file__).parent.parent / "agents" / "cost_tracking_agent.py").exists())

    def test_agents_registered(self):
        """Test agents are registered in orchestrator."""
        from agents.orchestrator import AGENT_REGISTRY

        # Check that Phase 6 agents are not in initial registry (lazy-loaded)
        self.assertNotIn("slack_integration", AGENT_REGISTRY)
        self.assertNotIn("email_digest", AGENT_REGISTRY)

        # Check lazy import works
        from agents.orchestrator import _get_agent_class
        agent_class = _get_agent_class("slack_integration")
        self.assertEqual(agent_class.__name__, "SlackIntegrationAgent")

        # After lazy import, should be in registry
        self.assertIn("slack_integration", AGENT_REGISTRY)

    def test_schema_version_16(self):
        """Test schema version is at least 16."""
        from pathlib import Path
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()
        self.assertTrue(
            "_SCHEMA_VERSION = 16" in schema_content or "_SCHEMA_VERSION = 17" in schema_content,
            "Schema version should be >= 16"
        )

    def test_new_tables_in_schema(self):
        """Test new tables are in schema."""
        from pathlib import Path
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()

        self.assertIn("CREATE TABLE IF NOT EXISTS tenants", schema_content)
        self.assertIn("CREATE TABLE IF NOT EXISTS api_webhooks", schema_content)


if __name__ == "__main__":
    unittest.main()

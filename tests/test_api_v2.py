"""Tests for API v2 routers."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAPIV2Opportunities(unittest.TestCase):
    """Test opportunities v2 router."""

    def setUp(self):
        """Set up test fixtures."""
        from api.v2.opportunities import router
        self.router = router

    def test_router_exists(self):
        """Test router is created."""
        self.assertIsNotNone(self.router)
        self.assertEqual(self.router.prefix, "/v2/opportunities")


class TestAPIV2Signals(unittest.TestCase):
    """Test signals v2 router."""

    def setUp(self):
        """Set up test fixtures."""
        from api.v2.signals import router
        self.router = router

    def test_router_exists(self):
        """Test router is created."""
        self.assertIsNotNone(self.router)
        self.assertEqual(self.router.prefix, "/v2/signals")


class TestAPIV2Webhooks(unittest.TestCase):
    """Test webhooks v2 router."""

    def setUp(self):
        """Set up test fixtures."""
        from api.v2.webhooks import router
        self.router = router

    def test_router_exists(self):
        """Test router is created."""
        self.assertIsNotNone(self.router)
        self.assertEqual(self.router.prefix, "/v2/webhooks")


class TestAPIV2Export(unittest.TestCase):
    """Test export v2 router."""

    def setUp(self):
        """Set up test fixtures."""
        from api.v2.export import router
        self.router = router

    def test_router_exists(self):
        """Test router is created."""
        self.assertIsNotNone(self.router)
        self.assertEqual(self.router.prefix, "/v2/export")


if __name__ == "__main__":
    unittest.main()

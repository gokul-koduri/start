"""Phase 4 Integration Tests - verify all collectors are properly integrated."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPhase4CollectorsImportable:
    """Test that all Phase 4 collectors can be imported."""

    def test_import_regulatory_collector(self):
        """Test regulatory collector is importable."""
        from collectors.regulatory_collector import RegulatoryCollector
        assert RegulatoryCollector is not None

    def test_import_newsletter_collector(self):
        """Test newsletter collector is importable."""
        from collectors.newsletter_collector import NewsletterCollector
        assert NewsletterCollector is not None

    def test_import_arxiv_collector(self):
        """Test arXiv collector is importable."""
        from collectors.arxiv_collector import ArxivCollector
        assert ArxivCollector is not None

    def test_import_producthunt_collector(self):
        """Test Product Hunt collector is importable."""
        from collectors.producthunt_collector import ProductHuntCollector
        assert ProductHuntCollector is not None

    def test_import_website_monitor_collector(self):
        """Test Website Monitor collector is importable."""
        from collectors.website_monitor_collector import WebsiteMonitorCollector
        assert WebsiteMonitorCollector is not None

    def test_import_twitter_collector(self):
        """Test Twitter collector is importable."""
        from collectors.twitter_collector import TwitterCollector
        assert TwitterCollector is not None

    def test_import_stackoverflow_collector(self):
        """Test Stack Overflow collector is importable."""
        from collectors.stackoverflow_collector import StackOverflowCollector
        assert StackOverflowCollector is not None

    def test_import_npm_pypi_collector(self):
        """Test NPM/PyPI collector is importable."""
        from collectors.npm_pypi_collector import NPMPyPICollector
        assert NPMPyPICollector is not None


class TestPhase4CollectorsRegistered:
    """Test that all Phase 4 collectors are registered in agents/collection.py."""

    def test_all_collectors_dict(self):
        """Test ALL_COLLECTORS dict exists and has expected collectors."""
        from agents.collection_agent import ALL_COLLECTORS

        # Expected Phase 4 collectors
        phase4_collectors = [
            "arxiv",
            "producthunt",
            "website_monitor",
            "twitter",
            "stackoverflow",
            "npm_pypi",
            "regulatory",
            "newsletter",
        ]

        for name in phase4_collectors:
            assert name in ALL_COLLECTORS, f"Collector '{name}' not in ALL_COLLECTORS"

    def test_regulatory_registered(self):
        """Test regulatory collector is registered."""
        from agents.collection_agent import ALL_COLLECTORS
        assert "regulatory" in ALL_COLLECTORS
        assert ALL_COLLECTORS["regulatory"] is not None

    def test_newsletter_registered(self):
        """Test newsletter collector is registered."""
        from agents.collection_agent import ALL_COLLECTORS
        assert "newsletter" in ALL_COLLECTORS
        assert ALL_COLLECTORS["newsletter"] is not None


class TestPhase4CollectorInterface:
    """Test that all Phase 4 collectors implement BaseCollector interface."""

    def test_regulatory_has_name_property(self):
        """Test regulatory collector has name property."""
        from collectors.regulatory_collector import RegulatoryCollector
        c = RegulatoryCollector(config={})
        assert hasattr(c, 'name')
        assert c.name == "regulatory"

    def test_regulatory_has_collect_method(self):
        """Test regulatory collector has collect method."""
        from collectors.regulatory_collector import RegulatoryCollector
        c = RegulatoryCollector(config={})
        assert hasattr(c, 'collect')
        assert callable(c.collect)

    def test_newsletter_has_name_property(self):
        """Test newsletter collector has name property."""
        from collectors.newsletter_collector import NewsletterCollector
        c = NewsletterCollector(config={})
        assert hasattr(c, 'name')
        assert c.name == "newsletter"

    def test_newsletter_has_collect_method(self):
        """Test newsletter collector has collect method."""
        from collectors.newsletter_collector import NewsletterCollector
        c = NewsletterCollector(config={})
        assert hasattr(c, 'collect')
        assert callable(c.collect)

    def test_arxiv_has_name_property(self):
        """Test arXiv collector has name property."""
        from collectors.arxiv_collector import ArxivCollector
        c = ArxivCollector(config={})
        assert hasattr(c, 'name')
        assert c.name == "arxiv"

    def test_producthunt_has_name_property(self):
        """Test Product Hunt collector has name property."""
        from collectors.producthunt_collector import ProductHuntCollector
        c = ProductHuntCollector(config={})
        assert hasattr(c, 'name')
        assert c.name == "producthunt"


class TestPhase4ConfigLoading:
    """Test that config loading works for all Phase 4 collectors."""

    def test_regulatory_config_exists(self):
        """Test regulatory config exists in settings."""
        from config import load_config
        config = load_config()
        assert "regulatory" in config
        assert "enabled" in config["regulatory"]

    def test_newsletter_config_exists(self):
        """Test newsletter config exists in settings."""
        from config import load_config
        config = load_config()
        assert "newsletter" in config
        assert "enabled" in config["newsletter"]

    def test_arxiv_config_exists(self):
        """Test arXiv config exists in settings."""
        from config import load_config
        config = load_config()
        assert "arxiv" in config
        assert "enabled" in config["arxiv"]

    def test_producthunt_config_exists(self):
        """Test Product Hunt config exists in settings."""
        from config import load_config
        config = load_config()
        assert "producthunt" in config
        assert "enabled" in config["producthunt"]

    def test_stackoverflow_config_exists(self):
        """Test Stack Overflow config exists in settings."""
        from config import load_config
        config = load_config()
        assert "stackoverflow" in config
        assert "enabled" in config["stackoverflow"]

    def test_npm_pypi_config_exists(self):
        """Test NPM/PyPI config exists in settings."""
        from config import load_config
        config = load_config()
        assert "npm_pypi" in config
        assert "enabled" in config["npm_pypi"]


class TestPhase4SchemaTables:
    """Test that schema tables exist for all Phase 4 collectors."""

    def test_regulatory_filings_table_exists(self):
        """Test regulatory_filings table is in schema."""
        # Read schema file directly to avoid mock issues
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()
        assert "regulatory_filings" in schema_content
        assert "filing_id" in schema_content
        assert "filing_type" in schema_content

    def test_newsletter_articles_table_exists(self):
        """Test newsletter_articles table is in schema."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()
        assert "newsletter_articles" in schema_content
        assert "title" in schema_content
        assert "source_name" in schema_content

    def test_arxiv_papers_table_exists(self):
        """Test arxiv_papers table is in schema."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()
        assert "arxiv_papers" in schema_content
        assert "arxiv_id" in schema_content

    def test_producthunt_launches_table_exists(self):
        """Test producthunt_launches table is in schema."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()
        assert "producthunt_launches" in schema_content
        assert "ph_id" in schema_content

    def test_website_monitor_snapshots_table_exists(self):
        """Test website_monitor_snapshots table is in schema."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()
        assert "website_monitor_snapshots" in schema_content
        assert "url" in schema_content

    def test_stackoverflow_posts_table_exists(self):
        """Test stackoverflow_posts table is in schema."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()
        assert "stackoverflow_posts" in schema_content
        assert "post_id" in schema_content

    def test_package_trends_table_exists(self):
        """Test package_trends table is in schema."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()
        assert "package_trends" in schema_content
        assert "package_name" in schema_content

    def test_schema_version_is_14(self):
        """Test schema version is at least 14 (Phase 4 or later)."""
        schema_path = Path(__file__).parent.parent / "db" / "schema.py"
        schema_content = schema_path.read_text()
        # Allow version 14, 15, or 16 (Phase 6 bumped it)
        assert "_SCHEMA_VERSION = 14" in schema_content or "_SCHEMA_VERSION = 15" in schema_content or "_SCHEMA_VERSION = 16" in schema_content or "_SCHEMA_VERSION = 17" in schema_content or "_SCHEMA_VERSION = 18" in schema_content or "_SCHEMA_VERSION = 19" in schema_content or "_SCHEMA_VERSION = 20" in schema_content or "_SCHEMA_VERSION = 21" in schema_content

"""SQLite schema definitions for the Startup Research database."""

import sqlite3
import logging

_logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 1

_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS failed_startups (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        name                TEXT NOT NULL,
        sector              TEXT,
        manufacturing_sub_sector TEXT,
        country             TEXT,
        region              TEXT,
        funding_raised_usd  REAL,
        funding_description TEXT,
        peak_valuation_usd  REAL,
        year_founded        INTEGER,
        year_shutdown       INTEGER NOT NULL,
        shutdown_date       TEXT,
        failure_reason      TEXT NOT NULL,
        failure_category    TEXT,
        notable             INTEGER DEFAULT 0,
        source              TEXT NOT NULL,
        source_url          TEXT,
        collected_at        TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at          TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(name, region)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS failure_reasons_taxonomy (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        reason              TEXT NOT NULL UNIQUE,
        percentage          REAL,
        rank_order          INTEGER,
        source              TEXT DEFAULT 'cb_insights',
        collected_at        TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS failure_idea_patterns (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        idea_category       TEXT NOT NULL,
        example_startups    TEXT,
        why_failed          TEXT NOT NULL,
        market_reality      TEXT NOT NULL,
        source              TEXT,
        collected_at        TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS manufacturing_failure_categories (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        failure_category    TEXT NOT NULL,
        description         TEXT NOT NULL,
        estimated_pct       REAL,
        example_startups    TEXT,
        source              TEXT,
        collected_at        TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS bls_survival_rates (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        naics_code          TEXT NOT NULL,
        industry_name       TEXT NOT NULL,
        year                INTEGER NOT NULL,
        quarter             INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
        age_1_yr_survival   REAL,
        age_2_yr_survival   REAL,
        age_3_yr_survival   REAL,
        age_5_yr_survival   REAL,
        establishment_count INTEGER,
        source_url          TEXT,
        collected_at        TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(naics_code, year, quarter)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS news_articles (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        title               TEXT NOT NULL,
        url                 TEXT NOT NULL UNIQUE,
        source_name         TEXT NOT NULL,
        source_feed         TEXT NOT NULL,
        published_at        TEXT,
        summary             TEXT,
        is_manufacturing    INTEGER DEFAULT 0,
        mentions_failure    INTEGER DEFAULT 0,
        startup_name_extracted TEXT,
        collected_at        TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS reshoring_data (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        report_year         INTEGER NOT NULL,
        data_year           INTEGER NOT NULL,
        industry            TEXT,
        jobs_created        INTEGER,
        jobs_announced      INTEGER,
        project_count       INTEGER,
        success_rate_pct    REAL,
        cost_reduction_pct  REAL,
        country_of_origin   TEXT,
        notes               TEXT,
        source_report       TEXT,
        source_url          TEXT,
        collected_at        TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS reshoring_summary_stats (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        stat_year           INTEGER NOT NULL,
        total_jobs          INTEGER,
        total_reshoring_jobs  INTEGER,
        total_fdi_jobs       INTEGER,
        success_rate_pct     REAL,
        key_policy TEXT,
        headline              TEXT,
        source                TEXT,
        collected_at          TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(stat_year)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS revival_industries (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        industry            TEXT NOT NULL UNIQUE,
        died_period         TEXT,
        why_returning       TEXT NOT NULL,
        closed_site_types   TEXT,
        market_fit          TEXT NOT NULL,
        key_investors       TEXT,
        market_size_2030    TEXT,
        collected_at        TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS geographic_hotspots (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        region              TEXT NOT NULL,
        closed_facility_types TEXT NOT NULL,
        revival_potential   TEXT NOT NULL,
        collected_at        TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS collection_runs (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        collector_name      TEXT NOT NULL,
        started_at          TEXT NOT NULL,
        completed_at        TEXT,
        status              TEXT NOT NULL CHECK (status IN ('running', 'success', 'partial', 'failed')),
        records_collected   INTEGER DEFAULT 0,
        records_deduped     INTEGER DEFAULT 0,
        error_message       TEXT,
        parameters          TEXT
    );
    """,
]

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_startups_region ON failed_startups(region);",
    "CREATE INDEX IF NOT EXISTS idx_startups_sector ON failed_startups(sector);",
    "CREATE INDEX IF NOT EXISTS idx_startups_manufacturing ON failed_startups(manufacturing_sub_sector) WHERE manufacturing_sub_sector IS NOT NULL;",
    "CREATE INDEX IF NOT EXISTS idx_startups_shutdown_year ON failed_startups(year_shutdown);",
    "CREATE INDEX IF NOT EXISTS idx_startups_failure_category ON failed_startups(failure_category);",
    "CREATE INDEX IF NOT EXISTS idx_startups_source ON failed_startups(source);",
    "CREATE INDEX IF NOT EXISTS idx_news_manufacturing ON news_articles(is_manufacturing) WHERE is_manufacturing = 1;",
    "CREATE INDEX IF NOT EXISTS idx_news_failure ON news_articles(mentions_failure) WHERE mentions_failure = 1;",
    "CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at);",
    "CREATE INDEX IF NOT EXISTS idx_bls_industry_year ON bls_survival_rates(naics_code, year);",
    "CREATE INDEX IF NOT EXISTS idx_reshoring_year ON reshoring_data(data_year);",
    "CREATE INDEX IF NOT EXISTS idx_collection_runs_collector ON collection_runs(collector_name, started_at DESC);",
]


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes if they don't exist."""
    for table_sql in _TABLES:
        conn.execute(table_sql)
    for index_sql in _INDEXES:
        conn.execute(index_sql)
    conn.commit()
    _logger.info("Database schema initialized (version %d)", _SCHEMA_VERSION)


def get_schema_version() -> int:
    return _SCHEMA_VERSION

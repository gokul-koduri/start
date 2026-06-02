"""MySQL schema definitions for the Startup Research database."""

import logging

_logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 5

_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS failed_startups (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        name                VARCHAR(255) NOT NULL,
        sector              VARCHAR(255),
        manufacturing_sub_sector TEXT,
        country             VARCHAR(100),
        region              VARCHAR(100),
        funding_raised_usd  DOUBLE,
        funding_description TEXT,
        peak_valuation_usd  DOUBLE,
        year_founded        INT,
        year_shutdown       INT NOT NULL,
        shutdown_date       VARCHAR(50),
        failure_reason      TEXT NOT NULL,
        failure_category    VARCHAR(100),
        notable             INT DEFAULT 0,
        source              VARCHAR(100) NOT NULL,
        source_url          TEXT,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_name_region (name, region)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS failure_reasons_taxonomy (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        reason              VARCHAR(255) NOT NULL UNIQUE,
        percentage          DOUBLE,
        rank_order          INT,
        source              VARCHAR(100) DEFAULT 'cb_insights',
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS failure_idea_patterns (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        idea_category       VARCHAR(255) NOT NULL,
        example_startups    TEXT,
        why_failed          TEXT NOT NULL,
        market_reality      TEXT NOT NULL,
        source              VARCHAR(255),
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS manufacturing_failure_categories (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        failure_category    VARCHAR(255) NOT NULL,
        description         TEXT NOT NULL,
        estimated_pct       DOUBLE,
        example_startups    TEXT,
        source              VARCHAR(255),
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS bls_survival_rates (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        naics_code          VARCHAR(20) NOT NULL,
        industry_name       VARCHAR(255) NOT NULL,
        year                INT NOT NULL,
        quarter             INT,
        quarter_key         INT GENERATED ALWAYS AS (COALESCE(quarter, -1)) STORED,
        age_1_yr_survival   DOUBLE,
        age_2_yr_survival   DOUBLE,
        age_3_yr_survival   DOUBLE,
        age_5_yr_survival   DOUBLE,
        establishment_count INT,
        source_url          TEXT,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_bls_naics_year_quarter (naics_code, year, quarter_key),
        CHECK (quarter IS NULL OR quarter BETWEEN 1 AND 4)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS news_articles (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        title               TEXT NOT NULL,
        url                 VARCHAR(2048) NOT NULL,
        source_name         VARCHAR(255) NOT NULL,
        source_feed         VARCHAR(100) NOT NULL,
        published_at        TEXT,
        summary             TEXT,
        is_manufacturing    INT DEFAULT 0,
        mentions_failure    INT DEFAULT 0,
        startup_name_extracted TEXT,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_news_url (url(767))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS reshoring_data (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        report_year         INT NOT NULL,
        data_year           INT NOT NULL,
        industry            VARCHAR(255),
        jobs_created        INT,
        jobs_announced      INT,
        project_count       INT,
        success_rate_pct    DOUBLE,
        cost_reduction_pct  DOUBLE,
        country_of_origin   VARCHAR(100),
        notes               TEXT,
        source_report       VARCHAR(255),
        source_url          TEXT,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS reshoring_summary_stats (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        stat_year           INT NOT NULL,
        total_jobs          INT,
        total_reshoring_jobs  INT,
        total_fdi_jobs       INT,
        success_rate_pct     DOUBLE,
        key_policy TEXT,
        headline              TEXT,
        source                VARCHAR(255),
        collected_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_stat_year (stat_year)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS revival_industries (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        industry            VARCHAR(255) NOT NULL UNIQUE,
        died_period         TEXT,
        why_returning       TEXT NOT NULL,
        closed_site_types   TEXT,
        market_fit          TEXT NOT NULL,
        key_investors       TEXT,
        market_size_2030    TEXT,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS geographic_hotspots (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        region              VARCHAR(255) NOT NULL,
        closed_facility_types TEXT NOT NULL,
        revival_potential   TEXT NOT NULL,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS collection_runs (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        collector_name      VARCHAR(255) NOT NULL,
        started_at          VARCHAR(50) NOT NULL,
        completed_at        VARCHAR(50),
        status              ENUM('running','success','partial','failed') NOT NULL,
        records_collected   INT DEFAULT 0,
        records_deduped     INT DEFAULT 0,
        error_message       TEXT,
        parameters          TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_runs (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        pipeline_name       VARCHAR(255) NOT NULL,
        agent_name          VARCHAR(255) NOT NULL,
        started_at          VARCHAR(50) NOT NULL,
        completed_at        VARCHAR(50),
        status              ENUM('running','success','partial','failed') NOT NULL,
        records_affected    INT DEFAULT 0,
        error_message       TEXT,
        result_data         TEXT,
        trigger_type        VARCHAR(50) DEFAULT 'manual'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS discovered_sources (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        url                 VARCHAR(2048) NOT NULL,
        source_type         VARCHAR(100),
        description         TEXT,
        relevance_score     DOUBLE DEFAULT 0.0,
        content_sample      TEXT,
        validation_status   VARCHAR(50) DEFAULT 'pending',
        last_validated_at   TEXT,
        discovered_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        search_query        TEXT,
        metadata            TEXT,
        UNIQUE KEY uq_discovered_url (url(767))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_failure_patterns (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_type       VARCHAR(255) NOT NULL,
        insights_json       TEXT NOT NULL,
        analyzed_at         VARCHAR(50) NOT NULL,
        record_count        INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_survival_trends (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_type       VARCHAR(255) NOT NULL,
        insights_json       TEXT NOT NULL,
        analyzed_at         VARCHAR(50) NOT NULL,
        record_count        INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_revival_opportunities (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_type       VARCHAR(255) NOT NULL,
        insights_json       TEXT NOT NULL,
        analyzed_at         VARCHAR(50) NOT NULL,
        record_count        INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_geographic_strategy (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_type       VARCHAR(255) NOT NULL,
        insights_json       TEXT NOT NULL,
        analyzed_at         VARCHAR(50) NOT NULL,
        record_count        INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_news_intelligence (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_type       VARCHAR(255) NOT NULL,
        insights_json       TEXT NOT NULL,
        analyzed_at         VARCHAR(50) NOT NULL,
        record_count        INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_opportunity_pipeline (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_type       VARCHAR(255) NOT NULL,
        insights_json       TEXT NOT NULL,
        analyzed_at         VARCHAR(50) NOT NULL,
        record_count        INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_whale_investors (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_type       VARCHAR(255) NOT NULL,
        insights_json       TEXT NOT NULL,
        analyzed_at         VARCHAR(50) NOT NULL,
        record_count        INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_global_market_viability (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_type       VARCHAR(255) NOT NULL,
        insights_json       LONGTEXT NOT NULL,
        analyzed_at         VARCHAR(50) NOT NULL,
        record_count        INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
]

_INDEXES = [
    "CREATE INDEX idx_startups_region ON failed_startups(region);",
    "CREATE INDEX idx_startups_sector ON failed_startups(sector);",
    "CREATE INDEX idx_startups_manufacturing ON failed_startups(manufacturing_sub_sector);",
    "CREATE INDEX idx_startups_shutdown_year ON failed_startups(year_shutdown);",
    "CREATE INDEX idx_startups_failure_category ON failed_startups(failure_category);",
    "CREATE INDEX idx_startups_source ON failed_startups(source);",
    "CREATE INDEX idx_news_manufacturing ON news_articles(is_manufacturing);",
    "CREATE INDEX idx_news_failure ON news_articles(mentions_failure);",
    "CREATE INDEX idx_news_published ON news_articles(published_at);",
    "CREATE INDEX idx_bls_industry_year ON bls_survival_rates(naics_code, year);",
    "CREATE INDEX idx_reshoring_year ON reshoring_data(data_year);",
    "CREATE INDEX idx_collection_runs_collector ON collection_runs(collector_name, started_at DESC);",
    "CREATE INDEX idx_agent_runs_pipeline ON agent_runs(pipeline_name, started_at DESC);",
    "CREATE INDEX idx_discovered_sources_status ON discovered_sources(validation_status);",
    "CREATE INDEX idx_whale_investors_type ON analysis_whale_investors(analysis_type);",
    "CREATE INDEX idx_gmv_type ON analysis_global_market_viability(analysis_type);",
]


def init_schema(conn) -> None:
    """Create all tables and indexes if they don't exist."""
    cursor = conn.cursor()
    for table_sql in _TABLES:
        cursor.execute(table_sql)
    for index_sql in _INDEXES:
        try:
            cursor.execute(index_sql)
        except Exception as e:
            _logger.debug("Index creation note: %s", e)
    conn.commit()
    cursor.close()
    _logger.info("Database schema initialized (version %d)", _SCHEMA_VERSION)


def get_schema_version() -> int:
    return _SCHEMA_VERSION

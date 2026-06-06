"""MySQL schema definitions for the Startup Research database."""

import logging

_logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 17

_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS tenants (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        name            VARCHAR(255) NOT NULL,
        slug            VARCHAR(100) NOT NULL UNIQUE,
        config          TEXT COMMENT 'JSON tenant configuration',
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        is_active       TINYINT DEFAULT 1
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS api_webhooks (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        url             VARCHAR(2048) NOT NULL,
        events_json     TEXT NOT NULL COMMENT 'JSON: list of event types',
        headers_json    TEXT COMMENT 'JSON: custom headers',
        active          TINYINT DEFAULT 1,
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
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
        sentiment_score     FLOAT DEFAULT NULL COMMENT '-1.0 (negative) to 1.0 (positive)',
        sentiment_label     VARCHAR(20) DEFAULT NULL COMMENT 'positive, negative, neutral, mixed',
        sentiment_model     VARCHAR(100) DEFAULT NULL COMMENT 'Which model produced the score',
        sentiment_analyzed_at DATETIME DEFAULT NULL,
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
    """
    CREATE TABLE IF NOT EXISTS llm_pricing (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        provider            VARCHAR(100) NOT NULL,
        model_name          VARCHAR(255) NOT NULL,
        model_id            VARCHAR(255),
        input_price_per_1m  DOUBLE NOT NULL COMMENT 'USD per 1M input tokens',
        output_price_per_1m DOUBLE NOT NULL COMMENT 'USD per 1M output tokens',
        context_window      INT,
        training_data_cutoff VARCHAR(100),
        modality            VARCHAR(100) DEFAULT 'text',
        pricing_tier        VARCHAR(100) DEFAULT 'standard',
        pricing_url         TEXT,
        notes               TEXT,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_pricing_provider_model (provider, model_name, pricing_tier)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS ollama_usage_snapshots (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        snapshot_at         DATETIME NOT NULL COMMENT 'When this snapshot was taken',
        model_name          VARCHAR(255) NOT NULL,
        prompt_tokens       BIGINT DEFAULT 0,
        completion_tokens   BIGINT DEFAULT 0,
        total_tokens        BIGINT DEFAULT 0,
        inference_count     INT DEFAULT 0 COMMENT 'Number of inferences since last snapshot',
        vram_usage_bytes    BIGINT DEFAULT 0,
        cost_equivalence_json TEXT COMMENT 'JSON: estimated costs across providers',
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_snapshot_model_time (model_name, snapshot_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS llm_benchmarks (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        provider            VARCHAR(100) NOT NULL,
        model_name          VARCHAR(255) NOT NULL,
        benchmark_name      VARCHAR(255) NOT NULL COMMENT 'e.g. MMLU, HumanEval, GPQA',
        benchmark_score     DOUBLE COMMENT 'normalized 0-100',
        benchmark_category  VARCHAR(100) COMMENT 'reasoning, coding, math, instruction_following, long_context',
        speed_tokens_per_sec DOUBLE COMMENT 'output speed if available',
        source_url          TEXT,
        benchmarked_at      DATE,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_bench (provider, model_name, benchmark_name, benchmarked_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS llm_portfolio (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        task_category       VARCHAR(255) NOT NULL COMMENT 'code_gen, summarization, analysis, etc.',
        provider            VARCHAR(100) NOT NULL,
        model_name          VARCHAR(255) NOT NULL,
        allocation_pct      DOUBLE NOT NULL COMMENT '0-100, recommended workload share',
        rank_position       INT DEFAULT 0 COMMENT '1=primary, 2=secondary, 3=tertiary',
        composite_score     DOUBLE COMMENT 'weighted: quality*0.4 + cost*0.3 + speed*0.2 + context*0.1',
        quality_score       DOUBLE,
        cost_score          DOUBLE,
        speed_score         DOUBLE,
        context_score       DOUBLE,
        cost_per_1m_tokens  DOUBLE COMMENT 'average input+output cost per 1M tokens',
        recommended_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_portfolio_task (task_category, provider, model_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS llm_price_changes (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        provider            VARCHAR(100) NOT NULL,
        model_name          VARCHAR(255) NOT NULL,
        old_input_price     DOUBLE NOT NULL,
        old_output_price    DOUBLE NOT NULL,
        new_input_price     DOUBLE NOT NULL,
        new_output_price    DOUBLE NOT NULL,
        input_change_pct    DOUBLE,
        output_change_pct   DOUBLE,
        detected_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        alert_generated     INT DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS llm_optimization_alerts (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        alert_type          VARCHAR(100) NOT NULL COMMENT 'price_drop, new_model, better_alternative, portfolio_rebalance',
        title               VARCHAR(500) NOT NULL,
        description         TEXT,
        affected_models     TEXT COMMENT 'JSON: list of model names',
        estimated_savings_pct DOUBLE,
        priority            VARCHAR(20) DEFAULT 'medium' COMMENT 'low, medium, high, critical',
        dismissed           INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS user_licenses (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        license_key         VARCHAR(64) NOT NULL UNIQUE,
        email               VARCHAR(255),
        tier                ENUM('free','pro','enterprise') NOT NULL DEFAULT 'free',
        activated_at        DATETIME,
        expires_at          DATETIME,
        stripe_session_id   VARCHAR(255),
        status              ENUM('active','expired','revoked') DEFAULT 'active',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS subscription_metrics (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        metric_date         DATE NOT NULL,
        free_users          INT DEFAULT 0,
        pro_users           INT DEFAULT 0,
        enterprise_users     INT DEFAULT 0,
        total_page_views    INT DEFAULT 0,
        pro_conversions     INT DEFAULT 0,
        revenue_usd         DOUBLE DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_metric_date (metric_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS kg_entity_types (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        type_name           VARCHAR(50) NOT NULL UNIQUE,
        description         TEXT,
        icon                VARCHAR(10),
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS kg_entities (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        name                VARCHAR(255) NOT NULL,
        normalized_name     VARCHAR(255) NOT NULL,
        entity_type_id      INT NOT NULL,
        attributes_json     TEXT,
        first_seen_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
        mention_count       INT DEFAULT 1,
        UNIQUE KEY uq_entity_type_name (entity_type_id, normalized_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS kg_relationships (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        source_entity_id    INT NOT NULL,
        target_entity_id    INT NOT NULL,
        relationship_type   VARCHAR(100) NOT NULL,
        weight              DOUBLE DEFAULT 1.0,
        source_table        VARCHAR(100),
        source_record_id    INT,
        discovered_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_relationship (source_entity_id, target_entity_id, relationship_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS generated_reports (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        report_type         VARCHAR(100) NOT NULL COMMENT 'weekly_digest, monthly_deep_dive',
        format              VARCHAR(20) NOT NULL COMMENT 'markdown, html',
        file_path           TEXT,
        sent_to             TEXT COMMENT 'JSON: list of email addresses',
        status              ENUM('pending','success','failed') DEFAULT 'pending',
        record_count        INT DEFAULT 0,
        generated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS alert_dispatches (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        alert_id            INT NOT NULL COMMENT 'FK to llm_optimization_alerts.id',
        channel              VARCHAR(50) NOT NULL COMMENT 'email, webhook_slack, webhook_discord, webhook_custom',
        destination          VARCHAR(500),
        dispatch_status     ENUM('pending','sent','failed') DEFAULT 'pending',
        error_message       TEXT,
        dispatched_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS alert_rules (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        rule_name           VARCHAR(255) NOT NULL UNIQUE,
        rule_type           VARCHAR(100) NOT NULL COMMENT 'data_freshness, pipeline_failure, threshold',
        condition_json      TEXT NOT NULL COMMENT 'JSON: thresholds and parameters',
        channel             VARCHAR(50) NOT NULL,
        enabled             INT DEFAULT 1,
        cooldown_minutes    INT DEFAULT 1440 COMMENT 'min minutes between alerts for this rule',
        last_triggered_at   DATETIME,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS payment_events (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        stripe_session_id  VARCHAR(255) NOT NULL UNIQUE,
        customer_email      VARCHAR(255),
        tier                ENUM('free','pro','enterprise') NOT NULL,
        amount_usd          DOUBLE NOT NULL,
        status              ENUM('pending','completed','refunded','failed') DEFAULT 'pending',
        license_key         VARCHAR(64),
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS span_snapshots (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        pipeline_name       VARCHAR(255) NOT NULL,
        agent_name          VARCHAR(255) NOT NULL,
        duration_seconds     DOUBLE DEFAULT 0,
        records_affected    INT DEFAULT 0,
        status              VARCHAR(20) NOT NULL,
        anomaly_detected    INT DEFAULT 0,
        anomaly_type         VARCHAR(50) COMMENT 'slow_run, high_failure, data_drop',
        anomaly_detail       TEXT,
        snapshot_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS startup_risk_scores (
        id                  INT AUTO_INCREMENT PRIMARY KEY,
        startup_id          INT NOT NULL,
        risk_score          FLOAT NOT NULL COMMENT '0.0 (safe) to 1.0 (critical)',
        risk_level          VARCHAR(20) NOT NULL COMMENT 'low, moderate, high, critical',
        factors_json        JSON COMMENT 'Contributing risk factors',
        recommendation      TEXT COMMENT 'Actionable recommendation',
        scored_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        model_name          VARCHAR(255) DEFAULT NULL COMMENT 'Which model produced this score',
        model_version       VARCHAR(50) DEFAULT NULL COMMENT 'Model version/iteration',
        confidence          FLOAT DEFAULT NULL COMMENT 'Model confidence 0.0-1.0',
        UNIQUE KEY uk_startup (startup_id),
        FOREIGN KEY (startup_id) REFERENCES failed_startups(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS ml_models (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        model_name          VARCHAR(255) NOT NULL COMMENT 'e.g. startup_failure_rf',
        model_type          VARCHAR(100) NOT NULL COMMENT 'random_forest, xgboost',
        model_path          VARCHAR(500) COMMENT 'Path to saved joblib file',
        trained_at          DATETIME NOT NULL,
        training_rows       INT DEFAULT 0,
        features_used       TEXT COMMENT 'JSON: list of feature column names',
        accuracy           FLOAT DEFAULT NULL,
        f1_score            FLOAT DEFAULT NULL,
        precision_score     FLOAT DEFAULT NULL,
        recall_score        FLOAT DEFAULT NULL,
        is_active           INT DEFAULT 0 COMMENT '1 = currently used for predictions',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 1: Opportunity Intelligence Platform tables ──
    """
    CREATE TABLE IF NOT EXISTS raw_signals (
        id              BIGINT PRIMARY KEY AUTO_INCREMENT,
        signal_type     VARCHAR(50) NOT NULL COMMENT 'sec_filing, job_posting_spike, github_trend, funding_round, patent_filed, social_buzz, website_change, news_mention',
        source_name     VARCHAR(100) NOT NULL,
        source_url      VARCHAR(2048),
        title           TEXT,
        body_text       LONGTEXT,
        entity_name     VARCHAR(255) COMMENT 'Extracted company/person/technology name',
        published_at    DATETIME,
        collected_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        processed       TINYINT DEFAULT 0 COMMENT '0=pending, 1=enriched, 2=scored',
        UNIQUE KEY uq_signal_source_url (signal_type, source_url(500))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS opportunity_scores (
        id              BIGINT PRIMARY KEY AUTO_INCREMENT,
        entity_name     VARCHAR(255) NOT NULL,
        entity_type     VARCHAR(50) NOT NULL DEFAULT 'company' COMMENT 'company, technology, market',
        composite_score FLOAT NOT NULL COMMENT '0.0-100.0 weighted composite',
        raw_weighted_score FLOAT DEFAULT 0.0,
        signal_count    INT DEFAULT 0,
        signal_types_json TEXT COMMENT 'JSON: which signal types contributed',
        signal_weights_json TEXT COMMENT 'JSON: individual signal weights and contributions',
        freshness_score FLOAT COMMENT 'Average time-decay score 0.0-1.0',
        anomaly_z_score FLOAT COMMENT 'Z-score anomaly detection value',
        anomaly_type    VARCHAR(50) COMMENT 'spike, drop, or NULL',
        trend_direction VARCHAR(10) COMMENT 'rising, falling, stable',
        confidence      FLOAT DEFAULT 1.0 COMMENT 'Signal coverage confidence 0.0-1.0',
        attribution_json TEXT COMMENT 'Full feature attribution JSON',
        scored_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_opp_entity (entity_name, entity_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS signal_events (
        id              BIGINT PRIMARY KEY AUTO_INCREMENT,
        event_type      VARCHAR(100) NOT NULL COMMENT 'funding_round, hiring_spike, product_launch, patent_filed, competitor_entry, distress_signal',
        entity_name     VARCHAR(255) NOT NULL,
        entity_type     VARCHAR(50) NOT NULL,
        event_data_json LONGTEXT COMMENT 'JSON: full event payload',
        source_signal_id BIGINT,
        correlation_key VARCHAR(255) COMMENT 'For pattern matching across signals',
        score_boost     FLOAT DEFAULT 0.0 COMMENT 'Score adjustment from pattern detection',
        detected_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_events_type (event_type),
        INDEX idx_events_entity (entity_name),
        INDEX idx_events_time (detected_at DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS sec_filings (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        cik             VARCHAR(20) COMMENT 'SEC CIK number',
        company_name    VARCHAR(255) NOT NULL,
        filing_type     VARCHAR(20) NOT NULL COMMENT '10-K, 10-Q, 8-K, S-1, DEF14A',
        filed_date      DATE,
        document_url    VARCHAR(2048),
        summary_text    TEXT,
        extracted_data  TEXT COMMENT 'JSON: key financials, risks, segments',
        sentiment_score FLOAT COMMENT '-1.0 to 1.0 basic sentiment',
        collected_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_sec_filing (company_name, filing_type, filed_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS job_postings (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        company_name    VARCHAR(255) NOT NULL,
        job_title       VARCHAR(255) NOT NULL,
        location        VARCHAR(255),
        salary_min      INT,
        salary_max      INT,
        job_type        VARCHAR(50) COMMENT 'full_time, contract, remote',
        skills_json     TEXT COMMENT 'JSON: extracted skill tags',
        source_site     VARCHAR(100),
        posted_date     DATE,
        collected_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_job (company_name, job_title, source_site, posted_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS github_trends (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        repo_name       VARCHAR(255) NOT NULL,
        repo_url        VARCHAR(2048),
        stars           INT DEFAULT 0,
        forks           INT DEFAULT 0,
        language        VARCHAR(50),
        description     TEXT,
        topic_tags      TEXT COMMENT 'JSON: repo topics',
        created_at      DATETIME,
        pushed_at       DATETIME,
        weekly_stars_delta INT DEFAULT 0 COMMENT 'Stars gained per week (velocity)',
        source_signal_type VARCHAR(20) DEFAULT 'github_trending',
        collected_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_github_repo (repo_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS funding_events (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        company_name    VARCHAR(255) NOT NULL,
        round_type      VARCHAR(50) COMMENT 'Seed, Series A, Series B, etc.',
        amount_usd      BIGINT COMMENT 'Amount in USD',
        investors_json  TEXT COMMENT 'JSON: list of investor names',
        announced_date  DATE,
        source          VARCHAR(100),
        collected_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_funding (company_name, round_type, announced_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 2: Intelligence tables ──
    """
    CREATE TABLE IF NOT EXISTS patent_filings (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        patent_number   VARCHAR(50) NOT NULL COMMENT 'e.g., US20250123456A1',
        title           TEXT NOT NULL,
        assignee        VARCHAR(255) COMMENT 'Company or organization',
        abstract_text   TEXT,
        filing_date     DATE,
        grant_date      DATE,
        classification  VARCHAR(50) COMMENT 'CPC classification code',
        inventors_json  TEXT COMMENT 'JSON: list of inventor names',
        citations_count INT DEFAULT 0,
        claims_count    INT DEFAULT 0,
        document_url    VARCHAR(2048),
        source          VARCHAR(100) DEFAULT 'uspto',
        collected_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_patent_number (patent_number)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS social_posts (
        id              INT PRIMARY KEY AUTO_INCREMENT,
        platform        VARCHAR(20) NOT NULL COMMENT 'reddit, hacker_news',
        post_id         VARCHAR(50) NOT NULL COMMENT 'Platform-specific post ID',
        title           TEXT NOT NULL,
        body_text       TEXT,
        author          VARCHAR(100),
        score           INT DEFAULT 0,
        num_comments    INT DEFAULT 0,
        url             VARCHAR(2048),
        subreddit       VARCHAR(100) COMMENT 'Reddit-specific',
        entity_name     VARCHAR(255) COMMENT 'Extracted entity name',
        entity_type     VARCHAR(50) DEFAULT 'company',
        post_url        VARCHAR(2048) COMMENT 'Original post URL for link posts',
        published_at    DATETIME,
        collected_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_social_post (platform, post_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS vector_embeddings (
        id              BIGINT PRIMARY KEY AUTO_INCREMENT,
        entity_name     VARCHAR(255) NOT NULL,
        entity_type     VARCHAR(50) NOT NULL,
        content_type    VARCHAR(50) NOT NULL COMMENT 'title, body, summary',
        content_text    TEXT NOT NULL,
        embedding_model VARCHAR(100) NOT NULL DEFAULT 'all-MiniLM-L6-v2',
        vector_data     JSON NOT NULL COMMENT '384-dim float array',
        qdrant_point_id VARCHAR(100) COMMENT 'Qdrant point UUID for sync',
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_vec_entity (entity_name),
        INDEX idx_vec_type (entity_type),
        INDEX idx_vec_model (embedding_model)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS kg_entity_aliases (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        alias_name          VARCHAR(255) NOT NULL,
        normalized_alias    VARCHAR(255) NOT NULL,
        canonical_entity_id INT NOT NULL,
        alias_source        VARCHAR(100) COMMENT 'Where this alias was seen',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_alias_normalized (normalized_alias),
        INDEX idx_alias_canonical (canonical_entity_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS company_profiles (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        company_name        VARCHAR(255) NOT NULL,
        company_number      VARCHAR(100) NOT NULL COMMENT 'Unique company identifier',
        jurisdiction_code   VARCHAR(10) NOT NULL COMMENT 'ISO country code',
        incorporation_date  DATE,
        dissolution_date    DATE,
        company_type        VARCHAR(100),
        current_status      VARCHAR(50),
        registered_address   TEXT,
        officers            TEXT COMMENT 'JSON: list of officer names/positions',
        registry_url        VARCHAR(2048),
        source_search_term  VARCHAR(255),
        raw_score           FLOAT DEFAULT 0,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_company_jurisdiction (jurisdiction_code, company_number),
        KEY idx_company_name (company_name),
        KEY idx_status (current_status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS arxiv_papers (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        arxiv_id            VARCHAR(50) NOT NULL,
        title               TEXT NOT NULL,
        authors             TEXT COMMENT 'JSON: list of author names',
        abstract            TEXT,
        primary_category    VARCHAR(50),
        categories          TEXT COMMENT 'JSON: list of category codes',
        published_date      DATE,
        updated_date        DATE,
        pdf_url             VARCHAR(2048),
        source_url          VARCHAR(2048),
        doi                 VARCHAR(255),
        search_term         VARCHAR(255),
        raw_score           FLOAT DEFAULT 0,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_arxiv_id (arxiv_id),
        KEY idx_category (primary_category),
        KEY idx_published (published_date),
        KEY idx_search_term (search_term)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS producthunt_launches (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        ph_id               VARCHAR(50) NOT NULL,
        name                VARCHAR(255) NOT NULL,
        tagline             TEXT,
        description         TEXT,
        product_url         VARCHAR(2048),
        votes_count         INT DEFAULT 0,
        comments_count      INT DEFAULT 0,
        topics              TEXT COMMENT 'JSON: list of topic names',
        makers              TEXT COMMENT 'JSON: list of maker names',
        website_url         VARCHAR(2048),
        featured            BOOL DEFAULT FALSE,
        launched_at         DATETIME,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_ph_id (ph_id),
        KEY idx_votes (votes_count),
        KEY idx_launched (launched_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS website_monitor_snapshots (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        url                 VARCHAR(2048) NOT NULL,
        page_title          VARCHAR(512),
        meta_description    TEXT,
        content_hash        VARCHAR(64) COMMENT 'SHA-256 of body text',
        signals_found       TEXT COMMENT 'JSON: list of matched signal keywords',
        body_text_excerpt   TEXT COMMENT 'First 1000 chars of body text',
        http_status         INT,
        snapshot_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        KEY idx_url (url(255)),
        KEY idx_snapshot (snapshot_at),
        KEY idx_content_hash (content_hash)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 4: Stack Overflow posts ──
    """
    CREATE TABLE IF NOT EXISTS stackoverflow_posts (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        post_id             BIGINT NOT NULL COMMENT 'Stack Overflow question ID',
        title               TEXT NOT NULL,
        body_text           TEXT COMMENT 'Stripped HTML body text',
        tags                TEXT COMMENT 'JSON array of tags',
        score               INT DEFAULT 0,
        answer_count        INT DEFAULT 0,
        view_count          INT DEFAULT 0,
        author_name         VARCHAR(255),
        author_reputation   INT DEFAULT 0,
        is_answered         TINYINT DEFAULT 0,
        bounty_amount       INT DEFAULT 0,
        link                VARCHAR(512),
        created_at          DATETIME,
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_post_id (post_id),
        KEY idx_score (score),
        KEY idx_created (created_at),
        KEY idx_tags (tags(255))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 4: Package trends (NPM/PyPI) ──
    """
    CREATE TABLE IF NOT EXISTS package_trends (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        package_name        VARCHAR(255) NOT NULL,
        registry            VARCHAR(20) NOT NULL COMMENT 'npm or pypi',
        version             VARCHAR(100),
        description         TEXT,
        monthly_downloads   BIGINT DEFAULT 0,
        keywords            TEXT COMMENT 'JSON array of keywords',
        author              VARCHAR(255),
        license_type        VARCHAR(100),
        project_url         VARCHAR(512),
        created_at_registry DATETIME COMMENT 'Date package was first published',
        updated_at_registry DATETIME COMMENT 'Last update on registry',
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_pkg_registry (package_name, registry),
        KEY idx_downloads (monthly_downloads),
        KEY idx_updated (updated_at_registry),
        KEY idx_registry (registry)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 4: SEC Regulatory Filings ──
    """
    CREATE TABLE IF NOT EXISTS regulatory_filings (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        filing_id           VARCHAR(100) NOT NULL COMMENT 'SEC filing accession number',
        filing_type         VARCHAR(20) NOT NULL COMMENT 'S-1, 8-K, SC 13D',
        company_name        VARCHAR(512),
        summary             TEXT,
        filed_date          DATETIME,
        link                VARCHAR(512),
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_filing_id (filing_id),
        KEY idx_type (filing_type),
        KEY idx_filed (filed_date),
        KEY idx_company (company_name(255))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 4: Newsletter Articles ──
    """
    CREATE TABLE IF NOT EXISTS newsletter_articles (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        title               TEXT NOT NULL,
        source_name         VARCHAR(255),
        author              VARCHAR(255),
        content_text        TEXT,
        publish_date        DATETIME,
        url                 VARCHAR(2048),
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_url (url(255)),
        KEY idx_source (source_name),
        KEY idx_published (publish_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Market Sizing Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_market_sizing (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        sector              VARCHAR(255) NOT NULL,
        market_size_usd     BIGINT COMMENT 'Estimated total market size in USD',
        growth_rate         DOUBLE COMMENT 'Expected annual growth rate (0-1)',
        confidence_score    DOUBLE COMMENT 'Confidence in estimate (0-1)',
        data_sources        TEXT COMMENT 'JSON: data sources and counts',
        methodology          VARCHAR(100) COMMENT 'Estimation methodology used',
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0 COMMENT 'Number of data points analyzed',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_sector_market (sector)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Competitive Landscape Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_competitive_landscape (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        sector              VARCHAR(255) NOT NULL,
        competitor_count    INT DEFAULT 0,
        market_concentration DOUBLE COMMENT 'HHI or concentration metric',
        fragmentation_score DOUBLE COMMENT '0-1, 1=highly fragmented',
        avg_funding_competitors BIGINT,
        top_competitors_json TEXT COMMENT 'JSON: top 5 competitors',
        entry_barriers       VARCHAR(50) COMMENT 'low, medium, high',
        rivalry_intensity    VARCHAR(50) COMMENT 'low, medium, high',
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_sector_competitive (sector)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Founder Background Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_founder_background (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_type       VARCHAR(255) NOT NULL,
        insights_json       TEXT NOT NULL,
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Technology Stack Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_technology_stack (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        technology          VARCHAR(255) NOT NULL,
        category            VARCHAR(100) COMMENT 'language, framework, database, etc',
        adoption_score      DOUBLE COMMENT '0-1 adoption rate',
        trend_direction     VARCHAR(20) COMMENT 'rising, stable, declining',
        github_repos        INT DEFAULT 0,
        stackoverflow_questions INT DEFAULT 0,
        avg_company_age     DOUBLE COMMENT 'Avg age of companies using this',
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_tech_category (technology, category)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Moat Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_moat (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        sector              VARCHAR(255) NOT NULL,
        moat_type           VARCHAR(100) COMMENT 'network_effect, ip, switching_cost, scale',
        moat_strength       DOUBLE COMMENT '0-1 strength score',
        defensibility       VARCHAR(50) COMMENT 'low, medium, high',
        sustainability      VARCHAR(50) COMMENT 'short_term, medium_term, long_term',
        examples_json       TEXT COMMENT 'JSON: example companies',
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_sector_moat (sector, moat_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Timing Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_timing (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        sector              VARCHAR(255) NOT NULL,
        market_phase        VARCHAR(50) COMMENT 'emerging, growth, mature, declining',
        entry_timing        VARCHAR(50) COMMENT 'too_early, optimal, crowded, late',
        opportunity_score   DOUBLE COMMENT '0-1 timing attractiveness',
        success_rate        DOUBLE COMMENT 'Historical success rate',
        avg_funding_required BIGINT,
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_sector_timing (sector)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Graph Traversal Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_graph_traversal (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        start_entity        VARCHAR(255) NOT NULL,
        traversal_type      VARCHAR(100) COMMENT 'bfs, dfs, shortest_path',
        path_length         INT DEFAULT 0,
        entities_visited    INT DEFAULT 0,
        relationships_found INT DEFAULT 0,
        path_json           TEXT COMMENT 'JSON: traversal path',
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Community Detection Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_community_detection (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        community_id        INT NOT NULL,
        community_size      INT DEFAULT 0,
        centrality_score    DOUBLE,
        key_entities_json   TEXT COMMENT 'JSON: central entities',
        cohesion_score      DOUBLE,
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Influence Propagation Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_influence_propagation (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        source_entity       VARCHAR(255) NOT NULL,
        propagation_depth   INT DEFAULT 0,
        entities_influenced INT DEFAULT 0,
        influence_score     DOUBLE,
        propagation_paths_json TEXT,
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Temporal Graph Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_temporal_graph (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        entity_name         VARCHAR(255) NOT NULL,
        time_window_start   DATETIME,
        time_window_end     DATETIME,
        relationship_count  INT DEFAULT 0,
        centrality_change   DOUBLE,
        emergence_score     DOUBLE,
        temporal_patterns_json TEXT,
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Topic Modeling Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_topic_modeling (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        topic_id            INT NOT NULL,
        topic_name          VARCHAR(255),
        topic_words         TEXT COMMENT 'JSON: top words',
        document_count      INT DEFAULT 0,
        coherence_score     DOUBLE,
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_topic (topic_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Relationship Extraction Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_relationship_extraction (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        source_entity       VARCHAR(255) NOT NULL,
        target_entity       VARCHAR(255) NOT NULL,
        relationship_type   VARCHAR(100) NOT NULL,
        confidence          DOUBLE COMMENT '0-1 extraction confidence',
        evidence_json       TEXT COMMENT 'JSON: supporting evidence',
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_relationship (source_entity, target_entity, relationship_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Trend Detection Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_trend_detection (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        trend_name          VARCHAR(255) NOT NULL,
        trend_direction     VARCHAR(20) NOT NULL COMMENT 'rising, falling, stable',
        magnitude           DOUBLE COMMENT 'Trend strength',
        start_period        DATETIME,
        end_period          DATETIME,
        supporting_signals  INT DEFAULT 0,
        confidence          DOUBLE,
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_trend_period (trend_name, start_period)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Intent Classification Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_intent_classification (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        entity_name         VARCHAR(255) NOT NULL,
        intent_category     VARCHAR(100) NOT NULL COMMENT 'investment, partnership, acquisition, etc',
        confidence          DOUBLE,
        context_json        TEXT COMMENT 'JSON: contextual signals',
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_entity_intent (entity_name, intent_category)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Sector Rotation Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_sector_rotation (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        sector              VARCHAR(255) NOT NULL,
        rotation_signal     VARCHAR(20) NOT NULL COMMENT 'inflow, outflow, neutral',
        flow_strength       DOUBLE COMMENT '0-1 strength of rotation signal',
        capital_change      BIGINT,
        sentiment_shift    DOUBLE,
        momentum_score      DOUBLE,
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_sector_rotation (sector, analyzed_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Phase 5: Cohort Analysis ──
    """
    CREATE TABLE IF NOT EXISTS analysis_cohort_analysis (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        cohort_name         VARCHAR(255) NOT NULL,
        cohort_definition   TEXT COMMENT 'How cohort is defined',
        survival_rate       DOUBLE,
        avg_funding         BIGINT,
        failure_rate        DOUBLE,
        success_rate        DOUBLE,
        time_horizon       INT COMMENT 'Months/years analyzed',
        metrics_json        TEXT COMMENT 'JSON: detailed cohort metrics',
        analyzed_at         DATETIME NOT NULL,
        record_count        INT DEFAULT 0,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_cohort_time (cohort_name, analyzed_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Sprint 1: Feedback System tables ──
    """
    CREATE TABLE IF NOT EXISTS query_log (
        id              BIGINT AUTO_INCREMENT PRIMARY KEY,
        query           VARCHAR(500) NOT NULL,
        search_mode     VARCHAR(20) DEFAULT 'hybrid',
        results_count   INT DEFAULT 0,
        response_ms     INT DEFAULT 0,
        source          VARCHAR(50) DEFAULT 'web',
        ip_hash         VARCHAR(64) DEFAULT NULL,
        user_agent      VARCHAR(200) DEFAULT NULL,
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_query_created (query(100), created_at),
        INDEX idx_ql_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_log (
        id              BIGINT AUTO_INCREMENT PRIMARY KEY,
        session_id      VARCHAR(36) DEFAULT NULL,
        user_message    TEXT NOT NULL,
        ai_response     TEXT,
        model_used      VARCHAR(50) DEFAULT 'llama3:8b',
        response_ms     INT DEFAULT 0,
        sources_used    TEXT,
        ip_hash         VARCHAR(64) DEFAULT NULL,
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_cl_session (session_id),
        INDEX idx_cl_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS score_feedback (
        id              BIGINT AUTO_INCREMENT PRIMARY KEY,
        entity_name     VARCHAR(200) NOT NULL,
        score_given     FLOAT,
        rating          TINYINT NOT NULL,
        user_score      INT DEFAULT NULL,
        comment         TEXT DEFAULT NULL,
        ip_hash         VARCHAR(64) DEFAULT NULL,
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_sf_entity (entity_name),
        INDEX idx_sf_rating (rating),
        INDEX idx_sf_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS feature_requests (
        id              BIGINT AUTO_INCREMENT PRIMARY KEY,
        feature         VARCHAR(500) NOT NULL,
        category        VARCHAR(50) DEFAULT 'general',
        source          VARCHAR(50) DEFAULT 'feedback',
        upvotes         INT DEFAULT 1,
        status          VARCHAR(20) DEFAULT 'open',
        ip_hash         VARCHAR(64) DEFAULT NULL,
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_fr_status (status),
        INDEX idx_fr_upvotes (upvotes DESC),
        INDEX idx_fr_category (category)
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
    "CREATE INDEX idx_llm_pricing_provider ON llm_pricing(provider);",
    "CREATE INDEX idx_llm_pricing_collected ON llm_pricing(collected_at DESC);",
    "CREATE INDEX idx_ollama_usage_snap_time ON ollama_usage_snapshots(snapshot_at DESC);",
    "CREATE INDEX idx_ollama_usage_model ON ollama_usage_snapshots(model_name);",
    "CREATE INDEX idx_benchmarks_provider ON llm_benchmarks(provider);",
    "CREATE INDEX idx_benchmarks_category ON llm_benchmarks(benchmark_category);",
    "CREATE INDEX idx_benchmarks_model ON llm_benchmarks(model_name);",
    "CREATE INDEX idx_portfolio_task ON llm_portfolio(task_category);",
    "CREATE INDEX idx_portfolio_recommended ON llm_portfolio(recommended_at DESC);",
    "CREATE INDEX idx_price_changes_detected ON llm_price_changes(detected_at DESC);",
    "CREATE INDEX idx_alerts_priority ON llm_optimization_alerts(priority, dismissed);",
    "CREATE INDEX idx_alerts_type ON llm_optimization_alerts(alert_type);",
    "CREATE INDEX idx_licenses_key ON user_licenses(license_key);",
    "CREATE INDEX idx_licenses_status ON user_licenses(status);",
    "CREATE INDEX idx_licenses_tier ON user_licenses(tier);",
    "CREATE INDEX idx_sub_metrics_date ON subscription_metrics(metric_date);",
    "CREATE INDEX idx_kg_entities_type ON kg_entities(entity_type_id);",
    "CREATE INDEX idx_kg_entities_name ON kg_entities(normalized_name);",
    "CREATE INDEX idx_kg_entities_mentions ON kg_entities(mention_count DESC);",
    "CREATE INDEX idx_kg_rels_source_table ON kg_relationships(source_table);",
    "CREATE INDEX idx_generated_reports_type ON generated_reports(report_type);",
    "CREATE INDEX idx_generated_reports_status ON generated_reports(status);",
    "CREATE INDEX idx_payment_stripe ON payment_events(stripe_session_id);",
    "CREATE INDEX idx_span_pipeline_time ON span_snapshots(pipeline_name, snapshot_at DESC);",
    "CREATE INDEX idx_span_agent ON span_snapshots(agent_name);",
    "CREATE INDEX idx_span_anomaly ON span_snapshots(anomaly_detected, anomaly_type);",
    "CREATE INDEX idx_ml_models_active ON ml_models(is_active);",
    "CREATE INDEX idx_news_sentiment ON news_articles(sentiment_score);",
    # ── Phase 1: Opportunity Intelligence indexes ──
    "CREATE INDEX idx_raw_signals_type ON raw_signals(signal_type);",
    "CREATE INDEX idx_raw_signals_entity ON raw_signals(entity_name);",
    "CREATE INDEX idx_raw_signals_collected ON raw_signals(collected_at DESC);",
    "CREATE INDEX idx_raw_signals_processed ON raw_signals(processed);",
    "CREATE INDEX idx_opp_scores_composite ON opportunity_scores(composite_score DESC);",
    "CREATE INDEX idx_opp_scores_trend ON opportunity_scores(trend_direction);",
    "CREATE INDEX idx_opp_scores_entity ON opportunity_scores(entity_name);",
    "CREATE INDEX idx_sec_filings_company ON sec_filings(company_name);",
    "CREATE INDEX idx_sec_filings_type ON sec_filings(filing_type);",
    "CREATE INDEX idx_sec_filings_date ON sec_filings(filed_date DESC);",
    "CREATE INDEX idx_job_postings_company ON job_postings(company_name);",
    "CREATE INDEX idx_job_postings_date ON job_postings(posted_date DESC);",
    "CREATE INDEX idx_github_trends_language ON github_trends(language);",
    "CREATE INDEX idx_github_trends_velocity ON github_trends(weekly_stars_delta DESC);",
    "CREATE INDEX idx_funding_events_company ON funding_events(company_name);",
    "CREATE INDEX idx_funding_events_date ON funding_events(announced_date DESC);",
    "CREATE INDEX idx_funding_events_amount ON funding_events(amount_usd DESC);",
    # ── Phase 2: Intelligence indexes ──
    "CREATE INDEX idx_patent_assignee ON patent_filings(assignee);",
    "CREATE INDEX idx_patent_filing_date ON patent_filings(filing_date DESC);",
    "CREATE INDEX idx_patent_classification ON patent_filings(classification);",
    "CREATE INDEX idx_social_entity ON social_posts(entity_name);",
    "CREATE INDEX idx_social_score ON social_posts(score DESC);",
    "CREATE INDEX idx_social_published ON social_posts(published_at DESC);",
    # ── Phase 3: Composite indexes for dashboard queries ──
    "CREATE INDEX idx_startups_region_sector ON failed_startups(region, sector);",
    "CREATE INDEX idx_news_manufacturing_sentiment ON news_articles(is_manufacturing, sentiment_score);",
    "CREATE INDEX idx_opp_score_composite_trend ON opportunity_scores(composite_score DESC, trend_direction);",
    "CREATE INDEX idx_vector_embed_entity ON vector_embeddings(entity_name);",
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

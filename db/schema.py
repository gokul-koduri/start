"""MySQL schema definitions for the Startup Research database."""

import logging

_logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 30

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
    CREATE TABLE IF NOT EXISTS alert_preferences (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        user_id             INT NOT NULL,
        email_enabled       INT DEFAULT 1,
        slack_enabled       INT DEFAULT 1,
        discord_enabled     INT DEFAULT 1,
        webhook_enabled     INT DEFAULT 1,
        min_score_threshold DOUBLE DEFAULT 80.0,
        quiet_hours_start   VARCHAR(5) COMMENT 'HH:MM UTC, e.g. 22:00',
        quiet_hours_end     VARCHAR(5) COMMENT 'HH:MM UTC, e.g. 08:00',
        max_alerts_per_hour INT DEFAULT 20,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_prefs (user_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
    CREATE TABLE IF NOT EXISTS score_deltas (
        id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
        entity_name         VARCHAR(255) NOT NULL,
        entity_type         VARCHAR(50) NOT NULL DEFAULT 'company',
        old_score           FLOAT,
        new_score           FLOAT NOT NULL,
        delta               FLOAT NOT NULL COMMENT 'Change in score (positive or negative)',
        trend_previous      VARCHAR(10),
        trend_current       VARCHAR(10),
        signal_breakdown_json TEXT COMMENT 'JSON: per-signal contribution changes',
        detected_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_entity (entity_name, entity_type),
        INDEX idx_detected (detected_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS score_accuracy_runs (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        accuracy_pct        FLOAT NOT NULL COMMENT 'Percentage correct (0-100)',
        total_tested        INT NOT NULL,
        correct             INT NOT NULL,
        true_positives      INT DEFAULT 0,
        false_positives     INT DEFAULT 0,
        true_negatives      INT DEFAULT 0,
        false_negatives     INT DEFAULT 0,
        precision_pct       FLOAT,
        recall_pct          FLOAT,
        f1_score            FLOAT,
        threshold_used      FLOAT DEFAULT 70.0,
        weights_snapshot    TEXT COMMENT 'JSON snapshot of weights used',
        run_notes           TEXT,
        run_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_run_at (run_at)
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
    # ── Sprint 3: Feedback + Analytics tables ──
    """
    CREATE TABLE IF NOT EXISTS feedback_analysis (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_week       VARCHAR(20) NOT NULL COMMENT 'ISO week e.g. 2026-W23',
        trending_queries    TEXT COMMENT 'JSON: list of trending search queries with counts',
        common_questions    TEXT COMMENT 'JSON: list of common chat questions with counts',
        avg_rating          FLOAT DEFAULT 0.0 COMMENT 'Average score feedback rating (1-5)',
        rating_count        INT DEFAULT 0,
        rating_distribution TEXT COMMENT 'JSON: {1: count, 2: count, ...}',
        calibration_gaps    TEXT COMMENT 'JSON: entities where user_score differs from AI score',
        top_feature_requests TEXT COMMENT 'JSON: top feature requests with upvotes',
        total_queries       INT DEFAULT 0,
        total_chats         INT DEFAULT 0,
        total_feedback      INT DEFAULT 0,
        analyzed_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_analysis_week (analysis_week)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS error_log (
        id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
        error_type          VARCHAR(100) NOT NULL COMMENT 'Python exception class name',
        error_message       TEXT NOT NULL,
        traceback_text      TEXT,
        endpoint            VARCHAR(255) COMMENT 'API endpoint or module path',
        request_method      VARCHAR(10),
        request_path        VARCHAR(500),
        severity            VARCHAR(20) DEFAULT 'error' COMMENT 'warning, error, critical',
        fingerprint         VARCHAR(64) COMMENT 'SHA-256 hash for deduplication',
        request_data        TEXT COMMENT 'JSON: sanitized request body/params',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_el_type (error_type),
        INDEX idx_el_endpoint (endpoint),
        INDEX idx_el_severity (severity),
        INDEX idx_el_created (created_at),
        INDEX idx_el_fingerprint (fingerprint)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        email               VARCHAR(255) NOT NULL UNIQUE,
        password_hash       VARCHAR(255) NOT NULL COMMENT 'bcrypt hash',
        display_name        VARCHAR(255),
        role                VARCHAR(50) NOT NULL DEFAULT 'viewer' COMMENT 'viewer, analyst, admin',
        is_active           TINYINT DEFAULT 1,
        last_login_at       DATETIME,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_users_email (email),
        INDEX idx_users_role (role),
        INDEX idx_users_active (is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS api_keys (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        user_id             INT NOT NULL,
        key_prefix          VARCHAR(8) NOT NULL COMMENT 'First 8 chars for identification',
        key_hash            VARCHAR(255) NOT NULL UNIQUE COMMENT 'SHA-256 hash of the key',
        name                VARCHAR(255) COMMENT 'Human-readable key label',
        permissions         TEXT COMMENT 'JSON: list of permission strings',
        last_used_at        DATETIME,
        expires_at          DATETIME,
        is_active           TINYINT DEFAULT 1,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        INDEX idx_apikeys_hash (key_hash),
        INDEX idx_apikeys_user (user_id),
        INDEX idx_apikeys_active (is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Email queue tables (schema v23) ──
    """
    CREATE TABLE IF NOT EXISTS outbound_emails (
        id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
        recipient           VARCHAR(255) NOT NULL,
        recipient_name      VARCHAR(255),
        subject             VARCHAR(500) NOT NULL,
        email_type          VARCHAR(50) NOT NULL COMMENT 'report, digest, alert, welcome, notification',
        plain_body          TEXT NOT NULL,
        html_body           MEDIUMTEXT NOT NULL,
        from_address        VARCHAR(255) NOT NULL,
        reply_to            VARCHAR(255),
        status              VARCHAR(20) NOT NULL DEFAULT 'queued' COMMENT 'queued, sending, sent, failed, dead',
        priority            TINYINT NOT NULL DEFAULT 5 COMMENT '1=urgent, 5=normal, 9=low',
        attempts            TINYINT NOT NULL DEFAULT 0,
        max_attempts        TINYINT NOT NULL DEFAULT 5,
        last_attempt_at     DATETIME,
        next_retry_at       DATETIME COMMENT 'Exponential backoff: now + 2^attempts minutes',
        last_error          TEXT,
        sent_at             DATETIME,
        message_id          VARCHAR(255) COMMENT 'SMTP Message-ID for tracking',
        related_id          VARCHAR(100) COMMENT 'FK-like reference: report_id, alert_id, etc.',
        metadata_json       TEXT COMMENT 'JSON: arbitrary metadata for this email',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_oe_status_priority (status, priority, next_retry_at),
        INDEX idx_oe_status_created (status, created_at),
        INDEX idx_oe_recipient (recipient),
        INDEX idx_oe_type (email_type),
        INDEX idx_oe_sent (sent_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS email_delivery_log (
        id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
        outbound_email_id   BIGINT NOT NULL,
        event_type          VARCHAR(30) NOT NULL COMMENT 'queued, sent, bounced, deferred, complained, opened, clicked',
        smtp_response       TEXT COMMENT 'Raw SMTP server response',
        smtp_status_code    VARCHAR(10),
        detail              TEXT COMMENT 'Human-readable detail',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (outbound_email_id) REFERENCES outbound_emails(id) ON DELETE CASCADE,
        INDEX idx_edl_email (outbound_email_id),
        INDEX idx_edl_event (event_type),
        INDEX idx_edl_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS email_suppressions (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        email               VARCHAR(255) NOT NULL UNIQUE,
        reason              VARCHAR(50) NOT NULL COMMENT 'bounce, complaint, manual, unsubscribe',
        detail              TEXT,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_es_email (email),
        INDEX idx_es_reason (reason)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlists (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        user_id             INT NOT NULL COMMENT 'FK to users table',
        name                VARCHAR(255) NOT NULL,
        description         TEXT,
        is_active           TINYINT DEFAULT 1,
        alert_config_json   TEXT COMMENT 'JSON: threshold, channels, quiet_hours config',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlist_items (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        watchlist_id        INT NOT NULL COMMENT 'FK to watchlists table',
        entity_name         VARCHAR(255) NOT NULL,
        entity_type         VARCHAR(50) NOT NULL DEFAULT 'company' COMMENT 'company, technology, market',
        notes               TEXT,
        added_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_watchlist_entity (watchlist_id, entity_name, entity_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlist_alert_history (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        watchlist_id        INT NOT NULL COMMENT 'FK to watchlists table',
        alert_type          VARCHAR(50) NOT NULL COMMENT 'score_change, trend_change, threshold_breach',
        entity_name         VARCHAR(255) NOT NULL,
        old_score           FLOAT,
        new_score           FLOAT,
        delta               FLOAT NOT NULL COMMENT 'Score change amount',
        alert_data_json     TEXT COMMENT 'JSON: additional alert context',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_wah_watchlist (watchlist_id),
        INDEX idx_wah_entity (entity_name),
        INDEX idx_wah_created (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # -------------------------------------------------------------------------
    # LLM Report Insights (v11)
    # -------------------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS report_insights (
        id               INT PRIMARY KEY AUTO_INCREMENT,
        insight_type     VARCHAR(100) NOT NULL COMMENT 'executive_summary, failure_patterns, etc.',
        section          VARCHAR(50) NOT NULL COMMENT 'header, part1, part2, etc.',
        content          TEXT NOT NULL COMMENT 'Rendered markdown content',
        raw_response     TEXT COMMENT 'Full JSON response from LLM',
        model_used       VARCHAR(100) NOT NULL DEFAULT 'llama3',
        generation_ms    INT DEFAULT 0,
        cached           TINYINT DEFAULT 0,
        confidence_score FLOAT DEFAULT NULL,
        valid_until      DATETIME COMMENT 'Cache expiry (NULL = no expiry)',
        error_message    TEXT,
        generated_at     VARCHAR(50) NOT NULL,
        created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_ri_type (insight_type),
        INDEX idx_ri_section (section),
        INDEX idx_ri_valid_until (valid_until),
        UNIQUE KEY uq_insight_type_section (insight_type, section)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Pipeline Operations Research (v27) ──
    """
    CREATE TABLE IF NOT EXISTS pipeline_companies (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        name                VARCHAR(255) NOT NULL,
        company_type        VARCHAR(50) NOT NULL COMMENT 'failed, active, acquired',
        pipeline_type       VARCHAR(100) NOT NULL COMMENT 'inspection, management, infrastructure, monitoring',
        technology_focus   VARCHAR(255) COMMENT 'smart_pigging, leak_detection, corrosion_mgmt, etc.',
        country             VARCHAR(100),
        region              VARCHAR(100),

        -- Company details
        year_founded        INT,
        year_shutdown       INT,
        headquarters        VARCHAR(255),
        website             VARCHAR(2048),
        employee_count      INT,
        company_description TEXT,

        -- Funding & Investment
        funding_total       DOUBLE,
        last_funding_round  VARCHAR(100),
        last_funding_date   DATE,
        investors           TEXT COMMENT 'JSON: list of investor names',
        peak_valuation_usd  DOUBLE,

        -- Market positioning
        technology_stack    TEXT COMMENT 'JSON: full tech stack',
        market_segments     VARCHAR(255) COMMENT 'oil_gas, water, chemical, hydrogen',
        geographic_focus    VARCHAR(255) COMMENT 'regions served',
        customers           TEXT COMMENT 'JSON: notable customers',
        competitive_position VARCHAR(50) COMMENT 'leader, challenger, niche',

        -- Status & History
        company_status      VARCHAR(50) DEFAULT 'active' COMMENT 'active, declined, acquired, bankrupt',
        acquisition_status  VARCHAR(50),
        acquisition_by      VARCHAR(255),
        acquisition_year    INT,
        failure_reason      TEXT,

        -- Data quality
        data_confidence_score FLOAT DEFAULT 0.5 COMMENT '0.0-1.0 confidence in data',
        last_enriched_at    DATETIME,

        -- Sources
        funding_raised_usd  DOUBLE,
        description         TEXT,
        key_technology      TEXT COMMENT 'JSON: list of key technologies',
        market_segment      VARCHAR(100) COMMENT 'oil_gas, water, chemical, general',
        source              VARCHAR(100),
        source_url          VARCHAR(2048),
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_pipeline_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS pipeline_opportunities (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        opportunity_type    VARCHAR(100) NOT NULL COMMENT 'technology_gap, market_need, revival_candidate',
        pipeline_category   VARCHAR(100) NOT NULL COMMENT 'inspection, management, corrosion, etc.',
        title               VARCHAR(500) NOT NULL,
        description         TEXT NOT NULL,

        -- Market analysis
        market_size_estimate TEXT COMMENT 'Estimated market size',
        market_demand_score   FLOAT COMMENT '0-100: market demand',
        technology_readiness FLOAT COMMENT '0-100: technology maturity',
        regulatory_pressure  FLOAT COMMENT '0-100: regulatory push',
        investment_interest   FLOAT COMMENT '0-100: investor interest',

        -- Scoring
        opportunity_score   FLOAT COMMENT '0-100: overall score (avg of above - competition)',
        competition_level   VARCHAR(50) COMMENT 'low, medium, high',
        competition_score    FLOAT COMMENT '0-100: competition intensity',

        entry_barriers      VARCHAR(255),
        investment_needed   VARCHAR(100),
        confidence_score    FLOAT DEFAULT 0.5 COMMENT '0.0-1.0 confidence',
        related_company_id  INT COMMENT 'FK to pipeline_companies.id if applicable',
        source_data        TEXT COMMENT 'JSON: supporting data',

        analyzed_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS pipeline_funding_events (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        company_name        VARCHAR(255) NOT NULL,
        round_type          VARCHAR(50) NOT NULL COMMENT 'Seed, Series A, B, C, IPO, Acquisition',
        amount_usd          BIGINT,
        announced_date      DATE,
        investors_json      TEXT COMMENT 'JSON: list of investor names',
        lead_investors      TEXT,
        valuation_at_round  BIGINT,
        source              VARCHAR(100),
        source_url          VARCHAR(2048),
        collected_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_funding_event (company_name, round_type, announced_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS pipeline_failure_analysis (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        analysis_type       VARCHAR(100) NOT NULL COMMENT 'failure_pattern, hardware_vs_software, etc.',
        category            VARCHAR(100) COMMENT 'inspection, management, etc.',
        insight_json        TEXT NOT NULL COMMENT 'JSON: detailed insights',
        pattern_count       INT DEFAULT 0,
        confidence          FLOAT DEFAULT 0.5,
        recommendation_json TEXT COMMENT 'JSON: recommendations for revival',
        analyzed_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_analysis_category (analysis_type, category)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ─── Phase v2: Manufacturing Opportunity Intelligence Engine ───
    """
    CREATE TABLE IF NOT EXISTS manufacturing_opportunities (
        -- Identity
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        opportunity_type    VARCHAR(50) NOT NULL COMMENT 'new_build, revival, expansion',
        title               VARCHAR(500) NOT NULL COMMENT 'e.g., Ohio EV Battery Manufacturing',
        description         TEXT NOT NULL,

        -- Industry classification
        sector              VARCHAR(255) NOT NULL COMMENT 'e.g., EV Battery, Semiconductors',
        sub_sector          VARCHAR(255),
        manufacturing_process VARCHAR(500) COMMENT 'e.g., Lithium-ion cell manufacturing',

        -- Multi-dimensional scoring (0-100)
        opportunity_score   FLOAT COMMENT 'Should this company exist?',
        demand_score        FLOAT COMMENT 'Market demand 0-100',
        supply_gap_score    FLOAT COMMENT 'Supply gap 0-100',
        feasibility_score   FLOAT COMMENT 'Manufacturing feasibility 0-100',
        timing_score        FLOAT COMMENT 'Timing/opportunity window 0-100',
        competition_score   FLOAT COMMENT 'Competition intensity 0-100',

        -- Revival scoring (for failed company revivals)
        revival_score       FLOAT COMMENT 'Could failed company succeed today? 0-100',
        failure_addressed   FLOAT COMMENT 'Original failure reason addressed 0-100',
        market_change       FLOAT COMMENT 'Market conditions change 0-100',
        tech_change         FLOAT COMMENT 'Technology change 0-100',
        cost_change         FLOAT COMMENT 'Cost structure change 0-100',
        policy_change       FLOAT COMMENT 'Policy change 0-100',

        -- Market intelligence
        total_addressable_market_billion FLOAT COMMENT 'TAM in $B',
        service_addressable_market_billion FLOAT COMMENT 'SAM in $B',
        expected_growth_rate_pct  FLOAT COMMENT 'Annual growth %',
        addressable_customer_types TEXT COMMENT 'JSON: list of customer segments',
        estimated_capex_min       BIGINT COMMENT 'Minimum CAPEX in USD',
        estimated_capex_max       BIGINT COMMENT 'Maximum CAPEX in USD',
        time_to_market_months     INT COMMENT 'Estimated months to first revenue',
        jobs_creation_estimate    INT COMMENT 'Estimated direct jobs',

        -- Evidence and confidence
        evidence_json       TEXT COMMENT 'JSON: supporting signals and sources',
        confidence_score    FLOAT COMMENT '0-1: How confident are we in this opportunity',
        confidence_factors_json TEXT COMMENT 'JSON: breakdown of confidence components',
        model_version       VARCHAR(50) COMMENT 'Scoring model version',
        model_score_date    DATETIME COMMENT 'When score was computed',

        -- Status and tracking
        status              VARCHAR(50) DEFAULT 'active' COMMENT 'active, validated, pursued, archived',
        priority            INT DEFAULT 0 COMMENT '1=highest, higher=lower',

        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_opportunity_title (title(200))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS opportunity_outcomes (
        -- Links opportunity to actual outcomes
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        opportunity_id      INT NOT NULL,
        audience_type       VARCHAR(50) NOT NULL COMMENT 'government, investor, founder',

        -- Recommendation delivery
        recommended_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        delivered_to       VARCHAR(255) COMMENT 'Email/contact the recommendation was sent to',
        interaction_type    VARCHAR(50) COMMENT 'viewed, downloaded, discussed, meeting_scheduled',
        interaction_at      DATETIME,

        -- Outcome tracking
        outcome_type        VARCHAR(50) COMMENT 'reviewed, funded, company_created, investment_made, jobs_created, not_pursued',
        outcome_detail      TEXT COMMENT 'Details of what happened',
        outcome_date        DATETIME,

        -- Attribution (what in our recommendation led to the outcome)
        successful_factors_json TEXT COMMENT 'JSON: what factors in our score were accurate',
        missed_factors_json     TEXT COMMENT 'JSON: what we missed or got wrong',

        -- Source tracking
        source_opportunity_id INT COMMENT 'Reference to failed_startup or other source entity',
        customer_id         INT COMMENT 'FK to users/customers if tracked',
        notes               TEXT,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        FOREIGN KEY (opportunity_id) REFERENCES manufacturing_opportunities(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS regional_fit_scores (
        -- Where should an opportunity be built? (cross-reference opportunities x regions)
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        opportunity_id      INT NOT NULL,
        region              VARCHAR(100) NOT NULL COMMENT 'e.g., Ohio, Michigan, Southeast',

        -- Component scores (0-100)
        regional_fit_score  FLOAT COMMENT 'Overall regional fit 0-100',
        workforce_score     FLOAT COMMENT 'Workforce availability 0-100',
        infrastructure_score FLOAT COMMENT 'Industrial infrastructure 0-100',
        supplier_score      FLOAT COMMENT 'Supplier ecosystem maturity 0-100',
        energy_score        FLOAT COMMENT 'Energy costs and availability 0-100',
        incentive_score     FLOAT COMMENT 'Policy/incentive alignment 0-100',
        logistics_score     FLOAT COMMENT 'Logistics access 0-100',

        -- Contextual data
        details_json        TEXT COMMENT 'JSON: specific data supporting each score',
        ranked_position     INT COMMENT 'Rank among regions for this opportunity',
        confidence_score    FLOAT COMMENT '0-1: confidence in the ranking',

        -- Cost factors for this region
        avg_hourly_wage_usd FLOAT COMMENT 'Average manufacturing wage in region',
        electricity_cost_kwh FLOAT COMMENT 'Industrial electricity $/kWh',
        property_tax_rate   FLOAT COMMENT 'Effective property tax rate',
        incentive_value_millions FLOAT COMMENT 'Est. incentive package $M',
        training_cost_per_worker FLOAT,

        model_version       VARCHAR(50),
        scored_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_opp_region (opportunity_id, region)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS founder_fit_scores (
        -- Which founder should build this? (cross-reference opportunity x founder profile)
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        opportunity_id      INT NOT NULL,
        founder_profile_id  INT COMMENT 'Reference to a stored founder profile, or NULL for ad-hoc',

        -- Founder match scores (0-100)
        founder_fit_score   FLOAT COMMENT 'Overall founder-opportunity match 0-100',
        expertise_score     FLOAT COMMENT 'Domain expertise match 0-100',
        experience_score    FLOAT COMMENT 'Manufacturing experience 0-100',
        capital_score       FLOAT COMMENT 'Capital access match 0-100',
        network_score       FLOAT COMMENT 'Relevant network connections 0-100',
        location_score      FLOAT COMMENT 'Location fit 0-100',

        -- Gap analysis
        gap_analysis_json   TEXT COMMENT 'JSON: which factors are gaps',
        recommended_learning_json TEXT COMMENT 'JSON: what founder should learn',
        suggested_cos_founders_json TEXT COMMENT 'JSON: complementary cofounder profiles',

        -- Recommendation
        recommendation      VARCHAR(50) COMMENT 'strong_fit, good_fit, partial_fit, poor_fit',
        confidence_score    FLOAT,
        model_version       VARCHAR(50),
        scored_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_opp_founder (opportunity_id, founder_profile_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    # ── Sprint Cycle tables ──
    """
    CREATE TABLE IF NOT EXISTS sprint_tasks (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        task_id             VARCHAR(100) NOT NULL UNIQUE COMMENT 'e.g., SPRINT-2026-001',
        title               VARCHAR(500) NOT NULL,
        description         TEXT,

        -- Classification
        task_type           VARCHAR(50) NOT NULL COMMENT 'feature, bugfix, research, improvement',
        priority            INT DEFAULT 5 COMMENT '1=highest priority',

        -- Opportunity scoring (from OpportunityPipelineAgent)
        opportunity_score   FLOAT COMMENT '0-100 composite score',
        task_effort_minutes INT COMMENT 'Estimated effort in minutes',

        -- State machine
        state               VARCHAR(50) NOT NULL DEFAULT 'scanned' COMMENT 'scanned, planned, approved, rejected, in_progress, done, failed',

        -- Codex planning output
        plan_document       TEXT COMMENT 'Implementation plan from Codex/Plan Agent',
        plan_version        INT DEFAULT 1,
        plan_file_path      VARCHAR(500) COMMENT 'Path to plan document in docs/plans/',

        -- Execution tracking
        assigned_agent      VARCHAR(100),
        started_at          DATETIME,
        completed_at        DATETIME,
        execution_notes     TEXT,

        -- Source tracking
        source              VARCHAR(100) COMMENT 'opportunity_pipeline, manual, sprint_backlog',
        related_opp_id      INT COMMENT 'FK to manufacturing_opportunities.id',

        -- Metadata
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

        INDEX idx_state (state),
        INDEX idx_priority (priority),
        INDEX idx_opp_score (opportunity_score DESC),
        INDEX idx_created (created_at DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS pending_approvals (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        sprint_task_id      INT NOT NULL,

        -- Approval details
        approver_email      VARCHAR(255) COMMENT 'Email of designated approver',
        approval_type       VARCHAR(50) NOT NULL COMMENT 'major_task, scope_change, plan_revision',

        -- Request details
        request_summary     TEXT,
        plan_preview        TEXT COMMENT 'First 1000 chars of plan',
        plan_file_url       VARCHAR(500) COMMENT 'URL/path to full plan',

        -- Decision
        decision            VARCHAR(20) COMMENT 'approved, rejected, changes_requested',
        decision_at         DATETIME,
        decision_notes      TEXT,

        -- Notification tracking
        notified_at         DATETIME,
        responded_at        DATETIME,
        reminder_sent_at    DATETIME,

        -- Expiry
        expires_at          DATETIME,

        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (sprint_task_id) REFERENCES sprint_tasks(id) ON DELETE CASCADE,
        INDEX idx_pending (decision, created_at),
        INDEX idx_expires (expires_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS cycle_audit_log (
        id                  BIGINT PRIMARY KEY AUTO_INCREMENT,
        cycle_id            VARCHAR(50) NOT NULL COMMENT 'UUID for each scan cycle',
        sprint_task_id      VARCHAR(100) COMMENT 'Link to sprint_tasks.task_id',

        -- Action tracking
        action              VARCHAR(50) NOT NULL COMMENT 'scanned, planned, approved, rejected, executed, auto_approved, skipped',

        -- Details
        details_json        TEXT COMMENT 'JSON: action-specific details',
        llm_calls_json     TEXT COMMENT 'JSON: Codex/LLM API calls made',
        opportunity_data    TEXT COMMENT 'JSON: opportunity that triggered this task',

        -- Timing
        duration_ms         INT,
        cycle_started_at    DATETIME,
        cycle_completed_at  DATETIME,

        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

        INDEX idx_cycle (cycle_id),
        INDEX idx_task (sprint_task_id),
        INDEX idx_action (action),
        INDEX idx_created (created_at DESC)
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
    # ── Sprint 3: Feedback + Analytics indexes ──
    "CREATE INDEX idx_feedback_analysis_week ON feedback_analysis(analysis_week);",
    "CREATE INDEX idx_error_log_type_time ON error_log(error_type, created_at DESC);",
    # ── Email queue indexes (schema v23) ──
    "CREATE INDEX idx_oe_status_retry ON outbound_emails(status, next_retry_at);",
    "CREATE INDEX idx_oe_attempts ON outbound_emails(attempts, max_attempts);",
    "CREATE INDEX idx_edl_email_created ON email_delivery_log(outbound_email_id, created_at);",
    "CREATE INDEX idx_es_created ON email_suppressions(created_at);",
    # ── Pipeline Operations Research indexes ──
    "CREATE INDEX idx_pipeline_company_type ON pipeline_companies(company_type);",
    "CREATE INDEX idx_pipeline_type ON pipeline_companies(pipeline_type);",
    "CREATE INDEX idx_pipeline_country ON pipeline_companies(country);",
    "CREATE INDEX idx_pipeline_region ON pipeline_companies(region);",
    "CREATE INDEX idx_pipeline_shutdown_year ON pipeline_companies(year_shutdown);",
    "CREATE INDEX idx_pipeline_opp_type ON pipeline_opportunities(opportunity_type);",
    "CREATE INDEX idx_pipeline_opp_category ON pipeline_opportunities(pipeline_category);",
    "CREATE INDEX idx_pipeline_opp_confidence ON pipeline_opportunities(confidence_score DESC);",
    "CREATE INDEX idx_pipeline_opp_score ON pipeline_opportunities(opportunity_score DESC);",
    # Pipeline funding events
    "CREATE INDEX idx_pfe_company ON pipeline_funding_events(company_name);",
    "CREATE INDEX idx_pfe_round_date ON pipeline_funding_events(announced_date DESC);",
    "CREATE INDEX idx_pfe_amount ON pipeline_funding_events(amount_usd DESC);",
    # Pipeline failure analysis
    "CREATE INDEX idx_pfa_type ON pipeline_failure_analysis(analysis_type);",
    "CREATE INDEX idx_pfa_category ON pipeline_failure_analysis(category);",
    # ── Phase v2: Manufacturing Opportunity Intelligence indexes ──
    "CREATE INDEX idx_mfg_opp_sector ON manufacturing_opportunities(sector);",
    "CREATE INDEX idx_mfg_opp_type ON manufacturing_opportunities(opportunity_type);",
    "CREATE INDEX idx_mfg_opp_score ON manufacturing_opportunities(opportunity_score DESC);",
    "CREATE INDEX idx_mfg_opp_priority ON manufacturing_opportunities(priority, status);",
    "CREATE INDEX idx_mfg_opp_confidence ON manufacturing_opportunities(confidence_score DESC);",
    "CREATE INDEX idx_mfg_opp_created ON manufacturing_opportunities(created_at DESC);",
    "CREATE INDEX idx_mfg_outcome_opp ON opportunity_outcomes(opportunity_id);",
    "CREATE INDEX idx_mfg_outcome_type ON opportunity_outcomes(outcome_type);",
    "CREATE INDEX idx_mfg_outcome_date ON opportunity_outcomes(outcome_date);",
    "CREATE INDEX idx_regional_opp ON regional_fit_scores(opportunity_id);",
    "CREATE INDEX idx_regional_region ON regional_fit_scores(region);",
    "CREATE INDEX idx_regional_score ON regional_fit_scores(regional_fit_score DESC);",
    "CREATE INDEX idx_founder_opp ON founder_fit_scores(opportunity_id);",
    "CREATE INDEX idx_founder_score ON founder_fit_scores(founder_fit_score DESC);",
    # ── Sprint Cycle indexes ──
    "CREATE INDEX idx_sprint_task_type ON sprint_tasks(task_type);",
    "CREATE INDEX idx_sprint_task_state ON sprint_tasks(state);",
    "CREATE INDEX idx_sprint_task_created ON sprint_tasks(created_at DESC);",
    "CREATE INDEX idx_pending_task ON pending_approvals(sprint_task_id);",
    "CREATE INDEX idx_pending_decision ON pending_approvals(decision);",
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
    _logger.info("Database schema initialized (version %d)", _SCHEMA_VERSION)

    # ── API tables (need separate cursor) ──
    cursor = conn.cursor()
    _api_tables = [
        """
    CREATE TABLE IF NOT EXISTS api_organizations (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        name                VARCHAR(255) NOT NULL,
        slug                VARCHAR(100) UNIQUE,
        website             VARCHAR(2048),
        logo_url            VARCHAR(2048),
        description         TEXT,
        country             VARCHAR(100),
        founded_year        INT,
        employee_count      VARCHAR(50),
        social_links_json   TEXT COMMENT 'JSON: social media links',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_api_org_slug (slug),
        INDEX idx_api_org_country (country),
        INDEX idx_api_org_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
    CREATE TABLE IF NOT EXISTS api_registries (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        name                VARCHAR(255) NOT NULL,
        organization_id     INT,
        description         TEXT,
        documentation_url   VARCHAR(2048),
        base_url            VARCHAR(2048),
        is_public           TINYINT DEFAULT 1,
        popularity_score   INT DEFAULT 0,
        api_version         VARCHAR(20),
        category            VARCHAR(100),
        tags_json           TEXT COMMENT 'JSON: list of tags',
        logo_url            VARCHAR(2048),
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (organization_id) REFERENCES api_organizations(id) ON DELETE SET NULL,
        INDEX idx_api_reg_org (organization_id),
        INDEX idx_api_reg_category (category),
        INDEX idx_api_reg_popularity (popularity_score DESC),
        INDEX idx_api_reg_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
    CREATE TABLE IF NOT EXISTS api_endpoints (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        registry_id         INT NOT NULL,
        method              VARCHAR(10) NOT NULL COMMENT 'GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD',
        path                VARCHAR(500) NOT NULL,
        full_url            VARCHAR(2048),
        summary             VARCHAR(500),
        description         TEXT,
        auth_type           VARCHAR(50),
        rate_limit          VARCHAR(100),
        response_format     VARCHAR(50),
        status              VARCHAR(20) DEFAULT 'active',
        latency_ms          INT,
        popularity_score   INT DEFAULT 0,
        security_score      INT DEFAULT 0,
        tags_json           TEXT COMMENT 'JSON: list of tags',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (registry_id) REFERENCES api_registries(id) ON DELETE CASCADE,
        INDEX idx_ep_reg (registry_id),
        INDEX idx_ep_method (method),
        INDEX idx_ep_status (status),
        INDEX idx_ep_popularity (popularity_score DESC),
        INDEX idx_ep_security (security_score DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
    CREATE TABLE IF NOT EXISTS endpoint_requests (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        endpoint_id         INT NOT NULL,
        content_type        VARCHAR(100),
        headers_json        TEXT COMMENT 'JSON: required headers',
        body_schema_json    TEXT COMMENT 'JSON: request body schema',
        query_params_json   TEXT COMMENT 'JSON: query parameters',
        path_params_json    TEXT COMMENT 'JSON: path parameters',
        example_request     TEXT,
        example_response    TEXT,
        response_codes_json TEXT COMMENT 'JSON: possible response codes',
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (endpoint_id) REFERENCES api_endpoints(id) ON DELETE CASCADE,
        INDEX idx_er_ep (endpoint_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
    CREATE TABLE IF NOT EXISTS endpoint_technologies (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        endpoint_id         INT NOT NULL,
        technology          VARCHAR(100) NOT NULL,
        category            VARCHAR(50),
        version             VARCHAR(50),
        confidence          FLOAT DEFAULT 1.0,
        detected_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (endpoint_id) REFERENCES api_endpoints(id) ON DELETE CASCADE,
        INDEX idx_et_ep (endpoint_id),
        INDEX idx_et_tech (technology),
        INDEX idx_et_category (category)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
    CREATE TABLE IF NOT EXISTS security_analyses (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        endpoint_id         INT NOT NULL,
        check_type          VARCHAR(100),
        severity            VARCHAR(20),
        finding             TEXT,
        recommendation      TEXT,
        analyzed_at         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (endpoint_id) REFERENCES api_endpoints(id) ON DELETE CASCADE,
        INDEX idx_sa_ep (endpoint_id),
        INDEX idx_sa_severity (severity),
        INDEX idx_sa_type (check_type)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
    CREATE TABLE IF NOT EXISTS scan_jobs (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        scan_type           VARCHAR(50),
        target_url          VARCHAR(2048) NOT NULL,
        status              VARCHAR(20) DEFAULT 'pending' COMMENT 'pending, running, completed, failed',
        progress            INT DEFAULT 0 COMMENT '0-100',
        results_count       INT DEFAULT 0,
        options_json        TEXT COMMENT 'JSON: scan configuration',
        error_message       TEXT,
        started_at          DATETIME,
        completed_at        DATETIME,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_sj_status (status),
        INDEX idx_sj_created (created_at DESC),
        INDEX idx_sj_target (target_url(255))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
    CREATE TABLE IF NOT EXISTS api_favorites (
        id                  INT PRIMARY KEY AUTO_INCREMENT,
        user_id             INT NOT NULL,
        endpoint_id         INT,
        registry_id          INT,
        created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (endpoint_id) REFERENCES api_endpoints(id) ON DELETE CASCADE,
        FOREIGN KEY (registry_id) REFERENCES api_registries(id) ON DELETE CASCADE,
        INDEX idx_af_user (user_id),
        INDEX idx_af_ep (endpoint_id),
        INDEX idx_af_reg (registry_id),
        UNIQUE KEY uq_af_user_ep (user_id, endpoint_id),
        UNIQUE KEY uq_af_user_reg (user_id, registry_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ]

    # Execute API tables
    for table_sql in _api_tables:
        cursor.execute(table_sql)

    conn.commit()
    _logger.info("API Endpoint Explorer tables created (version %d)", _SCHEMA_VERSION)


def get_schema_version() -> int:
    return _SCHEMA_VERSION

# 🤖 Opportunity Intelligence Platform — Agent Development Guide

> How to build, test, and register new AI agents
> For contributors and developers

---

## Table of Contents

1. [Agent Architecture](#1-agent-architecture)
2. [Base Agent Class](#2-base-agent-class)
3. [Building a New Agent](#3-building-a-new-agent)
4. [Agent Registration](#4-agent-registration)
5. [Testing Your Agent](#5-testing-your-agent)
6. [Agent Patterns](#6-agent-patterns)
7. [Configuration](#7-configuration)
8. [Database Schema for Agents](#8-database-schema-for-agents)
9. [Best Practices](#9-best-practices)
10. [Complete Example: Sentiment Agent](#10-complete-example-sentiment-agent)

---

## 1. Agent Architecture

### How Agents Fit In

```
run_agent.py
    │
    ▼
agents/orchestrator.py
    │
    ├── AGENT_REGISTRY = {
    │       "failure_pattern": FailurePatternAgent,
    │       "survival_analysis": SurvivalAnalysisAgent,
    │       "your_agent": YourAgent,        ← You add this
    │   }
    │
    ▼
agents/base.py
    │
    └── BaseAgent (abstract)
            ├── name: str
            ├── run(conn, config) → dict
            └── validate_output(output) → bool
```

### Agent Lifecycle

```
1. Orchestrator reads AGENT_REGISTRY
2. Instantiates your agent with dependencies
3. Calls agent.run(conn, config)
4. Agent reads from database
5. Agent processes data (ML, NLP, LLM, rules)
6. Agent writes results to database
7. Agent returns output dict
8. Orchestrator logs results and continues
```

---

## 2. Base Agent Class

All agents inherit from `BaseAgent`:

```python
# agents/base.py (simplified)

from abc import ABC, abstractmethod
import logging
from typing import Any

class BaseAgent(ABC):
    """Abstract base class for all AI agents."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent."""
        pass

    @abstractmethod
    def run(self, conn, config: dict) -> dict:
        """
        Execute the agent's main logic.

        Args:
            conn: MySQL database connection (PyMySQL)
            config: Agent-specific configuration from settings.yaml

        Returns:
            dict with at minimum:
            {
                "status": "success" | "error",
                "agent": self.name,
                "records_processed": int,
                "results": Any,
                "error": str | None
            }
        """
        pass

    def validate_output(self, output: dict) -> bool:
        """Validate the output dict has required fields."""
        required = ["status", "agent", "records_processed"]
        return all(k in output for k in required)

    def log_execution(self, output: dict, duration: float):
        """Log agent execution metrics."""
        self.logger.info(
            f"Agent {self.name} completed in {duration:.2f}s "
            f"| Status: {output.get('status')} "
            f"| Records: {output.get('records_processed', 0)}"
        )
```

---

## 3. Building a New Agent

### Step 1: Create the Agent File

```python
# agents/market_sizing_agent.py

import logging
from typing import Any
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class MarketSizingAgent(BaseAgent):
    """Estimates TAM/SAM/SOM for sectors and geographies."""

    @property
    def name(self) -> str:
        return "market_sizing"

    def run(self, conn, config: dict) -> dict:
        """
        Calculate market sizes for all sectors.

        Steps:
        1. Read sector data from database
        2. Gather funding totals, startup counts, survival rates
        3. Apply TAM/SAM/SOM formulas
        4. Use LLM for qualitative estimation
        5. Write results to market_sizes table
        6. Return summary
        """
        try:
            # Step 1: Read input data
            sectors = self._read_sectors(conn)
            logger.info(f"Processing {len(sectors)} sectors")

            # Step 2: Calculate market sizes
            results = []
            for sector in sectors:
                market_size = self._calculate_market_size(conn, sector, config)
                results.append(market_size)

            # Step 3: Write to database
            self._write_results(conn, results)

            return {
                "status": "success",
                "agent": self.name,
                "records_processed": len(results),
                "results": {
                    "sectors_analyzed": len(results),
                    "avg_tam": sum(r["tam"] for r in results) / len(results) if results else 0,
                },
                "error": None,
            }

        except Exception as e:
            logger.error(f"Market sizing failed: {e}")
            return {
                "status": "error",
                "agent": self.name,
                "records_processed": 0,
                "results": None,
                "error": str(e),
            }

    def _read_sectors(self, conn) -> list[dict]:
        """Read all sectors from database."""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT sector, COUNT(*) as startup_count
                FROM failed_startups
                GROUP BY sector
            """)
            return [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]

    def _calculate_market_size(self, conn, sector: dict, config: dict) -> dict:
        """
        Calculate TAM/SAM/SOM for a sector.

        Formula:
        TAM = total_addressable_market (global market size for sector)
        SAM = serviceable_addressable_market (TAM × geographic_factor)
        SOM = serviceable_obtainable_market (SAM × capture_rate)
        """
        sector_name = sector["sector"]
        startup_count = sector["startup_count"]

        # Get funding data
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(funding_amount), 0) as total_funding
                FROM failed_startups
                WHERE sector = %s
            """, (sector_name,))
            row = cur.fetchone()
            total_funding = row[0] if row else 0

        # Simple estimation (enhance with real market data)
        tam = max(total_funding * 50, 1_000_000)  # Minimum $1M TAM
        sam = tam * 0.3  # 30% geographic reach
        som = sam * 0.05  # 5% capture rate

        return {
            "sector": sector_name,
            "tam": tam,
            "sam": sam,
            "som": som,
            "startup_count": startup_count,
            "total_funding": total_funding,
            "opportunity_score": min(som / max(tam, 1) * 100, 100),
        }

    def _write_results(self, conn, results: list[dict]):
        """Write market size results to database."""
        with conn.cursor() as cur:
            for r in results:
                cur.execute("""
                    INSERT INTO market_sizes
                        (sector, tam, sam, som, startup_count, total_funding,
                         opportunity_score, calculated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        tam = VALUES(tam),
                        sam = VALUES(sam),
                        som = VALUES(som),
                        opportunity_score = VALUES(opportunity_score),
                        calculated_at = NOW()
                """, (
                    r["sector"], r["tam"], r["sam"], r["som"],
                    r["startup_count"], r["total_funding"],
                    r["opportunity_score"],
                ))
            conn.commit()
```

---

## 4. Agent Registration

### Step 1: Add to Orchestrator Registry

```python
# agents/orchestrator.py

# Add import at top
from agents.market_sizing_agent import MarketSizingAgent

# Add to AGENT_REGISTRY dict
AGENT_REGISTRY = {
    # ... existing agents ...
    "market_sizing": MarketSizingAgent,
}

# Add to _get_agent_class method (if used)
def _get_agent_class(self, agent_name: str):
    agent_map = {
        # ... existing agents ...
        "market_sizing": MarketSizingAgent,
    }
    return agent_map.get(agent_name)
```

### Step 2: Add to Pipeline Config

```yaml
# config/settings.yaml

agents:
  # ... existing agents ...

  market_sizing:
    enabled: true
    schedule: weekly
    config:
      minimum_tam: 1000000
      geographic_factor: 0.3
      capture_rate: 0.05
      use_llm: true
```

### Step 3: Add Database Table

```python
# db/schema.py — add to _create_tables()

cur.execute("""
    CREATE TABLE IF NOT EXISTS market_sizes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sector VARCHAR(255) NOT NULL,
        tam DECIMAL(15, 2) NOT NULL DEFAULT 0,
        sam DECIMAL(15, 2) NOT NULL DEFAULT 0,
        som DECIMAL(15, 2) NOT NULL DEFAULT 0,
        startup_count INT NOT NULL DEFAULT 0,
        total_funding DECIMAL(15, 2) NOT NULL DEFAULT 0,
        opportunity_score FLOAT NOT NULL DEFAULT 0,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_sector (sector),
        INDEX idx_opportunity (opportunity_score DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")
```

### Step 4: Add to CLI

```python
# run_agent.py — add to available agents

AVAILABLE_AGENTS = [
    # ... existing agents ...
    "market_sizing",
]
```

---

## 5. Testing Your Agent

### Unit Test Template

```python
# tests/test_market_sizing.py

import pytest
from unittest.mock import MagicMock, patch
from agents.market_sizing_agent import MarketSizingAgent


@pytest.fixture
def agent():
    return MarketSizingAgent()


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


class TestMarketSizingAgent:

    def test_name(self, agent):
        assert agent.name == "market_sizing"

    def test_run_success(self, agent, mock_conn):
        conn, cursor = mock_conn

        # Mock sector data
        cursor.fetchall.return_value = [
            ("Manufacturing", 15),
            ("SaaS", 25),
        ]
        cursor.fetchone.return_value = (5000000,)

        config = {"minimum_tam": 1000000, "geographic_factor": 0.3}

        result = agent.run(conn, config)

        assert result["status"] == "success"
        assert result["agent"] == "market_sizing"
        assert result["records_processed"] == 2
        assert result["error"] is None

    def test_run_empty_sectors(self, agent, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.return_value = []

        result = agent.run(conn, {})

        assert result["status"] == "success"
        assert result["records_processed"] == 0

    def test_run_database_error(self, agent, mock_conn):
        conn, cursor = mock_conn
        cursor.execute.side_effect = Exception("DB connection lost")

        result = agent.run(conn, {})

        assert result["status"] == "error"
        assert "DB connection lost" in result["error"]

    def test_validate_output(self, agent):
        valid = {
            "status": "success",
            "agent": "market_sizing",
            "records_processed": 5,
        }
        assert agent.validate_output(valid) is True

        invalid = {"status": "success"}
        assert agent.validate_output(invalid) is False

    def test_market_size_calculation(self, agent, mock_conn):
        conn, cursor = mock_conn

        sector = {"sector": "AI/ML", "startup_count": 30}
        cursor.fetchone.return_value = (10000000,)

        result = agent._calculate_market_size(conn, sector, {})

        assert result["sector"] == "AI/ML"
        assert result["tam"] == 500_000_000  # 10M * 50
        assert result["sam"] == 150_000_000  # 500M * 0.3
        assert result["som"] == 7_500_000    # 150M * 0.05
        assert result["startup_count"] == 30
        assert 0 <= result["opportunity_score"] <= 100
```

### Integration Test Template

```python
# tests/test_phase5_integration.py

import pytest
from db.connection import get_connection
from agents.market_sizing_agent import MarketSizingAgent


@pytest.mark.integration
class TestMarketSizingIntegration:

    def test_full_pipeline(self):
        """Test agent with real database."""
        conn = get_connection()
        agent = MarketSizingAgent()

        result = agent.run(conn, {"minimum_tam": 1000000})

        assert result["status"] == "success"
        assert result["records_processed"] > 0

        # Verify data was written
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM market_sizes")
            count = cur.fetchone()[0]
            assert count > 0

        conn.close()
```

---

## 6. Agent Patterns

### Pattern 1: Database Reader Agent

```python
"""Reads from DB, processes, writes back to DB."""

class ReaderAgent(BaseAgent):
    def run(self, conn, config):
        # Read
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM source_table WHERE processed = FALSE")
            rows = cur.fetchall()

        # Process
        results = [self._process(row) for row in rows]

        # Write
        with conn.cursor() as cur:
            for r in results:
                cur.execute("INSERT INTO output_table ...", (r["field"],))
            conn.commit()

        return {"status": "success", "records_processed": len(results)}
```

### Pattern 2: LLM-Enhanced Agent

```python
"""Uses Ollama LLM for analysis."""

class LLMAgent(BaseAgent):
    def run(self, conn, config):
        rows = self._read_data(conn)

        for row in rows:
            prompt = self._build_prompt(row)
            response = self._call_llm(prompt)
            structured = self._parse_response(response)
            self._write_result(conn, row, structured)

        return {"status": "success", "records_processed": len(rows)}

    def _call_llm(self, prompt: str) -> str:
        import requests
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False}
        )
        return response.json()["response"]
```

### Pattern 3: Scoring Agent

```python
"""Produces scores (0-100) with feature attribution."""

class ScoringAgent(BaseAgent):
    def run(self, conn, config):
        entities = self._read_entities(conn)

        scores = []
        for entity in entities:
            score, attribution = self._calculate_score(entity, config)
            scores.append({
                "entity_id": entity["id"],
                "score": score,
                "attribution": attribution,
            })
            self._write_score(conn, entity["id"], score, attribution)

        return {
            "status": "success",
            "records_processed": len(scores),
            "results": {
                "avg_score": sum(s["score"] for s in scores) / len(scores),
                "high_score_count": sum(1 for s in scores if s["score"] >= 70),
            }
        }

    def _calculate_score(self, entity, config) -> tuple[float, list]:
        features = config.get("features", {})
        total = 0
        attribution = []

        for feature_name, weight in features.items():
            value = entity.get(feature_name, 0)
            contribution = value * weight
            total += contribution
            attribution.append({
                "feature": feature_name,
                "value": value,
                "weight": weight,
                "contribution": contribution,
            })

        score = min(max(total, 0), 100)
        return score, attribution
```

### Pattern 4: Graph Agent

```python
"""Operates on the knowledge graph."""

class GraphAgent(BaseAgent):
    def run(self, conn, config):
        # Read graph data
        entities = self._read_entities(conn)
        relationships = self._read_relationships(conn)

        # Build adjacency
        graph = self._build_graph(entities, relationships)

        # Run algorithm
        results = self._run_algorithm(graph, config)

        # Write back
        self._write_results(conn, results)

        return {"status": "success", "records_processed": len(results)}

    def _build_graph(self, entities, relationships):
        import networkx as nx
        G = nx.DiGraph()
        for e in entities:
            G.add_node(e["id"], **e)
        for r in relationships:
            G.add_edge(r["source_id"], r["target_id"], type=r["type"])
        return G
```

### Pattern 5: Streaming Agent

```python
"""Consumes from Kafka, processes, produces to Kafka."""

class StreamingAgent(BaseAgent):
    def run(self, conn, config):
        from kafka import KafkaConsumer, KafkaProducer

        consumer = KafkaConsumer(
            "raw.signals",
            bootstrap_servers=config.get("kafka_brokers", "localhost:9092"),
            group_id=f"{self.name}-group",
            auto_offset_reset="latest",
        )

        producer = KafkaProducer(
            bootstrap_servers=config.get("kafka_brokers", "localhost:9092"),
        )

        processed = 0
        for message in consumer:
            if processed >= config.get("max_messages", 100):
                break

            signal = json.loads(message.value)
            enriched = self._process_signal(signal)
            producer.send("enriched.signals", json.dumps(enriched).encode())
            processed += 1

        consumer.close()
        producer.close()

        return {"status": "success", "records_processed": processed}
```

---

## 7. Configuration

### settings.yaml Structure

```yaml
agents:
  agent_name:
    enabled: true | false
    schedule: daily | weekly | monthly | realtime
    timeout: 300          # seconds
    retries: 3
    config:
      # Agent-specific config here
      param1: value1
      param2: value2
```

### Reading Config in Agent

```python
def run(self, conn, config: dict) -> dict:
    # Config comes from settings.yaml -> orchestrator -> agent
    timeout = config.get("timeout", 300)
    param1 = config.get("param1", "default_value")

    # You can also read from environment
    import os
    api_key = os.environ.get("MY_API_KEY")
```

---

## 8. Database Schema for Agents

### Creating Tables for Your Agent

```python
# db/schema.py

# Add to _create_tables() method
# Follow existing naming convention: snake_case, plural table names

def _create_agent_output_tables(self, cur):
    """Create tables for agent output data."""

    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_outputs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            agent_name VARCHAR(100) NOT NULL,
            entity_type VARCHAR(100),
            entity_id INT,
            score FLOAT,
            data JSON,
            calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_agent (agent_name),
            INDEX idx_score (score DESC),
            INDEX idx_entity (entity_type, entity_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
```

### Schema Naming Conventions

| Pattern | Example | When to Use |
|---|---|---|
| `{entity}_scores` | `opportunity_scores`, `risk_scores` | When agent produces scores |
| `{entity}_analysis` | `failure_analysis`, `survival_analysis` | When agent produces analysis |
| `{entity}_sizes` | `market_sizes` | When agent produces measurements |
| `{entity}_events` | `signal_events`, `anomaly_events` | When agent produces events |
| `{entity}_graphs` | `community_graphs`, `influence_graphs` | When agent produces graph data |

---

## 9. Best Practices

### Do ✅

| Practice | Why |
|---|---|
| Always inherit from `BaseAgent` | Consistent interface, orchestrator can manage it |
| Return a dict with `status`, `agent`, `records_processed` | Orchestrator expects this format |
| Use `try/except` around database operations | Don't crash the entire pipeline |
| Log progress with `self.logger.info()` | Debug pipeline issues |
| Write idempotent agents (safe to run twice) | Pipeline may retry on failure |
| Use `ON DUPLICATE KEY UPDATE` for writes | Avoid duplicates |
| Add indexes on frequently queried columns | Performance at scale |
| Create one test file per agent | Clean test organization |
| Mock database in unit tests | Fast, deterministic tests |
| Add `@pytest.mark.integration` for DB tests | Can skip in CI |

### Don't ❌

| Anti-Pattern | Why |
|---|---|
| Hardcode database credentials | Use `config` parameter or environment variables |
| Print to stdout | Use `self.logger` instead |
| Modify other agents' tables | Each agent owns its output tables |
| Make external API calls without rate limiting | Will get blocked |
| Ignore `config["enabled"]` flag | User expects disabled agents to not run |
| Write tests that depend on specific data | Use mocks or fixtures |
| Create circular agent dependencies | Orchestrator runs agents sequentially |
| Store large blobs in MySQL | Use file storage or ClickHouse for large data |

---

## 10. Complete Example: Sentiment Agent

### Full Agent Code

```python
# agents/sentiment_agent.py

"""
Sentiment Analysis Agent

Analyzes sentiment of news articles and social media posts
related to tracked startups. Produces sentiment scores (-1 to +1)
and tracks sentiment trends over time.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Any
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class SentimentAgent(BaseAgent):
    """Analyzes sentiment across news and social media for tracked entities."""

    @property
    def name(self) -> str:
        return "sentiment"

    def run(self, conn, config: dict) -> dict:
        """
        Run sentiment analysis on unprocessed articles and posts.

        Pipeline:
        1. Read unprocessed articles from news_articles table
        2. Read unprocessed posts from social_posts table
        3. Analyze sentiment using keyword + LLM hybrid
        4. Write sentiment_scores to database
        5. Update entity-level sentiment aggregates
        6. Return summary
        """
        try:
            # Config
            batch_size = config.get("batch_size", 100)
            use_llm = config.get("use_llm", True)

            # Step 1: Read unprocessed content
            articles = self._read_unprocessed(conn, "news_articles", batch_size)
            posts = self._read_unprocessed(conn, "social_posts", batch_size)

            total_items = len(articles) + len(posts)
            logger.info(f"Processing {len(articles)} articles + {len(posts)} posts")

            # Step 2: Analyze sentiment
            results = []
            for item in articles + posts:
                sentiment = self._analyze_sentiment(item, use_llm)
                results.append(sentiment)

            # Step 3: Write results
            self._write_sentiment_scores(conn, results)

            # Step 4: Update aggregates
            self._update_aggregates(conn)

            return {
                "status": "success",
                "agent": self.name,
                "records_processed": total_items,
                "results": {
                    "articles_analyzed": len(articles),
                    "posts_analyzed": len(posts),
                    "avg_sentiment": (
                        sum(r["sentiment"] for r in results) / len(results)
                        if results else 0
                    ),
                    "positive_count": sum(1 for r in results if r["sentiment"] > 0.2),
                    "negative_count": sum(1 for r in results if r["sentiment"] < -0.2),
                    "neutral_count": sum(1 for r in results if -0.2 <= r["sentiment"] <= 0.2),
                },
                "error": None,
            }

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}", exc_info=True)
            return {
                "status": "error",
                "agent": self.name,
                "records_processed": 0,
                "results": None,
                "error": str(e),
            }

    def _read_unprocessed(self, conn, table: str, limit: int) -> list[dict]:
        """Read items not yet analyzed for sentiment."""
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, title, content, source, published_date
                FROM {table}
                WHERE sentiment_processed = FALSE
                  AND content IS NOT NULL
                ORDER BY published_date DESC
                LIMIT %s
            """, (limit,))
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def _analyze_sentiment(self, item: dict, use_llm: bool) -> dict:
        """
        Hybrid sentiment analysis:
        1. Keyword-based quick scoring
        2. LLM refinement (if enabled)
        """
        text = f"{item.get('title', '')} {item.get('content', '')}"

        # Keyword-based baseline
        score = self._keyword_sentiment(text)

        # LLM refinement for ambiguous cases
        if use_llm and abs(score) < 0.3:
            llm_score = self._llm_sentiment(text[:500])
            if llm_score is not None:
                score = (score + llm_score) / 2  # Average both

        return {
            "source_id": item["id"],
            "source_table": "news_articles" if "title" in item else "social_posts",
            "source": item.get("source", "unknown"),
            "sentiment": round(score, 3),
            "confidence": 0.8 if abs(score) > 0.5 else 0.5,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    def _keyword_sentiment(self, text: str) -> float:
        """Simple keyword-based sentiment scoring."""
        text_lower = text.lower()

        positive = [
            "growth", "profit", "success", "launch", "funding", "expand",
            "innovate", "breakthrough", "milestone", "partner", "acquire",
            "hire", "revenue", "up", "bullish", "opportunity", "revival",
        ]
        negative = [
            "fail", "bankrupt", "shutdown", "layoff", "loss", "decline",
            "close", "debt", "lawsuit", "fraud", "crash", "down", "bearish",
            "risk", "warning", "distress", "default", "fire",
        ]

        pos_count = sum(1 for w in positive if w in text_lower)
        neg_count = sum(1 for w in negative if w in text_lower)

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        return (pos_count - neg_count) / total  # Range: -1 to +1

    def _llm_sentiment(self, text: str) -> float | None:
        """Use Ollama LLM for sentiment analysis."""
        try:
            import requests
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": f"Rate the sentiment of this text from -1 (very negative) to +1 (very positive). Reply with ONLY a number:\n\n{text}",
                    "stream": False,
                },
                timeout=30,
            )
            result = response.json()["response"].strip()
            return float(result)
        except (ValueError, TypeError, Exception) as e:
            logger.warning(f"LLM sentiment failed: {e}")
            return None

    def _write_sentiment_scores(self, conn, results: list[dict]):
        """Write sentiment scores and mark items as processed."""
        with conn.cursor() as cur:
            for r in results:
                # Write score
                cur.execute("""
                    INSERT INTO sentiment_scores
                        (source_id, source_table, source, sentiment, confidence, analyzed_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    r["source_id"], r["source_table"], r["source"],
                    r["sentiment"], r["confidence"], r["analyzed_at"],
                ))

                # Mark as processed
                cur.execute(f"""
                    UPDATE {r["source_table"]}
                    SET sentiment_processed = TRUE
                    WHERE id = %s
                """, (r["source_id"],))

            conn.commit()

    def _update_aggregates(self, conn):
        """Update entity-level sentiment aggregates."""
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO entity_sentiment (entity_name, entity_type, avg_sentiment, post_count, updated_at)
                SELECT
                    ks.entity_name,
                    'startup' as entity_type,
                    AVG(ss.sentiment) as avg_sentiment,
                    COUNT(*) as post_count,
                    NOW() as updated_at
                FROM sentiment_scores ss
                JOIN news_articles na ON ss.source_id = na.id
                JOIN kg_entities ks ON na.title LIKE CONCAT('%', ks.entity_name, '%')
                WHERE ss.analyzed_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY ks.entity_name
                ON DUPLICATE KEY UPDATE
                    avg_sentiment = VALUES(avg_sentiment),
                    post_count = VALUES(post_count),
                    updated_at = NOW()
            """)
            conn.commit()
```

### Full Test Code

```python
# tests/test_sentiment_agent.py

import pytest
from unittest.mock import MagicMock, patch
from agents.sentiment_agent import SentimentAgent


@pytest.fixture
def agent():
    return SentimentAgent()


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cursor


class TestSentimentAgent:

    def test_name(self, agent):
        assert agent.name == "sentiment"

    def test_keyword_sentiment_positive(self, agent):
        text = "The startup showed incredible growth and revenue this quarter"
        score = agent._keyword_sentiment(text)
        assert score > 0

    def test_keyword_sentiment_negative(self, agent):
        text = "The company announced layoffs and bankruptcy filing"
        score = agent._keyword_sentiment(text)
        assert score < 0

    def test_keyword_sentiment_neutral(self, agent):
        text = "The company is located in San Francisco"
        score = agent._keyword_sentiment(text)
        assert score == 0.0

    def test_keyword_sentiment_mixed(self, agent):
        text = "Despite growth, the company announced layoffs"
        score = agent._keyword_sentiment(text)
        assert -1 <= score <= 1

    @patch("agents.sentiment_agent.requests.post")
    def test_llm_sentiment_success(self, mock_post, agent):
        mock_post.return_value.json.return_value = {"response": "0.7"}
        score = agent._llm_sentiment("Great news about the startup")
        assert score == 0.7

    @patch("agents.sentiment_agent.requests.post")
    def test_llm_sentiment_failure(self, mock_post, agent):
        mock_post.side_effect = Exception("Connection refused")
        score = agent._llm_sentiment("Some text")
        assert score is None

    def test_run_success(self, agent, mock_conn):
        conn, cursor = mock_conn

        # Mock unprocessed items
        cursor.fetchall.side_effect = [
            [(1, "Title1", "Great growth content", "techcrunch", "2024-01-01")],
            [(2, "Post1", "Layoffs announced", "reddit", "2024-01-01")],
        ]

        config = {"batch_size": 10, "use_llm": False}
        result = agent.run(conn, config)

        assert result["status"] == "success"
        assert result["records_processed"] == 2
        assert result["results"]["positive_count"] >= 1
        assert result["results"]["negative_count"] >= 1

    def test_run_empty(self, agent, mock_conn):
        conn, cursor = mock_conn
        cursor.fetchall.side_effect = [[], []]

        result = agent.run(conn, {})

        assert result["status"] == "success"
        assert result["records_processed"] == 0

    def test_analyze_sentiment_without_llm(self, agent):
        item = {"id": 1, "title": "Startup raises funding", "content": "Great growth"}
        result = agent._analyze_sentiment(item, use_llm=False)

        assert result["source_id"] == 1
        assert result["sentiment"] > 0
        assert 0 <= result["confidence"] <= 1
```

---

## Checklist: Publishing Your Agent

- [ ] Agent file created in `agents/`
- [ ] Inherits from `BaseAgent`
- [ ] Implements `name` property and `run()` method
- [ ] Registered in `agents/orchestrator.py` (AGENT_REGISTRY)
- [ ] Configuration added to `config/settings.yaml`
- [ ] Database table created in `db/schema.py`
- [ ] Schema version bumped
- [ ] Unit tests created in `tests/test_{agent_name}.py`
- [ ] All existing tests still pass (`pytest tests/`)
- [ ] Agent runs successfully: `python run_agent.py --agent {name}`
- [ ] Output validated in database
- [ ] No import errors: `python -c "from agents.{name} import {ClassName}"`

---

*Last updated: June 5, 2026*

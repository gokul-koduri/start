# ⚡ How to Make OIP Work in Real Time — Complete Technical Blueprint

> From "data gets collected eventually" to "user sees an alert within 15 minutes of a real-world event"

---

## Table of Contents

1. [What "Real Time" Means for OIP](#1-what-real-time-means-for-oip)
2. [What's Already Built](#2-whats-already-built)
3. [The Real-Time Architecture (Full Diagram)](#3-the-real-time-architecture)
4. [Component 1: Real-Time Collectors](#4-component-1-real-time-collectors)
5. [Component 2: Kafka Message Bus](#5-component-2-kafka-message-bus)
6. [Component 3: Bytewax Stream Processor](#6-component-3-bytewax-stream-processor)
7. [Component 4: Scoring in Real Time](#7-component-4-scoring-in-real-time)
8. [Component 5: Alerting Pipeline](#8-component-5-alerting-pipeline)
9. [Component 6: Push to Users (WebSocket + SSE)](#9-component-6-push-to-users)
10. [Component 7: NLP Without Blocking](#10-component-7-nlp-without-blocking)
11. [Component 8: Knowledge Graph Updates](#11-component-8-knowledge-graph-updates)
12. [Infrastructure You Need to Run](#12-infrastructure-you-need-to-run)
13. [Step-by-Step: Setting Up Real Time](#13-step-by-step-setup)
14. [Monitoring & Observability](#14-monitoring--observability)
15. [What Still Needs to Be Built](#15-what-still-needs-to-be-built)
16. [Cost Estimates](#16-cost-estimates)

---

## 1. What "Real Time" Means for OIP

Real time doesn't mean "instant" — it means **fast enough that the information is still valuable when it reaches the user**.

```
TIER 1: TRUE REAL-TIME (< 1 minute)
  Reddit posts, Hacker News stories, Twitter/X tweets
  → These sources support streaming APIs
  → Signal → Kafka → Process → Alert in under 60 seconds

TIER 2: NEAR REAL-TIME (5-15 minutes)
  News RSS feeds, GitHub trends, SEC EDGAR filings
  → These are polled every 5-15 minutes
  → Signal → Kafka → Process → Alert in 5-15 minutes

TIER 3: DAILY BATCH (once per day)
  BLS data, patent filings, OpenCorporates, regulatory filings
  → These sources update daily or less
  → No point checking more often than they update

TIER 4: WEEKLY/MONTHLY (periodic)
  Reshoring PDFs, newsletter content, deep analysis
  → These are inherently slow-moving sources
```

### The Target: End-to-End Latency

```
EVENT IN REAL WORLD
  "Neuromorphic Labs raises $5M Series A"
  │
  ├─ TIER 1 (Twitter/X):  0-60 seconds  → alert
  ├─ TIER 2 (TechCrunch): 5-15 minutes   → alert
  ├─ TIER 2 (Crunchbase): 4-8 hours      → alert
  ├─ TIER 2 (SEC EDGAR):  4-8 hours      → alert
  ├─ TIER 3 (Patents):    Next day       → score update
  └─ TIER 4 (Analysis):   Next week      → report
```

---

## 2. What's Already Built

The codebase already has significant real-time infrastructure:

```
✅ ALREADY WORKING:

1. Kafka Producer (ingestion/kafka_producer.py)
   - SignalKafkaProducer class
   - Publishes SignalEnvelope to Kafka topics
   - Auto-serialized to JSON
   - Dual-write: MySQL + Kafka simultaneously
   - Graceful fallback if Kafka unavailable

2. Bytewax Stream Pipeline (stream/pipeline.py)
   - 5-stage dataflow: Ingest → Enrich → Aggregate → Score → Output
   - Reads from Kafka topic "raw.signals"
   - Writes scored entities to MySQL opportunity_scores
   - Publishes to "scores.updates" and "alerts.triggered" topics
   - Tumbling window aggregation (configurable, default 5 min)
   - Simulated input for testing without Kafka

3. Stream Operators (stream/operators.py)
   - parse_signal_envelope(): Deserialize Kafka messages
   - enrich_signal(): Fast keyword-based sentiment (no external deps)
   - score_entity(): Runs CompositeScorer on aggregated signals
   - write_score_to_mysql(): Upserts to opportunity_scores table
   - emit_alert(): Creates alert if score > threshold (default 80)

4. Entity State Management (stream/state.py)
   - EntityState: Rolling buffer of 100 signals per entity
   - Score history for anomaly detection (50 scores)
   - Thread-safe state updates

5. Pipeline Metrics (stream/metrics.py)
   - PipelineMetrics: 12 counters (signals_processed, entities_scored, etc.)
   - MetricsWriter: Flushes to Redis every 30 seconds
   - Throughput calculation (signals/minute)

6. Real-Time Collectors:
   - HN Live (collectors/hn_live_collector.py): Firebase API streaming
   - Reddit Stream (collectors/reddit_stream_collector.py): PRAW streaming
   - Both publish to Kafka via BaseCollector.publish_signal()

7. WebSocket Server (api_server.py)
   - /ws/live endpoint with ConnectionManager
   - Broadcasts stats_update every 30 seconds
   - Manages multiple connected clients

8. Stream Status API (api_server.py)
   - /api/stream/status endpoint
   - Reads metrics from Redis
   - Reports pipeline health: healthy/stale/not_started/degraded

9. Docker Compose (docker-compose.yml)
   - All 10 infrastructure services defined:
     MySQL, Ollama, API, Streamlit, Pipeline, Stream Processor,
     Redis, Kafka (Redpanda), Qdrant, Elasticsearch, ClickHouse,
     TimescaleDB

10. Base Collector (collectors/base.py)
    - publish_signal() method: every collector can publish to Kafka
    - Lazy Kafka producer initialization
    - Silent fallback if Kafka unavailable
```

---

## 3. The Real-Time Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  REAL-WORLD EVENT                                                       │
│  "Startup X raises $5M Series A"                                        │
│                                                                         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
   ┌─────────┐           ┌─────────┐           ┌─────────────┐
   │ Twitter │           │TechCrunch│          │ Crunchbase   │
   │ STREAM  │           │  RSS    │           │    API       │
   │ <1 min  │           │ 15 min  │           │ 4 hours      │
   └────┬────┘           └────┬────┘           └──────┬───────┘
        │                     │                       │
        ▼                     ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  COLLECTORS (24 collectors, each in own thread/container)               │
│                                                                         │
│  Each collector does TWO things simultaneously:                         │
│    1. Write to MySQL (durable storage — always works)                   │
│    2. Publish to Kafka (real-time stream — if available)                │
│                                                                         │
│  publish_signal() → SignalEnvelope → KafkaProducer.send()               │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐         │
│  │  REAL-TIME COLLECTORS (Tier 1 - always running):         │         │
│  │  • twitter_collector.py    → Streaming API (continuous)  │         │
│  │  • reddit_stream_collector → PRAW stream (continuous)    │         │
│  │  • hn_live_collector.py    → Firebase API (continuous)   │         │
│  │                                                          │         │
│  │  NEAR-REAL-TIME (Tier 2 - polled):                       │         │
│  │  • google_news_rss.py      → Every 15 min               │         │
│  │  • techcrunch_rss.py       → Every 15 min               │         │
│  │  • sec_edgar_collector.py  → Every 4 hours              │         │
│  │  • github_trends_collector → Every hour                  │         │
│  │  • funding_events_collector→ Every 4 hours              │         │
│  │  • job_postings_collector  → Every 6 hours              │         │
│  │  • patent_collector.py     → Daily                      │         │
│  │  • github_deep_collector   → Hourly                     │         │
│  │  • producthunt_collector   → Daily                      │         │
│  │  • website_monitor         → Daily                      │         │
│  │  • npm_pypi_collector      → Daily                      │         │
│  │  • stackoverflow_collector → Daily                      │         │
│  │  • newsletter_collector    → Daily                      │         │
│  │                                                          │         │
│  │  BATCH (Tier 3 - slow sources):                          │         │
│  │  • bls_survival_rates.py   → Monthly                    │         │
│  │  • failory_scraper.py      → Weekly                     │         │
│  │  • reshoring_pdf.py        → Monthly                    │         │
│  │  • opencorporates          → Weekly                     │         │
│  │  • arxiv_collector.py      → Daily                      │         │
│  │  • regulatory_collector    → Daily                      │         │
│  └──────────────────────────────────────────────────────────┘         │
│                                                                         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                │ SignalEnvelope (JSON)
                                │ published to Kafka topic "raw.signals"
                                │ partitioned by entity_name
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  REDPANDA (Kafka-Compatible)                                            │
│                                                                         │
│  Topics:                                                                │
│    raw.signals          ← All incoming signals (partitioned by entity)  │
│    raw.signals.{type}   ← Typed signals (optional)                     │
│    scores.updates       ← Scored entities from stream processor         │
│    alerts.triggered     ← High-priority alerts                          │
│    enrichment.requests  ← Heavy NLP work items                          │
│    enrichment.complete  ← NLP results back                              │
│    graph.updates        ← Knowledge graph changes                       │
│    dead.letters         ← Failed messages (for debugging)               │
│                                                                         │
│  Configuration:                                                         │
│    Partitions: 12 (by entity_name hash)                                 │
│    Replication: 1 (single node), 3 (production)                        │
│    Retention: 7 days                                                    │
│    Compression: snappy                                                  │
│                                                                         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                │ Consumer group "signal-processor"
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  BYTEWAX STREAM PROCESSOR (stream/pipeline.py)                         │
│  5-stage dataflow, runs continuously                                    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  STAGE 1: INGEST (_op_ingest)                               │       │
│  │  • KafkaSource reads from "raw.signals"                     │       │
│  │  • parse_signal_envelope() → (entity_name, SignalEnvelope)  │       │
│  │  • Invalid messages → dead letter queue                     │       │
│  │  • Metrics: signals_processed counter                       │       │
│  │  • Time: < 1 ms per signal                                 │       │
│  └──────────────────────────┬──────────────────────────────────┘       │
│                             │                                          │
│                             ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  STAGE 2: ENRICH (_op_enrich)                               │       │
│  │  • Keyword sentiment: positive_words vs negative_words      │       │
│  │  • Entity name normalization                                │       │
│  │  • Metadata: stream_enriched=True, stream_sentiment, time   │       │
│  │  • FAST: No external API calls (no spaCy, no Ollama)       │       │
│  │  • Time: < 1 ms per signal                                 │       │
│  │                                                              │       │
│  │  WHY FAST: Heavy NLP is done ASYNCHRONOUSLY (see below)    │       │
│  └──────────────────────────┬──────────────────────────────────┘       │
│                             │                                          │
│                             ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  STAGE 3: AGGREGATE (tumbling window)                       │       │
│  │  • Group signals by entity_name                              │       │
│  │  • Tumbling window: 5 minutes (configurable)                │       │
│  │  • Within each window: collect all signals per entity       │       │
│  │  • Output: (entity_name, [signal1, signal2, ...])           │       │
│  │  • Time: Waits for window to close (5 min max)             │       │
│  └──────────────────────────┬──────────────────────────────────┘       │
│                             │                                          │
│                             ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  STAGE 4: SCORE (_op_score)                                 │       │
│  │  • CompositeScorer.score() on aggregated signals            │       │
│  │  • Signal weights: funding 25%, SEC 20%, jobs 15%, etc.    │       │
│  │  • Time decay: recent signals weighted higher               │       │
│  │  • Anomaly detection: Z-score check on historical values    │       │
│  │  • Output: {entity, score, trend, attribution, confidence}  │       │
│  │  • Time: 10-50 ms per entity                                │       │
│  └──────────────────────────┬──────────────────────────────────┘       │
│                             │                                          │
│                             ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  STAGE 5: OUTPUT                                            │       │
│  │  • 5a: write_score_to_mysql() → opportunity_scores table    │       │
│  │  • 5b: KafkaSink → "scores.updates" topic                   │       │
│  │  • 5c: emit_alert() → if score > 80 → "alerts.triggered"   │       │
│  │  • Metrics: scores_written, alerts_emitted                  │       │
│  │  • Time: 5-20 ms per entity                                 │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  TOTAL PIPELINE LATENCY:                                                │
│    Best case (window already has signals): < 1 second                   │
│    Worst case (wait for window close): 5 minutes                        │
│    Typical: 30 seconds to 2 minutes                                     │
│                                                                         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
    │ MySQL        │   │ "scores.     │   │ "alerts.         │
    │ opportunity  │   │  updates"    │   │  triggered"      │
    │ _scores      │   │ Kafka topic  │   │ Kafka topic      │
    └──────────────┘   └──────┬───────┘   └───────┬──────────┘
                              │                   │
                              ▼                   ▼
                   ┌──────────────────┐  ┌──────────────────────┐
                   │  SCORE CONSUMER  │  │  ALERT DISPATCHER     │
                   │  (API Server)    │  │  (New component)      │
                   │                  │  │                       │
                   │  Reads scores.   │  │  Reads alerts.        │
                   │  updates topic   │  │  triggered topic      │
                   │  and pushes via  │  │  and sends via:       │
                   │  WebSocket/SSE   │  │  • Slack webhook      │
                   │  to connected    │  │  • Email (SMTP)       │
                   │  dashboards      │  │  • Discord webhook    │
                   │                  │  │  • Custom webhook     │
                   └──────────────────┘  └──────────────────────┘
                              │
                              ▼
                   ┌──────────────────────────────────────────────┐
                   │                                              │
                   │  USER'S BROWSER (Dashboard)                  │
                   │                                              │
                   │  Two real-time channels:                     │
                   │                                              │
                   │  1. WebSocket: /ws/live                      │
                   │     → Full stats update every 30 seconds     │
                   │     → Score updates pushed immediately       │
                   │     → Connected via ConnectionManager        │
                   │                                              │
                   │  2. SSE: /api/stream/scores (NEW)           │
                   │     → Server-Sent Events for score changes   │
                   │     → Lighter than WebSocket                 │
                   │     → Auto-reconnects on disconnect          │
                   │                                              │
                   │  3. Polling fallback: /api/opportunities     │
                   │     → Every 60 seconds if WS/SSE unavailable │
                   │                                              │
                   └──────────────────────────────────────────────┘
```

---

## 4. Component 1: Real-Time Collectors

### How Collectors Currently Work

Every collector extends `BaseCollector` which has a built-in `publish_signal()` method:

```python
# collectors/base.py — already implemented
class BaseCollector(ABC):
    def publish_signal(self, signal_type, title, entity_name,
                       source_url="", body_text="", raw_score=0.0, **metadata):
        """Publish a signal to Kafka for real-time processing.
        Fire-and-forget — if Kafka is unavailable, this silently skips.
        The collector's batch MySQL write is the primary data path."""
        if self.dry_run:
            return
        producer = self._get_kafka_producer()
        if producer is None:
            return
        envelope = normalize_signal(signal_type, self.name, ...)
        producer.send(envelope)
```

### How Each Collector Calls It

Look at any real-time collector — they already call `publish_signal()`:

```python
# collectors/hn_live_collector.py — line ~195
self.publish_signal(
    "hn_live",
    title=title[:1000],
    entity_name=entity_name,
    source_url=url,
    body_text=story_text[:5000],
    raw_score=raw_score,
    points=points,
    num_comments=descendants,
    platform="hacker_news",
)
```

### What Needs to Change: Continuous Running

Currently, collectors are run on-demand via `run_collectors.py`. For real-time, they need to run continuously:

```
CURRENT (batch):
  cron job → python run_collectors.py → runs all collectors → exits

NEEDED (real-time):
  ┌─────────────────────────────────────────────────────────┐
  │  COLLECTOR SCHEDULER (new component)                     │
  │                                                          │
  │  Runs 24/7, manages all collectors:                      │
  │                                                          │
  │  CONTINUOUS STREAMS (never stop):                        │
  │  ├── Twitter stream        → always running              │
  │  ├── Reddit stream (PRAW)  → always running              │
  │  └── HN Live (Firebase)    → always running              │
  │                                                          │
  │  HIGH-FREQUENCY POLLING (every 5-15 min):               │
  │  ├── Google News RSS       → every 15 min                │
  │  ├── TechCrunch RSS        → every 15 min                │
  │  ├── GitHub trends         → every 60 min                │
  │  └── Website monitor       → every 60 min                │
  │                                                          │
  │  MEDIUM-FREQUENCY (every 4-6 hours):                    │
  │  ├── SEC EDGAR             → every 4 hours               │
  │  ├── Funding events        → every 4 hours               │
  │  ├── Job postings          → every 6 hours               │
  │  └── GitHub deep           → every 4 hours               │
  │                                                          │
  │  LOW-FREQUENCY (daily/weekly):                           │
  │  ├── Patents               → daily at 6 AM               │
  │  ├── Product Hunt          → daily at 7 AM               │
  │  ├── NPM/PyPI              → daily at 8 AM               │
  │  ├── Stack Overflow        → daily at 9 AM               │
  │  ├── arXiv papers          → daily at 10 AM              │
  │  ├── OpenCorporates        → weekly (Sunday)             │
  │  ├── Regulatory            → daily at 11 AM              │
  │  ├── Newsletter            → daily at 12 PM              │
  │  ├── Failory               → weekly (Monday)             │
  │  └── BLS survival          → monthly (1st)               │
  │                                                          │
  │  Implementation: APScheduler (Python library)            │
  │  Run as: docker service or systemd unit                  │
  └─────────────────────────────────────────────────────────┘
```

### Collector Scheduler Implementation

```python
# NEW FILE: scheduler.py

import logging
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler
from collectors.hn_live_collector import HNLiveCollector
from collectors.reddit_stream_collector import RedditStreamCollector
from collectors.google_news_rss import GoogleNewsRSSCollector
from collectors.sec_edgar_collector import SECEdgarCollector
# ... import all collectors

logger = logging.getLogger(__name__)

class CollectorScheduler:
    """Manages continuous and scheduled collector execution."""

    def __init__(self, config: dict):
        self.config = config
        self.scheduler = BackgroundScheduler()
        self.threads = {}  # For continuous collectors

    def start(self):
        """Start all collectors on their schedules."""

        # ── Continuous streams (run in background threads) ──
        self._start_continuous("twitter", TwitterCollector(self.config))
        self._start_continuous("reddit_stream", RedditStreamCollector(self.config))
        self._start_continuous("hn_live", HNLiveCollector(self.config))

        # ── High-frequency polling ──
        self.scheduler.add_job(
            GoogleNewsRSSCollector(self.config).run, 'interval', minutes=15, id='google_news')
        self.scheduler.add_job(
            TechCrunchRSSCollector(self.config).run, 'interval', minutes=15, id='techcrunch')
        self.scheduler.add_job(
            GitHubTrendsCollector(self.config).run, 'interval', hours=1, id='github_trends')

        # ── Medium-frequency polling ──
        self.scheduler.add_job(
            SECEdgarCollector(self.config).run, 'interval', hours=4, id='sec_edgar')
        self.scheduler.add_job(
            FundingEventsCollector(self.config).run, 'interval', hours=4, id='funding')
        self.scheduler.add_job(
            JobPostingsCollector(self.config).run, 'interval', hours=6, id='jobs')

        # ── Low-frequency (daily) ──
        self.scheduler.add_job(
            PatentCollector(self.config).run, 'cron', hour=6, id='patents')
        self.scheduler.add_job(
            ProductHuntCollector(self.config).run, 'cron', hour=7, id='producthunt')
        self.scheduler.add_job(
            NPMPyPICollector(self.config).run, 'cron', hour=8, id='npm_pypi')

        self.scheduler.start()
        logger.info("Collector scheduler started with %d jobs",
                    len(self.scheduler.get_jobs()))

        # Keep main thread alive
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            self.stop()

    def _start_continuous(self, name: str, collector):
        """Start a collector that runs continuously in a background thread."""
        def run_loop():
            logger.info("Starting continuous collector: %s", name)
            while True:
                try:
                    result = collector.run()
                    logger.info("%s: %d collected", name, result.records_collected)
                except Exception as e:
                    logger.error("%s error: %s", name, e)
                time.sleep(30)  # Brief pause between runs

        thread = threading.Thread(target=run_loop, daemon=True, name=name)
        thread.start()
        self.threads[name] = thread

    def stop(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
```

---

## 5. Component 2: Kafka Message Bus

### Already Configured in Docker Compose

```yaml
# docker-compose.yml — already defined
kafka:
  image: docker.redpanda.com/redpandadata/redpanda:latest
  ports:
    - "9092:9092"
  healthcheck:
    test: ["CMD-SHELL", "rpk cluster health | grep -E 'Healthy|under-replication'"]
```

### Topic Setup Script Needed

```bash
# NEW FILE: scripts/create-topics.sh

#!/bin/bash
# Create Kafka topics for OIP real-time pipeline

BROKER="localhost:9092"

echo "Creating Kafka topics..."

# Main signal topic (partitioned by entity_name for parallelism)
rpk topic create raw.signals \
  --partitions 12 \
  --replication-factor 1 \
  --retention 604800000 \  # 7 days in ms
  --compression snappy \
  --brokers $BROKER

# Scored entities
rpk topic create scores.updates \
  --partitions 6 \
  --replication-factor 1 \
  --brokers $BROKER

# High-priority alerts
rpk topic create alerts.triggered \
  --partitions 3 \
  --replication-factor 1 \
  --brokers $BROKER

# Heavy NLP work queue
rpk topic create enrichment.requests \
  --partitions 6 \
  --replication-factor 1 \
  --brokers $BROKER

# NLP results
rpk topic create enrichment.complete \
  --partitions 6 \
  --replication-factor 1 \
  --brokers $BROKER

# Knowledge graph updates
rpk topic create graph.updates \
  --partitions 3 \
  --replication-factor 1 \
  --brokers $BROKER

# Dead letter queue
rpk topic create dead.letters \
  --partitions 3 \
  --replication-factor 1 \
  --brokers $BROKER

echo "Topics created. Verify with: rpk topic list --brokers $BROKER"
```

### Data Flow Through Kafka

```
COLLECTOR                     KAFKA TOPIC              CONSUMER
─────────                     ───────────              ────────

Twitter ─────┐
Reddit ──────┤
HN Live ─────┤                raw.signals          ┌─ Bytewax (stream processor)
News RSS ────┤ ──────────→    (partitioned by       │
TechCrunch ──┤                entity_name)          │
SEC EDGAR ───┤                                      │
GitHub ──────┘                                      │
                                                    │
                                         ┌──────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │  Bytewax Pipeline    │
                              │  5-stage dataflow    │
                              └──────────┬───────────┘
                                         │
                          ┌──────────────┼──────────────┐
                          │              │              │
                          ▼              ▼              ▼
                    scores.updates  alerts.triggered  enrichment.requests
                          │              │              │
                          ▼              ▼              ▼
                   ┌────────────┐ ┌────────────┐ ┌─────────────────┐
                   │ API Server │ │  Alert      │ │  NLP Worker     │
                   │ WebSocket  │ │  Dispatcher │ │  (spaCy+Ollama) │
                   │ push       │ │ (Slack/     │ │                 │
                   └────────────┘ │  Email/     │ └────────┬────────┘
                                  │  Webhook)   │          │
                                  └─────────────┘          ▼
                                                     enrichment.complete
                                                            │
                                                            ▼
                                                     Knowledge Graph
                                                      Update Worker
```

---

## 6. Component 3: Bytewax Stream Processor

### Already Built — What It Does

The stream processor in `stream/pipeline.py` is already fully implemented:

```python
# stream/pipeline.py — already implemented
def build_pipeline():
    flow = Dataflow("signal_processing")

    # Stage 1: Read from Kafka
    source = KafkaSource(brokers=..., topics=["raw.signals"])
    flow.input("kafka_in", source)

    # Stage 2: Fast enrichment (keyword sentiment, no API calls)
    flow.map(_op_enrich)

    # Stage 3: Aggregate by entity in tumbling windows
    flow.reduce_window(_collect_signals, TumblingClocker(300))

    # Stage 4: Score using CompositeScorer
    flow.map(_op_score)

    # Stage 5a: Write to MySQL
    flow.map(_op_write_mysql)

    # Stage 5b: Output scores to Kafka
    flow.output("kafka_scores", KafkaSink(..., topic="scores.updates"))

    # Stage 5c: Alert emission
    flow.filter(_op_emit_alert)
    flow.output("kafka_alerts", KafkaSink(..., topic="alerts.triggered"))

    return flow
```

### Key Design Decisions (Already Made)

```
1. FAST ENRICHMENT ONLY (no NLP in stream path)
   ┌─────────────────────────────────────────────────────────┐
   │  Stream enrichment: Keyword sentiment (< 1 ms)          │
   │  • No spaCy, no Ollama, no API calls                   │
   │  • Just word counting: "raised" = positive,             │
   │    "bankrupt" = negative                                 │
   │  • Sufficient for initial scoring                       │
   │                                                          │
   │  Heavy NLP: Done ASYNCHRONOUSLY via separate worker     │
   │  • spaCy NER, embeddings, Ollama summary                │
   │  • Published to enrichment.requests topic               │
   │  • Results come back via enrichment.complete topic       │
   │  • Doesn't block the real-time scoring path             │
   └─────────────────────────────────────────────────────────┘

2. TUMBLING WINDOW AGGREGATION
   ┌─────────────────────────────────────────────────────────┐
   │  Window: 5 minutes (configurable via WINDOW_SECONDS)    │
   │                                                          │
   │  Why 5 minutes:                                         │
   │  - Fast enough: Score updates every 5 min               │
   │  - Efficient: Batches signals per entity                │
   │  - Not too long: User doesn't wait > 5 min for score   │
   │                                                          │
   │  How it works:                                          │
   │  12:00-12:05: Collect signals for all entities          │
   │  12:05: Score all entities, write to DB, push alerts   │
   │  12:05-12:10: Next window starts                       │
   └─────────────────────────────────────────────────────────┘

3. GRACEFUL DEGRADATION
   ┌─────────────────────────────────────────────────────────┐
   │  If Kafka is down:                                      │
   │  → Collectors still write to MySQL (batch mode)         │
   │  → Stream processor exits with warning                  │
   │  → No data loss, just delayed processing               │
   │                                                          │
   │  If MySQL is down:                                      │
   │  → Stream processor keeps processing                    │
   │  → Scores published to Kafka                            │
   │  → MySQL write fails silently, logged                   │
   │                                                          │
   │  If Ollama is down:                                     │
   │  → Stream enrichment still works (no Ollama needed)    │
   │  → Heavy NLP worker fails gracefully                    │
   │  → AI Chat falls back to keyword-based answers          │
   └─────────────────────────────────────────────────────────┘
```

---

## 7. Component 4: Scoring in Real Time

### How Scoring Works in the Stream

```
EVERY 5 MINUTES (tumbling window):

1. All signals for "Neuromorphic Labs" in the last 5 minutes are collected
   - funding_round: score=85, time=2min ago
   - hn_live: score=60, time=4min ago

2. Combined with entity's historical state (from EntityState):
   - Previous score: 62.3
   - Score history: [55.0, 58.2, 62.3]
   - Signal history: last 100 signals

3. CompositeScorer.score() calculates:
   - Weighted sum with time decay
   - Anomaly check (Z-score)
   - Trend direction (rising/stable/declining)

4. Output:
   {
     "entity_name": "Neuromorphic Labs",
     "composite_score": 84.0,        ← was 62.3, now 84.0!
     "trend_direction": "rising",
     "signal_count": 15,
     "anomaly_detected": true,
     "attribution": [
       {"signal": "funding_round", "contribution": 19.0},
       {"signal": "hn_live", "contribution": 3.5},
       ...
     ]
   }

5. Written to:
   - MySQL opportunity_scores (durable)
   - Kafka scores.updates (for real-time push)
   - If score > 80: Kafka alerts.triggered (for alert dispatch)
```

---

## 8. Component 5: Alerting Pipeline

### Current State
- `emit_alert()` in `stream/operators.py` creates alert dicts
- Published to `alerts.triggered` Kafka topic
- **No consumer exists yet** — alerts go into Kafka but nobody reads them

### What Needs to Be Built: Alert Dispatcher

```python
# NEW FILE: alerting/dispatcher.py

import json
import logging
import smtplib
from email.mime.text import MIMEText
from typing import Any

import requests

logger = logging.getLogger(__name__)


class AlertDispatcher:
    """Consumes alerts from Kafka and dispatches them to channels."""

    def __init__(self, config: dict):
        self.config = config
        self.channels = config.get("alert_channels", {})

    def dispatch(self, alert: dict[str, Any]) -> None:
        """Dispatch an alert to all configured channels.

        Args:
            alert: Alert dict from alerts.triggered Kafka topic.
        """
        entity = alert.get("entity_name", "Unknown")
        score = alert.get("composite_score", 0)

        logger.info("Dispatching alert: %s (score: %.1f)", entity, score)

        # Send to all configured channels
        if self.channels.get("slack"):
            self._send_slack(alert)
        if self.channels.get("discord"):
            self._send_discord(alert)
        if self.channels.get("email"):
            self._send_email(alert)
        if self.channels.get("webhook"):
            self._send_webhook(alert)

    def _send_slack(self, alert: dict) -> bool:
        """Send alert to Slack via webhook."""
        webhook_url = self.channels["slack"]["webhook_url"]
        entity = alert.get("entity_name", "Unknown")
        score = alert.get("composite_score", 0)
        trend = alert.get("trend_direction", "stable")
        attribution = alert.get("attribution", [])

        # Build rich Slack message
        attribution_text = "\n".join(
            f"  • {a.get('signal', '?')}: +{a.get('contribution', 0):.1f}"
            for a in attribution[:5]
        )

        payload = {
            "text": f"🚀 High Opportunity Alert",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"🚀 {entity}"},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Score:* {score:.1f}"},
                        {"type": "mrkdwn", "text": f"*Trend:* {trend}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Top signals:*\n{attribution_text}"},
                },
            ],
        }

        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Slack alert failed: %s", e)
            return False

    def _send_discord(self, alert: dict) -> bool:
        """Send alert to Discord via webhook."""
        webhook_url = self.channels["discord"]["webhook_url"]
        entity = alert.get("entity_name", "Unknown")
        score = alert.get("composite_score", 0)

        payload = {
            "content": f"🚀 **High Opportunity Alert**\n"
                       f"**{entity}** — Score: {score:.1f} ({alert.get('trend_direction', '')})",
        }

        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Discord alert failed: %s", e)
            return False

    def _send_email(self, alert: dict) -> bool:
        """Send alert via email."""
        smtp_config = self.channels["email"]
        entity = alert.get("entity_name", "Unknown")
        score = alert.get("composite_score", 0)

        subject = f"🚀 OIP Alert: {entity} (Score: {score:.1f})"
        body = json.dumps(alert, indent=2)

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_config.get("from", "alerts@oip.local")
        msg["To"] = smtp_config.get("to", "")

        try:
            with smtplib.SMTP(smtp_config["host"], smtp_config.get("port", 587)) as server:
                if smtp_config.get("tls", True):
                    server.starttls()
                if smtp_config.get("user"):
                    server.login(smtp_config["user"], smtp_config["password"])
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error("Email alert failed: %s", e)
            return False

    def _send_webhook(self, alert: dict) -> bool:
        """Send alert to a custom webhook URL."""
        url = self.channels["webhook"]["url"]
        try:
            resp = requests.post(url, json=alert, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error("Webhook alert failed: %s", e)
            return False
```

### Alert Consumer (reads from Kafka)

```python
# NEW FILE: alerting/consumer.py

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from kafka import KafkaConsumer
from alerting.dispatcher import AlertDispatcher

logger = logging.getLogger(__name__)


def run_alert_consumer():
    """Consume alerts from Kafka and dispatch them."""
    import os

    brokers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.environ.get("KAFKA_TOPIC_ALERTS", "alerts.triggered")

    # Load alert config
    config = {
        "alert_channels": {
            "slack": {
                "webhook_url": os.environ.get("SLACK_WEBHOOK_URL", ""),
            },
            "discord": {
                "webhook_url": os.environ.get("DISCORD_WEBHOOK_URL", ""),
            },
            "email": {
                "host": os.environ.get("SMTP_HOST", ""),
                "port": int(os.environ.get("SMTP_PORT", "587")),
                "from": os.environ.get("ALERT_EMAIL_FROM", ""),
                "to": os.environ.get("ALERT_EMAIL_TO", ""),
                "user": os.environ.get("SMTP_USER", ""),
                "password": os.environ.get("SMTP_PASSWORD", ""),
            },
            "webhook": {
                "url": os.environ.get("ALERT_WEBHOOK_URL", ""),
            },
        },
    }

    dispatcher = AlertDispatcher(config)

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=brokers.split(","),
        group_id="alert-dispatcher",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
    )

    logger.info("Alert consumer started, listening on %s", topic)

    for message in consumer:
        alert = message.value
        logger.info("Received alert: %s", alert.get("entity_name", "?"))
        dispatcher.dispatch(alert)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_alert_consumer()
```

---

## 9. Component 6: Push to Users (WebSocket + SSE)

### What Exists: WebSocket Server

```python
# api_server.py — already implemented
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    async def broadcast(self, data: dict):
        for ws in self.active:
            await ws.send_json(data)

@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket):
    """Push stats updates every 30 seconds."""
    await ws_manager.connect(websocket)
    while True:
        # ... collect stats from DB ...
        await ws_manager.broadcast({"type": "stats_update", "data": {...}})
        await asyncio.sleep(30)
```

### What Needs to Be Built: Score Push via Kafka Consumer

The WebSocket currently polls MySQL every 30 seconds. For true real-time, it should consume from Kafka:

```python
# ENHANCEMENT to api_server.py

import asyncio
import json
from kafka import KafkaConsumer

# Background task: consume scores.updates and push to WebSocket clients
async def kafka_score_pusher():
    """Background task that reads scores from Kafka and pushes to WS clients."""
    consumer = KafkaConsumer(
        "scores.updates",
        bootstrap_servers="kafka:9092",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
    )

    while True:
        # Non-blocking check for new messages
        messages = consumer.poll(timeout_ms=1000)
        for topic_partition, records in messages.items():
            for record in records:
                score_update = record.value
                # Push to all connected WebSocket clients
                await ws_manager.broadcast({
                    "type": "score_update",
                    "data": score_update,
                })
        await asyncio.sleep(0.1)  # Yield to event loop


# Add to startup:
@app.on_event("startup")
async def startup():
    asyncio.create_task(kafka_score_pusher())
```

### SSE Endpoint (for users who can't use WebSocket)

```python
# NEW ENDPOINT in api_server.py

from fastapi.responses import StreamingResponse

@app.get("/api/stream/scores")
async def stream_scores():
    """Server-Sent Events endpoint for real-time score updates."""

    async def event_generator():
        # Simple polling approach (every 5 seconds)
        last_scores = {}
        while True:
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT entity_name, composite_score, trend_direction, last_updated
                       FROM opportunity_scores
                       WHERE last_updated > NOW() - INTERVAL 5 MINUTE
                       ORDER BY composite_score DESC LIMIT 20"""
                )
                rows = cursor.fetchall()
                cursor.close()
                conn.close()

                for row in rows:
                    entity = row["entity_name"]
                    score = row["composite_score"]
                    if entity not in last_scores or last_scores[entity] != score:
                        last_scores[entity] = score
                        data = json.dumps(dict(row), default=str)
                        yield f"data: {data}\n\n"

            except Exception:
                pass

            await asyncio.sleep(5)  # Poll every 5 seconds

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 10. Component 7: NLP Without Blocking

### The Problem

Real-time scoring must be fast (< 100 ms). But NLP is slow:
```
spaCy NER:           50-200 ms per article
Sentence-Transformers: 100-500 ms per article
Ollama LLM summary:    2-10 seconds per article
```

### The Solution: Two-Track Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  TRACK 1: FAST PATH (stream processor — already built)         │
│  ───────────────────────────────────────────────────────        │
│  Keyword sentiment:   < 1 ms                                   │
│  Entity name heuristics: < 1 ms                                │
│  CompositeScorer:      10-50 ms                                │
│                                                                 │
│  This is what runs in the Bytewax pipeline.                    │
│  Good enough for initial scoring.                              │
│                                                                 │
│  RESULT: Score within seconds of signal arrival                │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TRACK 2: DEEP PATH (async worker — needs building)            │
│  ─────────────────────────────────────────────────────          │
│  spaCy NER:           Entity extraction, relationships          │
│  Sentence-Transformers: Embeddings for semantic search          │
│  Ollama LLM:          Summary, classification, deep analysis   │
│                                                                 │
│  This runs in a SEPARATE worker, consuming from                │
│  enrichment.requests topic and publishing to                    │
│  enrichment.complete topic.                                    │
│                                                                 │
│  RESULT: Full NLP enrichment within 5-60 seconds               │
│  (does NOT block the fast path)                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### NLP Worker Implementation

```python
# NEW FILE: enrichment/nlp_worker.py

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class NLPWorker:
    """Consumes signals from Kafka, runs heavy NLP, publishes results."""

    def __init__(self):
        self.nlp = None       # spaCy model
        self.embedder = None  # Sentence-Transformers model
        self.llm = None       # Ollama client

    def initialize(self):
        """Load ML models (done once at startup)."""
        # spaCy for NER
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded")
        except Exception as e:
            logger.warning("spaCy not available: %s", e)

        # Sentence-Transformers for embeddings
        try:
            from sentence_transformers import SentenceTransformer
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Sentence-Transformers model loaded")
        except Exception as e:
            logger.warning("Sentence-Transformers not available: %s", e)

        # Ollama for LLM (runs separately, API call)
        self.ollama_url = "http://ollama:11434/api/chat"

    def process_signal(self, signal: dict) -> dict:
        """Run full NLP pipeline on a signal."""
        result = {"signal_id": signal.get("id"), "enrichments": {}}

        text = (signal.get("title", "") + " " + signal.get("body_text", ""))[:5000]

        # 1. Named Entity Recognition
        if self.nlp:
            doc = self.nlp(text)
            entities = [
                {"text": ent.text, "label": ent.label_}
                for ent in doc.ents
            ]
            result["enrichments"]["entities"] = entities

        # 2. Embedding for semantic search
        if self.embedder:
            embedding = self.embedder.encode(text).tolist()
            result["enrichments"]["embedding"] = embedding

            # Store in Qdrant
            self._store_embedding(signal.get("entity_name", ""), embedding)

        # 3. LLM summary (optional, slow)
        if len(text) > 500:  # Only summarize long texts
            summary = self._ollama_summarize(text)
            result["enrichments"]["summary"] = summary

        return result

    def _store_embedding(self, entity_name: str, embedding: list):
        """Store embedding in Qdrant for semantic search."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import PointStruct

            client = QdrantClient("qdrant", port=6333)
            client.upsert(
                collection_name="signals",
                points=[
                    PointStruct(
                        id=hash(entity_name) % (2**63),
                        vector=embedding,
                        payload={"entity_name": entity_name},
                    )
                ],
            )
        except Exception as e:
            logger.debug("Qdrant store failed: %s", e)

    def _ollama_summarize(self, text: str) -> str:
        """Get summary from Ollama LLM."""
        import requests
        try:
            resp = requests.post(
                self.ollama_url,
                json={
                    "model": "llama3",
                    "messages": [
                        {"role": "user",
                         "content": f"Summarize in 2 sentences: {text[:2000]}"}
                    ],
                    "stream": False,
                },
                timeout=30,
            )
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.debug("Ollama summary failed: %s", e)
            return ""

    def run(self):
        """Main loop: consume from Kafka, process, publish."""
        from kafka import KafkaConsumer, KafkaProducer

        consumer = KafkaConsumer(
            "raw.signals",
            bootstrap_servers="kafka:9092",
            group_id="nlp-worker",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
        )

        producer = KafkaProducer(
            bootstrap_servers="kafka:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        logger.info("NLP worker started, consuming from raw.signals")

        for message in consumer:
            signal = message.value
            result = self.process_signal(signal)
            producer.send("enrichment.complete", value=result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    worker = NLPWorker()
    worker.initialize()
    worker.run()
```

---

## 11. Component 8: Knowledge Graph Updates

### How the Graph Stays Real-Time

```
ENRICHMENT RESULTS (from NLP worker) contain extracted relationships:
  {
    "signal_id": "sig_001",
    "enrichments": {
      "entities": [
        {"text": "Neuromorphic Labs", "label": "ORG"},
        {"text": "Horizon Ventures", "label": "ORG"},
        {"text": "Austin", "label": "GPE"},
        {"text": "$5M", "label": "MONEY"},
      ]
    }
  }

GRAPH UPDATE WORKER consumes enrichment.complete:
  1. Extract entities with labels ORG, PERSON, GPE
  2. Resolve to existing entities (fuzzy match)
  3. Create new entities if no match
  4. Create/update relationships:
     Neuromorphic Labs --funded_by--> Horizon Ventures
     Neuromorphic Labs --located_in--> Austin
  5. Write to kg_entities and kg_relationships tables
  6. Publish to graph.updates topic (for real-time graph viz)
```

---

## 12. Infrastructure You Need to Run

### Minimum (Laptop/Desktop)

```
SERVICES NEEDED:
  1. MySQL 8.0         — Primary database
  2. Redpanda (Kafka)   — Message bus
  3. Redis              — Metrics + caching
  4. Bytewax            — Stream processor
  5. FastAPI            — API server + WebSocket

RAM: 4 GB minimum
CPU: 2 cores minimum
Disk: 10 GB minimum

START:
  docker compose up mysql redis kafka api stream_processor
  python -m stream.pipeline --test    # Test mode
```

### Full Stack (Production)

```
ALL 10 SERVICES:
  1. MySQL 8.0          — Primary database
  2. Redpanda (Kafka)   — Message bus
  3. Redis              — Metrics + caching + pub/sub
  4. Bytewax            — Stream processor
  5. FastAPI            — API server
  6. Ollama             — Local LLM
  7. Qdrant             — Vector search
  8. Elasticsearch      — Full-text search
  9. ClickHouse         — OLAP analytics
  10. TimescaleDB       — Time-series data

RAM: 16 GB minimum
CPU: 4 cores minimum
Disk: 100 GB minimum

START:
  docker compose up -d                  # All services
  python scheduler.py                   # Collector scheduler
  python -m stream.pipeline             # Stream processor
  python -m alerting.consumer           # Alert dispatcher
  python -m enrichment.nlp_worker       # NLP worker
  python api_server.py --host 0.0.0.0  # API + WebSocket
```

---

## 13. Step-by-Step: Setting Up Real Time

### Step 1: Start Infrastructure

```bash
# Start MySQL, Redis, Kafka (Redpanda)
docker compose up -d mysql redis kafka

# Wait for healthy
docker compose ps  # All should show "healthy"
```

### Step 2: Create Kafka Topics

```bash
# Create topics
bash scripts/create-topics.sh

# Verify
docker exec startup-research-kafka rpk topic list
```

### Step 3: Start Stream Processor

```bash
# Test mode first (no Kafka needed)
python -m stream.pipeline --test

# Production mode
docker compose up -d stream_processor

# Check logs
docker logs -f startup-research-stream
```

### Step 4: Start Collector Scheduler

```bash
# Start continuous + scheduled collectors
python scheduler.py &

# Or via Docker
docker compose up -d pipeline
```

### Step 5: Start API Server with WebSocket

```bash
python api_server.py --host 0.0.0.0 --port 8000

# Verify WebSocket
# In browser console:
ws = new WebSocket("ws://localhost:8000/ws/live")
ws.onmessage = (e) => console.log(JSON.parse(e.data))
```

### Step 6: Start Alert Dispatcher

```bash
# Set environment variables
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Start consumer
python -m alerting.consumer
```

### Step 7: Verify End-to-End

```bash
# 1. Check stream status
curl http://localhost:8000/api/stream/status

# Expected:
# {
#   "status": "healthy",
#   "pipeline": {
#     "signals_processed": 145,
#     "entities_scored": 23,
#     "throughput_per_minute": 12.5
#   }
# }

# 2. Watch for score updates
curl -N http://localhost:8000/api/stream/scores

# 3. Check opportunities
curl http://localhost:8000/api/opportunities?limit=5

# 4. Open dashboard
open http://localhost:8000/
```

---

## 14. Monitoring & Observability

### Metrics Dashboard

```
REDIS KEY: stream:metrics (updated every 30 seconds)
{
  "signals_processed": 14523,
  "signals_enriched": 14520,
  "signals_scored": 12800,
  "signals_errored": 3,
  "entities_scored": 245,
  "scores_written": 245,
  "alerts_emitted": 12,
  "throughput_per_minute": 45.2,
  "processing_lag_seconds": 2.3
}

API ENDPOINT: GET /api/stream/status
  → Returns above metrics + component health

WEBSOCKET: /ws/live
  → Pushes metrics to dashboard every 30 seconds
```

### Health Checks

```
SERVICE            CHECK
─────────          ─────
MySQL              GET /api/health → {status: "healthy"}
Kafka              rpk cluster health
Redis              redis-cli ping → PONG
Stream Processor   GET /api/stream/status → {status: "healthy"}
Bytewax            signals_processed > 0 AND lag < 300s
Collectors         collection_runs table → last run < 1 hour
```

---

## 15. What Still Needs to Be Built

### Critical (Required for Real-Time)

```
1. COLLECTOR SCHEDULER (scheduler.py)
   Priority: HIGH
   Effort: 2-3 days
   → Manages continuous + scheduled collector execution
   → Uses APScheduler for cron-like scheduling
   → Runs Tier 1 collectors in background threads

2. ALERT DISPATCHER (alerting/dispatcher.py + consumer.py)
   Priority: HIGH
   Effort: 2-3 days
   → Consumes alerts.triggered from Kafka
   → Sends to Slack, Discord, Email, Webhook
   → Configurable per user

3. KAFKA TOPIC CREATION SCRIPT (scripts/create-topics.sh)
   Priority: HIGH
   Effort: 1 hour
   → Creates all required topics with proper configuration

4. SCORE PUSH VIA KAFKA (enhancement to api_server.py)
   Priority: MEDIUM
   Effort: 1 day
   → Background task reads scores.updates from Kafka
   → Pushes to WebSocket clients in real-time
   → Replaces current MySQL polling
```

### Important (Enhances Real-Time)

```
5. NLP WORKER (enrichment/nlp_worker.py)
   Priority: MEDIUM
   Effort: 3-5 days
   → Separate worker for heavy NLP (spaCy + embeddings + Ollama)
   → Consumes from raw.signals, publishes to enrichment.complete
   → Does NOT block stream processor

6. SSE ENDPOINT (/api/stream/scores)
   Priority: MEDIUM
   Effort: 1 day
   → Server-Sent Events for users without WebSocket
   → Lighter weight alternative

7. KNOWLEDGE GRAPH REAL-TIME UPDATES
   Priority: LOW
   Effort: 3-5 days
   → Consumes enrichment.complete
   → Updates kg_entities and kg_relationships
   → Publishes to graph.updates

8. COLLECTOR HEALTH MONITORING
   Priority: LOW
   Effort: 2 days
   → Dashboard showing collector status
   → Alert if a collector hasn't run recently
   → Auto-restart failed collectors
```

### Nice-to-Have

```
9. CLICKHOUSE INTEGRATION
   → Write scored signals to ClickHouse for OLAP
   → Enables fast analytical queries

10. TIMESCALEDB INTEGRATION
    → Write score history to TimescaleDB
    → Enables time-series trend analysis

11. QDRANT REAL-TIME INDEXING
    → Index new signals in Qdrant as they arrive
    → Enables instant semantic search

12. ELASTICSEARCH REAL-TIME INDEXING
    → Index new signals in ES as they arrive
    → Enables instant full-text search
```

---

## 16. Cost Estimates

### Self-Hosted (Production)

```
SERVER (cloud VM):
  AWS c5.2xlarge (8 vCPU, 16 GB RAM)
  $0.34/hr × 730 hrs = $248/month

  Or: Hetzner dedicated (64 GB RAM, 8 cores)
  €59/month = ~$65/month

SOFTWARE:
  All open-source (Redpanda, Bytewax, Redis, etc.)
  $0/month

EXTERNAL APIs:
  Twitter/X API: $100/month (Basic tier)
  Reddit API: Free (PRAW)
  HN API: Free
  Crunchbase API: Free tier (or $490/mo for full)
  SEC EDGAR: Free
  Total: $0-600/month

TOTAL MONTHLY COST:
  Minimum: $65 (Hetzner + free APIs)
  Recommended: $165 (Hetzner + Twitter API)
  Full-featured: $765 (Hetzner + Twitter + Crunchbase)
```

---

## Summary: How to Go Real-Time in 2 Weeks

```
WEEK 1: Infrastructure + Core Pipeline
  Day 1-2: Docker Compose up (MySQL + Kafka + Redis)
  Day 3-4: Create Kafka topics + test stream processor
  Day 5:   Build collector scheduler
  Day 6-7: Test end-to-end: collector → Kafka → process → MySQL

WEEK 2: Push + Alerts + NLP
  Day 8-9: Build alert dispatcher (Slack + Email)
  Day 10:  Enhance WebSocket with Kafka score push
  Day 11:  Build SSE endpoint
  Day 12:  Build NLP worker (spaCy + embeddings)
  Day 13:  Integration testing
  Day 14:  Deploy + monitor

RESULT: Real-world event → alert in under 15 minutes
```

---

*Last updated: June 5, 2026*

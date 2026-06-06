"""Prometheus metrics collection."""

import logging
from typing import Dict
from collections import defaultdict

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

_logger = logging.getLogger(__name__)


class MetricsRegistry:
    """Prometheus metrics registry."""

    def __init__(self):
        """Initialize metrics."""
        if HAS_PROMETHEUS:
            self.request_count = Counter(
                "api_requests_total",
                "Total API requests",
                ["endpoint", "method"]
            )
            self.request_latency = Histogram(
                "api_request_latency_seconds",
                "API request latency"
            )
            self.agent_runs = Counter(
                "agent_runs_total",
                "Total agent runs",
                ["agent_name", "status"]
            )
            self.collector_records = Counter(
                "collector_records_total",
                "Total records collected",
                ["collector_name"]
            )
            self.active_connections = Gauge(
                "active_connections",
                "Active database connections"
            )
        else:
            _logger.warning("prometheus_client not installed — using mock metrics")
            self.request_count = defaultdict(int)
            self.request_latency = defaultdict(list)
            self.agent_runs = defaultdict(int)
            self.collector_records = defaultdict(int)
            self.active_connections = 0

    def increment_request(self, endpoint: str, method: str = "GET"):
        """Increment request counter."""
        if HAS_PROMETHEUS:
            self.request_count.labels(endpoint=endpoint, method=method).inc()
        else:
            self.request_count[f"{endpoint}:{method}"] += 1

    def observe_latency(self, latency_seconds: float):
        """Observe request latency."""
        if HAS_PROMETHEUS:
            self.request_latency.observe(latency_seconds)
        else:
            self.request_latency["all"].append(latency_seconds)

    def increment_agent_run(self, agent_name: str, status: str = "success"):
        """Increment agent run counter."""
        if HAS_PROMETHEUS:
            self.agent_runs.labels(agent_name=agent_name, status=status).inc()
        else:
            self.agent_runs[f"{agent_name}:{status}"] += 1

    def increment_collector_records(self, collector_name: str, count: int = 1):
        """Increment collector record counter."""
        if HAS_PROMETHEUS:
            self.collector_records.labels(collector_name=collector_name).inc(count)
        else:
            self.collector_records[collector_name] += count

    def set_active_connections(self, count: int):
        """Set active connections gauge."""
        if HAS_PROMETHEUS:
            self.active_connections.set(count)
        else:
            self.active_connections = count


# Global registry
metrics = MetricsRegistry()

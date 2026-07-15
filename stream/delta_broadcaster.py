"""Score delta broadcaster — reads from score_deltas Kafka and pushes to WebSocket clients.

Architecture:
  Kafka (score_deltas topic)
      ↓  delta_broadcaster.py (Kafka consumer + Redis publisher)
  Redis pub/sub channel "stream:score_deltas"
      ↓  api_server.py (/ws/live endpoint)
  Browser WebSocket clients

Usage:
    python -m stream.delta_broadcaster            # Start as daemon
    python -m stream.delta_broadcaster --test      # Simulated deltas, no Kafka
    ^C or SIGTERM                                 # Graceful shutdown

Dependencies: kafka-python, redis (pip install)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))


_logger = logging.getLogger("delta_broadcaster")

# ── Config ─────────────────────────────────────────────────────

DEFAULT_KAFKA_BROKERS = "localhost:9092"
DEFAULT_KAFKA_TOPIC = "score_deltas"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
REDIS_CHANNEL = "stream:score_deltas"


# ── Kafka consumer ─────────────────────────────────────────────

def _create_kafka_consumer(brokers: str) -> Any:
    from kafka import KafkaConsumer

    return KafkaConsumer(
        DEFAULT_KAFKA_TOPIC,
        bootstrap_servers=brokers.split(","),
        group_id="delta_broadcaster",
        auto_offset_reset="latest",
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        consumer_timeout_ms=5000,
    )


def _redis_publish(redis_url: str, channel: str, message: dict) -> bool:
    import redis as redis_client

    try:
        r = redis_client.from_url(redis_url, socket_connect_timeout=2, decode_responses=False)
        r.publish(channel, json.dumps(message, default=str))
        r.close()
        return True
    except Exception as e:
        _logger.debug("Redis publish failed (server unavailable): %s", e)
        return False


def _emit_to_websocket(ws_manager, message: dict) -> int:
    """Broadcast delta message to all connected WebSocket clients.

    Returns the number of clients that received the message.
    """
    if ws_manager is None:
        return 0
    try:
        count = 0
        disconnected = []
        loop = asyncio.get_event_loop()

        for client_id, ws in ws_manager.active_connections.items():
            try:
                loop.call_soon_threadsafe(lambda w: _send_ws(w, message), ws)
                count += 1
            except Exception:
                disconnected.append(client_id)

        for client_id in disconnected:
            ws_manager.disconnect(client_id)

        return count
    except Exception:
        return 0


def _send_ws(ws, message: dict):
    """Send JSON to a WebSocket — fire and forget."""
    try:
        if hasattr(ws, "_loop") and ws._loop.is_running():
            asyncio.get_event_loop().create_task(ws.send_json(message))
        else:
            asyncio.run(ws.send_json(message))
    except Exception:
        pass


# ── Broadcast loop ─────────────────────────────────────────────

def _broadcast_loop(
    kafka_brokers: str,
    redis_url: str,
    ws_manager,
    running: threading.Event,
    poll_interval: float = 2.0,
) -> None:
    """Main loop: poll Kafka, emit deltas to Redis + WebSocket."""
    consumer = None
    published_total = 0

    try:
        consumer = _create_kafka_consumer(kafka_brokers)
        _logger.info(
            "Kafka consumer connected — topic: %s, brokers: %s",
            DEFAULT_KAFKA_TOPIC,
            kafka_brokers,
        )
    except Exception as e:
        _logger.warning("Kafka unavailable, falling back to Redis polling: %s", e)

    _logger.info("Delta broadcaster started — Redis: %s", redis_url)

    while running.is_set():
        try:
            if consumer:
                for record in consumer:
                    if not running.is_set():
                        break
                    delta = record.value
                    _logger.debug("Delta received: %s", delta.get("entity_name"))

                    _redis_publish(redis_url, REDIS_CHANNEL, delta)

                    if ws_manager:
                        n = _emit_to_websocket(ws_manager, delta)
                        if n > 0:
                            _logger.debug("Pushed delta to %d WebSocket clients", n)

                    published_total += 1

            else:
                time.sleep(poll_interval)

        except Exception as e:
            _logger.error("Broadcast loop error: %s", e)
            time.sleep(5)

    if consumer:
        try:
            consumer.close()
        except Exception:
            pass
    _logger.info("Delta broadcaster stopped (published %d deltas)", published_total)


# ── Simulated test loop ───────────────────────────────────────

def _test_loop(ws_manager, running: threading.Event, interval: float = 3.0) -> None:
    """Generate fake score deltas for local testing without Kafka."""
    import random

    _logger.info("Test mode: generating simulated deltas every %.0fs", interval)
    while running.is_set():
        time.sleep(interval)
        if not running.is_set():
            break

        test_deltas = [
            {
                "entity_name": "NeuralForge AI",
                "old_score": 72.0,
                "new_score": 81.5,
                "change": 9.5,
                "is_first_score": False,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "entity_name": "LangChain",
                "old_score": None,
                "new_score": 65.0,
                "change": 65.0,
                "is_first_score": True,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "entity_name": "CloudSync Inc",
                "old_score": 88.0,
                "new_score": 79.0,
                "change": -9.0,
                "is_first_score": False,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        delta = random.choice(test_deltas).copy()
        delta["detected_at"] = datetime.now(timezone.utc).isoformat()

        _redis_publish(os.environ.get("REDIS_URL", DEFAULT_REDIS_URL), REDIS_CHANNEL, delta)
        if ws_manager:
            _emit_to_websocket(ws_manager, delta)


# ── CLI ───────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Score delta broadcaster")
    parser.add_argument(
        "--kafka-brokers",
        type=str,
        default=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", DEFAULT_KAFKA_BROKERS),
        help="Kafka bootstrap servers",
    )
    parser.add_argument(
        "--redis-url",
        type=str,
        default=os.environ.get("REDIS_URL", DEFAULT_REDIS_URL),
        help="Redis URL for pub/sub",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Generate simulated deltas (no Kafka required)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [delta_broadcaster] %(levelname)s: %(message)s",
    )

    running = threading.Event()
    running.set()

    def _shutdown(signum, _frame):
        _logger.info("Shutdown signal received...")
        running.clear()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    _broadcast_loop(
        args.kafka_brokers,
        args.redis_url,
        ws_manager=None,
        running=running,
    )


if __name__ == "__main__":
    main()
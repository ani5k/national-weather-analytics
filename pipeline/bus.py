"""Kafka/Redpanda publish helper (no-op if broker unavailable)."""

from __future__ import annotations

import json
import logging
import os
import socket
from typing import Any

logger = logging.getLogger(__name__)

_broker_down = False


def _broker_reachable(bootstrap: str) -> bool:
    host, _, port = bootstrap.partition(":")
    try:
        with socket.create_connection((host or "127.0.0.1", int(port or "19092")), timeout=0.4):
            return True
    except OSError:
        return False


def publish_raw(doc: dict[str, Any], topic: str | None = None) -> bool:
    """Publish a report dict to Kafka. Returns False if broker missing."""
    global _broker_down
    if _broker_down:
        return False

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:19092").split(",")[0].strip()
    topic = topic or os.getenv("KAFKA_TOPIC", "weather.raw")
    if not _broker_reachable(bootstrap):
        _broker_down = True
        logger.warning("Kafka publish skipped: broker %s is not running", bootstrap)
        return False

    try:
        from kafka import KafkaProducer
    except ImportError:
        logger.debug("kafka-python not installed; skip publish")
        return False

    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap.split(","),
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            request_timeout_ms=2000,
            retries=0,
            max_block_ms=2000,
        )
        payload = {k: v for k, v in doc.items() if k != "_id"}
        producer.send(topic, payload)
        producer.flush(timeout=3)
        producer.close()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Kafka publish skipped: %s", exc)
        return False

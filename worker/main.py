"""
Kafka/Redpanda worker: weather.raw → enrich → Mongo.

    python -m worker.main
"""

from __future__ import annotations

import json
import logging
import os
import time

from pymongo import MongoClient

from api.enrichment import process_single_document
from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("worker")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "weather.raw")
GROUP_ID = os.getenv("KAFKA_GROUP", "weather-enricher")


def get_collection():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME][COLLECTION_NAME]


def handle_message(collection, payload: dict) -> None:
    report_id = payload.get("report_id")
    if not report_id:
        logger.warning("skip message without report_id")
        return
    existing = collection.find_one({"report_id": report_id})
    if existing is None:
        collection.insert_one(payload)
        existing = collection.find_one({"report_id": report_id})
    process_single_document(collection, existing or payload, apply_ml_status=True)
    logger.info("processed %s", report_id)


def run_kafka_loop() -> None:
    from kafka import KafkaConsumer

    collection = get_collection()
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        consumer_timeout_ms=1000,
    )
    logger.info("Worker listening on %s/%s", KAFKA_BOOTSTRAP, KAFKA_TOPIC)
    while True:
        polled = consumer.poll(timeout_ms=1000)
        if not polled:
            time.sleep(0.2)
            continue
        for _tp, records in polled.items():
            for record in records:
                try:
                    handle_message(collection, record.value)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Failed message: %s", exc)


def run_mongo_poll_fallback() -> None:
    """If Kafka is down, periodically enrich newest pending docs."""
    collection = get_collection()
    logger.info("Worker fallback mode: Mongo poll enrich")
    while True:
        pending = list(
            collection.find(
                {
                    "$or": [
                        {"credibility": None},
                        {"duplicate_group_id": None},
                    ]
                }
            )
            .sort("timestamp", -1)
            .limit(30)
        )
        for doc in pending:
            try:
                process_single_document(collection, doc, apply_ml_status=True)
            except Exception as exc:  # noqa: BLE001
                logger.exception("enrich failed: %s", exc)
        time.sleep(15)


def main() -> None:
    try:
        run_kafka_loop()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Kafka unavailable (%s); using Mongo poll fallback", exc)
        run_mongo_poll_fallback()


if __name__ == "__main__":
    main()

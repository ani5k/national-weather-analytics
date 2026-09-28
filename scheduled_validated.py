"""
Hourly multi-source collector (canonical scheduler).

    python scheduled_validated.py --once
    python scheduled_validated.py
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

import schedule
from pymongo import MongoClient

from pipeline.collect_openmeteo import collect_openmeteo
from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("collector.log"), logging.StreamHandler()],
)
logger = logging.getLogger("scheduled_validated")


def get_collection():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    return client[DB_NAME][COLLECTION_NAME]


def collect_all(collection, enrich: bool = True, social: bool = True) -> None:
    logger.info("=" * 50)
    logger.info("Cycle start")
    logger.info("Open-Meteo saved=%s", collect_openmeteo(collection))
    if social:
        try:
            from pipeline.collect_rss import collect_rss
            from pipeline.collect_reddit import collect_reddit
            from pipeline.collect_imd import collect_imd_bulletins

            logger.info("RSS saved=%s", collect_rss(collection))
            logger.info("IMD saved=%s", collect_imd_bulletins(collection))
            logger.info("Reddit saved=%s", collect_reddit(collection))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Social/RSS collect issue: %s", exc)
    if enrich:
        from api.enrichment import enrich_and_persist

        logger.info("Enrichment %s", enrich_and_persist(collection, limit=500, apply_ml_status=True))
    logger.info("Total=%s", collection.count_documents({}))
    logger.info("=" * 50)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-enrich", action="store_true")
    parser.add_argument("--no-social", action="store_true")
    args = parser.parse_args()
    try:
        collection = get_collection()
    except Exception as exc:  # noqa: BLE001
        logger.error("Mongo failed: %s", exc)
        return 1

    collect_all(collection, enrich=not args.no_enrich, social=not args.no_social)
    if args.once:
        return 0

    schedule.every().hour.at(":00").do(
        collect_all,
        collection=collection,
        enrich=not args.no_enrich,
        social=not args.no_social,
    )
    logger.info("Scheduler active")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        logger.info("Stopped")
        raise SystemExit(0)

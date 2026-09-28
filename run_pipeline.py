"""
Canonical multi-source pipeline (Phase 1+).

    python run_pipeline.py
    python run_pipeline.py --skip-enrich --skip-social
"""

from __future__ import annotations

import argparse
import logging
import sys

from pymongo import MongoClient

from pipeline.collect_openmeteo import collect_openmeteo
from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("run_pipeline")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-enrich", action="store_true")
    parser.add_argument("--skip-social", action="store_true")
    parser.add_argument("--skip-rss", action="store_true")
    parser.add_argument("--enrich-limit", type=int, default=800)
    args = parser.parse_args()

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    collection = client[DB_NAME][COLLECTION_NAME]
    collection.create_index([("source.platform", 1), ("location.city", 1), ("timestamp_hour", 1)])
    collection.create_index("report_id", unique=True, sparse=True)
    collection.create_index("hashtags")
    collection.create_index("duplicate_group_id")

    logger.info("Open-Meteo collect...")
    saved_om = collect_openmeteo(collection)
    logger.info("Open-Meteo saved=%s", saved_om)

    if not args.skip_rss:
        from pipeline.collect_rss import collect_rss
        from pipeline.collect_imd import collect_imd_bulletins

        logger.info("RSS collect...")
        logger.info("RSS saved=%s", collect_rss(collection))
        logger.info("IMD/official bulletins...")
        logger.info("IMD saved=%s", collect_imd_bulletins(collection))

    if not args.skip_social:
        from pipeline.collect_reddit import collect_reddit

        logger.info("Reddit collect...")
        logger.info("Reddit saved=%s", collect_reddit(collection))

    total = collection.count_documents({})
    logger.info("Collection size=%s", total)

    if not args.skip_enrich and total:
        from api.enrichment import enrich_and_persist

        summary = enrich_and_persist(collection, limit=args.enrich_limit, apply_ml_status=True)
        logger.info("Enrichment %s", summary)

    logger.info("Done. API: python -m uvicorn api.main:app --port 8000")
    return 0


if __name__ == "__main__":
    sys.exit(main())

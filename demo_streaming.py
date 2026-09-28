"""
Demo: publish a raw weather message onto Redpanda topic weather.raw (or Mongo fallback).

    python demo_streaming.py
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from pymongo import MongoClient

from pipeline.bus import publish_raw
from pipeline.schema import build_report
from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI, city_meta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo_streaming")


def main() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    city = "Pune"
    state, lat, lng = city_meta(city)
    report_id = f"STREAM_{now.strftime('%Y%m%d%H%M%S')}_PUN"
    doc = build_report(
        report_id=report_id,
        text="Live stream demo: gusty winds and light rain near Swargate #WeatherAlert",
        platform="citizen_report",
        source_type="citizen",
        city=city,
        state=state,
        event_type="strong_wind",
        timestamp=now.isoformat().replace("+00:00", "Z"),
        timestamp_hour=now.replace(minute=0, second=0).isoformat(),
        lat=lat,
        lng=lng,
        confidence=0.7,
        hashtags=["#WeatherAlert"],
    )
    # Always persist so UI/SSE tick even if Kafka is down
    col = MongoClient(MONGO_URI)[DB_NAME][COLLECTION_NAME]
    if not col.find_one({"report_id": report_id}):
        col.insert_one(doc)
    ok = publish_raw(doc)
    logger.info("published_to_bus=%s report_id=%s", ok, report_id)
    logger.info("payload=%s", json.dumps({"report_id": report_id, "city": city}, indent=2))
    logger.info("Watch dashboard live stream line / worker enriching weather.raw")


if __name__ == "__main__":
    main()

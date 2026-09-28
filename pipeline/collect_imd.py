"""IMD / official bulletin ingest (trusted anchors)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import requests
from pymongo.collection import Collection

from pipeline.bus import publish_raw
from pipeline.geocode import detect_city_state
from pipeline.hashtags import extract_hashtags, inject_hashtags
from pipeline.schema import build_report
from pipeline.weather_text import looks_like_weather
from ml.event_classifier import classify_event

logger = logging.getLogger(__name__)

# Public weather/warning-style feeds used as IMD-tier anchors for demo
IMD_FEEDS = [
    "https://www.hindustantimes.com/feeds/rss/cities/mumbai-news/rssfeed.xml",
    "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",  # India climate/env-ish bucket
]


def _parse_items(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall(".//item"):
        items.append(
            {
                "title": (item.findtext("title") or "").strip(),
                "description": (item.findtext("description") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "pubDate": item.findtext("pubDate"),
            }
        )
    return items


def _ts(pub: str | None) -> str:
    if pub:
        try:
            dt = parsedate_to_datetime(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except Exception:  # noqa: BLE001
            pass
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def collect_imd_bulletins(collection: Collection, limit_per_feed: int = 10) -> int:
    saved = 0
    for feed in IMD_FEEDS:
        try:
            resp = requests.get(feed, timeout=20, headers={"User-Agent": "weather-collector-imd/1.0"})
            if resp.status_code != 200:
                continue
            items = _parse_items(resp.text)[:limit_per_feed]
        except Exception as exc:  # noqa: BLE001
            logger.warning("IMD feed fail %s: %s", feed, exc)
            continue

        for item in items:
            title = item["title"]
            if not title:
                continue
            raw_text = f"{title}. {item['description']}"
            if not looks_like_weather(raw_text):
                continue
            text = inject_hashtags(f"IMD bulletin: {raw_text}", ["#IMD", "#WeatherAlert"])
            city, state, lat, lng = detect_city_state(text)
            event, conf = classify_event(text)
            ts = _ts(item.get("pubDate"))
            report_id = f"IMD_{abs(hash(item.get('link') or title)) % 10_000_000}_{city[:3].upper()}"
            if collection.find_one({"report_id": report_id}):
                continue
            doc = build_report(
                report_id=report_id,
                text=text[:900],
                platform="imd",
                source_type="government",
                city=city,
                state=state,
                event_type=event,
                timestamp=ts,
                timestamp_hour=ts[:13] + ":00:00",
                lat=lat,
                lng=lng,
                confidence=max(conf, 0.85),
                hashtags=extract_hashtags(text),
                raw_data={"feed": feed, **item, "trust_tier": "official"},
            )
            doc["classification"]["method"] = "imd_bulletin"
            doc["trust_tier"] = "official"
            doc["is_official_anchor"] = True
            collection.insert_one(doc)
            publish_raw(doc)
            saved += 1
            logger.info("IMD anchor %s | %s", city, title[:50])
    return saved


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from pymongo import MongoClient
    from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI

    col = MongoClient(MONGO_URI)[DB_NAME][COLLECTION_NAME]
    print("saved", collect_imd_bulletins(col))

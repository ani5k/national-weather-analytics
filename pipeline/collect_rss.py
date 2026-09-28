"""RSS / news / IMD-like bulletin collector."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
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

DEFAULT_FEEDS = [
    # Public weather/news RSS mirrors suitable for demo (replace with IMD when available)
    "https://www.hindustantimes.com/feeds/rss/cities/mumbai-news/rssfeed.xml",
    "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",  # India news
]


def _parse_rss_items(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate")
        items.append({"title": title, "description": description, "link": link, "pubDate": pub})
    return items


def _timestamp_from_pub(pub: str | None) -> str:
    if pub:
        try:
            dt = parsedate_to_datetime(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except Exception:  # noqa: BLE001
            pass
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def collect_rss(
    collection: Collection,
    feeds: Iterable[str] | None = None,
    limit_per_feed: int = 15,
) -> int:
    feeds = list(feeds or DEFAULT_FEEDS)
    saved = 0
    for feed_url in feeds:
        try:
            resp = requests.get(feed_url, timeout=20, headers={"User-Agent": "weather-collector/1.0"})
            if resp.status_code != 200:
                logger.warning("RSS HTTP %s for %s", resp.status_code, feed_url)
                continue
            items = _parse_rss_items(resp.text)[:limit_per_feed]
        except Exception as exc:  # noqa: BLE001
            logger.error("RSS fetch failed %s: %s", feed_url, exc)
            continue

        for item in items:
            title = item["title"]
            desc = item["description"]
            raw_text = f"{title}. {desc}"
            if not looks_like_weather(raw_text):
                continue
            tags = ["#IMD"] if "imd" in raw_text.lower() else ["#Weather"]
            text = inject_hashtags(raw_text, tags)
            city, state, lat, lng = detect_city_state(f"{title} {desc}")
            event, confidence = classify_event(text)
            ts = _timestamp_from_pub(item.get("pubDate"))
            report_id = f"RSS_{abs(hash(item.get('link') or title)) % 10_000_000}_{city[:3].upper()}"
            if collection.find_one({"report_id": report_id}):
                continue
            doc = build_report(
                report_id=report_id,
                text=text[:800],
                platform="news_rss",
                source_type="news",
                city=city,
                state=state,
                event_type=event,
                timestamp=ts,
                timestamp_hour=ts[:13] + ":00:00",
                lat=lat,
                lng=lng,
                confidence=confidence,
                hashtags=extract_hashtags(text),
                raw_data={"feed": feed_url, **item},
            )
            doc["classification"]["method"] = "nlp_classifier"
            collection.insert_one(doc)
            publish_raw(doc)
            saved += 1
            logger.info("RSS saved %s | %s | %s", city, event, title[:60])
    return saved


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from pymongo import MongoClient
    from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI

    col = MongoClient(MONGO_URI)[DB_NAME][COLLECTION_NAME]
    print("saved", collect_rss(col))

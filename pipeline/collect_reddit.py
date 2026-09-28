"""Reddit social collector (public JSON, no paid API)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests
from pymongo.collection import Collection

from pipeline.bus import publish_raw
from pipeline.geocode import detect_city_state
from pipeline.hashtags import extract_hashtags, inject_hashtags
from pipeline.schema import build_report
from ml.event_classifier import classify_event

logger = logging.getLogger(__name__)

SEARCH_QUERIES = [
    "IMD weather India",
    "flooding Mumbai OR Chennai OR Assam",
    "rainfall thunderstorm India",
    "heatwave Delhi OR Rajasthan",
    "#IMD rain",
]


def _fetch_reddit_search(query: str, limit: int = 20) -> list[dict]:
    params = {"q": query, "sort": "new", "limit": limit, "t": "week"}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }
    last_status = None
    for url in (
        "https://old.reddit.com/search.json",
        "https://www.reddit.com/search.json",
    ):
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        last_status = resp.status_code
        if resp.status_code != 200:
            continue
        children = resp.json().get("data", {}).get("children", [])
        return [c.get("data", {}) for c in children]
    logger.warning("Reddit HTTP %s for %s", last_status, query)
    return []


def collect_reddit(collection: Collection, limit_per_query: int = 12) -> int:
    saved = 0
    for query in SEARCH_QUERIES:
        try:
            posts = _fetch_reddit_search(query, limit=limit_per_query)
        except Exception as exc:  # noqa: BLE001
            logger.error("Reddit fetch failed: %s", exc)
            continue

        for post in posts:
            title = (post.get("title") or "").strip()
            body = (post.get("selftext") or "").strip()
            if not title:
                continue
            raw_text = f"{title}. {body}".strip()
            tags = ["#IMD"] if "imd" in raw_text.lower() else ["#Weather"]
            text = inject_hashtags(raw_text, tags)
            city, state, lat, lng = detect_city_state(text)
            event, confidence = classify_event(text)
            created = post.get("created_utc")
            if created:
                ts = datetime.fromtimestamp(float(created), tz=timezone.utc).isoformat().replace("+00:00", "Z")
            else:
                ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            pid = post.get("id") or abs(hash(title)) % 10_000_000
            report_id = f"RD_{pid}_{city[:3].upper()}"
            if collection.find_one({"report_id": report_id}):
                continue
            media_url = None
            preview = post.get("url") or ""
            if preview.endswith((".jpg", ".png", ".jpeg", ".webp")):
                media_url = preview
            doc = build_report(
                report_id=report_id,
                text=text[:900],
                platform="reddit",
                source_type="social",
                city=city,
                state=state,
                event_type=event,
                timestamp=ts,
                timestamp_hour=ts[:13] + ":00:00",
                lat=lat,
                lng=lng,
                confidence=confidence,
                hashtags=extract_hashtags(text),
                media_url=media_url,
                user_id=post.get("author"),
                raw_data={"permalink": post.get("permalink"), "subreddit": post.get("subreddit"), "query": query},
            )
            doc["classification"]["method"] = "nlp_classifier"
            collection.insert_one(doc)
            publish_raw(doc)
            saved += 1
            logger.info("Reddit saved %s | %s | %s", city, event, title[:50])
    return saved


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from pymongo import MongoClient
    from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI

    col = MongoClient(MONGO_URI)[DB_NAME][COLLECTION_NAME]
    print("saved", collect_reddit(col))

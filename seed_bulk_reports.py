"""Bulk-seed 500+ schema-valid reports for demos (Phase 0)."""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

from pipeline.hashtags import extract_hashtags, inject_hashtags
from pipeline.schema import build_report
from pipeline.settings import CITIES, COLLECTION_NAME, DB_NAME, MONGO_URI

EVENT_TEMPLATES = {
    "rainfall": [
        "Heavy rainfall reported since morning #Rainfall waterlogging on main road in {locality}.",
        "Continuous rain for hours in {city} #IMD alert shared by locals near {locality}.",
    ],
    "thunderstorm": [
        "Loud thunderstorm with lightning near {locality} #Thunderstorm #IMD",
        "Severe thunder activity over {city}; power flickers reported around {locality}.",
    ],
    "flooding": [
        "Flood water entering ground-floor homes near {locality} #Flood #IMD",
        "Roads flooded after overnight rain in {locality}, {city}. Residents evacuating.",
    ],
    "heatwave": [
        "Extreme heat today across {city}; feels much hotter near {locality} #Heatwave",
        "Heatwave conditions persist #IMD advisory mentioned for {city}.",
    ],
    "fog": [
        "Dense fog since early morning, low visibility near {locality} #Fog",
        "Airport delays possible in {city} due to thick fog around {locality}.",
    ],
    "dust_storm": [
        "Sudden dust storm reduced visibility near {locality} #DustStorm",
        "Strong dusty winds sweeping through {city} around {locality}.",
    ],
    "strong_wind": [
        "Very strong winds uprooted trees near {locality} #StrongWind",
        "Gusty winds reported across {city}; outdoor activity unsafe near {locality}.",
    ],
}

LOCALITIES = {
    "Mumbai": ["Dharavi", "Kurla", "Andheri", "Bandra"],
    "Delhi": ["Dwarka", "Yamuna Bank", "Minto Road", "Saket"],
    "Bengaluru": ["Whitefield", "Bellandur", "Koramangala", "Indiranagar"],
    "Chennai": ["Velachery", "T Nagar", "Mylapore", "Adyar"],
    "Kolkata": ["Salt Lake", "Howrah", "Behala", "Park Street"],
    "Hyderabad": ["Hitech City", "Banjara Hills", "Secunderabad"],
    "Pune": ["Hinjewadi", "Koregaon Park", "Shivaji Nagar"],
    "Jaipur": ["Malviya Nagar", "Sanganer", "C Scheme"],
    "Guwahati": ["Anil Nagar", "Zoo Road", "Paltan Bazaar"],
    "Lucknow": ["Gomti Nagar", "Chowk", "Hazratganj"],
    "Ahmedabad": ["Maninagar", "Vastrapur", "SG Highway"],
    "Bhubaneswar": ["Patia", "Old Town", "Chandrasekharpur"],
}

SOURCES = [
    ("citizen_report", "citizen"),
    ("reddit", "social"),
    ("news_rss", "news"),
    ("open-meteo", "api"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=520)
    parser.add_argument("--enrich", action="store_true")
    args = parser.parse_args()

    client = MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]
    now = datetime.now(timezone.utc)
    city_names = list(CITIES.keys())
    events = list(EVENT_TEMPLATES.keys())
    inserted = 0

    for i in range(args.count):
        city = random.choice(city_names)
        state, lat, lng = CITIES[city]
        event = random.choice(events)
        locality = random.choice(LOCALITIES.get(city, [city]))
        platform, source_type = random.choice(SOURCES)
        hours_ago = random.uniform(0.5, 96)
        ts = now - timedelta(hours=hours_ago)
        text = random.choice(EVENT_TEMPLATES[event]).format(city=city, locality=locality)
        if random.random() < 0.35:
            text = inject_hashtags(text, ["#IMD"])
        hashtags = extract_hashtags(text)
        report_id = f"BULK_{ts.strftime('%Y%m%d%H%M%S')}_{i:04d}_{city[:3].upper()}"

        if collection.find_one({"report_id": report_id}):
            continue

        jitter_lat = lat + random.uniform(-0.08, 0.08)
        jitter_lng = lng + random.uniform(-0.08, 0.08)
        doc = build_report(
            report_id=report_id,
            text=text,
            platform=platform,
            source_type=source_type,
            city=city,
            state=state,
            event_type=event,
            timestamp=ts.isoformat().replace("+00:00", "Z"),
            timestamp_hour=ts.replace(minute=0, second=0, microsecond=0).isoformat(),
            lat=jitter_lat,
            lng=jitter_lng,
            confidence=round(random.uniform(0.55, 0.95), 2),
            hashtags=hashtags,
            locality=locality,
            media_url=f"https://example.com/media/{report_id}.jpg" if random.random() < 0.25 else None,
        )
        collection.insert_one(doc)
        inserted += 1

    print(f"inserted={inserted} total={collection.count_documents({})}")
    if args.enrich:
        from api.enrichment import enrich_and_persist

        print(enrich_and_persist(collection, limit=min(args.count, 800), apply_ml_status=True))


if __name__ == "__main__":
    main()

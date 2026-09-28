"""Seed extra demo reports (varied event types) so the dashboard is useful."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pymongo import MongoClient

from pipeline.schema import build_report
from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI

SAMPLES = [
    ("Mumbai", "flooding", "Flood water entering ground-floor homes near Dharavi, residents evacuating."),
    ("Mumbai", "rainfall", "Heavy rainfall reported since morning, waterlogging on main road in Kurla."),
    ("Chennai", "thunderstorm", "Loud thunderstorm with lightning strikes near Velachery residential area."),
    ("Delhi", "heatwave", "Extreme heat today across central Delhi, temperatures feel much higher than forecast."),
    ("Delhi", "fog", "Dense fog since early morning, visibility very low on the highway near Dwarka."),
    ("Jaipur", "dust_storm", "Sudden dust storm reduced visibility near Sanganer, strong winds carrying dust."),
    ("Bengaluru", "rainfall", "Heavy rainfall causing waterlogging in Whitefield and Bellandur."),
    ("Guwahati", "flooding", "Flooding reported near Anil Nagar after continuous overnight rain."),
    ("Kolkata", "thunderstorm", "Thunderstorm with strong winds reported over Salt Lake and Howrah."),
    ("Pune", "strong_wind", "Very strong winds uprooted trees near the market area in central Pune."),
    ("Lucknow", "heatwave", "Severe heatwave conditions in Gomti Nagar, people advised to stay indoors."),
    ("Ahmedabad", "rainfall", "Moderate to heavy rain across Maninagar with local waterlogging."),
]


def main() -> None:
    client = MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]
    now = datetime.now(timezone.utc)
    inserted = 0

    for i, (city, event, text) in enumerate(SAMPLES):
        ts = now - timedelta(hours=i * 2 + 1)
        report_id = f"DEMO_{ts.strftime('%Y%m%d%H')}_{city[:3].upper()}_{event[:3].upper()}"
        if collection.find_one({"report_id": report_id}):
            continue
        doc = build_report(
            report_id=report_id,
            text=text,
            platform="citizen_report",
            source_type="citizen",
            city=city,
            event_type=event,
            timestamp=ts.isoformat().replace("+00:00", "Z"),
            timestamp_hour=ts.replace(minute=0, second=0, microsecond=0).isoformat(),
            confidence=0.8,
        )
        # Force source platform string the mapper maps to citizen_report
        doc["source"] = {"type": "citizen", "platform": "citizen_report", "user_id": f"user_{i}"}
        collection.insert_one(doc)
        inserted += 1

    from api.enrichment import enrich_and_persist

    summary = enrich_and_persist(collection, limit=200, apply_ml_status=True)
    print(f"seeded={inserted} enrich={summary} total={collection.count_documents({})}")


if __name__ == "__main__":
    main()

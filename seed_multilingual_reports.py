"""
Seed paired EN + HI/Hinglish reports that should corroborate/cluster.

    python seed_multilingual_reports.py
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from pymongo import MongoClient

from api.enrichment import enrich_and_persist
from pipeline.languages import detect_languages
from pipeline.schema import build_report
from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI, city_meta

PAIRS = [
    {
        "city": "Mumbai",
        "event": "flooding",
        "en": "Heavy waterlogging near Andheri station after continuous rain. Roads partially submerged #MumbaiRain",
        "hi": "अंधेरी स्टेशन के पास लगातार बारिश के बाद सड़कों पर जलभराव हो गया है #MumbaiRain",
    },
    {
        "city": "Delhi",
        "event": "heatwave",
        "en": "Severe afternoon heatwave advisory — avoid outdoor work between 12 and 4 pm #IMD",
        "hi": "दोपहर में भीषण गर्मी की चेतावनी — दोपहर 12 से 4 बजे बाहर काम न करें #IMD",
    },
    {
        "city": "Chennai",
        "event": "rainfall",
        "en": "Sudden baarish and waterlogging reported around T Nagar market this evening",
        "hi": "टी नागर बाजार के आसपास अचानक बारिश और पानी भर गया है शाम को",
    },
]


def main() -> None:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    col = client[DB_NAME][COLLECTION_NAME]
    now = datetime.now(timezone.utc)
    saved = 0
    for i, pair in enumerate(PAIRS):
        state, lat, lng = city_meta(pair["city"])
        for lang_key, text in (("EN", pair["en"]), ("HI", pair["hi"])):
            ts = (now - timedelta(minutes=i * 3 + (0 if lang_key == "EN" else 1))).replace(
                microsecond=0
            )
            report_id = f"MLING_{pair['city'][:3].upper()}_{lang_key}_{ts.strftime('%H%M%S')}"
            if col.find_one({"report_id": report_id}):
                continue
            doc = build_report(
                report_id=report_id,
                text=text,
                platform="citizen_report",
                source_type="citizen",
                city=pair["city"],
                state=state,
                event_type=pair["event"],
                timestamp=ts.isoformat().replace("+00:00", "Z"),
                timestamp_hour=ts.replace(minute=0, second=0).isoformat(),
                lat=lat,
                lng=lng,
                confidence=0.8,
                hashtags=[],
                media_url="https://example.com/media/stock_beach.jpg" if lang_key == "EN" else None,
            )
            if lang_key == "EN":
                doc["media_meta"] = {"exif_city": "Bengaluru", "exif_lat": 12.97, "exif_lng": 77.59}
            doc["languages"] = detect_languages(text)
            doc["classification"]["method"] = "multilingual_seed"
            col.insert_one(doc)
            saved += 1
            print("seeded", report_id, doc["languages"])

    summary = enrich_and_persist(col, limit=400, apply_ml_status=True)
    print("saved", saved, "enrich", summary)


if __name__ == "__main__":
    main()

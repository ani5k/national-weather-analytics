"""
Open-Meteo collector (no API key required).

Fetches live weather for Indian cities and upserts Schema V1 docs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests
from pymongo.collection import Collection

from pipeline.bus import publish_raw
from pipeline.hashtags import extract_hashtags, inject_hashtags
from pipeline.schema import build_report
from pipeline.settings import CITIES

logger = logging.getLogger(__name__)

WEATHER_CODE_MAP = {
    0: "clear",
    1: "cloudy",
    2: "cloudy",
    3: "cloudy",
    45: "fog",
    48: "fog",
    51: "rainfall",
    53: "rainfall",
    55: "rainfall",
    56: "rainfall",
    57: "rainfall",
    61: "rainfall",
    63: "rainfall",
    65: "rainfall",
    66: "rainfall",
    67: "rainfall",
    71: "fog",
    73: "fog",
    75: "fog",
    77: "fog",
    80: "rainfall",
    81: "rainfall",
    82: "flooding",
    85: "fog",
    86: "fog",
    95: "thunderstorm",
    96: "thunderstorm",
    99: "thunderstorm",
}


def map_weather_code(code: int, wind_speed: float | None = None) -> str:
    event = WEATHER_CODE_MAP.get(int(code or 0), "unknown")
    if wind_speed is not None and wind_speed >= 40 and event in {"clear", "cloudy", "unknown"}:
        return "strong_wind"
    if wind_speed is not None and wind_speed >= 50:
        return "dust_storm"
    return event


def fetch_openmeteo(lat: float, lon: float) -> dict | None:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
    )
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            logger.warning("Open-Meteo HTTP %s for %s,%s", response.status_code, lat, lon)
            return None
        return response.json()
    except requests.RequestException as exc:
        logger.error("Open-Meteo network error: %s", exc)
        return None


def collect_openmeteo(collection: Collection, cities: dict | None = None) -> int:
    cities = cities or CITIES
    saved = 0

    for city, (state, lat, lon) in cities.items():
        data = fetch_openmeteo(lat, lon)
        if not data:
            continue
        current = data.get("current_weather") or {}
        if not current:
            continue

        temp = current.get("temperature")
        wind = current.get("windspeed")
        code = current.get("weathercode", 0)
        event = map_weather_code(code, wind)

        time_str = current.get("time") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        # Open-Meteo with timezone=auto returns a local wall-clock time without offset.
        # Treat it as UTC-naive wall time by converting "now" stamp instead of appending a fake Z.
        try:
            local_naive = datetime.fromisoformat(str(time_str).replace("Z", ""))
            # Prefer collection time in real UTC so dashboard "time ago" is correct
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            timestamp_hour = local_naive.replace(minute=0, second=0, microsecond=0).isoformat()
        except ValueError:
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            timestamp_hour = timestamp

        report_id = f"OM_{datetime.now(timezone.utc).strftime('%Y%m%d%H')}_{city[:3].upper()}"

        # Dedup by platform + city + hour
        existing = collection.find_one(
            {
                "$or": [
                    {"report_id": report_id},
                    {
                        "source.platform": "open-meteo",
                        "location.city": city,
                        "timestamp_hour": timestamp_hour,
                    },
                ]
            }
        )
        if existing:
            logger.info("skip duplicate %s %s", city, timestamp_hour)
            continue

        text = (
            f"{event.replace('_', ' ').capitalize()} conditions in {city}, {state}: "
            f"{temp}°C with wind {wind} km/h reported near the city centre. #Weather"
        )
        if event in {"rainfall", "thunderstorm", "flooding", "heatwave"}:
            text = inject_hashtags(text, ["#IMD"])

        doc = build_report(
            report_id=report_id,
            text=text,
            platform="open-meteo",
            city=city,
            state=state,
            event_type=event,
            timestamp=timestamp,
            timestamp_hour=timestamp_hour,
            temperature=temp,
            wind_speed=wind,
            condition=event,
            lat=lat,
            lng=lon,
            confidence=0.95,
            raw_data=data,
            hashtags=extract_hashtags(text),
        )
        doc["classification"]["method"] = "ingest_api_code"

        collection.insert_one(doc)
        publish_raw(doc)
        saved += 1
        logger.info("saved %s | %s | %s°C", city, event, temp)

    return saved

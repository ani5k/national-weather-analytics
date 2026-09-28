"""Build Schema V2 documents that the FastAPI mapper understands."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pipeline.hashtags import extract_hashtags
from pipeline.settings import city_meta


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_event_type(event: str) -> str:
    aliases = {
        "strong_winds": "strong_wind",
        "rain": "rainfall",
        "flood": "flooding",
        "floods": "flooding",
        "duststorm": "dust_storm",
        "dust storm": "dust_storm",
        "clear": "rainfall",  # avoid unknown clutter in PS demo filters — only when forced
    }
    key = (event or "unknown").strip().lower().replace("-", "_").replace(" ", "_")
    # Do not remap clear/cloudy here for collectors — keep as-is unless alias hit
    if key in {"clear", "cloudy", "unknown", "forecast"}:
        return key
    return aliases.get(key, key)


def build_report(
    *,
    report_id: str,
    text: str,
    platform: str,
    city: str,
    event_type: str,
    timestamp: str,
    temperature: Optional[float] = None,
    humidity: Optional[float] = None,
    wind_speed: Optional[float] = None,
    condition: Optional[str] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    state: Optional[str] = None,
    source_type: str = "api",
    confidence: float = 0.9,
    raw_data: Any = None,
    timestamp_hour: Optional[str] = None,
    hashtags: Optional[list[str]] = None,
    locality: Optional[str] = None,
    media_url: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    meta_state, meta_lat, meta_lng = city_meta(city)
    event = normalize_event_type(event_type)
    tags = hashtags if hashtags is not None else extract_hashtags(text)

    return {
        "report_id": report_id,
        "text": text,
        "hashtags": tags,
        "source": {
            "type": source_type,
            "platform": platform,
            "user_id": user_id,
        },
        "location": {
            "city": city,
            "state": state or meta_state,
            "latitude": lat if lat is not None else meta_lat,
            "longitude": lng if lng is not None else meta_lng,
            "locality": locality,
        },
        "timestamp": timestamp,
        "timestamp_hour": timestamp_hour,
        "media": {
            "has_photo": bool(media_url),
            "media_url": media_url,
        },
        "media_url": media_url,
        "weather_metrics": {
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "condition": condition or event,
        },
        "classification": {
            "event_type": event,
            "event_types": [event],
            "confidence": confidence,
            "categorized_at": _now(),
            "method": "ingest",
        },
        "raw_data": raw_data,
        "created_at": _now(),
        "cleaned_text": None,
        "duplicate_detection": None,
        "duplicate_group_id": None,
        "credibility": None,
        "credibility_score": None,
        "credibility_reasons": None,
        "verification": {
            "status": "pending",
            "verified_by": None,
            "verified_at": None,
        },
        "verification_status": "pending",
        "verified_by": None,
        "updated_at": None,
    }

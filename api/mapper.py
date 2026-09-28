"""
Map nested MongoDB collector documents -> flat Report objects
expected by Frontend/INTEGRATION.md.
"""

from __future__ import annotations

from typing import Any, Optional

# Fallback when collectors leave location.state as null
CITY_TO_STATE = {
    "Mumbai": "Maharashtra",
    "Delhi": "Delhi",
    "Bengaluru": "Karnataka",
    "Bangalore": "Karnataka",
    "Chennai": "Tamil Nadu",
    "Kolkata": "West Bengal",
    "Hyderabad": "Telangana",
    "Pune": "Maharashtra",
    "Jaipur": "Rajasthan",
    "Guwahati": "Assam",
    "Bhubaneswar": "Odisha",
    "Lucknow": "Uttar Pradesh",
    "Ahmedabad": "Gujarat",
}

# City centroids used when lat/lng are missing (e.g. forecast rows)
CITY_COORDS = {
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.6139, 77.2090),
    "Bengaluru": (12.9716, 77.5946),
    "Bangalore": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Kolkata": (22.5726, 88.3639),
    "Hyderabad": (17.3850, 78.4867),
    "Pune": (18.5204, 73.8567),
    "Jaipur": (26.9124, 75.7873),
    "Guwahati": (26.1445, 91.7362),
    "Bhubaneswar": (20.2961, 85.8245),
    "Lucknow": (26.8467, 80.9462),
    "Ahmedabad": (23.0225, 72.5714),
}

SOURCE_MAP = {
    "openweathermap": "news_rss",
    "openweathermap-forecast": "news_rss",
    "open-meteo": "open-meteo",
    "openmeteo": "open-meteo",
    "twitter": "twitter",
    "x": "twitter",
    "reddit": "reddit",
    "citizen_report": "citizen_report",
    "citizen": "citizen_report",
    "news_rss": "news_rss",
    "rss": "news_rss",
    "imd": "imd",
}

EVENT_TYPE_MAP = {
    "strong_winds": "strong_wind",
    "strong wind": "strong_wind",
    "duststorm": "dust_storm",
    "dust storm": "dust_storm",
    "flood": "flooding",
    "floods": "flooding",
    "rain": "rainfall",
    "heavy_rain": "rainfall",
    "thunder": "thunderstorm",
    "heat": "heatwave",
    "coldwave": "fog",  # no coldwave in UI enum — closest non-breaking fallback unused often
}

FRONTEND_EVENT_TYPES = {
    "rainfall",
    "thunderstorm",
    "flooding",
    "heatwave",
    "fog",
    "dust_storm",
    "strong_wind",
}


def _dig(doc: dict, *path: str, default=None):
    cur: Any = doc
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def normalize_source(raw: Any) -> str:
    if isinstance(raw, dict):
        raw = raw.get("platform") or raw.get("type") or ""
    key = str(raw or "").strip().lower()
    return SOURCE_MAP.get(key, "news_rss")


def normalize_event_type(raw: Any) -> str:
    if isinstance(raw, dict):
        raw = raw.get("event_type") or (raw.get("event_types") or [None])[0]
    key = str(raw or "unknown").strip().lower().replace("-", "_").replace(" ", "_")
    mapped = EVENT_TYPE_MAP.get(key, key)
    # clear / cloudy / forecast / unknown stay as-is so data is not inventively remapped
    return mapped


def resolve_state(city: str, state: Optional[str]) -> str:
    if state and str(state).strip():
        return str(state).strip()
    return CITY_TO_STATE.get(city, "Unknown")


def resolve_coords(city: str, lat: Any, lng: Any) -> tuple[float, float]:
    try:
        if lat is not None and lng is not None:
            return float(lat), float(lng)
    except (TypeError, ValueError):
        pass
    return CITY_COORDS.get(city, (20.5937, 78.9629))  # India centroid fallback


def resolve_credibility(doc: dict) -> int:
    credibility = doc.get("credibility")
    if isinstance(credibility, dict):
        score = credibility.get("score")
        if score is not None:
            return int(max(0, min(100, round(float(score)))))
    if isinstance(credibility, (int, float)):
        return int(max(0, min(100, round(float(credibility)))))

    # Flat field already written by enrichment
    flat = doc.get("credibility_score")
    if flat is not None:
        return int(max(0, min(100, round(float(flat)))))

    # Lazy compute from rules (keeps GET working before enrichment runs)
    from credibility.scorer import score_report

    return score_report(doc)


def resolve_verification(doc: dict) -> tuple[str, str]:
    verification = doc.get("verification") or {}
    status = (
        doc.get("verification_status")
        or verification.get("status")
        or "pending"
    )
    verified_by = (
        doc.get("verified_by")
        or verification.get("verified_by")
        or "ml"
    )
    if status not in {"verified", "pending", "rejected"}:
        status = "pending"
    if not verified_by:
        verified_by = "ml"
    return status, verified_by


def resolve_duplicate_group_id(doc: dict) -> Optional[str]:
    if doc.get("duplicate_group_id"):
        return doc["duplicate_group_id"]
    dup = doc.get("duplicate_detection") or {}
    if isinstance(dup, dict):
        return dup.get("group_id") or dup.get("duplicate_group_id")
    return None


def doc_to_report(doc: dict) -> dict:
    """Convert one Mongo document into the flat frontend Report dict."""
    location = doc.get("location") or {}
    city = (
        location.get("city")
        or doc.get("city")
        or "Unknown"
    )
    lat, lng = resolve_coords(
        city,
        location.get("latitude", location.get("lat", doc.get("lat"))),
        location.get("longitude", location.get("lng", doc.get("lng"))),
    )

    classification = doc.get("classification") or {}
    event_type = normalize_event_type(
        classification.get("event_type")
        or doc.get("event_type")
        or classification
    )

    media = doc.get("media") or {}
    media_url = doc.get("media_url")
    if media_url is None:
        media_url = media.get("media_url")

    report_id = doc.get("report_id") or doc.get("id")
    if not report_id and doc.get("_id") is not None:
        report_id = str(doc["_id"])

    status, verified_by = resolve_verification(doc)
    timestamp = doc.get("timestamp") or doc.get("created_at") or ""
    if hasattr(timestamp, "isoformat"):
        timestamp = timestamp.isoformat()
        if not timestamp.endswith("Z"):
            timestamp += "Z"

    credibility = doc.get("credibility") if isinstance(doc.get("credibility"), dict) else {}
    reasons = doc.get("credibility_reasons") or credibility.get("reasons") or []
    factors = doc.get("credibility_factors") or credibility.get("factors") or []
    risk = doc.get("risk") if isinstance(doc.get("risk"), dict) else {}
    forensics = doc.get("media_forensics") if isinstance(doc.get("media_forensics"), dict) else {}

    return {
        "id": str(report_id),
        "text": doc.get("text") or doc.get("cleaned_text") or "",
        "source": normalize_source(doc.get("source")),
        "event_type": event_type,
        "city": city,
        "state": resolve_state(city, location.get("state") or doc.get("state")),
        "locality": location.get("locality") or doc.get("locality"),
        "lat": lat,
        "lng": lng,
        "timestamp": str(timestamp),
        "credibility_score": resolve_credibility(doc),
        "verification_status": status,
        "verified_by": verified_by,
        "media_url": media_url,
        "duplicate_group_id": resolve_duplicate_group_id(doc),
        "hashtags": doc.get("hashtags") or [],
        "credibility_reasons": reasons,
        "credibility_factors": factors,
        "risk_severity": risk.get("severity"),
        "people_at_risk": risk.get("people_at_risk"),
        "hospitals_nearby": risk.get("hospitals_nearby"),
        "major_roads_nearby": risk.get("major_roads_nearby"),
        "official_anchor_id": doc.get("official_anchor_id"),
        "media_forensics_detail": forensics.get("detail") or doc.get("media_forensics_detail"),
        "languages": doc.get("languages") or [],
    }

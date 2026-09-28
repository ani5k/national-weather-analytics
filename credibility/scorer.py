"""
Trust Fusion Score v3 — explainable, factorized credibility.

Rubric version: trust_fusion_v3
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse, unquote

from pipeline.hashtags import has_official_imd_tag

TRUST_RUBRIC_VERSION = "trust_fusion_v3"

ESTABLISHED_SOURCES = {
    "openweathermap",
    "openweathermap-forecast",
    "open-meteo",
    "openmeteo",
    "news_rss",
    "imd",
    "datagov",
    "data.gov.in",
}
SOCIAL_SOURCES = {"reddit", "twitter", "x"}
CITIZEN_SOURCES = {"citizen_report", "citizen"}

# Event types that are implausible overnight in many Indian cities (demo heuristic)
DAYTIME_EVENTS = {"heatwave", "dust_storm"}


def _dig(doc: dict, *path: str, default=None):
    cur: Any = doc
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur


def _source_key(doc: dict) -> str:
    source = doc.get("source")
    if isinstance(source, dict):
        return str(source.get("platform") or source.get("type") or "").strip().lower()
    return str(source or "").strip().lower()


def _hashtags(doc: dict) -> list[str]:
    tags = doc.get("hashtags")
    return tags if isinstance(tags, list) else []


def _event_type(doc: dict) -> str:
    classification = doc.get("classification") or {}
    return str(classification.get("event_type") or doc.get("event_type") or "").lower()


def _parse_hour(doc: dict) -> Optional[int]:
    ts = doc.get("timestamp") or doc.get("created_at")
    if not ts:
        return None
    try:
        if hasattr(ts, "hour"):
            return int(ts.hour)
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return int(dt.hour)
    except Exception:  # noqa: BLE001
        return None


def geo_time_plausibility_adjustment(doc: dict) -> tuple[int, Optional[dict]]:
    """
    Penalize clearly implausible event/time pairs.
    Optional weather_metrics cross-check (sensor snapshot).
    """
    event = _event_type(doc)
    hour = _parse_hour(doc)
    metrics = doc.get("weather_metrics") or {}

    if event in DAYTIME_EVENTS and hour is not None and (hour < 5 or hour > 21):
        return -15, {
            "factor": "geo_time_plausibility",
            "delta": -15,
            "detail": f"{event} reported at hour={hour} (unlikely overnight)",
        }

    temp = metrics.get("temperature")
    if event == "heatwave" and isinstance(temp, (int, float)) and temp < 28:
        return -12, {
            "factor": "geo_time_plausibility",
            "delta": -12,
            "detail": f"heatwave claim vs sensor temp={temp}°C",
        }
    if event == "fog" and isinstance(temp, (int, float)) and temp > 38:
        return -10, {
            "factor": "geo_time_plausibility",
            "delta": -10,
            "detail": f"fog claim vs hot sensor temp={temp}°C",
        }
    return 0, None


def text_image_consistency_adjustment(doc: dict) -> tuple[int, Optional[dict]]:
    """
    Lightweight caption vs media filename/URL heuristic (pre-vision).
    Flood text + beach/sunset/stock filename → downrank.
    """
    text = (doc.get("cleaned_text") or doc.get("text") or "").lower()
    media = doc.get("media") or {}
    url = str(doc.get("media_url") or media.get("media_url") or "").lower()
    if not url:
        return 0, None

    path = unquote(urlparse(url).path)
    floodish = any(w in text for w in ("flood", "waterlog", "inundat", "submerged"))
    rainish = any(w in text for w in ("rain", "downpour", "thunderstorm"))
    mismatch_tokens = ("beach", "sunset", "sunrise", "vacation", "stock", "portrait", "selfie", "cat", "dog")
    hit = [t for t in mismatch_tokens if t in path or t in url]
    if (floodish or rainish) and hit:
        return -20, {
            "factor": "text_image_consistency",
            "delta": -20,
            "detail": f"caption weather vs media tokens {hit}",
        }
    # mild boost if filename suggests rain/flood
    align = [t for t in ("flood", "rain", "storm", "water") if t in path]
    if (floodish or rainish) and align:
        return 5, {
            "factor": "text_image_consistency",
            "delta": 5,
            "detail": f"media filename aligns ({align})",
        }
    return 0, None


def score_report_detailed(
    doc: dict,
    corroboration_count: Optional[int] = None,
    official_nearby: bool = False,
    media_penalty: int = 0,
    official_anchor_id: Optional[str] = None,
) -> dict:
    """Return score, band, reasons, factors, rubric version."""
    reasons: list[str] = []
    factors: list[dict] = []
    score = 0

    lat = _dig(doc, "location", "latitude")
    lng = _dig(doc, "location", "longitude")
    city = _dig(doc, "location", "city") or doc.get("city")
    try:
        has_coords = lat is not None and lng is not None
        if has_coords:
            float(lat)
            float(lng)
    except (TypeError, ValueError):
        has_coords = False
    if has_coords or city:
        score += 20
        reasons.append("+20 location/city present")
        factors.append({"factor": "location", "delta": 20, "detail": "geo or city present"})

    media = doc.get("media") or {}
    media_url = doc.get("media_url") or media.get("media_url")
    if media.get("has_photo") or media_url:
        score += 15
        reasons.append("+15 media attached")
        factors.append({"factor": "media", "delta": 15, "detail": "media_url present"})

    if doc.get("timestamp") or doc.get("created_at"):
        score += 10
        reasons.append("+10 timestamp present")
        factors.append({"factor": "timestamp", "delta": 10, "detail": "timestamp present"})

    src = _source_key(doc)
    if src in ESTABLISHED_SOURCES or src == "imd":
        score += 20
        reasons.append("+20 established/API/news/IMD source")
        factors.append({"factor": "source_reputation", "delta": 20, "detail": src or "established"})
    elif src in SOCIAL_SOURCES:
        score += 8
        reasons.append("+8 social source (needs corroboration)")
        factors.append({"factor": "source_reputation", "delta": 8, "detail": src})
    elif src in CITIZEN_SOURCES:
        score += 10
        reasons.append("+10 citizen report")
        factors.append({"factor": "source_reputation", "delta": 10, "detail": "citizen"})

    text = doc.get("cleaned_text") or doc.get("text") or ""
    words = [w for w in str(text).split() if w]
    if len(words) >= 8:
        score += 10
        reasons.append("+10 detailed description")
        factors.append({"factor": "detail", "delta": 10, "detail": f"{len(words)} words"})

    metrics = doc.get("weather_metrics") or {}
    if any(metrics.get(k) is not None for k in ("temperature", "humidity", "wind_speed", "condition")):
        score += 10
        reasons.append("+10 weather metrics present")
        factors.append({"factor": "sensor_metrics", "delta": 10, "detail": "weather_metrics"})

    tags = _hashtags(doc)
    if has_official_imd_tag(tags):
        score += 12
        reasons.append("+12 official #IMD hashtag")
        factors.append({"factor": "imd_hashtag", "delta": 12, "detail": "#IMD"})

    if corroboration_count is None:
        dup = doc.get("duplicate_detection") or {}
        if isinstance(dup, dict):
            corroboration_count = dup.get("corroboration_count")
            if corroboration_count is None and dup.get("group_size"):
                corroboration_count = max(0, int(dup["group_size"]) - 1)
    corroboration_count = int(corroboration_count or 0)
    if corroboration_count >= 2:
        score += 25
        reasons.append(f"+25 corroboration ({corroboration_count} peers)")
        factors.append({"factor": "corroboration", "delta": 25, "detail": f"{corroboration_count} peers"})
    elif corroboration_count == 1:
        score += 15
        reasons.append("+15 one corroborating report")
        factors.append({"factor": "corroboration", "delta": 15, "detail": "1 peer"})

    if official_nearby or official_anchor_id or doc.get("official_anchor_id"):
        score += 10
        anchor = official_anchor_id or doc.get("official_anchor_id") or "nearby"
        reasons.append(f"+10 official anchor ({anchor})")
        factors.append({"factor": "official_anchor", "delta": 10, "detail": str(anchor)})

    gt_delta, gt_factor = geo_time_plausibility_adjustment(doc)
    if gt_factor:
        score += gt_delta
        reasons.append(f"{gt_delta:+d} {gt_factor['detail']}")
        factors.append(gt_factor)

    ti_delta, ti_factor = text_image_consistency_adjustment(doc)
    if ti_factor:
        score += ti_delta
        reasons.append(f"{ti_delta:+d} {ti_factor['detail']}")
        factors.append(ti_factor)

    # Extra media forensics penalties passed in
    if media_penalty:
        score -= abs(media_penalty)
        reasons.append(f"-{abs(media_penalty)} media integrity penalty")
        factors.append(
            {
                "factor": "media_forensics",
                "delta": -abs(media_penalty),
                "detail": doc.get("media_forensics_detail") or "integrity checks",
            }
        )

    score = int(max(0, min(100, score)))
    return {
        "score": score,
        "band": credibility_band(score),
        "reasons": reasons,
        "factors": factors,
        "method": TRUST_RUBRIC_VERSION,
        "rubric_version": TRUST_RUBRIC_VERSION,
    }


def credibility_band(score: int) -> str:
    if score >= 80:
        return "HIGH"
    if score >= 60:
        return "MEDIUM"
    if score >= 40:
        return "LOW"
    return "VERY_LOW"


def score_report(doc: dict, corroboration_count: Optional[int] = None) -> int:
    return score_report_detailed(doc, corroboration_count=corroboration_count)["score"]


def score_and_label(doc: dict, corroboration_count: Optional[int] = None, **kwargs) -> dict:
    return score_report_detailed(doc, corroboration_count=corroboration_count, **kwargs)

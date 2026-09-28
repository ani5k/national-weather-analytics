"""Hashtag extraction for #IMD and weather-related tags."""

from __future__ import annotations

import re

HASHTAG_RE = re.compile(r"#([A-Za-z][A-Za-z0-9_]{1,48})")

KNOWN_WEATHER_TAGS = {
    "imd",
    "rainfall",
    "rain",
    "flood",
    "flooding",
    "thunderstorm",
    "thunder",
    "heatwave",
    "heat",
    "fog",
    "duststorm",
    "dust_storm",
    "strongwind",
    "strong_wind",
    "cyclone",
    "monsoon",
    "weather",
    "weatheralert",
}


def extract_hashtags(text: str) -> list[str]:
    if not text:
        return []
    found = []
    seen = set()
    for match in HASHTAG_RE.findall(text):
        tag = f"#{match}"
        key = match.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(tag)
    return found


def has_official_imd_tag(hashtags: list[str] | None) -> bool:
    return any(h.lower() == "#imd" for h in (hashtags or []))


def inject_hashtags(text: str, tags: list[str]) -> str:
    existing = {h.lower() for h in extract_hashtags(text)}
    extra = [t for t in tags if t.lower() not in existing]
    if not extra:
        return text
    return f"{text.rstrip()} {' '.join(extra)}".strip()

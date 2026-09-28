"""City/state gazetteer helper for RSS/Reddit text."""

from __future__ import annotations

from pipeline.settings import CITIES

# Longer names first so "New Delhi" style matches aren't needed — we use known cities
_CITY_NAMES = sorted(CITIES.keys(), key=len, reverse=True)


def detect_city_state(text: str) -> tuple[str, str, float, float]:
    lowered = (text or "").lower()
    for city in _CITY_NAMES:
        if city.lower() in lowered:
            state, lat, lng = CITIES[city]
            return city, state, lat, lng
    # default India centroid-ish — Mumbai as fallback for demo continuity
    state, lat, lng = CITIES["Mumbai"]
    return "Mumbai", state, lat, lng

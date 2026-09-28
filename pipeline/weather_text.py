"""Shared check so news ingest keeps weather items only."""

from __future__ import annotations

import re

_WEATHER = re.compile(
    r"\b("
    r"rains?|rainfall|floods?|flooding|storms?|cyclones?|thunder|lightning|"
    r"heatwaves?|heat wave|monsoon|weather|fog|winds?|cold wave|coldwave|"
    r"drought|landslides?|waterlog\w*|cloudbursts?|hail|imd|mausam|"
    r"temperature|downpour|deluge|humidity"
    r")\b",
    re.IGNORECASE,
)


def looks_like_weather(text: str) -> bool:
    return bool(_WEATHER.search(text or ""))

"""
Lightweight event classifier for PS event types.

Uses keyword rules + optional embedding prototype matching (hash embeddings
when sentence-transformers is unavailable). Active-learning prototypes from
ml/active_prototypes.json are merged when present.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from duplicate_detection.embeddings import get_embedding
from duplicate_detection.similarity import text_similarity

EVENT_TYPES = [
    "rainfall",
    "thunderstorm",
    "flooding",
    "heatwave",
    "fog",
    "dust_storm",
    "strong_wind",
]

KEYWORD_MAP = {
    "flooding": ["flood", "flooded", "waterlogging", "inundat", "submerged"],
    "thunderstorm": ["thunder", "lightning", "storm cell"],
    "rainfall": ["rain", "rainfall", "downpour", "drizzle", "shower", "monsoon"],
    "heatwave": ["heatwave", "heat wave", "scorching", "extreme heat", "hot day"],
    "fog": ["fog", "mist", "low visibility", "smog"],
    "dust_storm": ["dust storm", "duststorm", "sandstorm", "dusty wind"],
    "strong_wind": ["strong wind", "gusty", "gale", "uprooted", "windstorm"],
}

PROTOTYPE_TEXTS = {
    "rainfall": "heavy rainfall and continuous rain causing wet roads",
    "thunderstorm": "thunderstorm with lightning and loud thunder",
    "flooding": "flood water entering homes and inundated streets",
    "heatwave": "extreme heatwave and scorching temperatures",
    "fog": "dense fog with very low visibility on highway",
    "dust_storm": "sudden dust storm reducing visibility with dusty winds",
    "strong_wind": "very strong winds uprooting trees near market",
}

ACTIVE_PATH = Path(__file__).resolve().parent / "active_prototypes.json"
_prototypes: dict[str, Optional[object]] = {}


def _load_active_texts() -> dict[str, str]:
    if not ACTIVE_PATH.exists():
        return {}
    try:
        data = json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    merged = {}
    for event, samples in data.items():
        if isinstance(samples, list) and samples:
            merged[event] = samples[0]
        elif isinstance(samples, str):
            merged[event] = samples
    return merged


def _ensure_prototypes() -> None:
    if _prototypes:
        return
    texts = {**PROTOTYPE_TEXTS, **_load_active_texts()}
    for key, text in texts.items():
        _prototypes[key] = get_embedding(text)


def classify_by_keywords(text: str) -> tuple[str | None, float]:
    lowered = (text or "").lower()
    scores = []
    for event, words in KEYWORD_MAP.items():
        hits = sum(1 for w in words if w in lowered)
        if hits:
            scores.append((event, hits))
    if not scores:
        return None, 0.0
    scores.sort(key=lambda x: x[1], reverse=True)
    best, hits = scores[0]
    conf = min(0.95, 0.55 + 0.1 * hits)
    return best, conf


def classify_by_embedding(text: str) -> tuple[str, float]:
    _ensure_prototypes()
    emb = get_embedding(text or "")
    if emb is None:
        return "rainfall", 0.4
    best_event = "rainfall"
    best_score = -1.0
    for event, proto in _prototypes.items():
        score = text_similarity(emb, proto)
        if score > best_score:
            best_score = score
            best_event = event
    conf = max(0.45, min(0.9, (best_score + 1) / 2))
    return best_event, float(conf)


def classify_event(text: str) -> tuple[str, float]:
    kw_event, kw_conf = classify_by_keywords(text)
    emb_event, emb_conf = classify_by_embedding(text)
    if kw_event and kw_conf >= 0.65:
        return kw_event, kw_conf
    if kw_event and kw_event == emb_event:
        return kw_event, max(kw_conf, emb_conf)
    if kw_event:
        return kw_event, max(0.5, (kw_conf + emb_conf) / 2)
    return emb_event, emb_conf

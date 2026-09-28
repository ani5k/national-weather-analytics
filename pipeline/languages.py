"""Detect rough language tags for multilingual clustering demos."""

from __future__ import annotations

import re

_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_LATIN = re.compile(r"[A-Za-z]")


def detect_languages(text: str) -> list[str]:
    """Return coarse language tags: hi / en / hinglish."""
    if not text:
        return []
    has_deva = bool(_DEVANAGARI.search(text))
    has_latin = bool(_LATIN.search(text))
    if has_deva and has_latin:
        return ["hi", "en", "hinglish"]
    if has_deva:
        return ["hi"]
    if has_latin:
        # Hinglish heuristic: common romanized Hindi tokens
        lower = text.lower()
        hinglish_tokens = ("baarish", "barsaat", "paani", "garmi", "andhi", "tezi", "bahaav")
        if any(t in lower for t in hinglish_tokens):
            return ["en", "hinglish"]
        return ["en"]
    return []

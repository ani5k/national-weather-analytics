"""Media forensics lite: EXIF GPS mismatch, pHash reuse, rain/flood heuristics."""

from __future__ import annotations

import hashlib
import io
import logging
from typing import Optional
from urllib.parse import urlparse

import requests

from pipeline.settings import CITIES

logger = logging.getLogger(__name__)

# Tiny demo "known stock" hash set (md5 of placeholder strings / URLs)
KNOWN_STOCK_HASHES = {
    hashlib.md5(b"https://example.com/media/stock_beach.jpg").hexdigest(),
    hashlib.md5(b"https://example.com/media/sunset.jpg").hexdigest(),
    hashlib.md5(b"placeholder.jpg").hexdigest(),
}


def _city_coords(city: str) -> Optional[tuple[float, float]]:
    meta = CITIES.get(city)
    if not meta:
        return None
    return meta[1], meta[2]


def perceptual_hash_from_bytes(data: bytes) -> str:
    """Simple block-mean hash (not cryptographic)."""
    try:
        from PIL import Image
        import numpy as np

        img = Image.open(io.BytesIO(data)).convert("L").resize((8, 8))
        arr = np.asarray(img, dtype=float)
        avg = arr.mean()
        bits = "".join("1" if x > avg else "0" for x in arr.flatten())
        return hashlib.md5(bits.encode()).hexdigest()
    except Exception:  # noqa: BLE001
        return hashlib.md5(data[:4096]).hexdigest()


def rain_flood_visual_score(data: bytes) -> tuple[float, str]:
    """
    Heuristic: bluish/gray dominant images score higher as rain/flood-like.
    Returns (0..1, label).
    """
    try:
        from PIL import Image
        import numpy as np

        img = Image.open(io.BytesIO(data)).convert("RGB").resize((32, 32))
        arr = np.asarray(img, dtype=float)
        r, g, b = arr[:, :, 0].mean(), arr[:, :, 1].mean(), arr[:, :, 2].mean()
        # cool/wet bias
        cool = (b - r) / 255.0
        dark = 1.0 - ((r + g + b) / (3 * 255.0))
        score = max(0.0, min(1.0, 0.5 * cool + 0.5 * dark + 0.2))
        label = "wet_scene_likely" if score >= 0.45 else "dry_or_unclear"
        return score, label
    except Exception as exc:  # noqa: BLE001
        logger.debug("visual score failed: %s", exc)
        return 0.0, "unavailable"


def analyze_media(doc: dict) -> dict:
    """
    Returns {penalty, reasons, detail, phash, visual_label, exif_mismatch}.
    Safe if no media / fetch fails.
    """
    media = doc.get("media") or {}
    url = doc.get("media_url") or media.get("media_url")
    result = {
        "penalty": 0,
        "reasons": [],
        "detail": None,
        "phash": None,
        "visual_label": None,
        "exif_mismatch": False,
        "reuse_suspected": False,
    }
    if not url:
        return result

    # Known stock / placeholder reuse via URL hash
    url_hash = hashlib.md5(str(url).encode()).hexdigest()
    if url_hash in KNOWN_STOCK_HASHES or "example.com" in str(url) or "placeholder" in str(url).lower():
        result["penalty"] += 20
        result["reuse_suspected"] = True
        result["reasons"].append("-20 possible reused/stock image")

    # EXIF city mismatch from media_meta if present
    claimed = (_dig_city(doc) or "").lower()
    exif_city = str((doc.get("media_meta") or {}).get("exif_city") or "").lower()
    exif_lat = (doc.get("media_meta") or {}).get("exif_lat")
    exif_lng = (doc.get("media_meta") or {}).get("exif_lng")
    if exif_city and claimed and exif_city != claimed:
        result["penalty"] += 25
        result["exif_mismatch"] = True
        result["reasons"].append("-25 photo GPS/city mismatch")
    elif exif_lat is not None and exif_lng is not None and claimed:
        coords = _city_coords(claimed.title() if claimed.islower() else claimed)
        # try exact city key
        if not coords:
            for cname in CITIES:
                if cname.lower() == claimed:
                    coords = _city_coords(cname)
                    break
        if coords:
            try:
                dlat = abs(float(exif_lat) - coords[0])
                dlng = abs(float(exif_lng) - coords[1])
                if dlat > 0.8 or dlng > 0.8:
                    result["penalty"] += 25
                    result["exif_mismatch"] = True
                    result["reasons"].append("-25 photo EXIF far from claimed city")
            except (TypeError, ValueError):
                pass

    # Optional fetch for pHash / visual (skip non-http)
    if str(url).startswith("http") and "example.com" not in str(url):
        try:
            resp = requests.get(url, timeout=8, headers={"User-Agent": "weather-media/1.0"})
            if resp.status_code == 200 and resp.content:
                ph = perceptual_hash_from_bytes(resp.content)
                result["phash"] = ph
                if ph in KNOWN_STOCK_HASHES:
                    result["penalty"] += 15
                    result["reuse_suspected"] = True
                    result["reasons"].append("-15 perceptual hash matched stock set")
                vscore, vlabel = rain_flood_visual_score(resp.content)
                result["visual_label"] = vlabel
                text = (doc.get("text") or "").lower()
                if any(w in text for w in ("flood", "rain")) and vlabel == "dry_or_unclear":
                    result["penalty"] += 10
                    result["reasons"].append("-10 text claims rain/flood but image looks dry")
        except Exception as exc:  # noqa: BLE001
            logger.debug("media fetch skipped: %s", exc)

    result["detail"] = "; ".join(result["reasons"]) if result["reasons"] else None
    result["penalty"] = int(min(40, result["penalty"]))
    return result


def _dig_city(doc: dict) -> Optional[str]:
    loc = doc.get("location") or {}
    return loc.get("city") or doc.get("city")

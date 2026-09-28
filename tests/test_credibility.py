"""
tests/test_credibility.py
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from credibility.scorer import credibility_band, score_and_label, score_report


def test_established_source_with_location_scores_high():
    doc = {
        "text": "Heavy rainfall reported across several localities since morning hours #IMD",
        "hashtags": ["#IMD"],
        "source": {"platform": "OpenWeatherMap"},
        "location": {"city": "Mumbai", "latitude": 19.07, "longitude": 72.87},
        "timestamp": "2026-09-05T09:12:00Z",
        "media": {"has_photo": True, "media_url": "photo.jpg"},
        "weather_metrics": {"temperature": 28.0},
        "duplicate_detection": {"corroboration_count": 2},
    }
    detail = score_and_label(doc)
    assert detail["score"] >= 90
    assert credibility_band(detail["score"]) == "HIGH"
    assert detail["reasons"]
    assert detail.get("factors")
    assert detail.get("rubric_version") == "trust_fusion_v3"


def test_sparse_report_scores_low():
    doc = {"text": "rain"}
    score = score_report(doc)
    assert score < 40
    assert credibility_band(score) == "VERY_LOW"


def test_media_penalty_and_factors():
    doc = {
        "text": "Flooding downtown with photo evidence from morning patrol",
        "source": {"platform": "citizen_report"},
        "location": {"city": "Mumbai", "latitude": 19.07, "longitude": 72.87},
        "timestamp": "2026-09-05T10:00:00Z",
        "media_url": "https://example.com/media/stock_beach.jpg",
    }
    detail = score_and_label(doc, media_penalty=20, official_anchor_id="IMD_demo")
    assert any(f.get("factor") == "media_forensics" for f in detail["factors"])
    assert any(f.get("factor") == "official_anchor" for f in detail["factors"])


if __name__ == "__main__":
    test_established_source_with_location_scores_high()
    test_sparse_report_scores_low()
    test_media_penalty_and_factors()
    print("All credibility tests passed.")

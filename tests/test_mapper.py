"""
tests/test_mapper.py
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from api.mapper import doc_to_report


def test_maps_nested_collector_doc():
    doc = {
        "_id": "abc",
        "report_id": "OWM_20260909_Mum",
        "text": "Rain in Mumbai",
        "source": {"type": "api", "platform": "OpenWeatherMap"},
        "location": {
            "city": "Mumbai",
            "state": None,
            "latitude": 19.076,
            "longitude": 72.8777,
        },
        "timestamp": "2026-09-09T10:00:00Z",
        "classification": {"event_type": "rainfall"},
        "media": {"has_photo": False, "media_url": None},
        "credibility": None,
        "verification": {"status": "pending", "verified_by": None},
    }
    report = doc_to_report(doc)
    assert report["id"] == "OWM_20260909_Mum"
    assert report["source"] == "news_rss"
    assert report["event_type"] == "rainfall"
    assert report["city"] == "Mumbai"
    assert report["state"] == "Maharashtra"
    assert report["lat"] == 19.076
    assert report["lng"] == 72.8777
    assert report["verification_status"] == "pending"
    assert report["verified_by"] == "ml"
    assert 0 <= report["credibility_score"] <= 100


def test_normalizes_strong_winds():
    doc = {
        "report_id": "X1",
        "text": "Windy",
        "source": "open-meteo",
        "location": {"city": "Pune", "latitude": 18.5, "longitude": 73.8},
        "timestamp": "2026-09-09T10:00:00Z",
        "classification": {"event_type": "strong_winds"},
        "verification": {"status": "verified", "verified_by": "ml"},
    }
    report = doc_to_report(doc)
    assert report["event_type"] == "strong_wind"
    assert report["state"] == "Maharashtra"


if __name__ == "__main__":
    test_maps_nested_collector_doc()
    test_normalizes_strong_winds()
    print("All mapper tests passed.")

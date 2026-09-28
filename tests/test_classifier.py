"""tests/test_classifier.py"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from ml.event_classifier import classify_event


def test_flood_keywords():
    event, conf = classify_event("Flood water entering homes after heavy rain #Flood")
    assert event == "flooding"
    assert conf >= 0.55


def test_heatwave_keywords():
    event, _ = classify_event("Extreme heatwave and scorching temperatures in Delhi")
    assert event == "heatwave"


if __name__ == "__main__":
    test_flood_keywords()
    test_heatwave_keywords()
    print("classifier ok")

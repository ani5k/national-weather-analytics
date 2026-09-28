"""
tests/test_duplicates.py

Light unit tests that avoid loading the heavy sentence-transformer model.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from duplicate_detection.clustering import are_duplicates, time_difference_minutes
from duplicate_detection.location import distance_km


def test_time_difference():
    assert time_difference_minutes("2026-08-29T10:00:00Z", "2026-08-29T10:30:00Z") == 30


def test_are_duplicates_true():
    assert are_duplicates(0.8, 1.0, 30) is True


def test_are_duplicates_false_far_apart():
    assert are_duplicates(0.9, 50.0, 10) is False


def test_distance_small():
    d = distance_km((13.0078, 77.7512), (13.0080, 77.7515))
    assert d < 1.0


if __name__ == "__main__":
    test_time_difference()
    test_are_duplicates_true()
    test_are_duplicates_false_far_apart()
    test_distance_small()
    print("All duplicate tests passed.")

"""
duplicate_detection/clustering.py

Determines whether reports are likely duplicates using:
1. Semantic text similarity
2. Geographic distance
3. Time difference

Then groups duplicate reports using DBSCAN.
"""

from datetime import datetime, timezone
from sklearn.cluster import DBSCAN
import numpy as np


# Initial thresholds.
# These will be tuned later using real project data.
SIMILARITY_THRESHOLD = 0.70
DISTANCE_THRESHOLD_KM = 5.0
TIME_THRESHOLD_MINUTES = 180


def time_difference_minutes(timestamp_a: str, timestamp_b: str) -> float:
    """
    Calculate the time difference between two report timestamps.

    Returns:
        Difference in minutes.
    """

    time_a = datetime.fromisoformat(
        timestamp_a.replace("Z", "+00:00")
    )

    time_b = datetime.fromisoformat(
        timestamp_b.replace("Z", "+00:00")
    )

    return abs((time_a - time_b).total_seconds()) / 60


def are_duplicates(
    similarity: float,
    distance_km: float,
    time_difference: float
) -> bool:
    """
    Decide whether two reports are likely duplicates.

    A pair is considered a duplicate when:
    - semantic similarity is high
    - locations are close
    - reports happened within the time window
    """

    return (
        similarity >= SIMILARITY_THRESHOLD
        and distance_km <= DISTANCE_THRESHOLD_KM
        and time_difference <= TIME_THRESHOLD_MINUTES
    )


def cluster_duplicate_reports(duplicate_matrix):
    """
    Group duplicate reports using DBSCAN.

    duplicate_matrix:
        A matrix where:
        0 = reports are duplicates
        1 = reports are not duplicates

    Returns:
        Cluster labels.
    """

    dbscan = DBSCAN(
        eps=0.5,
        min_samples=1,
        metric="precomputed"
    )

    labels = dbscan.fit_predict(duplicate_matrix)

    return labels


if __name__ == "__main__":
    # Simple test of time difference
    timestamp_a = "2026-08-29T10:00:00Z"
    timestamp_b = "2026-08-29T10:30:00Z"

    difference = time_difference_minutes(
        timestamp_a,
        timestamp_b
    )

    print("Time difference:", difference, "minutes")

    # Test duplicate decision
    result = are_duplicates(
        similarity=0.7664,
        distance_km=0.039,
        time_difference=difference
    )

    print("Are reports duplicates?", result)
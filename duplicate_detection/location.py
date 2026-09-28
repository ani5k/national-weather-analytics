"""
duplicate_detection/location.py

Calculates geographical distance between two reports using geopy.
"""

from geopy.distance import geodesic


def distance_km(coord_a: tuple, coord_b: tuple) -> float:
    """
    Calculate the geographical distance between two coordinates.

    Coordinates must be in:
        (latitude, longitude)

    Returns:
        Distance in kilometres.
    """

    if not coord_a or not coord_b:
        return float("inf")

    return geodesic(coord_a, coord_b).km


if __name__ == "__main__":
    # Whitefield example coordinates
    report_a = (13.0078, 77.7512)
    report_b = (13.0080, 77.7515)

    distance = distance_km(report_a, report_b)

    print("Distance between reports:", round(distance, 3), "km")
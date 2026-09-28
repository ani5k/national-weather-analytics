"""Approximate people-at-risk estimates for event clusters (demo layer)."""

from __future__ import annotations

# Approximate metro populations (census-scale, rounded) for demo impact overlay
CITY_POPULATION = {
    "Mumbai": 12_400_000,
    "Delhi": 11_000_000,
    "Bengaluru": 8_400_000,
    "Chennai": 7_100_000,
    "Kolkata": 4_500_000,
    "Hyderabad": 6_800_000,
    "Pune": 3_100_000,
    "Jaipur": 3_000_000,
    "Guwahati": 1_000_000,
    "Lucknow": 2_800_000,
    "Ahmedabad": 5_500_000,
    "Bhubaneswar": 900_000,
}

# Precomputed amenity counts near city centroids (demo static layer)
CITY_AMENITIES = {
    "Mumbai": {"hospitals": 42, "major_roads": 28},
    "Delhi": {"hospitals": 55, "major_roads": 34},
    "Bengaluru": {"hospitals": 38, "major_roads": 30},
    "Chennai": {"hospitals": 31, "major_roads": 22},
    "Kolkata": {"hospitals": 29, "major_roads": 20},
    "Hyderabad": {"hospitals": 27, "major_roads": 24},
    "Pune": {"hospitals": 22, "major_roads": 18},
    "Jaipur": {"hospitals": 18, "major_roads": 14},
    "Guwahati": {"hospitals": 12, "major_roads": 10},
    "Lucknow": {"hospitals": 20, "major_roads": 15},
    "Ahmedabad": {"hospitals": 24, "major_roads": 19},
    "Bhubaneswar": {"hospitals": 11, "major_roads": 9},
}

SEVERITY_FRACTION = {
    "high": 0.012,
    "moderate": 0.004,
    "low": 0.001,
}

EVENT_MULTIPLIER = {
    "flooding": 1.4,
    "thunderstorm": 1.1,
    "rainfall": 0.8,
    "heatwave": 1.0,
    "fog": 0.5,
    "dust_storm": 0.9,
    "strong_wind": 0.9,
}


def estimate_people_at_risk(city: str, event_type: str, severity: str, group_size: int = 1) -> dict:
    pop = CITY_POPULATION.get(city, 500_000)
    frac = SEVERITY_FRACTION.get(severity, 0.001)
    mult = EVENT_MULTIPLIER.get(event_type, 1.0)
    # more corroborating reports → slightly higher estimated exposure
    cluster_boost = 1.0 + min(0.5, 0.05 * max(0, group_size - 1))
    people = int(pop * frac * mult * cluster_boost)
    amenities = CITY_AMENITIES.get(city, {"hospitals": 5, "major_roads": 5})
    return {
        "people_at_risk": people,
        "population_base": pop,
        "hospitals_nearby": amenities["hospitals"],
        "major_roads_nearby": amenities["major_roads"],
        "estimate_note": "Approximate demo estimate — not an official NDMA figure",
    }

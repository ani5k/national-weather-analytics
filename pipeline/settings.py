"""Shared env + city metadata for all collectors."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "mongodb://127.0.0.1:27017"
DB_NAME = os.getenv("DB_NAME", "weather_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "weather_data")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# city -> (state, lat, lng)
CITIES = {
    "Mumbai": ("Maharashtra", 19.0760, 72.8777),
    "Delhi": ("Delhi", 28.6139, 77.2090),
    "Bengaluru": ("Karnataka", 12.9716, 77.5946),
    "Chennai": ("Tamil Nadu", 13.0827, 80.2707),
    "Kolkata": ("West Bengal", 22.5726, 88.3639),
    "Hyderabad": ("Telangana", 17.3850, 78.4867),
    "Pune": ("Maharashtra", 18.5204, 73.8567),
    "Jaipur": ("Rajasthan", 26.9124, 75.7873),
    "Guwahati": ("Assam", 26.1445, 91.7362),
    "Lucknow": ("Uttar Pradesh", 26.8467, 80.9462),
    "Ahmedabad": ("Gujarat", 23.0225, 72.5714),
    "Bhubaneswar": ("Odisha", 20.2961, 85.8245),
}


def city_meta(city: str) -> tuple[str, Optional[float], Optional[float]]:
    meta = CITIES.get(city)
    if not meta:
        return ("Unknown", None, None)
    return meta

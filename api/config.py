"""
Central config — accepts both MONGO_URI and MONGODB_URI so collector
scripts and the API share the same Atlas cluster without fighting over names.
"""

import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")

# Prefer collector defaults (weather_db / weather_data) because that is where
# scheduled_*.py actually writes. Override via .env if you use sih_weather.
DB_NAME = os.getenv("DB_NAME", "weather_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "weather_data")

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

# Active-alert rule used by GET /stats (matches frontend mock for now)
ACTIVE_ALERT_EVENT_TYPES = {"flooding", "thunderstorm"}
ACTIVE_ALERT_MIN_CREDIBILITY = 60

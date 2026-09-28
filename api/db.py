"""MongoDB connection helpers for the API."""

from functools import lru_cache

from pymongo import MongoClient
from pymongo.collection import Collection

from api.config import COLLECTION_NAME, DB_NAME, MONGO_URI


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    if not MONGO_URI:
        raise ValueError(
            "MONGO_URI / MONGODB_URI is not set. Copy .env.example to .env and fill it in."
        )
    return MongoClient(MONGO_URI)


def get_collection() -> Collection:
    return get_client()[DB_NAME][COLLECTION_NAME]


def ensure_indexes() -> None:
    """Create indexes used by filters and admin updates."""
    collection = get_collection()
    collection.create_index("report_id", unique=True, sparse=True)
    collection.create_index("timestamp")
    collection.create_index("location.city")
    collection.create_index("location.state")
    collection.create_index("classification.event_type")
    collection.create_index("verification.status")
    collection.create_index("duplicate_detection.group_id")

"""
database/mongodb.py

Handles the connection between our Python project and MongoDB.
"""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "weather_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "weather_data")


def get_client() -> MongoClient:
    """Create and return a MongoDB client using the URI from .env."""
    if not MONGO_URI:
        raise ValueError(
            "MONGO_URI / MONGODB_URI is not set. Add it to your .env file "
            "(see .env.example for the expected format)."
        )
    return MongoClient(MONGO_URI)


def get_collection():
    """Return the reports collection we'll be reading/writing."""
    client = get_client()
    db = client[DB_NAME]
    return db[COLLECTION_NAME]


def test_connection():
    """Quick sanity check: ping the server and print result."""
    client = get_client()
    try:
        client.admin.command("ping")
        print("MongoDB connection successful.")
    except Exception as e:
        print("MongoDB connection failed:", e)
    finally:
        client.close()


if __name__ == "__main__":
    test_connection()

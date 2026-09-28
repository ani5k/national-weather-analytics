import pymongo
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

# FIX: Use the correct environment variable name
uri = os.getenv("MONGODB_URI")  # Make sure this matches your .env
if not uri:
    print("❌ MONGODB_URI not found in .env")
    exit(1)

client = pymongo.MongoClient(uri)
db = client["weather_db"]
collection = db["weather_data"]

# Update all records that either have no classification or classification is None
result = collection.update_many(
    {"$or": [{"classification": {"$exists": False}}, {"classification": None}]},
    {"$set": {
        "classification": {
            "event_type": "unknown",
            "event_types": ["unknown"],
            "confidence": 0.5,
            "categorized_at": datetime.now().isoformat() + "Z"
        }
    }}
)

print(f"✅ Updated {result.modified_count} records")

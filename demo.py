"""
Hackathon Demo Script
Shows the pipeline working with live data
"""

import os
import pymongo
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
db = client["weather_db"]
collection = db["weather_data"]

print("=" * 60)
print("🌤️  WEATHER DATA PIPELINE – DEMO")
print("=" * 60)

# 1. Total records
total = collection.count_documents({})
print(f"\n📊 Total Records Collected: {total}")

# 2. Records by source
print("\n📡 Data Sources:")
for doc in collection.aggregate([
    {"$group": {"_id": "$source.platform", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]):
    print(f"  {doc['_id']}: {doc['count']} records")

# 3. Records by event type
print("\n🏷️ Event Types:")
for doc in collection.aggregate([
    {"$group": {"_id": "$classification.event_type", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]):
    print(f"  {doc['_id']}: {doc['count']} records")

# 4. Latest records
print("\n📝 Latest 5 Records:")
for doc in collection.find().sort([('_id', -1)]).limit(5):
    print(f"  {doc.get('location', {}).get('city', 'Unknown')} | "
          f"{doc.get('source', {}).get('platform', 'Unknown')} | "
          f"{doc.get('classification', {}).get('event_type', 'Unknown')} | "
          f"{doc.get('created_at', '')[:19]}")

print("\n" + "=" * 60)
print("✅ Demo ready!")

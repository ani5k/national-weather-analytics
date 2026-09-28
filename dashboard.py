"""
Weather Data Pipeline Dashboard
Shows real-time stats from your MongoDB collection
"""

import os
import pymongo
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
db = client["weather_db"]
collection = db["weather_data"]

print("\n" + "=" * 60)
print("🌤️  WEATHER DATA PIPELINE DASHBOARD")
print("=" * 60)
print(f"📅 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 1. Total records
total = collection.count_documents({})
print(f"\n📊 Total Records Collected: {total}")

# 2. Records by source
print("\n📡 Records by Source:")
sources = collection.aggregate([
    {"$group": {"_id": "$source.platform", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
])
for s in sources:
    print(f"  {s['_id']}: {s['count']}")

# 3. Records by event type
print("\n🏷️ Records by Event Type:")
events = collection.aggregate([
    {"$group": {"_id": "$classification.event_type", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
])
for e in events:
    print(f"  {e['_id']}: {e['count']}")

# 4. Latest 5 records
print("\n📝 Latest 5 Records:")
for doc in collection.find().sort([('_id', -1)]).limit(5):
    city = doc.get('location', {}).get('city', 'Unknown')
    platform = doc.get('source', {}).get('platform', 'Unknown')
    event = doc.get('classification', {}).get('event_type', 'Unknown')
    temp = doc.get('weather_metrics', {}).get('temperature', 'N/A')
    print(f"  {city:12} | {platform:20} | {event:15} | {temp}°C")

# 5. Data freshness
print("\n⏰ Data Freshness:")
latest = collection.find_one(sort=[('_id', -1)])
if latest:
    created = latest.get('created_at')
    if created:
        print(f"  Latest record created: {created[:19]}")
    else:
        print("  No timestamp found")
else:
    print("  No records found")

print("\n" + "=" * 60)
print("✅ Dashboard ready!")

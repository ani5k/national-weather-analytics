"""
data.gov.in Weather Collector
Fetches historical temperature data from India Meteorological Department (IMD)
"""

import os
import requests
import pymongo
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("DATAGOV_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

# Resource ID for temperature dataset
RESOURCE_ID = "45787c4b-3210-4fd0-b120-63336e042370"

# Connect to MongoDB
client = pymongo.MongoClient(MONGO_URI)
db = client["weather_db"]
collection = db["weather_data"]

def fetch_datagov(limit=50):
    """Fetch temperature data from data.gov.in API"""
    url = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": limit
    }
    try:
        response = requests.get(url, params=params, timeout=120)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API error: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"❌ Network error: {e}")
        return None

def normalize_and_store(data):
    """Convert data.gov.in records to Schema V1 and store in MongoDB"""
    if not data:
        return
    
    records = data.get("records", [])
    if not records:
        print("⚠️  No records found")
        return
    
    saved = 0
    for record in records:
        # Extract fields from the record
        year = record.get("Year") or record.get("year")
        annual_temp = record.get("Annual") or record.get("annual")
        season = record.get("Season") or record.get("season")
        seasonal_temp = record.get("Seasonal") or record.get("seasonal")
        
        # Skip if no data
        if not year:
            continue
        
        # Build document
        doc = {
            "report_id": f"DG_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(year)[-4:]}",
            "text": f"India temperature data for {year}: Annual {annual_temp}°C",
            "source": {
                "type": "government",
                "platform": "data.gov.in",
                "user_id": "IMD"
            },
            "location": {
                "city": "India",
                "state": "All India",
                "latitude": None,
                "longitude": None
            },
            "timestamp": f"{year}-01-01T00:00:00Z",
            "timestamp_hour": f"{year}-01-01T00:00:00Z",
            "media": {"has_photo": False, "media_url": None},
            "weather_metrics": {
                "annual_temperature": annual_temp,
                "seasonal_temperature": seasonal_temp,
                "season": season,
                "source": "IMD"
            },
            "classification": {
                "event_type": "historical_temperature",
                "event_types": ["historical_temperature"],
                "confidence": 0.9,
                "categorized_at": datetime.now().isoformat() + "Z"
            },
            "raw_data": record,
            "created_at": datetime.now().isoformat() + "Z",
            "cleaned_text": None,
            "duplicate_detection": None,
            "credibility": None,
            "verification": {"status": "pending", "verified_by": None, "verified_at": None},
            "updated_at": None
        }
        
        # Dedup: check if this year already exists
        existing = collection.find_one({"weather_metrics.annual_temperature": annual_temp, "timestamp": f"{year}-01-01T00:00:00Z"})
        if existing:
            print(f"⏭️  Duplicate skipped: {year}")
            continue
        
        try:
            collection.insert_one(doc)
            saved += 1
            print(f"✅ Saved: {year} | Annual: {annual_temp}°C")
        except Exception as e:
            print(f"❌ DB error: {e}")
    
    print(f"✅ Saved {saved} new records from data.gov.in")

def main():
    print("🌤️  DATA.GOV.IN COLLECTOR STARTED")
    data = fetch_datagov(limit=10)
    if data:
        normalize_and_store(data)
    else:
        print("❌ Failed to fetch data")
    print("✅ Data.gov.in collection complete!")

if __name__ == "__main__":
    main()

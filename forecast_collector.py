"""
OpenWeatherMap 5-Day Forecast Collector
Fetches 5-day forecast (3-hour intervals) for Indian cities
"""

import os
import requests
import pymongo
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

client = pymongo.MongoClient(MONGO_URI)
db = client["weather_db"]
collection = db["weather_data"]

CITIES = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata"]

def fetch_forecast(city):
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"❌ Forecast API error for {city}: {r.status_code}")
            return None
    except Exception as e:
        print(f"❌ Network error: {e}")
        return None

def store_forecast(city, data):
    if not data:
        return
    
    # Get first 5 forecast entries (next ~15 hours)
    forecast_list = data.get("list", [])[:5]
    
    for entry in forecast_list:
        dt = datetime.fromtimestamp(entry.get("dt", 0))
        temp_c = round(entry["main"]["temp"] - 273.15, 1)
        
        doc = {
            "report_id": f"FC_{datetime.now().strftime('%Y%m%d%H%M%S')}_{city[:3]}",
            "text": f"Forecast for {city}: {entry['weather'][0]['description']}, {temp_c}°C",
            "source": {"type": "api", "platform": "OpenWeatherMap-Forecast", "user_id": None},
            "location": {"city": city, "state": None, "latitude": None, "longitude": None},
            "timestamp": dt.isoformat() + "Z",
            "timestamp_hour": dt.replace(minute=0, second=0, microsecond=0).isoformat(),
            "media": {"has_photo": False, "media_url": None},
            "weather_metrics": {
                "temperature": temp_c,
                "humidity": entry["main"].get("humidity"),
                "pressure": entry["main"].get("pressure"),
                "wind_speed": entry["wind"].get("speed"),
                "condition": entry["weather"][0]["description"]
            },
            "classification": {
                "event_type": "forecast",
                "event_types": ["forecast"],
                "confidence": 0.7,
                "categorized_at": datetime.now().isoformat() + "Z"
            },
            "raw_data": entry,
            "created_at": datetime.now().isoformat() + "Z",
            "cleaned_text": None,
            "duplicate_detection": None,
            "credibility": None,
            "verification": {"status": "pending", "verified_by": None, "verified_at": None},
            "updated_at": None
        }
        
        try:
            collection.insert_one(doc)
            print(f"✅ Forecast saved: {city} @ {dt.strftime('%H:%M')} - {temp_c}°C")
        except Exception as e:
            print(f"❌ DB error: {e}")

def main():
    print("🌤️  FORECAST COLLECTOR STARTED\n")
    for city in CITIES:
        print(f"--- {city} ---")
        data = fetch_forecast(city)
        if data:
            store_forecast(city, data)
        else:
            print(f"⚠️  No forecast for {city}")
        print()
    print("✅ Forecast collection complete!")

if __name__ == "__main__":
    main()

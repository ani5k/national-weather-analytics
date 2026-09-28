"""
Weather Data Collector v2 - OpenWeatherMap + MongoDB Atlas
Fetches weather for Indian cities and stores in MongoDB.
"""

import os
import requests
import pymongo
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

# List of Indian cities
CITIES = [
    "Mumbai",
    "Delhi",
    "Bengaluru",
    "Chennai",
    "Kolkata"
]

# Connect to MongoDB Atlas
client = pymongo.MongoClient(MONGO_URI)
db = client["weather_db"]
collection = db["weather_data"]

def get_weather(city):
    """Fetch current weather from OpenWeatherMap"""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ API error for {city}: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error for {city}: {e}")
        return None

def parse_and_store(data):
    """Parse weather data and store in MongoDB"""
    if not data:
        return None

    # Extract fields
    weather_doc = {
        "source": { "type": "api", "platform": "OpenWeatherMap", "user_id": None},
        "city": data.get("name"),
        "country": data.get("sys", {}).get("country"),
        "timestamp": datetime.utcnow(),  # collection time
        "api_timestamp": datetime.fromtimestamp(data.get("dt", 0)),
        "temperature": round(data["main"]["temp"] - 273.15, 1),
        "feels_like": round(data["main"]["feels_like"] - 273.15, 1),
        "humidity": data["main"].get("humidity"),
        "pressure": data["main"].get("pressure"),
        "condition": data["weather"][0]["description"],
        "condition_code": data["weather"][0]["id"],
        "wind_speed": data["wind"].get("speed"),
        "wind_deg": data["wind"].get("deg"),
        "clouds": data["clouds"].get("all"),
        "raw_data": data  # keep raw for debugging
    }

    # Insert into MongoDB
    try:
        result = collection.insert_one(weather_doc)
        print(f"✅ Saved {weather_doc['city']} | Temp: {weather_doc['temperature']}°C | ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        print(f"❌ Database error for {city}: {e}")
        return None

def main():
    print("🌤️  WEATHER COLLECTOR v2 STARTED\n")
    print(f"Collecting for {len(CITIES)} cities...\n")
    
    for city in CITIES:
        print(f"--- {city} ---")
        data = get_weather(city)
        if data:
            parse_and_store(data)
        else:
            print(f"⚠️  No data for {city}, skipping")
        print()
    
    print("✅ Collection cycle complete!")

if __name__ == "__main__":
    main()

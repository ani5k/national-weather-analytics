"""
Weather Collector - MERGED
Runs both OpenWeatherMap AND Open-Meteo every hour.
Logs everything to collector.log
"""

import os
import sys
import time
import logging
import requests
import pymongo
import schedule
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("collector.log"),
        logging.StreamHandler()
    ]
)

# Connect to MongoDB
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client["weather_db"]
    collection = db["weather_data"]
    logging.info("✅ Connected to MongoDB Atlas")
except Exception as e:
    logging.error(f"❌ MongoDB connection failed: {e}")
    sys.exit(1)

# ============================================
# OPENWEATHERMAP COLLECTOR
# ============================================
OWM_CITIES = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata"]

def fetch_openweathermap(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logging.warning(f"OWM API error for {city}: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"OWM network error for {city}: {e}")
        return None

def store_openweathermap(data):
    if not data:
        return None
    city = data.get("name")
    doc = {
        "report_id": f"OWM_{datetime.now().strftime('%Y%m%d%H%M%S')}_{city[:3]}",
        "text": f"Weather in {city}: {data['weather'][0]['description']}, {round(data['main']['temp'] - 273.15, 1)}°C",
        "source": {"type": "api", "platform": "OpenWeatherMap", "user_id": None},
        "location": {
            "city": city,
            "state": None,
            "latitude": data.get("coord", {}).get("lat"),
            "longitude": data.get("coord", {}).get("lon")
        },
        "timestamp": datetime.fromtimestamp(data.get("dt", 0)).isoformat() + "Z",
        "media": {"has_photo": False, "media_url": None},
        "weather_metrics": {
            "temperature": round(data["main"]["temp"] - 273.15, 1),
            "feels_like": round(data["main"]["feels_like"] - 273.15, 1),
            "humidity": data["main"].get("humidity"),
            "pressure": data["main"].get("pressure"),
            "wind_speed": data["wind"].get("speed"),
            "condition": data["weather"][0]["description"]
        },
        "raw_data": data,
        "created_at": datetime.now().isoformat() + "Z",
        "cleaned_text": None,
        "classification": None,
        "duplicate_detection": None,
        "credibility": None,
        "verification": {"status": "pending", "verified_by": None, "verified_at": None},
        "updated_at": None
    }
    try:
        result = collection.insert_one(doc)
        logging.info(f"✅ OWM - Saved {city} | Temp: {doc['weather_metrics']['temperature']}°C")
        return result.inserted_id
    except Exception as e:
        logging.error(f"❌ OWM DB error for {city}: {e}")
        return None

def collect_openweathermap():
    logging.info("--- OpenWeatherMap ---")
    for city in OWM_CITIES:
        data = fetch_openweathermap(city)
        if data:
            store_openweathermap(data)
        else:
            logging.warning(f"OWM: No data for {city}")

# ============================================
# OPEN-METEO COLLECTOR
# ============================================
OM_CITIES = {
    "Mumbai": (19.0760, 72.8777),
    "Delhi": (28.6139, 77.2090),
    "Bengaluru": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Kolkata": (22.5726, 88.3639),
    "Hyderabad": (17.3850, 78.4867),
    "Pune": (18.5204, 73.8567),
}

def fetch_openmeteo(lat, lon):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logging.warning(f"OM API error: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"OM network error: {e}")
        return None

def map_weather_code(code):
    if code == 0:
        return "clear"
    elif code in [1, 2, 3]:
        return "cloudy"
    elif code in [45, 48]:
        return "fog"
    elif code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        return "rainfall"
    elif code in [95, 96, 99]:
        return "thunderstorm"
    else:
        return "unknown"

def store_openmeteo(city, lat, lon, data):
    if not data:
        return None
    current = data.get("current_weather", {})
    if not current:
        logging.warning(f"OM: No current weather for {city}")
        return None

    doc = {
        "report_id": f"OM_{datetime.now().strftime('%Y%m%d%H%M%S')}_{city[:3]}",
        "text": f"Weather in {city}: {current.get('temperature')}°C, wind {current.get('windspeed')} km/h",
        "source": {"type": "api", "platform": "open-meteo", "user_id": None},
        "location": {
            "city": city,
            "state": None,
            "latitude": lat,
            "longitude": lon
        },
        "timestamp": current.get("time") + "Z",
        "media": {"has_photo": False, "media_url": None},
        "weather_metrics": {
            "temperature": current.get("temperature"),
            "wind_speed": current.get("windspeed"),
            "wind_direction": current.get("winddirection"),
            "weather_code": current.get("weathercode"),
            "condition": map_weather_code(current.get("weathercode"))
        },
        "raw_data": data,
        "created_at": datetime.now().isoformat() + "Z",
        "cleaned_text": None,
        "classification": None,
        "duplicate_detection": None,
        "credibility": None,
        "verification": {"status": "pending", "verified_by": None, "verified_at": None},
        "updated_at": None
    }
    try:
        result = collection.insert_one(doc)
        logging.info(f"✅ OM - Saved {city} | Temp: {doc['weather_metrics']['temperature']}°C")
        return result.inserted_id
    except Exception as e:
        logging.error(f"❌ OM DB error for {city}: {e}")
        return None

def collect_openmeteo():
    logging.info("--- Open-Meteo ---")
    for city, (lat, lon) in OM_CITIES.items():
        data = fetch_openmeteo(lat, lon)
        if data:
            store_openmeteo(city, lat, lon, data)
        else:
            logging.warning(f"OM: No data for {city}")

# ============================================
# MAIN COLLECTION FUNCTION
# ============================================
def collect_all():
    logging.info("=" * 50)
    logging.info("🌤️  MERGED COLLECTION CYCLE STARTED")
    collect_openweathermap()
    collect_openmeteo()
    logging.info("📊 Collection cycle complete")
    logging.info("=" * 50)

# ============================================
# SCHEDULER
# ============================================
def main():
    logging.info("🚀 MERGED Weather Collector started")
    logging.info("📅 Running every hour at minute 0")

    # Run once immediately
    collect_all()

    # Schedule every hour
    schedule.every().hour.at(":00").do(collect_all)

    logging.info("⏰ Scheduler active. Waiting...")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("🛑 Collector stopped by user")
        sys.exit(0)

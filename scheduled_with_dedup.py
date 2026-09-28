"""
Weather Collector v4 – With Deduplication
Checks for existing records before inserting.
"""

import os
import sys
import time
import logging
import requests
import pymongo
import schedule
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("collector.log"),
        logging.StreamHandler()
    ]
)

# MongoDB connection
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client["weather_db"]
    collection = db["weather_data"]
    logging.info("✅ Connected to MongoDB Atlas")
except Exception as e:
    logging.error(f"❌ MongoDB connection failed: {e}")
    sys.exit(1)

# Create index for deduplication (faster lookups)
try:
    collection.create_index([("source.platform", 1), ("location.city", 1), ("timestamp_hour", 1)])
    logging.info("✅ Deduplication index created")
except Exception as e:
    logging.warning(f"Index creation warning: {e}")

# ============================================
# DEDUPLICATION CHECK
# ============================================
def is_duplicate(platform, city, timestamp_hour):
    """Check if a record already exists for this source + city + hour"""
    existing = collection.find_one({
        "source.platform": platform,
        "location.city": city,
        "timestamp_hour": timestamp_hour
    })
    return existing is not None

def safe_insert(doc, platform, city, timestamp_hour):
    """Insert only if not a duplicate"""
    if is_duplicate(platform, city, timestamp_hour):
        logging.info(f"⏭️  DUPLICATE SKIPPED: {platform} - {city} @ {timestamp_hour}")
        return None
    
    try:
        result = collection.insert_one(doc)
        logging.info(f"✅ SAVED: {platform} - {city}")
        return result.inserted_id
    except Exception as e:
        logging.error(f"❌ DB error: {e}")
        return None

# ============================================
# OPENWEATHERMAP COLLECTOR
# ============================================
OWM_CITIES = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Kolkata"]

def fetch_owm(city):
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

def collect_owm():
    logging.info("--- OpenWeatherMap ---")
    for city in OWM_CITIES:
        data = fetch_owm(city)
        if not data:
            continue
        
        # Round timestamp to hour for deduplication
        dt = datetime.fromtimestamp(data.get("dt", 0))
        timestamp_hour = dt.replace(minute=0, second=0, microsecond=0).isoformat()

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
            "timestamp": dt.isoformat() + "Z",
            "timestamp_hour": timestamp_hour,  # for deduplication
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
        safe_insert(doc, "OpenWeatherMap", city, timestamp_hour)

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

def fetch_om(lat, lon):
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

def collect_om():
    logging.info("--- Open-Meteo ---")
    for city, (lat, lon) in OM_CITIES.items():
        data = fetch_om(lat, lon)
        if not data:
            continue
        
        current = data.get("current_weather", {})
        if not current:
            logging.warning(f"OM: No current weather for {city}")
            continue

        dt = datetime.fromisoformat(current.get("time"))
        timestamp_hour = dt.replace(minute=0, second=0, microsecond=0).isoformat()

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
            "timestamp_hour": timestamp_hour,
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
        safe_insert(doc, "open-meteo", city, timestamp_hour)

# ============================================
# MAIN
# ============================================
def collect_all():
    logging.info("=" * 50)
    logging.info("🌤️  COLLECTION WITH DEDUP STARTED")
    collect_owm()
    collect_om()
    logging.info("📊 Cycle complete")
    logging.info("=" * 50)

def main():
    logging.info("🚀 Weather Collector v4 (with deduplication) started")
    logging.info("📅 Running every hour at minute 0")
    collect_all()
    schedule.every().hour.at(":00").do(collect_all)
    logging.info("⏰ Scheduler active")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("🛑 Collector stopped")
        sys.exit(0)

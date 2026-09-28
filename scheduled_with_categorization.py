"""
Weather Collector v5 – With Event Categorization
Categorizes weather into event types.
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

# Create index for deduplication
try:
    collection.create_index([("source.platform", 1), ("location.city", 1), ("timestamp_hour", 1)])
    logging.info("✅ Deduplication index created")
except Exception as e:
    logging.warning(f"Index creation warning: {e}")

# ============================================
# EVENT CATEGORIZATION
# ============================================
def categorize_owm(weather_data):
    """Categorize OpenWeatherMap data"""
    temp = weather_data.get("main", {}).get("temp")
    temp_c = round(temp - 273.15, 1) if temp else None

    condition = weather_data.get("weather", [{}])[0].get("description", "").lower()
    condition_code = weather_data.get("weather", [{}])[0].get("id", 0)
    wind_speed = weather_data.get("wind", {}).get("speed", 0)

    events = []

    # Temperature-based
    if temp_c and temp_c > 40:
        events.append("heatwave")
    elif temp_c and temp_c < 10:
        events.append("coldwave")  # optional

    # Weather code-based
    if condition_code in [200, 201, 202, 210, 211, 212, 221, 230, 231, 232]:
        events.append("thunderstorm")
    elif condition_code in [300, 301, 302, 310, 311, 312, 313, 314, 321]:
        events.append("rainfall")
    elif condition_code in [500, 501, 502, 503, 504, 511, 520, 521, 522, 531]:
        events.append("rainfall")
    elif condition_code in [600, 601, 602, 611, 612, 613, 615, 616, 620, 621, 622]:
        events.append("snow")
    elif condition_code in [701, 711, 721, 731, 741, 751, 761, 762, 771, 781]:
        events.append("fog")
    elif condition_code in [800]:
        events.append("clear")
    elif condition_code in [801, 802, 803, 804]:
        events.append("cloudy")

    # Wind-based
    if wind_speed and wind_speed > 20:  # m/s ≈ 72 km/h
        events.append("strong_winds")

    # Description-based
    if "rain" in condition and "rainfall" not in events:
        events.append("rainfall")
    if "thunder" in condition and "thunderstorm" not in events:
        events.append("thunderstorm")
    if "fog" in condition and "fog" not in events:
        events.append("fog")
    if "heat" in condition and "heatwave" not in events:
        events.append("heatwave")

    return events if events else ["unknown"]

def categorize_om(weather_data, city_name):
    """Categorize Open-Meteo data"""
    current = weather_data.get("current_weather", {})
    temp = current.get("temperature")
    wind_speed = current.get("windspeed", 0)
    weather_code = current.get("weathercode", 0)

    events = []

    # Temperature-based
    if temp and temp > 40:
        events.append("heatwave")
    elif temp and temp < 10:
        events.append("coldwave")

    # Weather code-based (Open-Meteo codes)
    if weather_code == 0:
        events.append("clear")
    elif weather_code in [1, 2, 3]:
        events.append("cloudy")
    elif weather_code in [45, 48]:
        events.append("fog")
    elif weather_code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        events.append("rainfall")
    elif weather_code in [71, 73, 75, 77, 85, 86]:
        events.append("snow")
    elif weather_code in [95, 96, 99]:
        events.append("thunderstorm")

    # Wind-based
    if wind_speed and wind_speed > 30:  # km/h (Open-Meteo uses km/h)
        events.append("strong_winds")

    return events if events else ["unknown"]

# ============================================
# DEDUPLICATION CHECK
# ============================================
def is_duplicate(platform, city, timestamp_hour):
    existing = collection.find_one({
        "source.platform": platform,
        "location.city": city,
        "timestamp_hour": timestamp_hour
    })
    return existing is not None

def safe_insert(doc, platform, city, timestamp_hour):
    if is_duplicate(platform, city, timestamp_hour):
        logging.info(f"⏭️  DUPLICATE SKIPPED: {platform} - {city} @ {timestamp_hour}")
        return None
    try:
        result = collection.insert_one(doc)
        logging.info(f"✅ SAVED: {platform} - {city} | Events: {doc.get('classification', {}).get('event_types', [])}")
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

        dt = datetime.fromtimestamp(data.get("dt", 0))
        timestamp_hour = dt.replace(minute=0, second=0, microsecond=0).isoformat()

        # Categorize
        event_types = categorize_owm(data)

        # Get temp for text
        temp = data.get("main", {}).get("temp")
        temp_c = round(temp - 273.15, 1) if temp else None

        doc = {
            "report_id": f"OWM_{datetime.now().strftime('%Y%m%d%H%M%S')}_{city[:3]}",
            "text": f"Weather in {city}: {data['weather'][0]['description']}, {temp_c}°C",
            "source": {"type": "api", "platform": "OpenWeatherMap", "user_id": None},
            "location": {
                "city": city,
                "state": None,
                "latitude": data.get("coord", {}).get("lat"),
                "longitude": data.get("coord", {}).get("lon")
            },
            "timestamp": dt.isoformat() + "Z",
            "timestamp_hour": timestamp_hour,
            "media": {"has_photo": False, "media_url": None},
            "weather_metrics": {
                "temperature": temp_c,
                "feels_like": round(data["main"]["feels_like"] - 273.15, 1) if data.get("main", {}).get("feels_like") else None,
                "humidity": data["main"].get("humidity"),
                "pressure": data["main"].get("pressure"),
                "wind_speed": data["wind"].get("speed"),
                "condition": data["weather"][0]["description"]
            },
            # Classification (event types)
            "classification": {
                "event_type": event_types[0] if event_types else "unknown",
                "event_types": event_types,  # list of all events
                "confidence": 0.95,  # rule-based, high confidence
                "categorized_at": datetime.now().isoformat() + "Z"
            },
            "raw_data": data,
            "created_at": datetime.now().isoformat() + "Z",
            "cleaned_text": None,
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

        # Categorize
        event_types = categorize_om(data, city)

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
            },
            # Classification (event types)
            "classification": {
                "event_type": event_types[0] if event_types else "unknown",
                "event_types": event_types,
                "confidence": 0.95,
                "categorized_at": datetime.now().isoformat() + "Z"
            },
            "raw_data": data,
            "created_at": datetime.now().isoformat() + "Z",
            "cleaned_text": None,
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
    logging.info("🌤️  COLLECTION WITH CATEGORIZATION STARTED")
    collect_owm()
    collect_om()
    logging.info("📊 Cycle complete")
    logging.info("=" * 50)

def main():
    logging.info("🚀 Weather Collector v5 (with categorization) started")
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

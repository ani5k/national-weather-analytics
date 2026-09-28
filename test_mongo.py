
import os
import pymongo
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("MONGODB_URI")

if not uri:
    print("❌ MONGODB_URI not found in .env")
    exit(1)

try:
    client = pymongo.MongoClient(uri)
    # Test connection
    client.admin.command('ping')
    print("✅ Connected to MongoDB Atlas successfully!")
    
    # Insert test record
    db = client["weather_db"]
    collection = db["weather_data"]
    
    test_record = {
        "test": "hello",
        "city": "Mumbai",
        "temperature": 35,
        "message": "Connection test"
    }
    
    result = collection.insert_one(test_record)
    print(f"✅ Inserted test record with ID: {result.inserted_id}")
    
    # Read it back
    for doc in collection.find().limit(5):
        print(doc)
        
except pymongo.errors.ConnectionFailure as e:
    print(f"❌ Connection failed: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

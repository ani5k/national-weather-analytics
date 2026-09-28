"""
Open-Meteo Weather Collector (fixed)

Uses shared pipeline settings/schema. Prefer:
    python run_pipeline.py
"""

from pymongo import MongoClient

from pipeline.collect_openmeteo import collect_openmeteo
from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI


def main():
    client = MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]
    saved = collect_openmeteo(collection)
    print(f"Saved {saved} Open-Meteo reports. Total={collection.count_documents({})}")


if __name__ == "__main__":
    main()

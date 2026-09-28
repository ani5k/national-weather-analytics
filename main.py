"""
main.py

Phase 1 checkpoint:
    Python -> MongoDB -> Read 1 actual report -> Print it

Run this after filling in MONGO_URI in your .env file.
"""

from database.mongodb import get_collection


def main():
    collection = get_collection()
    report = collection.find_one()

    if report is None:
        print("Connected, but the collection has no documents yet.")
        return

    print("Found a report:")
    print(report)


if __name__ == "__main__":
    main()

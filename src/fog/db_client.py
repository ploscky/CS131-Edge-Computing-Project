"""
Shared MongoDB Atlas connection and helpers.

Requires:
    pip install pymongo python-dotenv

Environment variables (set in .env or shell):
    MONGO_URI     — Atlas connection string (see README)
    MONGO_DB_NAME — database name (default: occupancy_db)
"""

import os
from datetime import datetime, timezone, timedelta # for time snapshots

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

load_dotenv()

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.environ.get("MONGO_URI")
        if not uri:
            raise RuntimeError(
                "MONGO_URI is not set. Add it to your .env file or environment."
            )
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        try:
            _client.admin.command("ping")
            print("[db_client] Connected to MongoDB Atlas")
        except ConnectionFailure as e:
            raise RuntimeError(f"[db_client] Could not connect to MongoDB: {e}") from e
    return _client


def get_db():
    db_name = os.environ.get("MONGO_DB_NAME", "occupancy_db")
    return get_client()[db_name]


def ensure_indexes():
    db = get_db()

    db.seat_updates.create_index([("timestamp", DESCENDING)])
    db.seat_updates.create_index([("location_id", ASCENDING), ("timestamp", DESCENDING)])

    db.seat_updates.create_index([("timestamp", DESCENDING)])
    db.seat_updates.create_index([("location_id", ASCENDING), ("timestamp", DESCENDING)])

    print("[db_client] Indexes ensured")


def insert_wait_time_snapshot(
    location_id: str,
    people_inside: int,
    seated: int,
    waiting: int,
    estimated_wait_minutes: int,
    busy_status: str,
    timestamp: str | None = None,
) -> str:
    db = get_db()
    now = datetime.now(timezone.utc)
    ts = datetime.fromisoformat(timestamp) if timestamp else now
    doc = {
        "location_id": location_id,
        "people_inside": people_inside,
        "seated": seated,
        "waiting": waiting,
        "estimated_wait_minutes": estimated_wait_minutes,
        "busy_status": busy_status,
        "timestamp": ts,
        "created_at": now,
    }
    result = db.seat_updates.insert_one(doc)
    return str(result.inserted_id)


def get_recent_wait_times(location_id: str, limit: int = 20) -> list[dict]:
    db = get_db()
    cursor = (
        db.seat_updates
        .find({"location_id": location_id}, {"_id": 0})
        .sort("timestamp", DESCENDING)
        .limit(limit)
    )
    results = []
    for doc in cursor:
        for key in ("timestamp", "created_at"):
            if isinstance(doc.get(key), datetime):
                doc[key] = doc[key].isoformat()
        results.append(doc)
    return results

def get_best_time(location_id: str) -> dict:
    db = get_db()
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    # MongoDB $dayOfWeek: 1=Sun, 2=Mon, 3=Tue, 4=Wed, 5=Thu, 6=Fri, 7=Sat
    # Opening hours per day: [open_hour, close_hour]
    open_windows = [
        {"$and": [{"$eq": [{"$dayOfWeek": "$timestamp"}, 2]}, {"$gte": [{"$hour": "$timestamp"}, 8]}, {"$lte": [{"$hour": "$timestamp"}, 21]}]},  # Mon
        {"$and": [{"$eq": [{"$dayOfWeek": "$timestamp"}, 3]}, {"$gte": [{"$hour": "$timestamp"}, 8]}, {"$lte": [{"$hour": "$timestamp"}, 21]}]},  # Tue
        {"$and": [{"$eq": [{"$dayOfWeek": "$timestamp"}, 4]}, {"$gte": [{"$hour": "$timestamp"}, 8]}, {"$lte": [{"$hour": "$timestamp"}, 21]}]},  # Wed
        {"$and": [{"$eq": [{"$dayOfWeek": "$timestamp"}, 5]}, {"$gte": [{"$hour": "$timestamp"}, 8]}, {"$lte": [{"$hour": "$timestamp"}, 21]}]},  # Thu
        {"$and": [{"$eq": [{"$dayOfWeek": "$timestamp"}, 6]}, {"$gte": [{"$hour": "$timestamp"}, 8]}, {"$lte": [{"$hour": "$timestamp"}, 20]}]},  # Fri
        {"$and": [{"$eq": [{"$dayOfWeek": "$timestamp"}, 7]}, {"$gte": [{"$hour": "$timestamp"}, 11]}, {"$lte": [{"$hour": "$timestamp"}, 16]}]}, # Sat
    ]

    pipeline = [
        {"$match": {
            "location_id": location_id,
            "timestamp": {"$gte": week_ago},
            "seated": {"$gt": 0},
        }},
        {"$match": {
            "$expr": {"$or": open_windows}
        }},
        {"$group": {
            "_id": {"$hour": "$timestamp"},
            "avg_seated": {"$avg": "$seated"},
            "avg_waiting": {"$avg": "$waiting"},
        }},
        {"$sort": {"avg_seated": 1}},
        {"$limit": 1}
    ]

    result = list(db.seat_updates.aggregate(pipeline))

    if not result:
        return {"start": "", "end": "", "time": ""}

    best_hour = result[0]["_id"]
    next_hour = best_hour + 1

    def format_hour(h: int) -> tuple[str, str]:
        suffix = "AM" if h < 12 else "PM"
        display = h if h <= 12 else h - 12
        if display == 0:
            display = 12
        return str(display), suffix

    start_str, time_suffix = format_hour(best_hour)
    end_str, _ = format_hour(next_hour)

    return {"start": f"{start_str}:00", "end": f"{end_str}:00", "time": time_suffix}
    # aggregates seat_updates from past 7 days by hour-of-day
    # returns the hour with the lowest average waiting count
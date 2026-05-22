"""
Shared MongoDB Atlas connection and helpers.
Import this in entrance_counter.py, seats.py, and fog_server.py.

Requires:
    pip install pymongo python-dotenv

Environment variables (set in .env or shell):
    MONGO_URI     — Atlas connection string (see README)
    MONGO_DB_NAME — database name (default: occupancy_db)
"""

import os
from datetime import datetime, timezone

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
            print("[db_client] Connected to MongoDB Atlas ✓")
        except ConnectionFailure as e:
            raise RuntimeError(f"[db_client] Could not connect to MongoDB: {e}") from e
    return _client


def get_db():
    db_name = os.environ.get("MONGO_DB_NAME", "occupancy_db")
    return get_client()[db_name]


def ensure_indexes():
    db = get_db()

    # wait time snapshots
    db.wait_time_snapshots.create_index([("timestamp", DESCENDING)])
    db.wait_time_snapshots.create_index([("location_id", ASCENDING), ("timestamp", DESCENDING)])

    # record expiration (for clearing old data over 30d old) 
    db.wait_time_snapshots.create_index("timestamp", expireAfterSeconds=2592000)

    print("[db_client] Indexes ensured")

# wait time snapshots
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
    result = db.wait_time_snapshots.insert_one(doc)
    return str(result.inserted_id)


def get_recent_wait_times(location_id: str, limit: int = 20) -> list[dict]:
    db = get_db()
    cursor = (
        db.wait_time_snapshots
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


def get_peak_hours(location_id: str) -> list[dict]:
    db = get_db()
    
    pipeline = [
        {"$match": {"location_id": location_id}},
        {
            "$project": {
                "day_of_week": {
                    "$dayOfWeek": {
                        "date": "$timestamp", 
                        "timezone": os.environ.get("TZ", "America/Los_Angeles")
                    }
                },
                "hour": {
                    "$hour": {
                        "date": "$timestamp", 
                        "timezone": os.environ.get("TZ", "America/Los_Angeles")
                    }
                },
                "people_inside": 1
            }
        },
        {
            "$group": {
                "_id": {
                    "day_of_week": "$day_of_week",
                    "hour": "$hour"
                },
                "avg_people": {"$avg": "$people_inside"},
                "data_points_count": {"$sum": 1}
            }
        },
        {
            "$sort": {
                "_id.day_of_week": 1,
                "_id.hour": 1
            }
        },
        # output layout
        {
            "$project": {
                "_id": 0,
                "day_of_week": "$_id.day_of_week",
                "hour": "$_id.hour",
                "avg_people": {"$round": ["$avg_people", 1]},
                "sample_size": "$data_points_count"
            }
        }
    ]
    
    return list(db.wait_time_snapshots.aggregate(pipeline))
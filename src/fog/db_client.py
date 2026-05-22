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

    # entrance counter
    db.entrance_events.create_index([("timestamp", DESCENDING)])
    db.entrance_events.create_index([("device_id", ASCENDING), ("timestamp", DESCENDING)])

    # occupancy
    db.occupancy_snapshots.create_index([("timestamp", DESCENDING)])
    db.occupancy_snapshots.create_index([("device_id", ASCENDING), ("timestamp", DESCENDING)])

    db.current_state.create_index([("location_id", ASCENDING)], unique=True)

    # wait time snapshots
    db.wait_time_snapshots.create_index([("timestamp", DESCENDING)])
    db.wait_time_snapshots.create_index([("location_id", ASCENDING), ("timestamp", DESCENDING)])

    # record expiration (for clearing old data over 30d old) 
    db.entrance_events.create_index("timestamp", expireAfterSeconds=2592000)
    db.occupancy_snapshots.create_index("timestamp", expireAfterSeconds=2592000)
    db.wait_time_snapshots.create_index("timestamp", expireAfterSeconds=2592000)

    print("[db_client] Indexes ensured")


# entrance / exit events
def insert_entrance_event(
    device_id: str,
    people_inside_delta: int,
    total_people_seen: int,
    timestamp: str | None = None,
) -> str:
    db = get_db()
    now = datetime.now(timezone.utc)
    ts = datetime.fromisoformat(timestamp) if timestamp else now

    doc = {
        "device_id": device_id,
        "people_inside_delta": people_inside_delta,
        "total_people_seen": total_people_seen,
        "timestamp": ts,
        "created_at": now,
    }
    result = db.entrance_events.insert_one(doc)
    _update_current_state(device_id=device_id, delta=people_inside_delta)
    return str(result.inserted_id)



# table occupancy snapshots
def insert_occupancy_snapshot(
    device_id: str,
    people_seated: int,
    timestamp: str | None = None,
) -> str:
    db = get_db()
    now = datetime.now(timezone.utc)
    ts = datetime.fromisoformat(timestamp) if timestamp else now

    doc = {
        "device_id": device_id,
        "people_seated": people_seated,
        "timestamp": ts,
        "created_at": now,
    }
    result = db.occupancy_snapshots.insert_one(doc)
    return str(result.inserted_id)


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


# real-time current state (for frontend)

def _update_current_state(device_id: str, delta: int):
    db = get_db()
    db.current_state.update_one(
        {"location_id": device_id},
        {
            "$inc": {"people_inside": delta},
            "$set": {"last_updated": datetime.now(timezone.utc)},
            "$setOnInsert": {"location_id": device_id},
        },
        upsert=True,
    )


def get_current_occupancy(device_id: str) -> dict:
    db = get_db()
    doc = db.current_state.find_one({"location_id": device_id})
    if not doc:
        return {"location_id": device_id, "people_inside": 0, "last_updated": None}
    doc.pop("_id", None)
    return doc
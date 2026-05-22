import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone, timedelta
import random
from db_client import get_db

def seed():
    db = get_db()
    collection = db.wait_time_snapshots
    
    location_id = "restaurant-01-test"
    docs = []
    now = datetime.now(timezone.utc)

    # generate a snapshot every 5 minutes for the past 7 days
    for days_ago in range(7):
        for hour in range(7, 22):  # 7am to 10pm
            for minute in range(0, 60, 5):
                timestamp = now - timedelta(days=days_ago, hours=now.hour - hour, minutes=minute)

                # simulate realistic busy patterns
                if 11 <= hour < 14:  # lunch rush
                    waiting = random.randint(5, 20)
                elif 17 <= hour < 20:  # dinner rush
                    waiting = random.randint(3, 15)
                elif 7 <= hour < 9:  # breakfast
                    waiting = random.randint(0, 5)
                else:  # off peak
                    waiting = random.randint(0, 2)

                seated = random.randint(20, 50)
                people_inside = seated + waiting

                docs.append({
                    "location_id": location_id,
                    "people_inside": people_inside,
                    "seated": seated,
                    "waiting": waiting,
                    "estimated_wait_minutes": round((waiting / 50) * 60, 1),
                    "busy_status": "very busy" if waiting >= 10 else "busy" if waiting > 0 else "not busy",
                    "timestamp": timestamp,
                    "created_at": now,
                })

    collection.insert_many(docs)
    print(f"[seed] inserted {len(docs)} documents")

if __name__ == "__main__":
    seed()
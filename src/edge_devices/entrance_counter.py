import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import zmq

# Lets this file import config.py when it is run from the project folder.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import ENTRANCE_DEVICE_ID, ENTRANCE_UPDATE_SECONDS, FOG_SUB_CONNECT


def simulate_entrance_event() -> int:
    # Temporary stand-in for the camera/person tracking code.
    # Positive means someone walked in, negative means someone walked out.
    return random.choices(
        population=[1, -1, 0],
        weights=[0.35, 0.20, 0.45],
        k=1,
    )[0]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main():
    context = zmq.Context()
    socket = context.socket(zmq.PUB)

    # This edge device publishes updates to the local fog server.
    socket.connect(FOG_SUB_CONNECT)

    # Give PUB/SUB a moment to connect.
    time.sleep(1)

    total_people_seen = 0

    print(f"[{ENTRANCE_DEVICE_ID}] sending entrance updates to fog")

    while True:
        delta = simulate_entrance_event()

        if delta == 1:
            total_people_seen += 1

        # Keeping the message as basic JSON for now so it is easy to inspect.
        message = {
            "device_id": ENTRANCE_DEVICE_ID,
            "people_inside_delta": delta,
            "total_people_seen": total_people_seen,
            "timestamp": now_iso(),
        }

        socket.send_string(f"entrance {json.dumps(message)}")
        print("[entrance]", message)

        time.sleep(ENTRANCE_UPDATE_SECONDS)


if __name__ == "__main__":
    main()

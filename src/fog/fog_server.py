import json
import sys
from pathlib import Path

import zmq

# Lets this file import config.py when it is run from the project folder.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import FOG_SUB_BIND


def main():
    context = zmq.Context()
    socket = context.socket(zmq.SUB)

    # The fog server listens for updates from edge devices.
    socket.bind(FOG_SUB_BIND)
    socket.setsockopt_string(zmq.SUBSCRIBE, "entrance")

    # This is the running estimate based on entrance counter messages.
    people_inside = 0

    print("[fog] server started")
    print(f"[fog] listening on {FOG_SUB_BIND}")

    while True:
        raw_message = socket.recv_string()

        # Messages come in as: "entrance {json data}"
        topic, payload = raw_message.split(" ", 1)
        data = json.loads(payload)

        people_inside += int(data["people_inside_delta"])

        # Do not let exits push the count below zero.
        people_inside = max(0, people_inside)

        print(
            "[fog]",
            f"topic={topic}",
            f"device={data['device_id']}",
            f"change={data['people_inside_delta']}",
            f"people_inside={people_inside}",
            f"total_seen={data['total_people_seen']}",
        )


if __name__ == "__main__":
    main()

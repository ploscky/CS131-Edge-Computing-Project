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
    socket.setsockopt_string(zmq.SUBSCRIBE, "seats")

    # This is the running estimate based on entrance counter messages.
    people_inside = 0
    occupied_seats = 0

    # potentially make the edge device tell us the total number of seats instead of hardcoding it here
    TOTAL_SEATS = 2

    print("[fog] server started")
    print(f"[fog] listening on {FOG_SUB_BIND}")

    while True:
        raw_message = socket.recv_string()

        # Messages come in as: "entrance {json data}"
        topic, payload = raw_message.split(" ", 1)
        data = json.loads(payload)

        if topic == "entrance":
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
                f"timestamp={data['timestamp']}",
            )

        elif topic == "seats":
            occupied_seats = int(data["number of occupied seats"])
            open_seats = TOTAL_SEATS - occupied_seats
            people_waiting = max(0, people_inside - occupied_seats)

            print(
                "[fog]",
                f"topic={topic}",
                f"device={data['device_id']}",
                f"occupied={occupied_seats}",
                f"open_seats={open_seats}",
                f"people_waiting={people_waiting}",
                f"timestamp={data['timestamp']}",
            )


if __name__ == "__main__":
    main()

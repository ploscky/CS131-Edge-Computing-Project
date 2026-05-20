import json
import sys
from pathlib import Path

import zmq

# Lets this file import config.py when it is run from the project folder.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import FOG_SUB_BIND, LOCATION_ID
from db_client import insert_wait_time_snapshot
# from wait_time import estimate_wait_time ---------- uncomment when wait_time.py is merged


#sets up the format of the json file
dashboard_state = {
    "totalCapacity": 50,
    "peopleInside": 0,
    "waiting": 0,
    "seated": 0,
    "estimatedWaitTime": 0,
    "busyStatus": "not busy",
    "bestTime": {"start": "", "end": "", "time": ""},
    "tables": [
        {"id": 1, "status": "open", "capacity": 4},
        {"id": 2, "status": "open", "capacity": 4},
        {"id": 3, "status": "open", "capacity": 6},
        {"id": 4, "status": "open", "capacity": 6},
        {"id": 5, "status": "open", "capacity": 4},
        {"id": 6, "status": "open", "capacity": 6},
        {"id": 7, "status": "open", "capacity": 6},
        {"id": 8, "status": "open", "capacity": 4},
    ]
    #adjust later for real layout
}

total_Seats = 2  #hardcoded in depending on room

data_file = Path(__file__).resolve().parents[1] / "data.json"
print(data_file)

def write_dashboard(state: dict):
    with open(data_file, "w") as f:
        json.dump(state, f, indent=4)


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
    people_waiting = 0

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

        state = dashboard_state.copy()

        state["peopleInside"] = people_inside
        state["seated"] = occupied_seats
        state["waiting"] = max(0, people_waiting)

        # TODO: replace current estimatesWaitTime state with the commented line below when we merge wait_time.py
        # state["estimatedWaitTime"] = estimate_wait_time(state["waiting"], TOTAL_SEATS)
        state["estimatedWaitTime"] = state["waiting"] * 5    # delete

        # make a better function for how busy it is
        if state["waiting"] == 0:
            state["busyStatus"] = "not busy"
        elif state["waiting"] < 5:
            state["busyStatus"] = "busy"
        else:
            state["busyStatus"] = "very busy"

        write_dashboard(state)

        # send data to MongoDB
        try:
            insert_wait_time_snapshot(
                location_id=LOCATION_ID,
                people_inside=people_inside,
                seated=occupied_seats,
                waiting=people_waiting,
                estimated_wait_minutes=state["estimatedWaitTime"],
                busy_status=state["busyStatus"],
                timestamp=data.get("timestamp"),
            )
        except Exception as e:
            # write failure shouldn't crash fog server
            print(f"[fog] WARNING: could not write to MongoDB: {e}")

if __name__ == "__main__":
    main()

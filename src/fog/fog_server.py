import json
import sys
from pathlib import Path
import time
import zmq

# Lets this file import config.py when it is run from the project folder.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import FOG_SUB_BIND, LOCATION_ID
from db_client import insert_wait_time_snapshot, get_best_time
from wait_time import estimate_wait_time

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
        {"id": 1, "status": "open", "capacity": 4, "peopleSitting": 0},
        {"id": 2, "status": "open", "capacity": 4, "peopleSitting": 0},
        {"id": 3, "status": "open", "capacity": 6, "peopleSitting": 0},
        {"id": 4, "status": "open", "capacity": 6, "peopleSitting": 0},
        {"id": 5, "status": "open", "capacity": 4, "peopleSitting": 0},
        {"id": 6, "status": "open", "capacity": 6, "peopleSitting": 0},
        {"id": 7, "status": "open", "capacity": 6, "peopleSitting": 0},
        {"id": 8, "status": "open", "capacity": 4, "peopleSitting": 0},
    ]
    #adjust later for real layout
}

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
    total_seated = 0
    people_waiting = 0

    # potentially make the edge device tell us the total number of seats instead of hardcoding it here
    # calculate number of seats based on capacity of each table
    TOTAL_SEATS = sum(t["capacity"] for t in dashboard_state["tables"])

    print("[fog] server started")
    print(f"[fog] listening on {FOG_SUB_BIND}")

    # track least busy time of day
    last_best_time_update = 0
    BEST_TIME_UPDATE_SECONDS = 900  # every 15 minutes

    while True:
        raw_message = socket.recv_string()

        # messages come in as: "entrance {json data}"
        topic, payload = raw_message.split(" ", 1)
        data = json.loads(payload)

        if topic == "entrance":
            people_inside += int(data["people_inside_delta"])

            # do not let exits push the count below zero.
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
            zone_counts = data["zones"]

            for table in dashboard_state["tables"]: 
                table_id = str(table["id"])
                people = zone_counts.get(table_id, 0)
                table["peopleSitting"] = people
                total_seated += people

                if people > 0:
                    table["status"] = "occupied"
                else:
                    table["status"] = "open"

            open_seats = TOTAL_SEATS - total_seated
            people_waiting = max(0, people_inside - total_seated) 

            print(
                "[fog]",
                f"topic={topic}",
                f"device={data['device_id']}",
                f"occupied={total_seated}",
                f"open_seats={open_seats}",
                f"people_waiting={people_waiting}",
                f"timestamp={data['timestamp']}",
            )

        state = dashboard_state.copy()

        state["peopleInside"] = people_inside
        state["seated"] = total_seated
        state["waiting"] = max(0, people_waiting)
        state["estimatedWaitTime"] = estimate_wait_time(state["waiting"], TOTAL_SEATS)

        # make a better function for how busy it is
        # currently using 15 min wait time threshold for "busy"
        if state["estimatedWaitTime"] == 0:
            state["busyStatus"] = "not busy"
        elif state["estimatedWaitTime"] <= 15:
            state["busyStatus"] = "busy"
        else:
            state["busyStatus"] = "very busy"

        write_dashboard(state)
        
        # update best time if better hour is found
        if time.time() - last_best_time_update >= BEST_TIME_UPDATE_SECONDS:
            try:
                dashboard_state["bestTime"] = get_best_time(LOCATION_ID)
                last_best_time_update = time.time()
            except Exception as e:
                print(f"[fog] WARNING: could not update best time: {e}")

        # send data to MongoDB
        try:
            insert_wait_time_snapshot(
                location_id=LOCATION_ID,
                people_inside=people_inside,
                seated=total_seated,
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

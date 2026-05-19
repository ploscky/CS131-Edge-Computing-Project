import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import cv2
from ultralytics import YOLO
import supervision as sv

import zmq

# Lets this file import config.py when it is run from the project folder.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import ENTRANCE_DEVICE_ID, ENTRANCE_UPDATE_SECONDS, FOG_SUB_CONNECT

model = YOLO("yolov8n.pt") # download yolo model
cap = cv2.VideoCapture(0) # update later for jetson camera

# test for laptop webcam dimensions
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Resolution: {frame_width}x{frame_height}")

bound_start = sv.Point(frame_width // 2, 0) # adjust coordinates later for actual doorway
bound_end = sv.Point(frame_width // 2, frame_height)
people_counter = sv.LineZone(start=bound_start, end=bound_end) # tracks # of people crossing doorway
bound_annotator = sv.LineZoneAnnotator()
box_annotator = sv.BoxAnnotator()
tracker = sv.ByteTrack() # make sure a person isn't counted twice w/ ID

# helps track how many people come in per frame
prev_in = 0
prev_out = 0

def simulate_entrance_event() -> int:
    global prev_in, prev_out

    ret, frame = cap.read()
    if not ret:
        print("Failed frame grab")
        return 0
    
    # use supervision to check trajectory of movement (in or out) 
    results = model(frame, classes=[0])[0] # only detect people
    detections = sv.Detections.from_ultralytics(results)
    detections = tracker.update_with_detections(detections)
    people_counter.trigger(detections=detections)
    
    # show vid feed and boxes for testing
    frame = box_annotator.annotate(scene=frame, detections=detections)
    bound_annotator.annotate(frame, line_counter=people_counter)
    cv2.imshow("Video Feed", frame) 
    cv2.waitKey(1) # for vid playback

    # compute number of people that entered/exited since last frame grab
    people_in_building = (people_counter.in_count - prev_in) - (people_counter.out_count - prev_out)
    prev_in = people_counter.in_count 
    prev_out = people_counter.out_count
    return people_in_building

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
    delta_sum = 0 # accumulate delta between frame sending
    last_send_time = time.time() 

    print(f"[{ENTRANCE_DEVICE_ID}] sending entrance updates to fog")

    while True:
        delta = simulate_entrance_event()
        delta_sum += delta

        # only increment total people seen if someone entered
        if delta > 0:
            total_people_seen += 1

        # send ZMQ messages every 2 seconds
        if time.time() - last_send_time >= ENTRANCE_UPDATE_SECONDS:
            # Keeping the message as basic JSON for now so it is easy to inspect.
            message = {
                "device_id": ENTRANCE_DEVICE_ID,
                "people_inside_delta": delta_sum,
                "total_people_seen": total_people_seen,
                "timestamp": now_iso(),
            }

            socket.send_string(f"entrance {json.dumps(message)}")
            print("[entrance]", message)
            last_send_time = time.time()
            delta_sum = 0 # reset after sending frame

        #time.sleep(ENTRANCE_UPDATE_SECONDS)


if __name__ == "__main__":
    main()

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
# model.export(format="engine", device = 0)
# model.to('cuda')
# ^^^ 2 lines needs testing on jetson to utilize hardware accelerator instead of cpu

cap = cv2.VideoCapture(0)

# set resolution and framerate for usb webcam
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # get most recent frame

# test for laptop webcam dimensions
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Resolution: {frame_width}x{frame_height}")

bound_start = sv.Point(frame_width // 2, 0) # adjust coordinates later for actual doorway
bound_end = sv.Point(frame_width // 2, frame_height)

# adjusted line coords for resized frame (640, 360) -- use this if latency is an issue
# bound_start = sv.Point(320, 0)
# bound_end = sv.Point(320, 360)

people_counter = sv.LineZone(start=bound_start, end=bound_end) # tracks # of people crossing doorway
bound_annotator = sv.LineZoneAnnotator()
box_annotator = sv.BoxAnnotator()
tracker = sv.ByteTrack() # make sure a person isn't counted twice w/ ID

# helps track how many people come in per frame
prev_in = 0
prev_out = 0

# resize frame -- use this if latency is an issue
# def get_resized_frame():
#     ret, frame = cap.read()
#     if not ret:
#         return None
#     frame = cv2.resize(frame, (640, 360)) # halve resolution to reduce latency
#     return frame

def simulate_entrance_event() -> int:
    global prev_in, prev_out

    ret, frame = cap.read()
    if not ret:
        print("Failed frame grab")
        return 0
    # frame = get_resized_frame()
    # if frame is None:
    #     print("Failed frame grab")
    #     return 0
    
    # use supervision to check trajectory of movement (in or out) 
    results = model(frame, classes=[0])[0] # only detect people
    detections = sv.Detections.from_ultralytics(results)

    if detections.confidence is not None and len(detections.confidence) > 0:
        confidence_text = f"Confidence: {max(detections.confidence):.2f}"
    else:
        confidence_text = "Confidence: --"

    detections = tracker.update_with_detections(detections)
    people_counter.trigger(detections=detections)
    
    # show vid feed and boxes for testing
    frame = box_annotator.annotate(scene=frame, detections=detections)
    bound_annotator.annotate(frame, line_counter=people_counter)
    cv2.putText(frame, confidence_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow("Video Feed", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return -999 # returns when q is pressed during stream

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
        if delta == -999: 
            break # exiting on 'q'
        delta_sum += delta

        # only increment total people seen if someone entered
        if delta > 0:
            total_people_seen += delta

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

     # clean up data
    cap.release()
    cv2.destroyAllWindows()   


if __name__ == "__main__":
    main()

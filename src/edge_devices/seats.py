import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import cv2
from ultralytics import YOLO
import supervision as sv
import numpy as np

import zmq

# Lets this file import config.py when it is run from the project folder.
sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import SEAT_DEVICE_ID, SEAT_UPDATE_SECONDS, FOG_SUB_CONNECT

model = YOLO("yolov8n.pt") # download yolo model
cap = cv2.VideoCapture(0) # update later for jetson camera

# set resolution and framerate for usb webcam
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # get most recent frame

# define seat zones as rectangles using Polygon (will adjust later for actual coordinates)
# find actual coordinates by taking screenshot of camera feed and finding pixel coords
SEAT_ZONES = [
    sv.PolygonZone(polygon=np.array([[100, 100], [300, 100], [300, 300], [100, 300]])), # placeholder coords
    sv.PolygonZone(polygon=np.array([[350, 100], [550, 100], [550, 300], [350, 300]]))
    # add more zones later
]

# test for laptop webcam dimensions
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Resolution: {frame_width}x{frame_height}")

# show boxes for testing
box_annotator = sv.BoxAnnotator()
# draw green polygons around zones
zone_annotators = [sv.PolygonZoneAnnotator(zone=zone, color=sv.Color.GREEN) for zone in SEAT_ZONES]

# resize frame -- use this if latency is an issue
# def get_resized_frame():
#     ret, frame = cap.read()
#     if not ret:
#         return None
#     frame = cv2.resize(frame, (640, 360)) # halve resolution to reduce latency
#     return frame

def occupied_seats() -> int:
    ret, frame = cap.read()
    if not ret:
        print("Failed frame grab")
        return 0
    # frame = get_resized_frame()
    # if frame is None:
    #     print("Failed frame grab")
    #     return 0
    
    results = model(frame, classes=[0])[0] # only detect people
    detections = sv.Detections.from_ultralytics(results)

    frame = box_annotator.annotate(scene=frame, detections=detections)

    occupied = 0
    for zone, zone_annotator in zip(SEAT_ZONES, zone_annotators):
        zone.trigger(detections=detections)

        frame = zone_annotator.annotate(scene=frame)

        if zone.current_count >= 1:
            occupied += 1
    
    # show vid feed and boxes for testing
    cv2.imshow("Video Feed", frame) 
    cv2.waitKey(1) # for vid playback
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return -999 # returns when q is pressed during stream
    
    return occupied

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def main():
    context = zmq.Context()
    socket = context.socket(zmq.PUB)

    # This edge device publishes updates to the local fog server.
    socket.connect(FOG_SUB_CONNECT)

    # Give PUB/SUB a moment to connect.
    time.sleep(1)

    last_send_time = time.time() 

    print(f"[{SEAT_DEVICE_ID}] sending seating updates to fog")

    while True:
        occupied = occupied_seats()

        if occupied == -999: 
            break # exiting on 'q'

        # send ZMQ messages every 2 seconds
        if time.time() - last_send_time >= SEAT_UPDATE_SECONDS:
            # Keeping the message as basic JSON for now so it is easy to inspect.
            message = {
                "device_id": SEAT_DEVICE_ID,
                "number_of_occupied_seats": occupied,
                "timestamp": now_iso(),
            }

            socket.send_string(f"seats {json.dumps(message)}")
            print("[seats]", message)
            last_send_time = time.time()

        #time.sleep(ENTRANCE_UPDATE_SECONDS)
    
    # clean up data
    cap.release()
    cv2.destroyAllWindows()   


if __name__ == "__main__":
    main()
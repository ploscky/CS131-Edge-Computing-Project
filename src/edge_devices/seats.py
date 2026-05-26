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
    {
        "id": 1,
        "polygon": np.array([[100, 100], [300, 100], [300, 300], [100, 300]], dtype=np.int32) 
    },
    {
        "id": 2, 
        "polygon": np.array([[350, 100], [550, 100], [550, 300], [350, 300]], dtype=np.int32)
    },
    {
        "id": 3, 
        "polygon": np.array([[650, 400], [850, 400], [850, 600], [650, 600]], dtype=np.int32)
    },
    {
        "id": 4, 
        "polygon": np.array([[100, 400], [300, 400], [300, 600], [100, 600]], dtype=np.int32)
    },
    # add more zones later
]

# test for laptop webcam dimensions
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Resolution: {frame_width}x{frame_height}")

# show boxes for testing
# draw green polygons around zones
zone_annotators = [sv.PolygonZoneAnnotator(zone=sv.PolygonZone(polygon=zone["polygon"]), color=sv.Color.GREEN, text_scale=0) for zone in SEAT_ZONES]

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
        return {}
    # frame = get_resized_frame()
    # if frame is None:
    #     print("Failed frame grab")
    #     return 0
    
    results = model(frame, classes=[0])[0] # only detect people
    detections = sv.Detections.from_ultralytics(results)

    zone_counts = {}

    #Counts how many people are in each zone
    for zone, zone_annotator in zip(SEAT_ZONES, zone_annotators):
        frame = zone_annotator.annotate(scene=frame)

        people_in_zone = 0
        for xyxy in detections.xyxy:
            x1, y1, x2, y2 = xyxy

            cx = int((x1+x2) / 2)
            cy = int((y1+y2) / 2)

            result = cv2.pointPolygonTest(zone["polygon"], (cx,cy), False)

            if result >= 0:
                cv2.circle(frame, (cx, cy), 8, (0,255,0), -1)

            else:
                cv2.circle(frame, (cx, cy), 6, (0, 0, 255), -1)

            if result >= 0:
                people_in_zone += 1
        zone_counts[zone["id"]] = people_in_zone

        label_x = zone["polygon"][0][0]
        label_y = zone["polygon"][0][1] - 10

        count = people_in_zone

        cv2.putText(frame, f"People: {count}", (label_x, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # show vid feed and boxes for testing
    cv2.imshow("Video Feed", frame) 
    cv2.waitKey(1) # for vid playback
    if cv2.waitKey(1) & 0xFF == ord('q'):
        return -999 # returns when q is pressed during stream
    
    return zone_counts

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
        zone_counts = occupied_seats()

        if zone_counts == -999: 
            break # exiting on 'q'

        # send ZMQ messages every 2 seconds
        if time.time() - last_send_time >= SEAT_UPDATE_SECONDS:
            # Keeping the message as basic JSON for now so it is easy to inspect.
            message = {
                "device_id": SEAT_DEVICE_ID,
                "zones": zone_counts,
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
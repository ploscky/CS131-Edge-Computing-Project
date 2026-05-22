#!/bin/bash

# start pipeline
echo "Starting Campus Dining Tracker System"

# start fog
echo "Starting fog server"
cd fog
python fog_server.py &
FOG_PID=$!
cd ..

sleep 2 # wait for fog to be ready

# start edge layer (jetson 1)
echo "Starting edge layer"
cd edge_devices
python entrance_counter.py &
ENTRANCE_PID=$!
# python seats.py &
# SEATS_PID=$!
cd ..

# start web/cloud server
echo "Starting web server"
node server.js &
SERVER_PID=$!
cd ..

echo "Pipeline running!"
echo "Press Ctrl+C to stop all processes"

# stop all processes when script is interrupted
trap "kill $FOG_PID $ENTRY_PID $SEAT_PID $SERVER_PID" SIGINT

wait
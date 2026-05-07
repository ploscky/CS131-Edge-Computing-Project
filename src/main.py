# possible libraries needed

# edge layer
import cv2 # for computer vision
import numpy as np
from ultralytics import YOLO # for computer vision (detection)
import supervision as sv # for entry/exit logic
import zmq # pub/sub messaging between 2 Jetsons

# fog layer
import flask
from flask import Flask, jsonify # website backend
import sqlite3 # sql databases to track table states and timestamps

# cloud layer
import requests
import json
import os


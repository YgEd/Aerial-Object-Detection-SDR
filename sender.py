import cv2
import numpy as np
from ultralytics import YOLO
import paho.mqtt.client as mqtt
import json
import time
import threading
import signal
import sys

# ========================= CONFIG =========================
BROKER_HOST = "localhost"      # ← CHANGE TO BROKER IP if on different laptop
BROKER_PORT = 1883
TOPIC = "object/detections"
CAMERA_ID = "xps_sender"
CONF_THRESHOLD = 0.5
MODEL = "yolov8n.pt"
USE_ARUCO = True               # Set False to disable ArUco completely
MARKER_SIZE = 0.05             # meters – match your printed ArUco marker size
# =======================================================

# MQTT client (compatible with paho-mqtt v1 and v2)
def get_client():
    if hasattr(mqtt, 'CallbackAPIVersion'):
        return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    return mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT sender connected to broker")
    else:
        print(f"❌ MQTT connection failed: {rc}")



# ArUco setup
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
aruco_params = cv2.aruco.DetectorParameters()
aruco_detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

# Camera calibration for ArUco pose (optional)
camera_matrix = None
dist_coeffs = None
if USE_ARUCO:
    try:
        with open("calibrate.json", "r") as f:
            calib = json.load(f)
            camera_matrix = np.array(calib["camera_matrix"])
            dist_coeffs = np.array(calib["dist_coeffs"])
        print("✅ Loaded camera calibration – ArUco 3D pose ENABLED")
    except Exception:
        print("⚠️  No calibrate.json found – ArUco markers will be detected but pose = null")
        print("   Run calibrate.py once to enable full 3D pose.")

# Load YOLO
model = YOLO(MODEL)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Graceful shutdown
running = True
def signal_handler(sig, frame):
    global running
    print("\n🛑 Shutting down sender...")
    running = False
signal.signal(signal.SIGINT, signal_handler)

# client = get_client()
# client.on_connect = on_connect

# def mqtt_loop():
#     client.connect(BROKER_HOST, BROKER_PORT, 60)
#     client.loop_start()

# threading.Thread(target=mqtt_loop, daemon=True).start()

print("🎥 Sender started – press 'q' in window or Ctrl+C to stop")

while running:
    ret, frame = cap.read()
    if not ret:
        break

    # YOLO detection
    results = model(frame, verbose=False)

    detections = []

    # Process YOLO boxes
    for result in results:
        for box in result.boxes:
            if float(box.conf[0]) < CONF_THRESHOLD:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2

            detection = {
                "label": result.names[int(box.cls[0])],
                "confidence": round(float(box.conf[0]), 2),
                "center": [round(cx, 1), round(cy, 1)],
                "bbox": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                "aruco_pose": None
            }
            detections.append(detection)

            # Draw on frame
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, f"{detection['label']} {detection['confidence']}",
                        (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Optional ArUco detection + pose
    if USE_ARUCO:
        corners, ids, _ = aruco_detector.detectMarkers(frame)
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)

            rvecs = tvecs = None
            if camera_matrix is not None and dist_coeffs is not None:
                rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                    corners, MARKER_SIZE, camera_matrix, dist_coeffs)

            for i, marker_id in enumerate(ids.flatten()):
                # Marker center
                c = corners[i][0]
                cx_m = int(np.mean(c[:, 0]))
                cy_m = int(np.mean(c[:, 1]))

                aruco_pose = None
                if rvecs is not None:
                    tvec = tvecs[i][0]
                    aruco_pose = [round(float(tvec[0]), 3), round(float(tvec[1]), 3), round(float(tvec[2]), 3)]
                    cv2.drawFrameAxes(frame, camera_matrix, dist_coeffs, rvecs[i], tvecs[i], MARKER_SIZE)

                aruco_det = {
                    "label": f"aruco_marker_{marker_id}",
                    "confidence": 1.0,
                    "center": [cx_m, cy_m],
                    "bbox": None,
                    "aruco_pose": aruco_pose
                }
                detections.append(aruco_det)

    # Publish JSON
    payload = {
        "timestamp": time.time(),
        "camera_id": CAMERA_ID,
        "detections": detections
    }

    print(TOPIC, json.dumps(payload))

    cv2.imshow("Sender - Detections (press q to quit)", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
# client.loop_stop()
# client.disconnect()
print("✅ Sender shut down cleanly")
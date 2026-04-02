import cv2
import numpy as np
import paho.mqtt.client as mqtt
import json
import time
import threading
import signal

# ========================= CONFIG =========================
BROKER_HOST = "localhost"      # ← CHANGE TO BROKER IP
BROKER_PORT = 1883
TOPIC = "object/detections"
# =======================================================

latest_detections = []
detections_history = []        # last ~20 individual detections for the list
lock = threading.Lock()

# MQTT client
def get_client():
    if hasattr(mqtt, 'CallbackAPIVersion'):
        return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    return mqtt.Client()

client = get_client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT receiver connected")
        client.subscribe(TOPIC)
    else:
        print(f"❌ Connection failed: {rc}")

def on_message(client, userdata, msg):
    global latest_detections
    try:
        payload = json.loads(msg.payload.decode())
        current_dets = payload.get("detections", [])
        ts = payload.get("timestamp")

        with lock:
            latest_detections[:] = current_dets
            # Keep history for "last 10 detections" table
            for d in current_dets:
                d_copy = d.copy()
                d_copy["timestamp"] = ts
                detections_history.append(d_copy)
                if len(detections_history) > 20:
                    detections_history.pop(0)
    except Exception as e:
        print("JSON parse error:", e)

client.on_connect = on_connect
client.on_message = on_message

# Label colors (BGR)
label_colors = {
    "person": (0, 0, 255),
    "bottle": (255, 0, 0),
    "car": (0, 255, 0),
    "cell phone": (255, 255, 0),
    "laptop": (255, 0, 255),
}
default_color = (255, 255, 255)

running = True
def signal_handler(sig, frame):
    global running
    print("\n🛑 Shutting down receiver...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

def mqtt_loop():
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.loop_start()


print("📡 Receiver started – waiting for detections... (press q or Ctrl+C to quit)")

while running:
    with lock:
        current = latest_detections[:]
        history = detections_history[-10:]   # last 10 for list

    # === Object Map (640x480 scatter plot) ===
    map_img = np.zeros((480, 640, 3), dtype=np.uint8)
    for det in current:
        if "center" not in det or not det["center"]:
            continue
        cx, cy = int(det["center"][0]), int(det["center"][1])
        color = label_colors.get(det["label"], default_color)
        cv2.circle(map_img, (cx, cy), 12, color, -1)
        cv2.putText(map_img, det["label"][:6], (cx + 15, cy), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("Object Map (2D scatter)", map_img)

    # === Detections List Table ===
    list_img = np.zeros((420, 700, 3), dtype=np.uint8)
    cv2.putText(list_img, "Live Detections (last 10)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    y = 70
    for det in history:
        ts_str = time.strftime("%H:%M:%S", time.localtime(det["timestamp"]))
        text = f"{ts_str} | {det['label']:12} conf:{det['confidence']:.2f}  center:{det['center']}"
        if det.get("aruco_pose"):
            text += f"  pose:{det['aruco_pose']}"
        cv2.putText(list_img, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        y += 32
        if y > 400:
            break

    cv2.imshow("Detections List", list_img)

    if cv2.waitKey(100) & 0xFF == ord('q'):
        break

# Cleanup
cv2.destroyAllWindows()
print("✅ Receiver shut down cleanly")
import cv2
import numpy as np
import json
import time
import sys
import select
import signal

# ========================= CONFIG =========================
HISTORY_SIZE = 20
DISPLAY_HISTORY = 10
# ==========================================================

detections_history = []
current = []

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
    print("\n🛑 Shutting down viewer...")
    running = False

signal.signal(signal.SIGINT, signal_handler)

print("📡 Viewer started – reading detections from stdin... (press q or Ctrl+C to quit)")

while running:
    # --- Non-blocking stdin read ---
    if select.select([sys.stdin], [], [], 0.05)[0]:
        line = sys.stdin.readline()

        if not line:
            break  # pipe closed

        try:
            payload = json.loads(line.strip())

            # Accept formats:
            # 1. {"detections": [...], "timestamp": ...}
            # 2. [...]
            # 3. {...}
            if isinstance(payload, dict) and "detections" in payload:
                data = payload["detections"]
                ts = payload.get("timestamp", time.time())
                for d in data:
                    d["timestamp"] = ts
            else:
                data = payload
                if isinstance(data, dict):
                    data = [data]

                for d in data:
                    if "timestamp" not in d:
                        d["timestamp"] = time.time()

            current = data
            detections_history.extend(data)

            # Trim history
            if len(detections_history) > HISTORY_SIZE:
                detections_history = detections_history[-HISTORY_SIZE:]

        except json.JSONDecodeError:
            pass  # ignore bad lines

    history = detections_history[-DISPLAY_HISTORY:]

    # === Object Map (640x480 scatter plot) ===
    map_img = np.zeros((480, 640, 3), dtype=np.uint8)

    for det in current:
        if "center" not in det or not det["center"]:
            continue

        cx, cy = int(det["center"][0]), int(det["center"][1])
        color = label_colors.get(det.get("label"), default_color)

        cv2.circle(map_img, (cx, cy), 12, color, -1)
        cv2.putText(map_img,
                    det.get("label", "")[:6],
                    (cx + 15, cy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2)

    cv2.imshow("Object Map (2D scatter)", map_img)

    # === Detections List Table ===
    list_img = np.zeros((420, 700, 3), dtype=np.uint8)

    cv2.putText(list_img,
                "Live Detections (last 10)",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2)

    y = 70

    for det in history:
        ts = det.get("timestamp", time.time())
        ts_str = time.strftime("%H:%M:%S", time.localtime(ts))

        text = (
            f"{ts_str} | "
            f"{det.get('label',''):12} "
            f"conf:{det.get('confidence',0):.2f}  "
            f"center:{det.get('center')}"
        )

        if det.get("aruco_pose"):
            text += f"  pose:{det['aruco_pose']}"

        cv2.putText(list_img,
                    text,
                    (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (200, 200, 200),
                    1)

        y += 32
        if y > 400:
            break

    cv2.imshow("Detections List", list_img)

    # --- UI key handling ---
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cv2.destroyAllWindows()
print("✅ Viewer shut down cleanly")
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

print("📡 Viewer started – reading from stdin...")
print("💡 Tip: If you don't see anything, check if your input is actually arriving.")

while running:
    # 1. Non-blocking check for new data
    # We use a very small timeout (0.01) so we don't freeze the UI
    rlist, _, _ = select.select([sys.stdin], [], [], 0.01)
    
    if rlist:
        line = sys.stdin.readline()
        if not line:
            break
        
        try:
            # Clean and Extract JSON
            clean_line = line.strip().strip("'")
            if " " in clean_line:
                _, json_str = clean_line.split(" ", 1)
            else:
                json_str = clean_line

            payload = json.loads(json_str)
            print(f"✅ Received: {len(payload.get('detections', []))} detections") # DEBUG PRINT

            if isinstance(payload, dict) and "detections" in payload:
                data = payload["detections"]
                ts = payload.get("timestamp", time.time())
                for d in data: d["timestamp"] = ts
            else:
                data = payload if isinstance(payload, list) else [payload]
                for d in data:
                    if "timestamp" not in d: d["timestamp"] = time.time()

            current = data
            detections_history.extend(data)
            if len(detections_history) > HISTORY_SIZE:
                detections_history = detections_history[-HISTORY_SIZE:]

        except Exception as e:
            # Uncomment to debug parsing errors:
            # print(f"❌ Error: {e}")
            pass

    # 2. RENDER (Moved outside the 'if rlist' block so the window stays alive)
    # Map Window
    map_img = np.zeros((480, 640, 3), dtype=np.uint8)
    for det in current:
        if "center" in det and det["center"]:
            cx, cy = int(det["center"][0]), int(det["center"][1])
            color = label_colors.get(det.get("label"), default_color)
            cv2.circle(map_img, (cx, cy), 12, color, -1)
            cv2.putText(map_img, det.get("label", "")[:6], (cx + 15, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # List Window
    list_img = np.zeros((420, 700, 3), dtype=np.uint8)
    cv2.putText(list_img, "Live Detections (last 10)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    history = detections_history[-DISPLAY_HISTORY:]
    y = 70
    for det in history:
        ts_str = time.strftime("%H:%M:%S", time.localtime(det.get("timestamp", time.time())))
        text = f"{ts_str} | {det.get('label',''):12} conf:{det.get('confidence',0):.2f}"
        cv2.putText(list_img, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        y += 32

    cv2.imshow("Object Map", map_img)
    cv2.imshow("Detections List", list_img)

    # 3. UI EVENT LOOP (Crucial for showing the window)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()

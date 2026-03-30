import cv2
import numpy as np
import json

CHESSBOARD = (9, 6)      # inner corners of chessboard
SQUARE_SIZE = 0.025      # meters (adjust to your printed chessboard)

objp = np.zeros((CHESSBOARD[0] * CHESSBOARD[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:CHESSBOARD[0], 0:CHESSBOARD[1]].T.reshape(-1, 2) * SQUARE_SIZE

objpoints = []
imgpoints = []

cap = cv2.VideoCapture(0)
print("📸 Chessboard calibration")
print("   Show chessboard to camera → press SPACE when corners detected")
print("   Press ESC when you have 10+ good images")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ret_c, corners = cv2.findChessboardCorners(gray, CHESSBOARD, None)

    if ret_c:
        cv2.drawChessboardCorners(frame, CHESSBOARD, corners, ret_c)

    cv2.imshow("Calibration - SPACE = capture, ESC = finish", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord(' '):
        if ret_c:
            objpoints.append(objp)
            imgpoints.append(corners)
            print(f"   Captured {len(objpoints)} images")
        else:
            print("   No chessboard detected")
    elif key == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()

if len(objpoints) >= 8:
    print("🔧 Calibrating camera...")
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, gray.shape[::-1], None, None)

    if ret:
        calib = {
            "camera_matrix": mtx.tolist(),
            "dist_coeffs": dist.tolist()
        }
        with open("calibrate.json", "w") as f:
            json.dump(calib, f, indent=2)
        print("✅ Calibration saved to calibrate.json")
        print(f"   Reprojection error: {ret:.4f}")
        print("   You can now run sender.py with full ArUco 3D pose!")
    else:
        print("❌ Calibration failed")
else:
    print("❌ Not enough images captured")

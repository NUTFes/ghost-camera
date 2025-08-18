#!/usr/bin/env python3
import os, time, cv2
import numpy as np

# OpenCVのFFmpegにRTSPをTCPで掴ませる（不安定ならstimeoutも調整）
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|buffer_size;1048576"

URLS = [
    "rtsp://pi1.local:8554/stream",
    "rtsp://pi2.local:8554/stream",
    "rtsp://pi3.local:8554/stream",
]

TARGET_W, TARGET_H = 640, 360   # 各映像の表示サイズ（軽量）

def open_cap(url):
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    cap.set(cv2.CAP_PROP_FPS, 15)
    return cap

caps = [open_cap(u) for u in URLS]
last_ok = [False]*len(URLS)

while True:
    frames = []
    for i, (u, cap) in enumerate(zip(URLS, caps)):
        ok, frame = cap.read()
        if not ok or frame is None:
            # 再接続
            cap.release()
            time.sleep(0.5)
            caps[i] = open_cap(u)
            frames.append(np.zeros((TARGET_H, TARGET_W, 3), dtype=np.uint8))
            last_ok[i] = False
            continue
        last_ok[i] = True
        frame = cv2.resize(frame, (TARGET_W, TARGET_H))
        # ステータス表示
        status = "OK" if last_ok[i] else "RECONNECT"
        cv2.putText(frame, f"Cam{i+1} {status}", (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2, cv2.LINE_AA)
        frames.append(frame)

    # 3台を横並び（2x2にしたいなら行列整形）
    # 例: 2行2列にするなら上段=frames[0],frames[1] / 下段=frames[2],黒
    grid = np.hstack(frames)
    cv2.imshow("MultiCam (RTSP/TCP)", grid)

    if cv2.waitKey(1) & 0xFF == 27:  # ESCで終了
        break

for cap in caps:
    cap.release()
cv2.destroyAllWindows()

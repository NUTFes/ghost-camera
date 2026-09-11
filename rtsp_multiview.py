#!/usr/bin/env python3
import os, time, cv2
import numpy as np

# OpenCVのFFmpegにRTSPをTCPで掴ませる（不安定ならstimeoutも調整）
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|buffer_size;1048576"

# 表示したい名前とURLを辞書形式で対応させる
STREAMS = {
    "PiCam 2 (210)": "rtsp://100.64.0.10:8554/stream",
    "PiCam 3 (208)": "rtsp://100.64.0.14:8554/stream",  # 2台目のIPアドレス
    "PiCam 4 (1F)": "rtsp://100.64.0.15:8554/stream",     # 3台目のIPアドレス
}

TARGET_W, TARGET_H = 640, 360   # 各映像の表示サイズ（軽量）

def open_cap(url):
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    cap.set(cv2.CAP_PROP_FPS, 15)
    return cap

caps = [open_cap(url) for url in STREAMS.values()]
last_ok = [False]*len(STREAMS)

while True:
    frames = []
    # 辞書のキー(name)と値(url)、そしてcapオブジェクトを同時にループさせる
    for i, ((name, url), cap) in enumerate(zip(STREAMS.items(), caps)):
        ok, frame = cap.read()
        if not ok or frame is None:
            # 再接続
            cap.release()
            time.sleep(0.5)
            caps[i] = open_cap(url)
            last_ok[i] = False

            # 「No Connection」と中央に表示した黒いフレームを作成
            black_frame = np.zeros((TARGET_H, TARGET_W, 3), dtype=np.uint8)
            text = "No Connection"
            font_face = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            font_thickness = 2
            text_size = cv2.getTextSize(text, font_face, font_scale, font_thickness)[0]
            text_x = (TARGET_W - text_size[0]) // 2
            text_y = (TARGET_H + text_size[1]) // 2
            cv2.putText(black_frame, text, (text_x, text_y), font_face, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
            frames.append(black_frame)
            continue
        last_ok[i] = True
        frame = cv2.resize(frame, (TARGET_W, TARGET_H))

        # === ここから追加：暗所向けの簡易補正 ===
        # 1) 明るさ & コントラスト（alpha=コントラスト, beta=明るさ）
        frame = cv2.convertScaleAbs(frame, alpha=1.4, beta=25)

        # 2) ガンマ補正（暗部を持ち上げる）
        #    gamma>1 で暗部が見えやすくなる（2.0前後から調整）
        gamma = 1.8
        inv = 1.0 / gamma
        table = (np.arange(256) / 255.0) ** inv
        table = np.uint8(table * 255)
        frame = cv2.LUT(frame, table)
        
        # 3) CLAHE（適応ヒストグラム平坦化）
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        L, A, B = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        L_eq = clahe.apply(L)
        frame = cv2.merge([L_eq, A, B])
        frame = cv2.cvtColor(frame, cv2.COLOR_LAB2BGR)


        # 4) 軽いノイズ低減（暗所で乗るザラつき対策）
        frame = cv2.bilateralFilter(frame, d=5, sigmaColor=50, sigmaSpace=50)

        # ステータス表示
        status = "OK" # 接続成功時は常に"OK"
        cv2.putText(frame, f"{name} {status}", (10, 24),
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
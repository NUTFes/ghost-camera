#!/usr/bin/env python3
import cv2
import socket

def check_rtsp_connection(url):
    print(f"Testing RTSP connection: {url}")
    
    # ネットワーク接続確認
    host = url.split("//")[1].split(":")[0]
    port = int(url.split(":")[2].split("/")[0])
    
    try:
        sock = socket.create_connection((host, port), timeout=5)
        print(f"✓ Network connection to {host}:{port} successful")
        sock.close()
    except Exception as e:
        print(f"✗ Network connection failed: {e}")
        return False
    
    # RTSP接続テスト
    try:
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"✓ RTSP stream working, frame size: {frame.shape}")
                cap.release()
                return True
            else:
                print("✗ RTSP opened but no frame received")
        else:
            print("✗ Failed to open RTSP stream")
        cap.release()
    except Exception as e:
        print(f"✗ RTSP connection error: {e}")
    
    return False

if __name__ == "__main__":
    url = "rtsp://172.30.1.5:8554/stream"
    check_rtsp_connection(url)
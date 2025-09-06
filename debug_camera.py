#!/usr/bin/env python3
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
import os
import subprocess

def check_camera_devices():
    print("=== Camera Device Check ===")
    
    # v4l2デバイス確認
    try:
        result = subprocess.run(['ls', '-l', '/dev/video*'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("Video devices found:")
            print(result.stdout)
        else:
            print("No video devices found")
    except Exception as e:
        print(f"Error checking video devices: {e}")
    
    # v4l2-ctl確認
    try:
        result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("\nv4l2-ctl output:")
            print(result.stdout)
    except Exception as e:
        print(f"v4l2-ctl not available: {e}")

def test_gstreamer_pipeline():
    print("\n=== GStreamer Pipeline Test ===")
    Gst.init(None)
    
    # テスト用パイプライン
    pipeline_str = (
        "v4l2src device=/dev/video0 ! "
        "video/x-raw,width=640,height=480,framerate=15/1 ! "
        "videoconvert ! fakesink"
    )
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        pipeline.set_state(Gst.State.PLAYING)
        
        # 3秒待機
        import time
        time.sleep(3)
        
        pipeline.set_state(Gst.State.NULL)
        print("✓ GStreamer pipeline test successful")
        return True
        
    except Exception as e:
        print(f"✗ GStreamer pipeline test failed: {e}")
        return False

if __name__ == "__main__":
    check_camera_devices()
    test_gstreamer_pipeline()
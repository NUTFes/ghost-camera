#!/usr/bin/env python3
import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GObject, GstRtspServer
import sys

Gst.init(None)

# デバッグ出力を有効化
Gst.debug_set_active(True)
Gst.debug_set_default_threshold(Gst.DebugLevel.WARNING)

class RTSPFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, use_picam=True):
        super().__init__()
        self.use_picam = use_picam
        self.set_shared(True)

    def do_create_element(self, url):
        print(f"Creating element for URL: {url}")
        
        DEVICE = "/dev/video0"
        WIDTH, HEIGHT, FPS = 640, 480, 15
        BITRATE_KBPS = 1500

        # より確実なパイプライン（フォーマット自動選択）
        pipeline_str = (
            f"v4l2src device={DEVICE} ! "
            f"videoconvert ! "
            f"video/x-raw,width={WIDTH},height={HEIGHT},framerate={FPS}/1 ! "
            f"x264enc tune=zerolatency speed-preset=ultrafast bitrate={BITRATE_KBPS} ! "
            f"video/x-h264,profile=baseline ! "
            f"h264parse config-interval=1 ! "
            f"rtph264pay name=pay0 pt=96"
        )
        
        print(f"Pipeline: {pipeline_str}")
        
        try:
            pipeline = Gst.parse_launch(pipeline_str)
            print("Pipeline created successfully")
            return pipeline
        except Exception as e:
            print(f"Pipeline creation failed: {e}")
            return None

def main():
    print("Starting RTSP server with debug output...")
    
    loop = GObject.MainLoop()
    server = GstRtspServer.RTSPServer()
    server.props.service = "8554"
    
    factory = RTSPFactory(use_picam=False)
    mount_points = server.get_mount_points()
    mount_points.add_factory("/stream", factory)
    
    server.attach(None)
    print("RTSP server started on rtsp://<THIS_PI_IP>:8554/stream")
    
    try:
        loop.run()
    except KeyboardInterrupt:
        print("Stopping server...")
        sys.exit(0)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GObject, GstRtspServer

Gst.init(None)

class RTSPFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, use_picam=True):
        super().__init__()
        self.use_picam = use_picam
        self.set_shared(True)  # 複数クライアントから同時接続OK

    def do_create_element(self, url):
        WIDTH, HEIGHT, FPS = 1280, 720, 15  # 混雑対策
        BITRATE_KBPS = 1500                 # 1.5Mbps目安

        if self.use_picam:
            # Piカメラ(libcamera) → H.264 → RTP
            # ※ハードエンコーダが使えない場合は x264enc に切替
            pipeline = (
                f"libcamerasrc ! video/x-raw,width={WIDTH},height={HEIGHT},framerate={FPS}/1 "
                f"! videoconvert ! x264enc tune=zerolatency bitrate={BITRATE_KBPS} speed-preset=ultrafast "
                f"! video/x-h264,profile=baseline "
                f"! h264parse config-interval=1 "
                f"! rtph264pay name=pay0 pt=96"
            )
        else:
            # UVCカメラ(v4l2src)例
            pipeline = (
                f"v4l2src device=/dev/video0 ! video/x-raw,width={WIDTH},height={HEIGHT},framerate={FPS}/1 "
                f"! videoconvert ! x264enc tune=zerolatency bitrate={BITRATE_KBPS} speed-preset=ultrafast "
                f"! video/x-h264,profile=baseline "
                f"! h264parse config-interval=1 "
                f"! rtph264pay name=pay0 pt=96"
            )
        return Gst.parse_launch(pipeline)

def main():
    loop = GObject.MainLoop()
    server = GstRtspServer.RTSPServer()
    server.props.service = "8554"  # rtsp://<IP>:8554/stream
    factory = RTSPFactory(use_picam=True)
    mount_points = server.get_mount_points()
    mount_points.add_factory("/stream", factory)
    server.attach(None)
    print("RTSP on rtsp://<THIS_PI_IP>:8554/stream")
    loop.run()

if __name__ == "__main__":
    main()

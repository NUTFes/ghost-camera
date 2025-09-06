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
        DEVICE = "/dev/video0"
        WIDTH, HEIGHT, FPS = 640, 480, 15  # 混雑対策
        BITRATE_KBPS = 1500                 # 1.5Mbps目安

        pipeline = (
            f"v4l2src device={DEVICE} ! "
            f"image/jpeg,width={WIDTH},height={HEIGHT},framerate={FPS}/1 ! "
            f"jpegdec ! videoconvert ! "
            f"x264enc tune=zerolatency speed-preset=ultrafast bitrate={BITRATE_KBPS} ! "
            f"video/x-h264,profile=baseline ! "
            f"h264parse config-interval=1 ! rtph264pay name=pay0 pt=96"
        )
        return Gst.parse_launch(pipeline)

def main():
    loop = GObject.MainLoop()
    server = GstRtspServer.RTSPServer()
    server.props.service = "8554"  # rtsp://<IP>:8554/stream
    factory = RTSPFactory(use_picam=False)
    mount_points = server.get_mount_points()
    mount_points.add_factory("/stream", factory)
    server.attach(None)
    print("RTSP on rtsp://<THIS_PI_IP>:8554/stream")
    loop.run()

if __name__ == "__main__":
    main()

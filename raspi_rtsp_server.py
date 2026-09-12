#!/usr/bin/env python3
import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import Gst, GObject, GstRtspServer

Gst.init([])

class RTSPFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, use_picam=True):
        super().__init__()
        self.use_picam = use_picam
        self.set_shared(True)  # 複数クライアントから同時接続OK

    def do_create_element(self, url):
        DEVICE = "/dev/video0"
        WIDTH, HEIGHT = 640, 480
        # MJPEGの640x480は約120.101fpsしか列挙されないため、
        # 約120fps取り込み -> jpegdec -> videorateで15fpsに間引き、という
        # 無駄の多い構成になっていた。2台同時接続時の遅延の主因。
        # YUYV(YUY2) 640x480@30fps はこのカメラで正常動作するので、
        # 最初から30fpsで取り込んでJPEGデコードを省く。
        CAMERA_FPS = 30
        OUTPUT_FPS = 15
        BITRATE_KBPS = 1200

        pipeline = (
            f"v4l2src device={DEVICE} ! "
            f"video/x-raw,format=YUY2,width={WIDTH},height={HEIGHT},framerate={CAMERA_FPS}/1 ! "
            f"videoconvert ! "
            f"videorate ! video/x-raw,framerate={OUTPUT_FPS}/1 ! "
            f"x264enc tune=zerolatency speed-preset=ultrafast "
            f"bitrate={BITRATE_KBPS} key-int-max={OUTPUT_FPS} ! "
            f"video/x-h264,profile=baseline ! "
            f"h264parse config-interval=1 ! "
            f"rtph264pay name=pay0 pt=96 config-interval=1"
        )
        print("Pipeline:", pipeline)
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

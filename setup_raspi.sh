sudo apt update
sudo apt upgrade -y


sudo apt install -y python3-gi python3-gst-1.0 gir1.2-gst-rtsp-server-1.0 \
                    gstreamer1.0-tools gstreamer1.0-plugins-{base,good,bad} \
                    gstreamer1.0-libcamera  # Bookworm以降でPiカメラを使う場合

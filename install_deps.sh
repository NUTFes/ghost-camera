#!/bin/bash
sudo apt update
sudo apt upgrade -y


sudo apt install -y python3-gi python3-gst-1.0 gir1.2-gst-rtsp-server-1.0 \
                    gstreamer1.0-tools gstreamer1.0-plugins-{base,good,bad} \
                    gstreamer1.0-libcamera  # Bookworm以降でPiカメラを使う場合


# Raspberry Pi用 ghost-camera 依存関係インストールスクリプト

echo "Installing system dependencies..."

# システム依存関係
sudo apt update
sudo apt install -y \
    build-essential \
    pkg-config \
    python3-dev \
    libcairo2-dev \
    libgirepository1.0-dev \
    libgirepository-2.0-dev \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    python3-gi \
    python3-gi-cairo \
    python3-opencv

echo "Installing Python packages..."

# システムのPyGObject/pycairoを使用（コンパイルエラー回避）
echo "Note: Using system python3-gi and python3-gi-cairo packages"

# 必要なPythonパッケージのみ追加
uv add opencv-python numpy

echo "Installation complete!"
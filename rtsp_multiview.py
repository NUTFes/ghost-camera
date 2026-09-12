#!/usr/bin/env python3
import os, threading, cv2
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

RECONNECT_WAIT_SEC = 0.5   # 切断時に再接続を試すまでの待ち時間
DISPLAY_POLL_MS = 5        # 表示ループのポーリング間隔（GUIイベント処理も兼ねる）

# === 暗所補正のON/OFF ===
# 複数台を同時表示すると 15fps × 台数 ぶんの後処理が走るため、
# 重い処理から順に切っていけるようにフラグ化している。
# 遅延が出る場合は ENABLE_BILATERAL -> ENABLE_CLAHE の順にFalseにする。
ENABLE_GAMMA = True
ENABLE_CLAHE = True
ENABLE_BILATERAL = False   # bilateralFilterは重いのでデフォルトOFF

# ガンマ補正用LUTとCLAHEはフレームごとに作り直す必要がないので事前に生成
GAMMA = 1.8
GAMMA_LUT = np.uint8(((np.arange(256) / 255.0) ** (1.0 / GAMMA)) * 255)
CLAHE = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))


def open_cap(url):
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
    cap.set(cv2.CAP_PROP_FPS, 15)
    return cap


class CameraStream:
    """1台のRTSPカメラを専用スレッドで受信し、常に最新フレームだけを保持する。

    以前は1本のループで各カメラを順番に cap.read() していたため、
    1台の受信が詰まると他のカメラの表示まで待たされていた。
    受信をカメラごとのスレッドに分けることで、遅いカメラが他に波及しなくなる。
    また、読み捨てずに溜まったフレームを表示すると遅延が蓄積するので、
    メインループは「最新の1枚」だけを見る。
    """

    def __init__(self, name, url):
        self.name = name
        self.url = url
        self._lock = threading.Lock()
        self._frame = None      # 表示サイズにリサイズ済みの最新フレーム
        self._seq = 0           # 新しいフレームが来るたびに増える通し番号
        self._connected = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"cam:{name}", daemon=True)

    def start(self):
        self._thread.start()
        return self

    def _run(self):
        cap = None
        try:
            while not self._stop.is_set():
                if cap is None:
                    cap = open_cap(self.url)
                    if not cap.isOpened():
                        cap.release()
                        cap = None
                        self._mark_disconnected()
                        self._stop.wait(RECONNECT_WAIT_SEC)
                        continue

                ok, frame = cap.read()
                if not ok or frame is None:
                    # 再接続
                    cap.release()
                    cap = None
                    self._mark_disconnected()
                    self._stop.wait(RECONNECT_WAIT_SEC)
                    continue

                # リサイズはここで済ませる。メインスレッドの負荷が減るうえ、
                # resizeは必ず新しい配列を返すのでキャプチャ側のバッファと共有されない。
                frame = cv2.resize(frame, (TARGET_W, TARGET_H))
                with self._lock:
                    self._frame = frame
                    self._seq += 1
                    self._connected = True
        finally:
            if cap is not None:
                cap.release()

    def _mark_disconnected(self):
        with self._lock:
            self._frame = None
            self._connected = False

    def read(self):
        """(最新フレーム, 通し番号, 接続中か) を返す。未接続ならフレームはNone。"""
        with self._lock:
            return self._frame, self._seq, self._connected

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2.0)


def make_placeholder(name, text="No Connection"):
    """「No Connection」と中央に表示した黒いフレームを作成"""
    black_frame = np.zeros((TARGET_H, TARGET_W, 3), dtype=np.uint8)
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    font_thickness = 2
    text_size = cv2.getTextSize(text, font_face, font_scale, font_thickness)[0]
    text_x = (TARGET_W - text_size[0]) // 2
    text_y = (TARGET_H + text_size[1]) // 2
    cv2.putText(black_frame, text, (text_x, text_y), font_face, font_scale,
                (255, 255, 255), font_thickness, cv2.LINE_AA)
    cv2.putText(black_frame, name, (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return black_frame


def enhance(frame, name):
    """暗所向けの簡易補正とステータス表示を行い、新しいフレームを返す。"""
    # 1) 明るさ & コントラスト（alpha=コントラスト, beta=明るさ）
    #    convertScaleAbsは新しい配列を返すので、以降の書き込みが
    #    CameraStreamの保持するフレームを壊すことはない。
    frame = cv2.convertScaleAbs(frame, alpha=1.4, beta=25)

    # 2) ガンマ補正（暗部を持ち上げる）
    #    gamma>1 で暗部が見えやすくなる（2.0前後から調整）
    if ENABLE_GAMMA:
        frame = cv2.LUT(frame, GAMMA_LUT)

    # 3) CLAHE（適応ヒストグラム平坦化）
    if ENABLE_CLAHE:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        L, A, B = cv2.split(lab)
        L_eq = CLAHE.apply(L)
        frame = cv2.merge([L_eq, A, B])
        frame = cv2.cvtColor(frame, cv2.COLOR_LAB2BGR)

    # 4) 軽いノイズ低減（暗所で乗るザラつき対策）
    #    比較的重い処理なので、複数台同時表示では既定でOFF
    if ENABLE_BILATERAL:
        frame = cv2.bilateralFilter(frame, d=5, sigmaColor=50, sigmaSpace=50)

    # ステータス表示
    status = "OK"  # 接続成功時は常に"OK"
    cv2.putText(frame, f"{name} {status}", (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return frame


def main():
    streams = [CameraStream(name, url).start() for name, url in STREAMS.items()]
    placeholders = [make_placeholder(s.name) for s in streams]

    # 同じフレームを何度も処理しないよう、描画結果を通し番号付きでキャッシュする
    rendered = list(placeholders)
    rendered_seq = [-1] * len(streams)
    need_redraw = True

    try:
        while True:
            for i, stream in enumerate(streams):
                frame, seq, connected = stream.read()
                if not connected or frame is None:
                    if rendered_seq[i] != -1:
                        rendered[i] = placeholders[i]
                        rendered_seq[i] = -1
                        need_redraw = True
                    continue
                if seq == rendered_seq[i]:
                    continue    # 新しいフレームが来ていないので描画済みのものを使う
                rendered[i] = enhance(frame, stream.name)
                rendered_seq[i] = seq
                need_redraw = True

            if need_redraw:
                # 3台を横並び（2x2にしたいなら行列整形）
                # 例: 2行2列にするなら上段=rendered[0],rendered[1] / 下段=rendered[2],黒
                grid = np.hstack(rendered)
                cv2.imshow("MultiCam (RTSP/TCP)", grid)
                need_redraw = False

            if cv2.waitKey(DISPLAY_POLL_MS) & 0xFF == 27:  # ESCで終了
                break
    finally:
        for stream in streams:
            stream.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

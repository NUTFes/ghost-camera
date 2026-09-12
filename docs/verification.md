# 動作確認手順

技大祭お化け屋敷の監視カメラシステムを、Tailscale の起動から複数台同時表示まで順に確認する手順書。
上から順に実行し、途中で失敗したらその節の「うまくいかないとき」を見る。

セットアップ（OS 焼き込み・eduroam 接続・GitHub SSH・Tailscale 登録）が未了の場合は、
先に [README.md](../README.md) の手順を済ませること。この文書は**セットアップ済みの機材を動かす**ための手順。

---

## 1. 全体構成

```
[Raspberry Pi #1] --+
  USBカメラ         |
  raspi_rtsp_server.py
  rtsp://<PiのTailscale IP>:8554/stream
                    |
[Raspberry Pi #2] --+--- Tailscale (100.64.x.x) ---> [ノートPC]
                    |                                  rtsp_multiview.py
[Raspberry Pi #3] --+                                  3台を横並び表示
```

- 映像は **H.264 / 640x480 / 15fps** を RTSP over TCP で配信する
- Pi 側は 1 台につき 1 プロセス。`set_shared(True)` なので複数の PC から同時に見られる
- ノート PC 側はカメラごとに受信スレッドを分けており、1 台が詰まっても他は止まらない

---

## 2. 用意するもの

| 場所 | もの |
|---|---|
| Raspberry Pi（各台） | USB カメラを接続、電源、ネットワーク接続済み |
| ノート PC | 画面表示できる環境（GUI。SSH 越しの場合は X 転送が必要） |
| 共通 | Tailscale にログイン済みのアカウント |

確認用コマンドが入っていない場合は入れておく。

```bash
# Pi側：カメラ情報の確認に使う
sudo apt install -y v4l-utils

# ノートPC側：単体での接続確認に使う（ffplay）
sudo apt install -y ffmpeg

# 両方：CPU負荷の確認に使う
sudo apt install -y htop
```

---

## 3. 手順 1：Tailscale を起動して疎通確認

**Pi 側・ノート PC 側の両方**で実施する。

### 3-1. Tailscale が入っているか確認

```bash
tailscale version
```

`command not found` なら未インストール。

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

### 3-2. デーモンを起動する

```bash
sudo systemctl enable --now tailscaled
systemctl status tailscaled --no-pager
```

`active (running)` になっていること。`enable` を付けているので次回以降は自動起動する。

### 3-3. ログイン・接続する

```bash
sudo tailscale up
```

初回はブラウザでの認証 URL が表示されるので、ブラウザで開いてログインする。
Pi をヘッドレスで使っている場合は、表示された URL を手元の PC のブラウザに貼り付ける。

2 回目以降は認証済みなので、このコマンドだけで接続状態になる。

### 3-4. 自分の Tailscale IP を控える

**各 Pi で実行し、IP をメモする。** あとでノート PC 側の設定に書く。

```bash
tailscale ip -4
```

`100.64.x.x` の形式で表示される。

### 3-5. 全機材が見えているか確認

```bash
tailscale status
```

3 台の Pi とノート PC が一覧に出ること。出ていない機材は、その機材で `sudo tailscale up` が済んでいない。

### 3-6. ノート PC から Pi へ疎通確認

```bash
ping -c 3 <PiのTailscale IP>
```

**うまくいかないとき**

| 症状 | 対処 |
|---|---|
| `tailscale status` に出てこない | その機材で `sudo tailscale up` を実行する |
| `Logged out.` と出る | `sudo tailscale up` で再ログインする |
| ping が通らない | 両方が同じ Tailscale アカウント（tailnet）か確認する |
| eduroam に繋がっていない | 先に Wi-Fi 接続を確認する（Tailscale は別ネットワーク経由でも動く） |

---

## 4. 手順 2：カメラの確認（Pi 側）

RTSP サーバを起動する前に、カメラ単体が動くことを確認する。

### 4-1. デバイスが見えているか

```bash
ls -l /dev/video*
v4l2-ctl --list-devices
```

USB カメラは `/dev/video0` と `/dev/video1` の 2 つのノードを作ることが多い。
**このうち映像が取れるのは通常 `/dev/video0` の方**で、`/dev/video1` は
`not a capture device` になる。`raspi_rtsp_server.py` は `/dev/video0` を使う設定になっている。

### 4-2. 対応する解像度・フレームレートを確認する

```bash
v4l2-ctl -d /dev/video0 --list-formats-ext
```

出力に `YUYV` の `640x480` が含まれ、`30.000 fps` が並んでいることを確認する。
現在のサーバはこの **YUYV 640x480 / 30fps** を使う。

> 参考：このカメラの MJPEG 640x480 は約 **120.101fps** しか列挙されない。
> 以前は MJPEG で約 120fps 取り込んでから 15fps に間引いていたため負荷が高く、
> 2 台同時接続時の遅延の主因になっていた。

### 4-3. カメラ単体をテストする

```bash
gst-launch-1.0 -v \
  v4l2src device=/dev/video0 num-buffers=100 ! \
  'video/x-raw,format=YUY2,width=640,height=480,framerate=30/1' ! \
  videoconvert ! fakesink
```

最後に `Got EOS from element "pipeline0".` が出れば成功。

### 4-4. H.264 エンコードまでテストする

```bash
gst-launch-1.0 -v \
  v4l2src device=/dev/video0 num-buffers=100 ! \
  'video/x-raw,format=YUY2,width=640,height=480,framerate=30/1' ! \
  videoconvert ! \
  videorate ! 'video/x-raw,framerate=15/1' ! \
  x264enc tune=zerolatency speed-preset=ultrafast bitrate=1200 key-int-max=15 ! \
  'video/x-h264,profile=baseline' ! \
  h264parse ! fakesink
```

ここまで `Got EOS` になれば、カメラからエンコードまでは問題ない。

**うまくいかないとき**

| 症状 | 原因と対処 |
|---|---|
| `Device '/dev/video1' is not a capture device.` | 映像用ノードではない。`/dev/video0` を使う |
| `streaming stopped, reason not-negotiated (-4)` | 指定した形式・解像度・fps にカメラが対応していない。4-2 の一覧と突き合わせる |
| `No such element or plugin 'x264enc'` | `sudo apt install -y gstreamer1.0-plugins-ugly` |
| デバイスが 1 つも出ない | USB を挿し直す。`dmesg` の末尾で認識されているか確認する |

---

## 5. 手順 3：RTSP サーバを起動する（Pi 側・各台）

```bash
cd ~/workspace/ghost-camera
source .venv/bin/activate
python3 raspi_rtsp_server.py
```

起動すると、組み立てたパイプラインと待ち受け URL が表示される。

```
Pipeline: v4l2src device=/dev/video0 ! video/x-raw,format=YUY2,width=640,height=480,framerate=30/1 ! ...
RTSP on rtsp://<THIS_PI_IP>:8554/stream
```

**`format=YUY2` と `framerate=30/1` になっていること**を目視で確認する。

別のターミナルで、ポートが開いたか確認する。

```bash
ss -lntp | grep 8554
```

**3 台すべてで同じ手順を実施する。**

> 起動しっぱなしにしたい場合は `tmux` などを使う。ターミナルを閉じるとプロセスも終了する。

---

## 6. 手順 4：1 台ずつ接続を確認する（ノート PC 側）

いきなり 3 台表示せず、**まず 1 台ずつ**確認する。切り分けが楽になる。

### 6-1. ポートに届くか

```bash
nc -vz <PiのTailscale IP> 8554
```

### 6-2. 映像が出るか

```bash
ffplay -rtsp_transport tcp rtsp://<PiのTailscale IP>:8554/stream
```

ウィンドウが開いて映像が出れば、その 1 台は問題ない。`q` で終了する。

**うまくいかないとき**

| 症状 | 原因と対処 |
|---|---|
| `nc` が `Connection refused` | Pi 側でサーバが起動していない。手順 3 に戻る |
| `nc` が無反応のままタイムアウト | Tailscale の疎通の問題。手順 1 に戻る |
| ffplay は繋がるが映像が出ない | Pi 側のターミナルにエラーが出ていないか確認する |
| 映像が出るが非常に遅い | Pi 側で `htop` を見る。8-1 を参照 |

---

## 7. 手順 5：複数台を同時表示する（ノート PC 側）

### 7-1. 接続先を設定する

`rtsp_multiview.py` の先頭の `STREAMS` を、手順 3-4 で控えた Tailscale IP に合わせる。

```python
STREAMS = {
    "PiCam 2 (210)": "rtsp://100.64.0.10:8554/stream",
    "PiCam 3 (208)": "rtsp://100.64.0.14:8554/stream",
    "PiCam 4 (1F)":  "rtsp://100.64.0.15:8554/stream",
}
```

**2 台だけで試したい場合は、使わない行を消すか `#` でコメントアウトする。**
表示は登録した台数ぶんだけ横に並ぶ。

### 7-2. 起動する

```bash
cd ~/workspace/ghost-camera
source .venv/bin/activate
python3 rtsp_multiview.py
```

`MultiCam (RTSP/TCP)` というウィンドウが開く。**ESC キーで終了**する。

- 接続できているカメラ：映像の左上に `PiCam 2 (210) OK` のように表示される
- 接続できていないカメラ：黒画面に `No Connection` と表示される（自動で再接続を試み続ける）

---

## 8. 今回の変更で重点的に見るポイント

今回の変更は「2 台同時に繋ぐと読み込みが遅くなる」問題への対策。
以下を確認する。

### 8-1. Pi 側の CPU 負荷が下がっているか

RTSP 配信中に Pi 側で実行する。

```bash
htop
```

`python3` の CPU 使用率を見る。変更前は約 120fps 分を取り込んで JPEG デコードしていたため
負荷が高かった。**変更後は明確に下がっているはず。**
依然として 100% 前後に張り付いている場合は、9 章の調整つまみを試す。

### 8-2. 2 台同時でも遅くならないか

1 台だけ表示したときと、2〜3 台同時に表示したときで、
**映像の遅れ（カメラの前で手を振ってから画面に映るまで）が大きく変わらないこと**を確認する。

### 8-3. 1 台落としても他が固まらないか（スレッド化の効果）

複数台を表示した状態で、**1 台の Pi のサーバを `Ctrl+C` で止める**。

- 止めたカメラ → `No Connection` に変わる
- **残りのカメラ → 何事もなく動き続ける**

ここで残りのカメラまで止まったりカクついたりする場合は、スレッド化が効いていない。

### 8-4. 自動で復帰するか

8-3 で止めた Pi のサーバを起動し直す。
ノート PC 側は再起動せずに、数秒で `No Connection` から映像に戻ること。

### 確認結果メモ

| 項目 | 結果 | メモ |
|---|---|---|
| 8-1 Pi の CPU 使用率 | | 変更前 ___ % → 変更後 ___ % |
| 8-2 2 台同時の遅延 | | |
| 8-3 1 台落として他が継続 | | |
| 8-4 自動復帰 | | |

---

## 9. 調整つまみ

### Pi 側：`raspi_rtsp_server.py` の `do_create_element()`

| 変数 | 既定値 | 説明 |
|---|---|---|
| `DEVICE` | `/dev/video0` | カメラのデバイス。`/dev/video1` では映像が取れない |
| `WIDTH, HEIGHT` | `640, 480` | 取り込み解像度 |
| `CAMERA_FPS` | `30` | カメラからの取り込み fps。カメラが対応する値にすること |
| `OUTPUT_FPS` | `15` | 配信する fps。下げるとさらに軽くなる |
| `BITRATE_KBPS` | `1200` | H.264 のビットレート。回線が細いときは下げる |

**まだ重いとき**は `OUTPUT_FPS` を `10` に下げるか、`WIDTH, HEIGHT` を `480, 360` にする。

### ノート PC 側：`rtsp_multiview.py` の先頭

| 変数 | 既定値 | 説明 |
|---|---|---|
| `STREAMS` | 3 台 | 表示するカメラの名前と URL |
| `TARGET_W, TARGET_H` | `640, 360` | 1 台あたりの表示サイズ |
| `ENABLE_GAMMA` | `True` | 暗部を持ち上げるガンマ補正。軽い |
| `ENABLE_CLAHE` | `True` | 適応ヒストグラム平坦化。そこそこ重い |
| `ENABLE_BILATERAL` | `False` | ノイズ低減。**重いので既定で OFF** |

暗所補正は 15fps × 台数ぶん走るため、**遅いときは重い方から順に切る**。

```
ENABLE_BILATERAL = False   ← まずここ（既定で OFF 済み）
ENABLE_CLAHE     = False   ← まだ遅ければここ
```

逆に、PC に余裕があって画質を上げたいときは `ENABLE_BILATERAL = True` に戻す。

---

## 10. よくある詰まりどころ

| 症状 | 確認すること |
|---|---|
| すべて `No Connection` | Tailscale（手順 1）→ Pi 側サーバ起動（手順 3）の順に確認 |
| 特定の 1 台だけ `No Connection` | その Pi で手順 3、ノート PC から手順 4 を実施 |
| ウィンドウが開かない | GUI 環境か確認。SSH 越しなら `ssh -X` が必要 |
| `ModuleNotFoundError: cv2` | `source .venv/bin/activate` を忘れていないか |
| `gi` が見つからない | `uv venv --system-site-packages` で作り直す（システムの `python3-gi` を使うため） |
| 映像は出るが暗い | 9 章の暗所補正を調整する |
| 再起動したら Tailscale が繋がらない | `sudo systemctl enable --now tailscaled` を実行しておく |

### 補助スクリプト

| ファイル | 用途 |
|---|---|
| `debug_camera.py` | Pi 側でカメラデバイスと GStreamer の疎通を確認する |
| `debug_rtsp.py` | RTSP 接続を確認する。**URL がファイル内に直書きなので、実行前に書き換える** |
| `raspi_rtsp_debug.py` | GStreamer のデバッグ出力付きで RTSP サーバを起動する |

GStreamer のログを詳しく見たいときは、環境変数を付けて起動する。

```bash
GST_DEBUG=3 python3 raspi_rtsp_server.py
```

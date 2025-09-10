# ghost-camera

## セットアップ手順
### 依存関係インストール
```bash
sudo sh install_deps.sh
```

### uvインストール
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### uv環境構築
```bash
uv venv --system-site-packages

# 仮想環境を有効化
source .venv/bin/activate

# 同期
uv sync
```

## 実行ファイル

- ラズパイ：

```bash
python3 raspi_rtsp_server.py
```

- ノートPC

```bash
python3 rtsp_multiview.py
```



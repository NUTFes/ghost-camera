# ghost-camera
本プロジェクトは技大祭のお化け屋敷で使用する監視カメラシステムを作成するものである．以下にセットアップ手順を示す

# 手順

## UbuntuOSセットアップ

- microSDカードにUbuntuを焼く
    - https://qiita.com/daikiminobe/items/2df581b450a35f480e69
- ラズパイにmicroSDカードを差し込んで起動
- 初期設定を行う

## edroam接続

- 参考：https://qiita.com/tama14142356/items/ad69b35a09ad93f32cfa

## Googleアカウント作成

## githubアカウント作成とssh接続

### ssh接続

---

#### ユーザー設定

- ターミナルで以下のコマンドを実施
    
    ```bash
    git config --global user.name [名前]
    ```
    
    ```bash
    $ git config --global user.email [メールアドレス]
    ```
    

#### ssh-keyの作成

- ターミナルで以下のコマンドを実施
    
    ```bash
    ssh-keygen -t rsa -C "[メールアドレス]"
    ```
    

#### ssh-keyのコピー

- ターミナルで以下のコマンドを順に実施
    
    ```bash
    sudo apt update
    ```
    
    ```bash
    sudo apt install xclip
    ```
    
- さらに以下のコマンドを実施してssh-keyをコピー
    
    ```bash
    cat ~/.ssh/id_rsa.pub | xclip -selection clipboard
    
    ```
    

#### Githubにssh-keyを登録

1. Githubを開く
2. 右上の自分のアイコンをクリック
3. 「Settings」を開く
4. 「SSH and GPG keys」を開く
5. 緑色の「New SSH key」ボタンをクリック
6. 「Title」に任意のタイトルを入力
    1. （自分が何のSSH keyなのか分かればok）
7. 「Key」に `Ctrl + v` でコピーしたssh-keyを貼り付け
8. 緑色の「Add SSH Key」ボタンをクリック

#### 接続確認

- VSCodeのターミナルに戻る
- 以下のコマンドを実施
    
    ```bash
    ssh -T git@github.com
    
    ```
    
    - 成功したら完了

#### 念のため

- 以下のコマンドを実施
    
    ```bash
    git config --global core.fileMode false
    ```
    
    ```bash
    git config --global core.fileMode
    ```
    
    `false`と表示されればok
    

## tailscale登録とssh接続

- 参考：https://blog.tsukumijima.net/article/tailscale-vpn/

## プロジェクトclone

```bash
git clone https://github.com/NUTFes/ghost-camera.git
```

## 動作確認

- venv + uv の環境立てる
- 実行ファイルを実行
    - ラズパイ：raspi_rtsp_server.py
    - ノートPC：rtsp_multiview.py
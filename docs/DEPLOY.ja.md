<div align="center">

# WebToApp — デプロイガイド

[English](DEPLOY.md) · [简体中文](DEPLOY.zh.md) · **日本語** · [العربية](DEPLOY.ar.md) · [Русский](DEPLOY.ru.md) · [Español](DEPLOY.es.md) · [Português](DEPLOY.pt.md) · [Français](DEPLOY.fr.md) · [Deutsch](DEPLOY.de.md)

WebToApp を本番環境で動かすためのステップバイステップガイド。

</div>

---

## 目次

1. [必要要件](#1-必要要件)
2. [コードを取得](#2-コードを取得)
3. [Python 環境](#3-python-環境)
4. [設定](#4-設定)
5. [ローカル実行](#5-ローカル実行)
   - [Docker](#docker)
6. [サービスとして実行（systemd）](#6-サービスとして実行systemd)
7. [リバースプロキシ（Nginx）](#7-リバースプロキシnginx)
8. [HTTPS](#8-https)
9. [Android APK ビルド（任意）](#9-android-apk-ビルド任意)
10. [iOS プロファイル署名（任意）](#10-ios-プロファイル署名任意)
11. [Cloudflare R2 オフロード（任意）](#11-cloudflare-r2-オフロード任意)
12. [アップデート](#12-アップデート)
13. [トラブルシューティング](#13-トラブルシューティング)

---

## 1. 必要要件

- **Python 3.10+**
- Linux サーバー（ディストリビューション不問）。1 vCPU / 1 GB RAM で開始可能。
- 外部インターネットアクセス（アナライザーが対象サイトを取得します）。
- 任意、実際の Android APK ビルド時のみ：**Android SDK**（`aapt2`、`d8`、`apksigner`、`zipalign`）、**apktool**、**JDK**（`java` / `javac` / `keytool`）。無い場合、Android はインストール可能な PWA パッケージにフォールバックします。
- 任意、iOS 署名時のみ：**openssl**（ほぼ全ての Linux に標準搭載）。

唯一の必須依存は Python です。それ以外は任意で、優雅にフォールバックします。

## 2. コードを取得

```bash
git clone https://github.com/shiaho777/WebToApp.git
cd WebToApp
```

## 3. Python 環境

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

4 つのランタイム依存をインストールします：`fastapi`、`uvicorn[standard]`、`httpx`、`Pillow`。Cloudflare R2 オフロード（任意）に追加パッケージは不要です——§11 を参照。

## 4. 設定

すべての設定は環境変数から読み込まれます。各項目は任意で、妥当なデフォルトがあります。

```bash
cp .env.example .env
# .env を編集
```

| 変数 | 用途 | デフォルト |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | 公開オリジン（例 `https://app.example.com`）。本番では必須。さもないと iPhone が `localhost` を開こうとします。 | Host ヘッダから推測 |
| `ANDROID_PACKAGE_PREFIX` | デフォルトの Android パッケージ接頭辞。 | `com.webtoapp` |
| `ANDROID_KEYSTORE_DIR` | アプリごとの署名キーストアの保存先。公開パスの外に置くこと。 | `certs/app-keys` |
| `DAILY_BUILD_QUOTA` | デバイスごとの 1 日のビルド上限（`0` で無効）。 | `10` |
| `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` | iOS プロファイル署名用の公的 CA 証明書。 | 未設定（未署名でもインストール可） |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_PUBLIC_BASE_URL` | Cloudflare R2 オフロード（§11 参照）。 | 未設定（ローカル配信） |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` | URL 切替時に iOS `/launch` リダイレクトのキャッシュを即時パージ。 | 未設定 |

> **本物の `.env` を絶対にコミットしないでください。** デフォルトで git 無視されています。

## 5. ローカル実行

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

<http://127.0.0.1:8000> を開きます。ローカル開発では環境変数は不要です。

## Docker

一つのコマンドでイメージを作り、ポート 8000 で起動します。既定のイメージには Python、JDK、Android SDK、apktool が入っているので、Android の成果物は本物の APK です。イメージを作り直しても、生成済みのアプリと署名鍵は残ります。

```bash
cp .env.example .env
# 公開する前に PUBLIC_BASE_URL=https://your-domain.com を設定してください。
docker compose up -d --build
```

<http://127.0.0.1:8000> を開きます。初回ビルドは `dl.google.com` と GitHub から SDK を取得します。外向き通信と、およそ 2 GB のメモリが必要です。

残るもの:

- ボリューム `webtoapp-generated` — アプリ、履歴、コミュニティのデータベース
- `./certs` — アプリごとの Android 鍵と、任意の iOS PEM（`ios-cert.pem`、`ios-key.pem`、`ios-chain.pem`）

リバースプロキシを 8000 番へ向けます。プライベートアドレスのプロキシは `X-Forwarded-*` を信頼します。それ以外のアドレスなら `.env` に `DOCKER_TRUSTED_PROXY_CIDRS` を設定してください。

Android ツールチェーンなしの小さいイメージ（Android は PWA zip になります）:

```bash
WITH_ANDROID=0 docker compose up -d --build
```

更新:

```bash
git pull
docker compose up -d --build
```

## 6. サービスとして実行（systemd）

シークレットは unit にインラインで書かず、権限を絞った環境ファイルに保存します：

```bash
# /path/to/WebToApp/webtoapp.env  （chmod 600）
PUBLIC_BASE_URL=https://your-domain.com
# 必要に応じて R2_* / IOS_* / CLOUDFLARE_* を追加
```

```ini
# /etc/systemd/system/webtoapp.service
[Unit]
Description=WebToApp
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/WebToApp
EnvironmentFile=/path/to/WebToApp/webtoapp.env
ExecStart=/path/to/WebToApp/venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo chmod 600 /path/to/WebToApp/webtoapp.env
sudo systemctl daemon-reload
sudo systemctl enable --now webtoapp
sudo systemctl status webtoapp
```

> `--workers 1` を維持してください。ビルドキューとメモリ内レートリミッターは単一プロセスを前提としています。

## 7. リバースプロキシ（Nginx）

アプリは自前で静的フロントエンドを配信するため、Nginx はすべてを Uvicorn ポートへプロキシするだけです：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 25m;   # カスタムアイコンのアップロード

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # APK ビルドは時間がかかることがあります
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 8. HTTPS

iOS Web Clip と `.mobileconfig` プロファイルは HTTPS が必須です。よくある 2 つの方法：

**方法 A — Cloudflare Tunnel**（インバウンドポート開放不要、無料 TLS）：

```bash
cloudflared tunnel login
cloudflared tunnel create webtoapp
# ホスト名をトンネルにルーティングし、http://127.0.0.1:8000 に向ける
cloudflared tunnel route dns webtoapp your-domain.com
cloudflared tunnel run webtoapp
```

**方法 B — Nginx 上の Let's Encrypt：**

```bash
sudo certbot --nginx -d your-domain.com
```

いずれの場合も `PUBLIC_BASE_URL=https://your-domain.com` を設定します。

## 9. Android APK ビルド（任意）

実際にインストール可能な WebView APK を生成するには、サーバーに Android ビルドツールが必要です：

- `aapt2`、`d8`、`apksigner`、`zipalign` を含む Android SDK
- `apktool`
- `java`、`javac`、`keytool` を提供する JDK

自動検出されない場合は `ANDROID_HOME` / `ANDROID_SDK_ROOT` で SDK を指定します。生成される各アプリは**独自の**署名証明書（`ANDROID_KEYSTORE_DIR` に保存）を持つため、更新を上書きインストールできます。

**SDK が無い場合**、APK 生成はスキップされ、Android ユーザーは代わりにインストール可能な PWA パッケージを取得します。他の機能はそのまま動作します。

## 10. iOS プロファイル署名（任意）

デフォルトでは iOS の `.mobileconfig` は未署名です（iOS はインストール可能ですが「未検証」と表示）。iOS に提供元としてあなたのドメインを表示させるには、`IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` で公的 CA 証明書を指定するか、`certs/ios-cert.pem`、`certs/ios-key.pem`、`certs/ios-chain.pem` を配置します。署名にはシステムの `openssl` を使用します。[`certs/README.md`](../certs/README.md) を参照。

## 11. Cloudflare R2 オフロード（任意）

### 仕組み

生成されるインストーラ（APK / ZIP / `.mobileconfig`）は大きくなりがちで、毎回オリジンから配信すると帯域を消費します。R2 を有効にすると：

1. **ビルドごとに**、`generated/<app_id>/downloads/` 内の各ファイルが `<app_id>/downloads/<ファイル名>` というキーで R2 にミラーされ（`server/engine/storage.py`）、得られた公開 URL がアプリの `recipe.json` に `downloads_cdn` マップとして書き込まれます。
2. **ダウンロード時**、`GET /a/<id>/download/<platform>` は `downloads_cdn` の CDN URL を優先し、R2 への **302 リダイレクト**を返します。無ければローカルファイルの配信にフォールバックします。よってオリジンはビルド時に CPU を使うだけで、共有や QR スキャンのたびに帯域を消費しません。
3. **クリーンアップ時**、アプリが回収されると `<app_id>/` 配下のオブジェクトも R2 から削除されます。

いずれかの `R2_*` 変数が未設定なら機能は無効化され、ダウンロードはローカル配信になります。壊れません。R2 有効化前にビルドされた既存アプリは `python -m server.scripts.backfill_r2` で移行できます。

> **実装メモ：** R2 は S3 API を使い、認証は AWS Signature V4 です。重い `boto3`/`botocore` を導入せず、`server/engine/storage.py` が独自の SigV4 署名（標準ライブラリの `hmac`/`hashlib` のみ）を備え、アプリが既に使っている `httpx` でリクエストを送ります。そのため R2 オフロードに **AWS SDK は不要**です。署名実装は AWS 公式の SigV4 テストベクターで検証済みです（`python -m server.engine.storage`）。

### セットアップ

1. Cloudflare ダッシュボードで **R2** を開き、バケット（例 `webtoapp-downloads`）を作成。
2. **Manage R2 API Tokens → Create API Token** で **Object Read & Write** 権限を付与。**Access Key ID** と **Secret Access Key** をコピー（シークレットは一度しか表示されません）。
3. バケットを公開：バケットの **Settings → Public access**。手早く始めるなら **r2.dev** 開発 URL（`https://pub-xxxx.r2.dev`）を有効化、エッジキャッシュも得たいなら **カスタムドメイン**（例 `files.example.com`）を追加。
   > カスタムドメインは、バケットと**同じ Cloudflare アカウント**が管理するドメインである必要があります。
4. `webtoapp.env` に 5 つの変数を設定：

   ```bash
   R2_ACCOUNT_ID=...            # アカウント ID（hex）
   R2_BUCKET=webtoapp-downloads
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev   # または https://files.example.com
   ```
5. サービスを再起動。新しいビルドのダウンロードが R2 へリダイレクトされます。

> **r2.dev とカスタムドメイン：** `pub-xxxx.r2.dev` は既に Cloudflare のグローバルエッジから配信されます。カスタムドメインはエッジ**キャッシュ**を追加し（同一ファイルの再ダウンロードは R2 に当たらずキャッシュから配信）、トラフィックが多いほど有利です。

### 既存アプリのバックフィル

R2 有効化前にビルドされたアプリはまだローカルファイルを指しています。それらの成果物を R2 にアップロードし、`downloads_cdn` を一括更新：

```bash
set -a; . ./webtoapp.env; set +a
venv/bin/python -m server.scripts.backfill_r2 --dry-run   # プレビュー
venv/bin/python -m server.scripts.backfill_r2             # 実行
```

このスクリプトは冪等で、再実行しても安全です。

## 12. アップデート

```bash
git pull
source venv/bin/activate
pip install -r server/requirements.txt   # 依存が変わった場合
sudo systemctl restart webtoapp
```

フロントエンド資産（`css/`、`js/`）を変更した場合は、`index.html` の `?v=` クエリ文字列を更新し、ブラウザがキャッシュではなく新しいファイルを取得するようにします。

## 13. トラブルシューティング

| 症状 | 想定原因 / 対処 |
| --- | --- |
| iPhone が全画面でなく Safari でページを開く | `PUBLIC_BASE_URL` 未設定、または HTTPS でない。 |
| Android のダウンロードが APK でなく PWA zip | サーバーに Android SDK / apktool 未インストール（§9）。 |
| ダウンロードがまだオリジンから配信される | `R2_*` 変数の欠落、または設定後に未再起動。既存アプリはバックフィル要（§11）。 |
| iOS プロファイルが「未検証」と表示 | プロファイルが未署名。公的 CA 証明書を提供（§10）。 |
| `502 Bad Gateway` | サービス未起動かポート誤り——`systemctl status webtoapp`。 |
| ビルドエンドポイントが `429` を返す | デバイスごとの日次クォータまたは IP ごとのレート制限に到達。`DAILY_BUILD_QUOTA` を調整。 |

---

プロジェクトの概要は [README](README.ja.md) も参照してください。

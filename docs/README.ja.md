<div align="center">

<img src="../assets/site-logo.jpg" alt="WebToApp" width="120" height="120" style="border-radius: 24px;">

# WebToApp

**あらゆるウェブサイトを、数秒でインストール可能なアプリに。**

リンクを一つ入れるだけで、**iPhone / iPad · Android · Windows · macOS · Linux** 向けの完成品が出てきます——さらに公開アプリマーケット、クリエイタープロフィール、コメントと評価付き。登録は不要です。

[![ライブデモ](https://img.shields.io/badge/ライブデモ-shiaho.sbs-c97953?style=for-the-badge)](https://shiaho.sbs)
[![CI](https://img.shields.io/badge/CI-pytest%20336-059669?style=for-the-badge)](https://github.com/shiaho777/WebToApp/actions)
[![ライセンス: MIT](https://img.shields.io/badge/License-MIT-1e1914?style=for-the-badge)](../LICENSE)
[![プラットフォーム](https://img.shields.io/badge/プラットフォーム-5-736357?style=for-the-badge)](#生成されるもの)

[English](../README.md) · [简体中文](README.zh.md) · **日本語** · [العربية](README.ar.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Português](README.pt.md) · [Français](README.fr.md) · [Deutsch](README.de.md)

</div>

---

## 生成されるもの

URL を入力——または自分の `.html` / `.zip` をアップロード——するだけで、数秒後に全プラットフォーム対応のインストール可能な成果物が得られます。各成果物はサイトを指す薄いネイティブシェルなので、サイズは **MB ではなく KB** 単位。ダウンロードもインストールもほぼ一瞬です。

生成されたアプリはすべて専用のダウンロードページ `/a/<id>` を持ちます：プラットフォーム別インストール項目、クリエイターが内容を書き込める折りたたみ式「このページについて」、そしてコメントと星評価のコミュニティレイヤー。公開リンクとして発行すれば、**アプリマーケット**にも掲載されます。

オープンソース · 無料 · 登録不要。ライブで試す：**[shiaho.sbs](https://shiaho.sbs)**。

---

## スクリーンショット

<p align="center"><img src="assets/shots/landing.png" alt="ランディングページ：リンクを貼るだけ。生成数・ダウンロード数・閲覧数はライブカウンター" width="820"></p>
<p align="center"><em>リンクを貼る（または HTML ファイルをドロップ）——カウンターはすべてリアルタイム。</em></p>

<p align="center"><img src="assets/shots/config-about.png" alt="アプリ設定：名前、説明、About セクションのテキストと最大 3 枚の自動圧縮画像" width="820"></p>
<p align="center"><em>名前、一行説明、クリエイターが書く About セクション（最大 3 枚の画像付き）——800KB 超はほぼ無劣化で自動圧縮。</em></p>

<p align="center"><img src="assets/shots/config-platforms.png" alt="テーマカラー、復元されたアイコン、Android 没入モードなどのプラットフォーム別設定" width="820"></p>
<p align="center"><em>テーマカラーとアイコンはサイトから自動復元。Android の没入フルスクリーンなど、プラットフォーム別の切替も可能。</em></p>

<p align="center"><img src="assets/shots/config-publish.png" alt="生成前のリンク公開範囲と必須タグ" width="820"></p>
<p align="center"><em>非公開リンクかマーケット公開か——タグは必須で、アプリの発見性を担保します。</em></p>

<p align="center"><img src="assets/shots/download-page.png" alt="生成されたダウンロードページ：評価、クリエイターカード、コメント、プラットフォーム別インストールリスト" width="820"></p>
<p align="center"><em>生成されたアプリページ：右にインストールリスト、左に評価・クリエイター・コメント。</em></p>

<p align="center"><img src="assets/shots/about-fold.png" alt="展開された「このページについて」——クリエイターのテキストとアップロード画像" width="820"></p>
<p align="center"><em>「このページについて」にはクリエイター自身の文章と画像が入ります——定型文の埋め草はありません。</em></p>

<p align="center"><img src="assets/shots/market.png" alt="公開アプリマーケット：すべてのカードに作成者、タグ、相対時刻、評価" width="820"></p>
<p align="center"><em>公開マーケット：クリエイターカード、タグ絞り込み、検索、最新 / 高評価順 / ダウンロード順 / 閲覧順の並び替え。</em></p>

<p align="center"><img src="assets/shots/history.png" alt="デバイスごとのビルド履歴：訪問統計、エクスポートとインポート" width="820"></p>
<p align="center"><em>履歴はデバイスフィンガープリントに紐付き——訪問統計、再生成、デバイス間のエクスポート/インポートに対応。</em></p>

---

## 仕組み

<p align="center"><img src="assets/fig-pipeline.svg" alt="パイプライン：URL または HTML 入力 → 解析 + recipe → 5 プラットフォーム並行ビルド → コミュニティ付きアプリページ" width="800"></p>

1. **入力**——ウェブサイトの URL を貼るか、単一の `.html` / `index.html` を含む `.zip` をアップロード。アップロードされた HTML はサーバー上で `/a/<id>/site/...` としてホストされ、URL アプリと同じ手順でパッケージ化されます。
2. **解析 + recipe**——アナライザーがページを取得し、名前・テーマカラー・アイコン（複数候補から最高解像度を採用）を抽出。ビルドに必要な情報はすべて `recipe.json` に固定されます。
3. **並行ビルド**——5 プラットフォーム分のパッケージを同時に生成。どれか一つが失敗しても（例：Android ツールチェーン未導入）そのプラットフォームだけが縮退します。
4. **アプリページ**——ダウンロードページにプラットフォーム別インストール項目、クリエイターの About コンテンツ、コミュニティブロックが描画されます。

## 機能

- **2 つの入力モード**：ウェブサイト URL、または自分の HTML（`.html` 単体または `index.html` 入り `.zip`）——ホスト＆パッケージ化は URL アプリと同一です。
- **サイト解析**：名前、テーマカラー、最高解像度アイコン、広告/トラッカー/ポップアップ数（表示用の推定値）。
- **マルチプラットフォーム**：1 ビルド → 5 成果物：
  - **Android** — 実際にインストール可能な WebView APK（v1+v2+v3 署名）。アプリごとに**専用署名証明書**。
  - **iOS / iPadOS** — `.mobileconfig` Web Clip プロファイル。公開 CA 証明書による CMS 署名（「署名不要」インストール）も可能。
  - **macOS** — 単体で動く WKWebView `.app` ウィンドウ（アドレスバーなし、サードパーティブラウザ不要）。
  - **Windows / Linux** — システムブラウザをアプリモードで開く軽量 `.bat` / `.desktop` ランチャー。
- **クリエイターによる About セクション**：リッチテキスト＋最大 3 枚の画像。アップロードはデコード検証・EXIF 除去・WebP 再エンコードされ、800KB 超はサーバー側でほぼ無劣化圧縮。
- **アカウント不要のコミュニティ**：デバイスフィンガープリントが永続的な公開 ID（`?u=N`）に。名前・Markdown プロフィール・アバターは編集可能。発行したアプリにはクリエイターカードが付き、公開プロフィールページも持てます。
- **コメントと評価**：各アプリページにコメント欄があり、任意で 1〜5 星の評価を付けられます。平均点はマーケットカードに反映。
- **公開アプリマーケット**：タグ絞り込み、検索、最新 / 高評価（平均→件数）/ ダウンロード数 / 閲覧数の並び替え——相対時刻表示。
- **iOS の動的 URL 切替**：Web Clip は `/a/<id>/launch` を指すため、再インストールなしでサーバー側から遷移先を変更可能。
- **デバイスごとの履歴**：ビルドはデバイスフィンガープリントに保存され、訪問/ダウンロード統計、再生成、エクスポート/インポートに対応。削除すればアプリ本体も完全に消えます。
- **自動クリーンアップ**：30 日間アクセスのないアプリは自動で回収。
- **任意の Cloudflare R2 オフロード**：ダウンロードを CDN にリダイレクトし、オリジンの帯域を節約。
- **多言語 UI**：9 言語——English、简体中文、日本語、العربية（RTL）、Русский、Español、Português、Français、Deutsch——生成されるダウンロードページもローカライズ済み。

## 登録不要のコミュニティ

<p align="center"><img src="assets/fig-community.svg" alt="デバイスフィンガープリントが連番の公開ユーザー ID になり、作成者表記・プロフィール・コメント・評価が使える" width="800"></p>

登録はありません：デバイスが初めて現れた時点で、フィンガープリントに連番の公開番号が割り当てられます。その `#N` が実際のプロフィールになります——表示名、Markdown 自己紹介、アバターを設定すれば、公開したすべてのアプリにクリエイターカードが付きます。他のユーザーは `?u=N` であなたの公開プロフィールと発行済みアプリを見られます。コメントには任意の星評価を付けられ、マーケットのカードに反映されます。

## アプリサイズ

各パッケージはサイトへの薄い入り口——サイトの中身を同梱しないため、サイズは **MB ではなく KB** 単位です。

<p align="center"><img src="assets/fig-sizes.svg" alt="実測パッケージサイズ：macOS 135KB、Android 21KB、iOS 4KB、Windows 1.2KB、Linux 0.7KB" width="760"></p>

| プラットフォーム | パッケージ | 標準サイズ | 中身 |
| --- | --- | --- | --- |
| Android | `android.apk` | **~21 KB** | 実際にインストール可能な WebView APK（v1+v2+v3 署名） |
| iOS / iPadOS | `ios.mobileconfig` | **~4 KB** | Web Clip 構成プロファイル |
| macOS | `macos.zip` | **~135 KB** | `.app` バンドル（ネイティブ WKWebView ウィンドウ + アイコン） |
| Windows | `windows.zip` | **~1.2 KB** | `.bat` ランチャー + ショートカット補助 + アイコン |
| Linux | `linux.tar.gz` | **~0.7 KB** | `.desktop` エントリ + インストールスクリプト + アイコン |

## 技術スタック

- バックエンド：Python + FastAPI + Uvicorn · SQLite ストア（履歴・タスク・コミュニティ）
- フロントエンド：素の HTML / CSS / JS——ビルドステップなし、バックエンドから直接配信
- パッケージング：Android SDK（aapt2 / d8 / apktool / apksigner / zipalign）、Pillow、openssl
- CI：`pytest tests/` を Python 3.10 / 3.11 / 3.12 で実行——**336 テスト**

## プロジェクト構成

```
.
├── index.html                 ランディングページ + ビルドフォーム
├── css/ js/ assets/           フロントエンド静的アセット
│   ├── js/i18n.js             軽量 i18n ランタイム（9 言語）
│   ├── js/i18n.strings.js     全翻訳
│   ├── js/community.js        アプリページのコメント/評価/クリエイターブロック
│   └── js/mdmini.js           自己紹介用の極小 Markdown レンダラー
├── server/
│   ├── main.py                FastAPI アプリとルート（35 エンドポイント）
│   ├── config.py              環境変数による設定
│   ├── html_site.py           HTML アップロードのステージング/検証/配信
│   ├── history_store.py       デバイス別履歴 + アプリ/訪問統計（SQLite）
│   ├── community_store.py     プロフィール・作成者・コメント・評価（SQLite）
│   ├── task_store.py          ビルドタスクキューの永続化（SQLite）
│   └── engine/
│       ├── analyzer.py        サイト解析
│       ├── distiller.py       recipe → 各プラットフォームのパッケージ + ダウンロードページ（中核）
│       ├── apk_builder.py     Android APK のビルドと署名
│       ├── mobileconfig_signer.py  iOS プロファイル署名
│       ├── cache.py           取得/アイコンキャッシュ
│       └── storage.py         Cloudflare R2 オフロード
├── certs/                     署名用素材（秘密鍵はコミットしない）
└── generated/                 実行時に生成されるアプリとデータ（コミットしない）
```

## クイックスタート

Python 3.10+ が必要です。Android APK のビルドには Android SDK と `apktool` が必要です（無い場合は PWA オフラインパッケージにフォールバック）。

```bash
# 1. 仮想環境を作成して依存関係をインストール
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt

# 2. 設定（任意、すべてデフォルトあり）
cp .env.example .env
# 必要に応じて .env を編集

# 3. 起動
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

http://127.0.0.1:8000 を開きます。

> ローカル開発では環境変数は不要です。公開デプロイでは `PUBLIC_BASE_URL` を設定してください。
> さもないと iPhone が `localhost` を開けません。全一覧は [`.env.example`](../.env.example) を参照。

## デプロイ

> 完全なステップバイステップの本番ガイド（systemd、Nginx、HTTPS、Android/iOS、R2）は **[DEPLOY.md](DEPLOY.md)** を参照。

本番では systemd 下で Nginx リバースプロキシの後ろに置くのが一般的です：

```ini
# /etc/systemd/system/webtoapp.service
[Unit]
Description=WebToApp
After=network.target

[Service]
WorkingDirectory=/path/to/web-to-app
Environment=PUBLIC_BASE_URL=https://your-domain.com
ExecStart=/path/to/web-to-app/venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

iOS プロファイル署名（「署名不要」インストール）の証明書設定は [`certs/README.md`](../certs/README.md) を参照。

## Cloudflare R2 オフロードの仕組み

生成されるインストーラーは大きくなることがあり、すべてのダウンロードをオリジンで捌くと帯域を消費します。R2 を設定すると：

1. **各ビルド後**、`generated/<app_id>/downloads/` 内の全ファイルが `<app_id>/downloads/<filename>` というキーで R2 にミラーされ（`server/engine/storage.py`）、その公開 URL がアプリの `recipe.json` の `downloads_cdn` マップに書き込まれます。
2. **ダウンロード時**、`GET /a/<id>/download/<platform>` は `downloads_cdn` の CDN URL を優先し、R2 へ **302 リダイレクト**。無ければローカルファイルのストリームにフォールバック。オリジンはビルド時に CPU を使うだけで、共有や QR スキャンのたびに帯域を消費しません。
3. **クリーンアップ時**、R2 上の `<app_id>/` 以下のオブジェクトもローカルデータと一緒に削除されます。

`R2_*` 変数が一つでも未設定ならこの機能は no-op で、ダウンロードはローカル配信のまま——何も壊れません。R2 有効化以前に作られた既存アプリは `python -m server.scripts.backfill_r2` で移行できます。完全な設定手順（バケット、API トークン、公開アクセス、カスタムドメイン、バックフィル）は [DEPLOY.md §11](DEPLOY.md#11-cloudflare-r2-offload-optional) にあります。

## セキュリティ上の注意

- すべてのシークレット（R2、Cloudflare、署名パスワード）は環境変数から読み込まれ、リポジトリに実際の認証情報は含まれません。
- **署名用秘密鍵（`certs/*.keystore`、`certs/app-keys/`）と実行時データ（`generated/`）は `.gitignore` で除外済み——絶対にコミットしないでください。**
- 生成される Android アプリはそれぞれ独立した署名証明書を使うため、証明書フィンガープリントが一括でフラグされることを防ぎ、同一アプリのインプレース更新も可能です。
- クリエイターがアップロードする About 画像は Pillow でデコード検証され、生サイズ・ピクセル数・枚数の上限で制限され、全メタデータを剥がして WebP に再エンコードされます——アップロードされた生データがそのまま配信されることはありません。
- ユーザー生成テキストは描画時にすべて HTML エスケープ。アプリ内メディアのルートはサーバー生成ファイル名のみを許可リストします。

## ライセンス

[MIT](../LICENSE)

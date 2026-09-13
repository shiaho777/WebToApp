<div align="center">

<img src="assets/site-logo.jpg" alt="WebToApp" width="120" height="120" style="border-radius: 24px;">

# WebToApp

**Turn any website into an installable app — in seconds.**

One link in, finished products out for **iPhone / iPad · Android · Windows · macOS · Linux** — plus a public app market, creator profiles, comments and ratings, all without sign-up.

[![Live Demo](https://img.shields.io/badge/Live_Demo-shiaho.sbs-c97953?style=for-the-badge)](https://shiaho.sbs)
[![CI](https://img.shields.io/badge/CI-pytest%20336-059669?style=for-the-badge)](https://github.com/shiaho777/WebToApp/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-1e1914?style=for-the-badge)](LICENSE)
[![Platforms](https://img.shields.io/badge/Platforms-5-736357?style=for-the-badge)](#what-you-get)

**English** · [简体中文](docs/README.zh.md) · [日本語](docs/README.ja.md) · [العربية](docs/README.ar.md) · [Русский](docs/README.ru.md) · [Español](docs/README.es.md) · [Português](docs/README.pt.md) · [Français](docs/README.fr.md) · [Deutsch](docs/README.de.md)

</div>

---

<p align="center"><img src="docs/assets/fig-stats.svg" alt="WebToApp at a glance: 5 platforms, 9 languages, 336 tests" width="760"></p>

## What you get

Enter a URL — or upload your own `.html` / `.zip` — and seconds later you get an installable result covering every major platform. Each artifact is a thin native shell pointing at your site, so packages are measured in **kilobytes, not megabytes**, and download almost instantly.

Every generated app lives at its own download page `/a/<id>`: platform picks, a foldable "About this page" section the creator can fill with real content, and a community layer with comments and star ratings. Publish it as a public link and it also appears in the **app market** for everyone to find.

Open source · Free · No sign-up. Try it live at **[shiaho.sbs](https://shiaho.sbs)**.

---

## Screenshots

<p align="center"><img src="docs/assets/shots/landing.png" alt="Landing page: paste a link, get started — live counters for generated apps, downloads and views" width="820"></p>
<p align="center"><em>Paste a link (or drop an HTML file) — the counters are live.</em></p>

<p align="center"><img src="docs/assets/shots/config-about.png" alt="App configuration: name, description, about-section text and up to 3 auto-compressed images" width="820"></p>
<p align="center"><em>Name, one-line description, and the creator-written About section with up to 3 images — anything over 800KB is compressed near-losslessly.</em></p>

<p align="center"><img src="docs/assets/shots/config-platforms.png" alt="Theme color, recovered icon, and per-platform settings with Android immersive mode" width="820"></p>
<p align="center"><em>Theme color and icon recovered from the site; per-platform toggles like Android immersive fullscreen.</em></p>

<p align="center"><img src="docs/assets/shots/config-publish.png" alt="Link visibility and required tags before generating" width="820"></p>
<p align="center"><em>Private by default or public on the market — tags are required so apps stay discoverable.</em></p>

<p align="center"><img src="docs/assets/shots/download-page.png" alt="Generated download page: rating, creator card, comments, and per-platform install list" width="820"></p>
<p align="center"><em>The generated app page: install list on the right, rating / creator / comments on the left.</em></p>

<p align="center"><img src="docs/assets/shots/about-fold.png" alt="The About fold expanded, showing creator text and an uploaded image" width="820"></p>
<p align="center"><em>The "About this page" fold carries the creator's own text and images — no boilerplate filler.</em></p>

<p align="center"><img src="docs/assets/shots/market.png" alt="Public app market with creator attribution, tags, relative time and ratings on every card" width="820"></p>
<p align="center"><em>The public market: creator cards, tag filters, search, and newest / top-rated / most-downloaded / most-visited sorting.</em></p>

<p align="center"><img src="docs/assets/shots/history.png" alt="Per-device build history with visit stats, export and import" width="820"></p>
<p align="center"><em>Your history stays on your device fingerprint — with visit stats, regenerate, and export/import across devices.</em></p>

---

## How it works

<p align="center"><img src="docs/assets/fig-pipeline.svg" alt="Pipeline: URL or HTML input → analyze + recipe → five parallel platform builds → app page with community" width="800"></p>

1. **Input** — paste a website URL, or upload a single `.html` file / `.zip` bundle containing `index.html`. Uploaded HTML is hosted by the server under `/a/<id>/site/...` and packaged exactly like a URL app.
2. **Analyze + recipe** — the analyzer fetches the page and extracts the name, theme color and icon (multi-candidate fetch, highest resolution wins), then everything the build needs is pinned into a `recipe.json`.
3. **Parallel builds** — all five platform packages build concurrently; a failure in one (e.g. Android toolchain missing) degrades that platform only.
4. **App page** — the download page renders install entries per platform, the creator's About content, and the community block.

## Features

- **Two input modes**: website URL, or your own HTML (`.html` file or `.zip` with `index.html` inside) — hosted and packaged like any URL app.
- **Site analysis**: name, theme color, best-resolution icon, and ad/tracker/popup counts (display-only estimates).
- **Multi-platform packaging**, one build → five artifacts:
  - **Android** — a real, installable WebView APK (v1+v2+v3 signed), each app with its **own dedicated signing certificate**.
  - **iOS / iPadOS** — a `.mobileconfig` Web Clip profile, optionally CMS-signed with a public-CA certificate ("signature-free" install).
  - **macOS** — a standalone WKWebView `.app` window (no address bar, no third-party browser).
  - **Windows / Linux** — lightweight `.bat` / `.desktop` launchers that open the system browser in app mode.
- **Creator-authored About section**: rich text plus up to 3 images on every app page. Uploads are decode-verified, EXIF-stripped and re-encoded to WebP — anything over 800KB is auto-compressed near-losslessly server-side.
- **Community without accounts**: a device fingerprint becomes a persistent public identity (`?u=N`) — editable name, Markdown bio and avatar. Creators are credited on their apps and get a public profile page.
- **Comments & ratings**: every app page has a comment thread with optional 1–5 star ratings; averages roll up onto market cards.
- **Public app market**: tag filters, search, and sorting by newest, top-rated (avg → count), most downloaded or most visited — with relative timestamps.
- **iOS dynamic URL swap**: the Web Clip points at `/a/<id>/launch`, so the target URL can change server-side without reinstalling.
- **Per-device history**: builds are saved against the device fingerprint with visit/download stats, regenerate, and export / import across devices. Deleting an entry fully removes the app.
- **Auto cleanup**: apps with no visits for 30 days are reclaimed automatically.
- **Optional Cloudflare R2 offload**: downloads redirect to the CDN, saving origin bandwidth.
- **Multilingual UI**: 9 languages — English, 简体中文, 日本語, العربية (RTL), Русский, Español, Português, Français, Deutsch — with the generated download pages localized too.

## Community without sign-up

<p align="center"><img src="docs/assets/fig-community.svg" alt="Device fingerprint becomes a sequential public user ID unlocking creator attribution, profiles, comments and ratings" width="800"></p>

There is no registration: the first time a device shows up, its fingerprint is assigned a sequential public number. That `#N` becomes a real profile — set a display name, a Markdown bio and an avatar, and every app you publish carries your creator card. Other users open `?u=N` to see your public profile and the apps you published. Comments support optional star ratings, and the market reflects them on every card.

## App size

Each package is a thin entry point to your site — it bundles no site content, so the artifacts are measured in **kilobytes, not megabytes**.

<p align="center"><img src="docs/assets/fig-sizes.svg" alt="Measured package sizes: macOS 135KB, Android 21KB, iOS 4KB, Windows 1.2KB, Linux 0.7KB" width="760"></p>

| Platform | Package | Typical size | What's inside |
| --- | --- | --- | --- |
| Android | `android.apk` | **~21 KB** | A real, installable WebView APK (v1+v2+v3 signed) |
| iOS / iPadOS | `ios.mobileconfig` | **~4 KB** | A Web Clip configuration profile |
| macOS | `macos.zip` | **~135 KB** | A `.app` bundle (native WKWebView window + icon) |
| Windows | `windows.zip` | **~1.2 KB** | A `.bat` launcher + desktop-shortcut helper + icon |
| Linux | `linux.tar.gz` | **~0.7 KB** | A `.desktop` entry + install script + icon |

## Tech stack

- Backend: Python + FastAPI + Uvicorn · SQLite stores (history, tasks, community)
- Frontend: plain HTML / CSS / JS — no build step, served directly by the backend
- Packaging: Android SDK (aapt2 / d8 / apktool / apksigner / zipalign), Pillow, openssl
- CI: `pytest tests/` on Python 3.10 / 3.11 / 3.12 — **336 tests**

## Project structure

```
.
├── index.html                 Landing page + build form
├── css/ js/ assets/           Frontend static assets
│   ├── js/i18n.js             Lightweight i18n runtime (9 languages)
│   ├── js/i18n.strings.js     All translations
│   ├── js/community.js        Comments / ratings / creator block on app pages
│   └── js/mdmini.js           Tiny Markdown renderer for bios
├── server/
│   ├── main.py                FastAPI app and routes (35 endpoints)
│   ├── config.py              Environment-variable configuration
│   ├── html_site.py           HTML-upload staging / validation / serving
│   ├── history_store.py       Per-device history + app/visit stats (SQLite)
│   ├── community_store.py     Profiles, creators, comments, ratings (SQLite)
│   ├── task_store.py          Build task queue persistence (SQLite)
│   └── engine/
│       ├── analyzer.py        Site analysis
│       ├── distiller.py       Recipe → packages + download page (core)
│       ├── apk_builder.py     Android APK build and signing
│       ├── mobileconfig_signer.py  iOS profile signing
│       ├── cache.py           Fetch/icon caches
│       └── storage.py         Cloudflare R2 offload
├── certs/                     Signing material (private keys are not committed)
└── generated/                 Runtime-generated apps and data (not committed)
```

## Quick start

Requires Python 3.10+. Building an Android APK needs the Android SDK and `apktool` (it falls back to a PWA offline package when they are missing).

```bash
# 1. Create a virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt

# 2. Configure (optional, everything has defaults)
cp .env.example .env
# Edit .env as needed

# 3. Run
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000.

> No environment variables are needed for local development. When deploying publicly, set `PUBLIC_BASE_URL`,
> otherwise iPhones cannot open `localhost`. See [`.env.example`](.env.example) for the full list.

## Deployment

> For a complete step-by-step production guide (systemd, Nginx, HTTPS, Android/iOS, R2), see **[docs/DEPLOY.md](docs/DEPLOY.md)**.

In production it is common to run it under systemd, behind an Nginx reverse proxy:

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

For iOS profile signing ("signature-free" install), see the certificate setup in [`certs/README.md`](certs/README.md).

## How Cloudflare R2 offload works

Generated installers can be large, and serving every download from the origin burns its bandwidth. When R2 is configured:

1. **After each build**, every file in `generated/<app_id>/downloads/` is mirrored to R2 under the key `<app_id>/downloads/<filename>` (`server/engine/storage.py`), and the resulting public URLs are written into the app's `recipe.json` as a `downloads_cdn` map.
2. **On download**, `GET /a/<id>/download/<platform>` prefers the CDN URL in `downloads_cdn` and returns a **302 redirect** to R2; if absent, it falls back to streaming the local file. The origin therefore spends CPU during builds, not bandwidth on every share or QR scan.
3. **On cleanup**, an app's objects under `<app_id>/` are removed from R2 alongside its local data.

If any `R2_*` variable is unset the feature is a no-op and downloads are served locally — nothing breaks. Existing apps built before R2 was enabled can be migrated with `python -m server.scripts.backfill_r2`. Full setup steps (bucket, API token, public access, custom domain, backfill) are in [docs/DEPLOY.md §11](docs/DEPLOY.md#11-cloudflare-r2-offload-optional).

## Security notes

- All secrets (R2, Cloudflare, signing passwords) are read from environment variables; the repository contains no real credentials.
- **Signing private keys (`certs/*.keystore`, `certs/app-keys/`) and runtime data (`generated/`) are excluded by `.gitignore` by default — never commit them.**
- Each generated Android app uses its own independent signing certificate, which avoids the certificate fingerprint being flagged en masse and ensures the same app can be updated in place.
- Creator-uploaded about-images are decode-verified with Pillow, bounded by raw-size / pixel-count / count caps, stripped of all metadata and re-encoded to WebP — never served as uploaded.
- User-generated text is HTML-escaped on render; app-scoped media routes allowlist server-generated filenames only.

## License

[MIT](LICENSE)

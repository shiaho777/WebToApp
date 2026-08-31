<div align="center">

# WebToApp — Deployment Guide

**English** · [简体中文](DEPLOY.zh.md) · [日本語](DEPLOY.ja.md) · [العربية](DEPLOY.ar.md) · [Русский](DEPLOY.ru.md) · [Español](DEPLOY.es.md) · [Português](DEPLOY.pt.md) · [Français](DEPLOY.fr.md) · [Deutsch](DEPLOY.de.md)

A step-by-step guide to running WebToApp in production.

</div>

---

## Contents

1. [Requirements](#1-requirements)
2. [Get the code](#2-get-the-code)
3. [Python environment](#3-python-environment)
4. [Configuration](#4-configuration)
5. [Run locally](#5-run-locally)
6. [Run as a service (systemd)](#6-run-as-a-service-systemd)
7. [Reverse proxy (Nginx)](#7-reverse-proxy-nginx)
8. [HTTPS](#8-https)
9. [Android APK builds (optional)](#9-android-apk-builds-optional)
10. [iOS profile signing (optional)](#10-ios-profile-signing-optional)
11. [Cloudflare R2 offload (optional)](#11-cloudflare-r2-offload-optional)
12. [Updating](#12-updating)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Requirements

- **Python 3.10+**
- A Linux server (any distro). 1 vCPU / 1 GB RAM is enough to start.
- Outbound internet access (the analyzer fetches target sites).
- Optional, only for real Android APK builds: **Android SDK** (`aapt2`, `d8`, `apksigner`, `zipalign`), **apktool**, a **JDK** (`java` / `javac` / `keytool`). Without them, Android falls back to an installable PWA package.
- Optional, only for iOS profile signing: **openssl** (present on virtually every Linux box).

The only hard dependency is Python. Everything else is optional and degrades gracefully.

## 2. Get the code

```bash
git clone https://github.com/shiahonb777/WebToApp.git
cd WebToApp
```

## 3. Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

This installs the four runtime dependencies: `fastapi`, `uvicorn[standard]`, `httpx`, `Pillow`. Cloudflare R2 offload (optional) needs no extra package — see §11.

## 4. Configuration

All configuration is read from environment variables — every one is optional with a sensible default.

```bash
cp .env.example .env
# edit .env
```

| Variable | Purpose | Default |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | Public origin, e.g. `https://app.example.com`. Required in production so iPhones don't try to open `localhost`. | inferred from Host header |
| `ANDROID_PACKAGE_PREFIX` | Default Android package prefix. | `com.webtoapp` |
| `ANDROID_KEYSTORE_DIR` | Where per-app signing keystores live. Keep it OUTSIDE any public path. | `certs/app-keys` |
| `DAILY_BUILD_QUOTA` | Per-device daily build limit (`0` disables). | `10` |
| `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` | Public-CA cert to sign iOS profiles. | unset (unsigned, still installable) |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_PUBLIC_BASE_URL` | Cloudflare R2 offload (see §11). | unset (downloads served locally) |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` | Eagerly purge the iOS `/launch` redirect from cache on URL swap. | unset |

> **Never commit your real `.env`.** It is git-ignored by default.

## 5. Run locally

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. For local development you don't need any environment variables.

## 6. Run as a service (systemd)

Run the service as a dedicated, unprivileged user — never as root. Any RCE in
the app then stops at an account that can only touch `generated/`, `certs/`
and the APK template/tools caches.

```bash
sudo useradd -r -s /sbin/nologin -d /var/lib/webtoapp -M webtoapp
sudo mkdir -p /var/lib/webtoapp/.local/share /var/lib/webtoapp/.cache
sudo chown -R webtoapp:webtoapp /var/lib/webtoapp
# Writable paths the service needs (adjust to your deploy root):
sudo chown -R webtoapp:webtoapp \
  /path/to/WebToApp/generated \
  /path/to/WebToApp/certs \
  /path/to/WebToApp/server/engine/_android_template \
  /path/to/WebToApp/server/engine/_android_tools
```

Keep secrets in a locked-down environment file instead of inline in the unit:

```bash
# /path/to/WebToApp/webtoapp.env  (chmod 600)
PUBLIC_BASE_URL=https://your-domain.com
# Shared secret for GET /api/metrics (unset = loopback-only access)
METRICS_TOKEN=change-me
# add R2_* / IOS_* / CLOUDFLARE_* here as needed
```

```ini
# /etc/systemd/system/webtoapp.service
[Unit]
Description=WebToApp
After=network.target

[Service]
User=webtoapp
Group=webtoapp
WorkingDirectory=/path/to/WebToApp
EnvironmentFile=/path/to/WebToApp/webtoapp.env
Environment=HOME=/var/lib/webtoapp
Environment=XDG_DATA_HOME=/var/lib/webtoapp/.local/share
Environment=XDG_CACHE_HOME=/var/lib/webtoapp/.cache
ExecStart=/path/to/WebToApp/venv/bin/uvicorn server.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5
# ---- hardening ----
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/path/to/WebToApp
ProtectHome=yes
ProtectKernelTunables=yes
ProtectControlGroups=yes
ProtectClock=yes
RestrictSUIDSGID=yes
RestrictRealtime=yes
LockPersonality=yes

[Install]
WantedBy=multi-user.target
```

> **HOME must point somewhere writable** (`/var/lib/webtoapp` above), and the
> project root itself should stay owned by root. apktool needs to create
> `~/.local/share/apktool` even when only *decoding*; when it cannot, it
> fails **silently** — decoded manifests come back with empty attribute
> values and every APK build falls back to the PWA ZIP. `ProtectHome=yes` is
> unaffected: it fences off `/home`, `/root` and `/run/user`, not
> `/var/lib/webtoapp`.
>
> Keep `--workers 1`. The build queue and in-memory rate limiter assume a
> single process.

```bash
sudo chmod 600 /path/to/WebToApp/webtoapp.env
sudo systemctl daemon-reload
sudo systemctl enable --now webtoapp
sudo systemctl status webtoapp
# Smoke-test a real build afterwards; "android.apk" must be present:
#   curl -s http://127.0.0.1:8000/healthz
```

## 7. Reverse proxy (Nginx)

The app serves its own static frontend, so Nginx only needs to proxy everything to the Uvicorn port:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 25m;   # custom icon uploads

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # APK builds can take a while
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 8. HTTPS

iOS Web Clips and `.mobileconfig` profiles require HTTPS. Two common options:

**Option A — Cloudflare Tunnel** (no open inbound ports, free TLS):

```bash
cloudflared tunnel login
cloudflared tunnel create webtoapp
# route a hostname to the tunnel, then point it at http://127.0.0.1:8000
cloudflared tunnel route dns webtoapp your-domain.com
cloudflared tunnel run webtoapp
```

**Option B — Let's Encrypt on Nginx:**

```bash
sudo certbot --nginx -d your-domain.com
```

Either way, set `PUBLIC_BASE_URL=https://your-domain.com`.

## 9. Android APK builds (optional)

To produce a real, installable WebView APK the server needs the Android build tools:

- Android SDK with `aapt2`, `d8`, `apksigner`, `zipalign`
- `apktool`
- a JDK providing `java`, `javac`, `keytool`

### One-shot install (Linux)

```bash
# root (or writable /opt and /usr/local/bin) required
sudo bash server/scripts/install_android_sdk.sh
```

The script installs to `/opt/android-sdk` (platform 36 + build-tools 36.0.0) and places
`apktool` at `server/engine/_android_tools/apktool.jar` plus `/usr/local/bin/apktool`.

Then set in your env file (or systemd `EnvironmentFile`):

```bash
ANDROID_HOME=/opt/android-sdk
ANDROID_SDK_ROOT=/opt/android-sdk
PATH=/opt/android-sdk/build-tools/36.0.0:/opt/android-sdk/platform-tools:/usr/local/bin:$PATH
```

Restart the service and check `/api/metrics` for `"android_apk": true`.

### Rebuild historical zip fallbacks into real APKs

If the server previously lacked the SDK, some apps only have `android.zip`. After the toolchain is ready:

```bash
# rebuild apps missing android.apk and upload to R2 when configured
python -m server.scripts.rebuild_android_apks

# first 20 only / specific app
python -m server.scripts.rebuild_android_apks --limit 20
python -m server.scripts.rebuild_android_apks --app-id abcd1234
```

Each generated app gets its **own** signing certificate (stored under `ANDROID_KEYSTORE_DIR`), so updates install in place.

**Without the SDK**, APK generation is skipped and Android users get an installable PWA package instead — everything else still works.

## 10. iOS profile signing (optional)

By default the iOS `.mobileconfig` is unsigned (iOS still installs it, just shows "Unverified"). To have iOS show your domain as the source, provide a public-CA certificate via `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE`, or drop `certs/ios-cert.pem`, `certs/ios-key.pem`, `certs/ios-chain.pem`. Signing uses the system `openssl`. See [`certs/README.md`](../certs/README.md).

## 11. Cloudflare R2 offload (optional)

### How it works

Generated installers (APK / ZIP / `.mobileconfig`) can be heavy, and serving every download from the origin burns its bandwidth. With R2 enabled:

1. **After each build**, every file in `generated/<app_id>/downloads/` is uploaded to R2 under the key `<app_id>/downloads/<filename>` (see `server/engine/storage.py`). The resulting public URLs are saved into the app's `recipe.json` as a `downloads_cdn` map.
2. **On download**, `GET /a/<id>/download/<platform>` checks `downloads_cdn`. If a CDN URL exists it returns a **302 redirect** to R2; otherwise it falls back to streaming the local file. So the origin only spends CPU during builds, not bandwidth on every share/QR scan.
3. **On cleanup**, when an app is reclaimed its objects under `<app_id>/` are deleted from R2 too.

If any R2 variable is unset, the whole feature becomes a no-op and downloads are served locally — nothing breaks.

> **Implementation note:** R2 speaks the S3 API, which authenticates with AWS Signature V4. Rather than pull in the heavy `boto3`/`botocore` stack, `server/engine/storage.py` ships its own SigV4 signer (standard-library `hmac`/`hashlib`) and sends requests over `httpx` — the same HTTP client the app already uses. So R2 offload needs **no AWS SDK**; the signer is validated against AWS's published SigV4 test vectors (`python -m server.engine.storage`).

### Setup

1. In the Cloudflare dashboard, open **R2** and create a bucket, e.g. `webtoapp-downloads`.
2. **Manage R2 API Tokens → Create API Token** with **Object Read & Write**. Copy the **Access Key ID** and **Secret Access Key** (the secret is shown only once).
3. Make the bucket public: bucket **Settings → Public access**. Either enable the **r2.dev** development URL (`https://pub-xxxx.r2.dev`) for a quick start, or add a **Custom Domain** (e.g. `files.example.com`) to also get edge caching.
   > A custom domain must be on a domain managed by **the same Cloudflare account** as the bucket.
4. Set the five variables in `webtoapp.env`:

   ```bash
   R2_ACCOUNT_ID=...            # your account ID (hex)
   R2_BUCKET=webtoapp-downloads
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev   # or https://files.example.com
   ```
5. Restart the service. New builds now redirect downloads to R2.

> **r2.dev vs custom domain:** `pub-xxxx.r2.dev` already serves from Cloudflare's global edge. A custom domain adds edge **caching** (repeat downloads of the same file are served from cache without hitting R2), which matters more at higher traffic.

### Backfill existing apps

Apps built before R2 was enabled still point at local files. Upload their artifacts to R2 and update their `downloads_cdn` in one pass:

```bash
set -a; . ./webtoapp.env; set +a
venv/bin/python -m server.scripts.backfill_r2 --dry-run   # preview
venv/bin/python -m server.scripts.backfill_r2             # run for real
```

The script is idempotent — safe to re-run.

## 12. Updating

```bash
git pull
source venv/bin/activate
pip install -r server/requirements.txt   # if dependencies changed
sudo systemctl restart webtoapp
```

If you changed frontend assets (`css/`, `js/`), bump the `?v=` query string in `index.html` so browsers fetch the new files instead of cached ones.

## 13. Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| iPhone opens the page in Safari instead of fullscreen | `PUBLIC_BASE_URL` not set, or not HTTPS. |
| Android download is a PWA zip, not an APK | Android SDK / apktool not installed on the server (see §9). |
| Downloads still served from origin | An `R2_*` variable is missing, or you didn't restart after setting them. Run the backfill for old apps (§11). |
| iOS profile shows "Unverified" | Profile is unsigned. Provide a public-CA cert (§10). |
| `502 Bad Gateway` | The service isn't running or the port is wrong — `systemctl status webtoapp`. |
| Build endpoint returns `429` | Per-device daily quota or per-IP rate limit hit. Tune `DAILY_BUILD_QUOTA`. |

---

See also the [README](../README.md) for an overview of the project.

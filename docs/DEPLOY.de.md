<div align="center">

# WebToApp — Bereitstellungsanleitung

[English](DEPLOY.md) · [简体中文](DEPLOY.zh.md) · [日本語](DEPLOY.ja.md) · [العربية](DEPLOY.ar.md) · [Русский](DEPLOY.ru.md) · [Español](DEPLOY.es.md) · [Português](DEPLOY.pt.md) · [Français](DEPLOY.fr.md) · **Deutsch**

Schritt-für-Schritt-Anleitung für den Produktivbetrieb von WebToApp.

</div>

---

## Inhalt

1. [Voraussetzungen](#1-voraussetzungen)
2. [Code beziehen](#2-code-beziehen)
3. [Python-Umgebung](#3-python-umgebung)
4. [Konfiguration](#4-konfiguration)
5. [Lokal ausführen](#5-lokal-ausführen)
   - [Docker](#docker)
6. [Als Dienst ausführen (systemd)](#6-als-dienst-ausführen-systemd)
7. [Reverse Proxy (Nginx)](#7-reverse-proxy-nginx)
8. [HTTPS](#8-https)
9. [Android-APK-Builds (optional)](#9-android-apk-builds-optional)
10. [iOS-Profil-Signierung (optional)](#10-ios-profil-signierung-optional)
11. [Cloudflare-R2-Auslagerung (optional)](#11-cloudflare-r2-auslagerung-optional)
12. [Aktualisieren](#12-aktualisieren)
13. [Fehlerbehebung](#13-fehlerbehebung)

---

## 1. Voraussetzungen

- **Python 3.10+**
- Ein Linux-Server (beliebige Distribution). 1 vCPU / 1 GB RAM reichen zum Start.
- Ausgehender Internetzugang (der Analyzer ruft die Zielseiten ab).
- Optional, nur für echte Android-APK-Builds: **Android SDK** (`aapt2`, `d8`, `apksigner`, `zipalign`), **apktool**, ein **JDK** (`java` / `javac` / `keytool`). Ohne sie fällt Android auf ein installierbares PWA-Paket zurück.
- Optional, nur für iOS-Signierung: **openssl** (auf praktisch jedem Linux vorhanden).

Die einzige zwingende Abhängigkeit ist Python. Alles andere ist optional und degradiert sanft.

## 2. Code beziehen

```bash
git clone https://github.com/shiaho777/WebToApp.git
cd WebToApp
```

## 3. Python-Umgebung

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

Damit werden die vier Laufzeit-Abhängigkeiten installiert: `fastapi`, `uvicorn[standard]`, `httpx`, `Pillow`. Das Cloudflare-R2-Offload (optional) braucht kein zusätzliches Paket — siehe §11.

## 4. Konfiguration

Die gesamte Konfiguration wird aus Umgebungsvariablen gelesen — jede ist optional mit sinnvollem Standardwert.

```bash
cp .env.example .env
# .env bearbeiten
```

| Variable | Zweck | Standard |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | Öffentlicher Origin, z. B. `https://app.example.com`. In Produktion erforderlich, sonst versucht das iPhone `localhost` zu öffnen. | aus Host-Header abgeleitet |
| `ANDROID_PACKAGE_PREFIX` | Standard-Android-Paketpräfix. | `com.webtoapp` |
| `ANDROID_KEYSTORE_DIR` | Wo die Signier-Keystores pro App liegen. AUSSERHALB jedes öffentlichen Pfads halten. | `certs/app-keys` |
| `DAILY_BUILD_QUOTA` | Tägliches Build-Limit pro Gerät (`0` deaktiviert). | `10` |
| `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` | Public-CA-Zertifikat zum Signieren von iOS-Profilen. | nicht gesetzt (unsigniert, trotzdem installierbar) |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_PUBLIC_BASE_URL` | Cloudflare-R2-Auslagerung (siehe §11). | nicht gesetzt (Downloads lokal) |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` | Sofortiges Leeren des iOS-`/launch`-Redirects beim URL-Wechsel. | nicht gesetzt |

> **Committe niemals deine echte `.env`.** Sie ist standardmäßig in .gitignore.

## 5. Lokal ausführen

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Öffne <http://127.0.0.1:8000>. Für die lokale Entwicklung sind keine Umgebungsvariablen nötig.

## Docker

Ein Befehl baut das Image und startet die Seite auf Port 8000. Das Standard-Image enthält Python, ein JDK, das Android SDK und apktool, daher sind Android-Pakete echte APKs. Apps und Signierschlüssel bleiben beim Neubau erhalten.

```bash
cp .env.example .env
# Vor der Veröffentlichung PUBLIC_BASE_URL=https://your-domain.com setzen.
docker compose up -d --build
```

Öffne <http://127.0.0.1:8000>. Der erste Build lädt das Android SDK von `dl.google.com` und apktool von GitHub. Dafür braucht der Rechner ausgehendes Netz und etwa 2 GB RAM.

Das bleibt erhalten:

- Volume `webtoapp-generated` — Apps, Verlauf und die Community-Datenbank
- `./certs` — Android-Keystores je App und optionale iOS-PEMs (`ios-cert.pem`, `ios-key.pem`, `ios-chain.pem`)

Einen Reverse-Proxy auf Port 8000 legen. Proxys in privaten Netzen dürfen `X-Forwarded-*` setzen. Sonst `DOCKER_TRUSTED_PROXY_CIDRS` in `.env` setzen.

Kleineres Image ohne Android-Werkzeuge (Android wird ein PWA-Zip):

```bash
WITH_ANDROID=0 docker compose up -d --build
```

Aktualisieren:

```bash
git pull
docker compose up -d --build
```

## 6. Als Dienst ausführen (systemd)

Bewahre Geheimnisse in einer zugriffsbeschränkten Env-Datei auf, statt inline in der Unit:

```bash
# /path/to/WebToApp/webtoapp.env  (chmod 600)
PUBLIC_BASE_URL=https://your-domain.com
# bei Bedarf R2_* / IOS_* / CLOUDFLARE_* hinzufügen
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

> Behalte `--workers 1` bei. Die Build-Warteschlange und der In-Memory-Ratenbegrenzer setzen einen einzigen Prozess voraus.

## 7. Reverse Proxy (Nginx)

Die App liefert ihr eigenes statisches Frontend aus, daher muss Nginx nur alles an den Uvicorn-Port weiterleiten:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 25m;   # Upload benutzerdefinierter Icons

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # APK-Builds können dauern
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 8. HTTPS

iOS-Web-Clips und `.mobileconfig`-Profile erfordern HTTPS. Zwei gängige Optionen:

**Option A — Cloudflare Tunnel** (keine offenen eingehenden Ports, kostenloses TLS):

```bash
cloudflared tunnel login
cloudflared tunnel create webtoapp
cloudflared tunnel route dns webtoapp your-domain.com
cloudflared tunnel run webtoapp
```

**Option B — Let's Encrypt auf Nginx:**

```bash
sudo certbot --nginx -d your-domain.com
```

In beiden Fällen `PUBLIC_BASE_URL=https://your-domain.com` setzen.

## 9. Android-APK-Builds (optional)

Um ein echtes, installierbares WebView-APK zu erzeugen, braucht der Server die Android-Build-Tools:

- Android SDK mit `aapt2`, `d8`, `apksigner`, `zipalign`
- `apktool`
- ein JDK mit `java`, `javac`, `keytool`

Verweise die App per `ANDROID_HOME` / `ANDROID_SDK_ROOT` auf das SDK, falls es nicht automatisch gefunden wird. Jede generierte App erhält ihr **eigenes** Signaturzertifikat (in `ANDROID_KEYSTORE_DIR`), sodass Updates darüber installiert werden.

**Ohne SDK** wird die APK-Erzeugung übersprungen und Android-Nutzer erhalten stattdessen ein installierbares PWA-Paket — alles andere funktioniert weiter.

## 10. iOS-Profil-Signierung (optional)

Standardmäßig ist die iOS-`.mobileconfig` unsigniert (iOS installiert sie trotzdem, zeigt aber „Nicht verifiziert"). Damit iOS deine Domain als Quelle anzeigt, stelle ein Public-CA-Zertifikat über `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` bereit oder lege `certs/ios-cert.pem`, `certs/ios-key.pem`, `certs/ios-chain.pem` ab. Die Signierung nutzt das System-`openssl`. Siehe [`certs/README.md`](../certs/README.md).

## 11. Cloudflare-R2-Auslagerung (optional)

### Funktionsweise

Generierte Installer (APK / ZIP / `.mobileconfig`) können groß sein, und jeden Download vom Origin auszuliefern verbraucht dessen Bandbreite. Mit aktiviertem R2:

1. **Nach jedem Build** wird jede Datei in `generated/<app_id>/downloads/` unter dem Schlüssel `<app_id>/downloads/<dateiname>` nach R2 hochgeladen (siehe `server/engine/storage.py`), und die entstehenden öffentlichen URLs werden als `downloads_cdn`-Map in die `recipe.json` der App geschrieben.
2. **Beim Download** bevorzugt `GET /a/<id>/download/<platform>` die CDN-URL aus `downloads_cdn` und gibt eine **302-Weiterleitung** zu R2 zurück; fehlt sie, fällt es auf das Streamen der lokalen Datei zurück. Der Origin verbraucht somit CPU nur beim Bauen, nicht Bandbreite bei jedem Teilen oder QR-Scan.
3. **Beim Aufräumen** werden die Objekte der App unter `<app_id>/` zusammen mit ihren lokalen Daten aus R2 gelöscht.

Fehlt eine `R2_*`-Variable, wird das Feature zum No-op und Downloads werden lokal ausgeliefert — nichts bricht. Vor der R2-Aktivierung gebaute Apps lassen sich mit `python -m server.scripts.backfill_r2` migrieren.

> **Implementierungshinweis:** R2 spricht die S3-API, die sich mit AWS Signature V4 authentifiziert. Statt den schweren `boto3`/`botocore`-Stack einzubinden, bringt `server/engine/storage.py` einen eigenen SigV4-Signierer mit (nur Standardbibliothek `hmac`/`hashlib`) und sendet Anfragen über `httpx`, denselben HTTP-Client, den die App bereits nutzt. Das R2-Offload benötigt daher **kein AWS-SDK**; der Signierer ist gegen die von AWS veröffentlichten SigV4-Testvektoren validiert (`python -m server.engine.storage`).

### Einrichtung

1. Öffne im Cloudflare-Dashboard **R2** und erstelle einen Bucket, z. B. `webtoapp-downloads`.
2. **Manage R2 API Tokens → Create API Token** mit der Berechtigung **Object Read & Write**. Kopiere **Access Key ID** und **Secret Access Key** (das Secret wird nur einmal angezeigt).
3. Mache den Bucket öffentlich: **Settings → Public access**. Aktiviere entweder die **r2.dev**-Entwicklungs-URL (`https://pub-xxxx.r2.dev`) für einen schnellen Start, oder füge eine **Custom Domain** (z. B. `files.example.com`) hinzu, um zusätzlich Edge-Caching zu erhalten.
   > Eine Custom Domain muss zu einer Domain gehören, die vom **selben Cloudflare-Konto** wie der Bucket verwaltet wird.
4. Setze die fünf Variablen in `webtoapp.env`:

   ```bash
   R2_ACCOUNT_ID=...            # deine Konto-ID (hex)
   R2_BUCKET=webtoapp-downloads
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev   # oder https://files.example.com
   ```
5. Starte den Dienst neu. Neue Builds leiten Downloads nun zu R2 um.

> **r2.dev vs. Custom Domain:** `pub-xxxx.r2.dev` wird bereits über Cloudflares globalen Edge ausgeliefert. Eine Custom Domain fügt Edge-**Caching** hinzu (wiederholte Downloads derselben Datei kommen aus dem Cache, ohne R2 zu treffen), was bei höherem Traffic stärker zählt.

### Backfill bestehender Apps

Vor der R2-Aktivierung gebaute Apps zeigen noch auf lokale Dateien. Lade ihre Artefakte nach R2 hoch und aktualisiere ihr `downloads_cdn` in einem Durchlauf:

```bash
set -a; . ./webtoapp.env; set +a
venv/bin/python -m server.scripts.backfill_r2 --dry-run   # Vorschau
venv/bin/python -m server.scripts.backfill_r2             # ausführen
```

Das Skript ist idempotent — ein erneuter Lauf ist unbedenklich.

## 12. Aktualisieren

```bash
git pull
source venv/bin/activate
pip install -r server/requirements.txt   # falls sich Abhängigkeiten geändert haben
sudo systemctl restart webtoapp
```

Wenn du Frontend-Assets (`css/`, `js/`) geändert hast, erhöhe die `?v=`-Query in `index.html`, damit Browser die neuen Dateien statt der gecachten laden.

## 13. Fehlerbehebung

| Symptom | Wahrscheinliche Ursache / Lösung |
| --- | --- |
| iPhone öffnet die Seite in Safari statt im Vollbild | `PUBLIC_BASE_URL` nicht gesetzt oder kein HTTPS. |
| Android-Download ist ein PWA-Zip, kein APK | Android SDK / apktool auf dem Server nicht installiert (§9). |
| Downloads kommen weiterhin vom Origin | Eine `R2_*`-Variable fehlt, oder kein Neustart nach dem Setzen. Backfill für alte Apps ausführen (§11). |
| iOS-Profil zeigt „Nicht verifiziert" | Profil ist unsigniert. Public-CA-Zertifikat bereitstellen (§10). |
| `502 Bad Gateway` | Dienst läuft nicht oder falscher Port — `systemctl status webtoapp`. |
| Build-Endpoint gibt `429` zurück | Tägliches Geräte-Kontingent oder IP-Ratenlimit erreicht. `DAILY_BUILD_QUOTA` anpassen. |

---

Siehe auch die [README](README.de.md) für einen Projektüberblick.

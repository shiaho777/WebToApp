<div align="center">

# WebToApp — Guía de despliegue

[English](DEPLOY.md) · [简体中文](DEPLOY.zh.md) · [日本語](DEPLOY.ja.md) · [العربية](DEPLOY.ar.md) · [Русский](DEPLOY.ru.md) · **Español** · [Português](DEPLOY.pt.md) · [Français](DEPLOY.fr.md) · [Deutsch](DEPLOY.de.md)

Guía paso a paso para ejecutar WebToApp en producción.

</div>

---

## Contenido

1. [Requisitos](#1-requisitos)
2. [Obtener el código](#2-obtener-el-código)
3. [Entorno Python](#3-entorno-python)
4. [Configuración](#4-configuración)
5. [Ejecutar localmente](#5-ejecutar-localmente)
   - [Docker](#docker)
6. [Ejecutar como servicio (systemd)](#6-ejecutar-como-servicio-systemd)
7. [Proxy inverso (Nginx)](#7-proxy-inverso-nginx)
8. [HTTPS](#8-https)
9. [Compilación de APK Android (opcional)](#9-compilación-de-apk-android-opcional)
10. [Firma de perfil iOS (opcional)](#10-firma-de-perfil-ios-opcional)
11. [Descarga a Cloudflare R2 (opcional)](#11-descarga-a-cloudflare-r2-opcional)
12. [Actualizar](#12-actualizar)
13. [Solución de problemas](#13-solución-de-problemas)

---

## 1. Requisitos

- **Python 3.10+**
- Un servidor Linux (cualquier distribución). 1 vCPU / 1 GB de RAM bastan para empezar.
- Acceso saliente a internet (el analizador descarga los sitios objetivo).
- Opcional, solo para compilar APK reales de Android: **Android SDK** (`aapt2`, `d8`, `apksigner`, `zipalign`), **apktool**, un **JDK** (`java` / `javac` / `keytool`). Sin ellos, Android recurre a un paquete PWA instalable.
- Opcional, solo para firmar iOS: **openssl** (presente en casi cualquier Linux).

La única dependencia obligatoria es Python. Todo lo demás es opcional y degrada con elegancia.

## 2. Obtener el código

```bash
git clone https://github.com/shiaho777/WebToApp.git
cd WebToApp
```

## 3. Entorno Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

Esto instala las cuatro dependencias de ejecución: `fastapi`, `uvicorn[standard]`, `httpx`, `Pillow`. La descarga a Cloudflare R2 (opcional) no necesita ningún paquete adicional — ver §11.

## 4. Configuración

Toda la configuración se lee de variables de entorno: cada una es opcional con un valor por defecto sensato.

```bash
cp .env.example .env
# edita .env
```

| Variable | Propósito | Por defecto |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | Origen público, p. ej. `https://app.example.com`. Obligatoria en producción o el iPhone intentará abrir `localhost`. | inferida de la cabecera Host |
| `ANDROID_PACKAGE_PREFIX` | Prefijo de paquete Android por defecto. | `com.webtoapp` |
| `ANDROID_KEYSTORE_DIR` | Dónde se guardan los keystores de firma por app. Manténlo FUERA de cualquier ruta pública. | `certs/app-keys` |
| `DAILY_BUILD_QUOTA` | Límite diario de compilaciones por dispositivo (`0` lo desactiva). | `10` |
| `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` | Certificado de CA pública para firmar perfiles iOS. | sin definir (sin firma, igual se instala) |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_PUBLIC_BASE_URL` | Descarga a Cloudflare R2 (ver §11). | sin definir (descargas locales) |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` | Purga inmediata del redireccionamiento iOS `/launch` al cambiar la URL. | sin definir |

> **Nunca subas tu `.env` real.** Está ignorado por git por defecto.

## 5. Ejecutar localmente

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Abre <http://127.0.0.1:8000>. Para desarrollo local no necesitas variables de entorno.

## Docker

Un comando construye la imagen y arranca el sitio en el puerto 8000. La imagen por defecto incluye Python, un JDK, el SDK de Android y apktool, así que los paquetes de Android son APK reales. Las apps generadas y las claves de firma sobreviven a una reconstrucción.

```bash
cp .env.example .env
# Antes de publicarlo, define PUBLIC_BASE_URL=https://your-domain.com.
docker compose up -d --build
```

Abre <http://127.0.0.1:8000>. La primera construcción descarga el SDK de Android desde `dl.google.com` y apktool desde GitHub. Hace falta salida a internet y unos 2 GB de RAM.

Qué se conserva:

- el volumen `webtoapp-generated` — apps, historial y la base de la comunidad
- `./certs` — keystores de Android por app y PEM de iOS opcionales (`ios-cert.pem`, `ios-key.pem`, `ios-chain.pem`)

Pon un proxy inverso delante del puerto 8000. Los proxies en direcciones privadas pueden enviar `X-Forwarded-*`. Si no, define `DOCKER_TRUSTED_PROXY_CIDRS` en `.env`.

Imagen más pequeña, sin la cadena de Android (Android pasa a ser un zip PWA):

```bash
WITH_ANDROID=0 docker compose up -d --build
```

Actualizar:

```bash
git pull
docker compose up -d --build
```

## 6. Ejecutar como servicio (systemd)

Guarda los secretos en un archivo de entorno restringido en vez de en línea en la unidad:

```bash
# /path/to/WebToApp/webtoapp.env  (chmod 600)
PUBLIC_BASE_URL=https://your-domain.com
# añade R2_* / IOS_* / CLOUDFLARE_* según necesites
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

> Mantén `--workers 1`. La cola de compilación y el limitador de tasa en memoria asumen un solo proceso.

## 7. Proxy inverso (Nginx)

La app sirve su propio frontend estático, así que Nginx solo necesita redirigir todo al puerto de Uvicorn:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 25m;   # subida de iconos personalizados

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # compilar APK puede tardar
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 8. HTTPS

Los Web Clips de iOS y los perfiles `.mobileconfig` requieren HTTPS. Dos opciones comunes:

**Opción A — Cloudflare Tunnel** (sin abrir puertos entrantes, TLS gratis):

```bash
cloudflared tunnel login
cloudflared tunnel create webtoapp
cloudflared tunnel route dns webtoapp your-domain.com
cloudflared tunnel run webtoapp
```

**Opción B — Let's Encrypt en Nginx:**

```bash
sudo certbot --nginx -d your-domain.com
```

En cualquier caso, define `PUBLIC_BASE_URL=https://your-domain.com`.

## 9. Compilación de APK Android (opcional)

Para producir un APK WebView real e instalable, el servidor necesita las herramientas de compilación de Android:

- Android SDK con `aapt2`, `d8`, `apksigner`, `zipalign`
- `apktool`
- un JDK que provea `java`, `javac`, `keytool`

Apunta la app al SDK con `ANDROID_HOME` / `ANDROID_SDK_ROOT` si no se detecta automáticamente. Cada app generada obtiene su **propio** certificado de firma (en `ANDROID_KEYSTORE_DIR`), de modo que las actualizaciones se instalan encima.

**Sin el SDK**, se omite la generación de APK y los usuarios de Android reciben un paquete PWA instalable: todo lo demás sigue funcionando.

## 10. Firma de perfil iOS (opcional)

Por defecto el `.mobileconfig` de iOS no está firmado (iOS igual lo instala, pero muestra "Sin verificar"). Para que iOS muestre tu dominio como origen, provee un certificado de CA pública con `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE`, o coloca `certs/ios-cert.pem`, `certs/ios-key.pem`, `certs/ios-chain.pem`. La firma usa el `openssl` del sistema. Ver [`certs/README.md`](../certs/README.md).

## 11. Descarga a Cloudflare R2 (opcional)

### Cómo funciona

Los instaladores generados (APK / ZIP / `.mobileconfig`) pueden ser pesados, y servir cada descarga desde el origen consume su ancho de banda. Con R2 activado:

1. **Tras cada compilación**, cada archivo en `generated/<app_id>/downloads/` se sube a R2 con la clave `<app_id>/downloads/<nombre>` (ver `server/engine/storage.py`), y las URL públicas resultantes se escriben en el `recipe.json` de la app como un mapa `downloads_cdn`.
2. **Al descargar**, `GET /a/<id>/download/<platform>` prefiere la URL de CDN en `downloads_cdn` y devuelve un **redireccionamiento 302** a R2; si no existe, recurre a servir el archivo local. Así el origen gasta CPU al compilar, no ancho de banda en cada compartido o escaneo de QR.
3. **Al limpiar**, los objetos de la app bajo `<app_id>/` se eliminan de R2 junto con sus datos locales.

Si falta cualquier variable `R2_*`, la función queda inactiva y las descargas se sirven localmente: nada se rompe. Las apps creadas antes de activar R2 se migran con `python -m server.scripts.backfill_r2`.

> **Nota de implementación:** R2 habla la API de S3, que se autentica con AWS Signature V4. En lugar de incluir la pesada pila `boto3`/`botocore`, `server/engine/storage.py` trae su propio firmador SigV4 (solo con la biblioteca estándar `hmac`/`hashlib`) y envía las peticiones vía `httpx`, el mismo cliente HTTP que ya usa la app. Por eso la descarga a R2 **no necesita el SDK de AWS**; el firmador está validado con los vectores de prueba SigV4 publicados por AWS (`python -m server.engine.storage`).

### Configuración

1. En el panel de Cloudflare, abre **R2** y crea un bucket, p. ej. `webtoapp-downloads`.
2. **Manage R2 API Tokens → Create API Token** con permiso **Object Read & Write**. Copia el **Access Key ID** y el **Secret Access Key** (el secreto se muestra una sola vez).
3. Haz público el bucket: **Settings → Public access**. Activa la URL de desarrollo **r2.dev** (`https://pub-xxxx.r2.dev`) para empezar rápido, o añade un **dominio personalizado** (p. ej. `files.example.com`) para tener además caché en el borde.
   > Un dominio personalizado debe estar en un dominio gestionado por **la misma cuenta de Cloudflare** que el bucket.
4. Define las cinco variables en `webtoapp.env`:

   ```bash
   R2_ACCOUNT_ID=...            # tu ID de cuenta (hex)
   R2_BUCKET=webtoapp-downloads
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev   # o https://files.example.com
   ```
5. Reinicia el servicio. Las nuevas compilaciones ahora redirigen las descargas a R2.

> **r2.dev vs dominio personalizado:** `pub-xxxx.r2.dev` ya se sirve desde el borde global de Cloudflare. Un dominio personalizado añade **caché** en el borde (las descargas repetidas del mismo archivo se sirven de caché sin tocar R2), lo que importa más con más tráfico.

### Backfill de apps existentes

Las apps compiladas antes de activar R2 aún apuntan a archivos locales. Sube sus artefactos a R2 y actualiza su `downloads_cdn` de una pasada:

```bash
set -a; . ./webtoapp.env; set +a
venv/bin/python -m server.scripts.backfill_r2 --dry-run   # vista previa
venv/bin/python -m server.scripts.backfill_r2             # ejecutar
```

El script es idempotente: es seguro reejecutarlo.

## 12. Actualizar

```bash
git pull
source venv/bin/activate
pip install -r server/requirements.txt   # si cambiaron las dependencias
sudo systemctl restart webtoapp
```

Si cambiaste recursos del frontend (`css/`, `js/`), incrementa la cadena `?v=` en `index.html` para que los navegadores tomen los archivos nuevos en vez de los cacheados.

## 13. Solución de problemas

| Síntoma | Causa probable / solución |
| --- | --- |
| El iPhone abre la página en Safari en vez de a pantalla completa | `PUBLIC_BASE_URL` sin definir, o no es HTTPS. |
| La descarga de Android es un zip de PWA, no un APK | Android SDK / apktool no instalados en el servidor (§9). |
| Las descargas siguen sirviéndose desde el origen | Falta una variable `R2_*`, o no reiniciaste tras definirlas. Ejecuta el backfill para apps antiguas (§11). |
| El perfil iOS muestra "Sin verificar" | El perfil no está firmado. Provee un certificado de CA pública (§10). |
| `502 Bad Gateway` | El servicio no está corriendo o el puerto es incorrecto — `systemctl status webtoapp`. |
| El endpoint de compilación devuelve `429` | Se alcanzó la cuota diaria por dispositivo o el límite por IP. Ajusta `DAILY_BUILD_QUOTA`. |

---

Consulta también el [README](README.es.md) para una visión general del proyecto.

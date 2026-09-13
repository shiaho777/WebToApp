<div align="center">

<img src="../assets/site-logo.jpg" alt="WebToApp" width="120" height="120" style="border-radius: 24px;">

# WebToApp

**Convierte cualquier sitio web en una app instalable — en segundos.**

Un enlace entra, salen productos terminados para **iPhone / iPad · Android · Windows · macOS · Linux** — además de un mercado público de apps, perfiles de creador, comentarios y valoraciones, todo sin registro.

[![Demo en vivo](https://img.shields.io/badge/Demo_en_vivo-shiaho.sbs-c97953?style=for-the-badge)](https://shiaho.sbs)
[![CI](https://img.shields.io/badge/CI-pytest%20336-059669?style=for-the-badge)](https://github.com/shiaho777/WebToApp/actions)
[![Licencia: MIT](https://img.shields.io/badge/License-MIT-1e1914?style=for-the-badge)](../LICENSE)
[![Plataformas](https://img.shields.io/badge/Plataformas-5-736357?style=for-the-badge)](#qué-obtienes)

[English](../README.md) · [简体中文](README.zh.md) · [日本語](README.ja.md) · [العربية](README.ar.md) · [Русский](README.ru.md) · **Español** · [Português](README.pt.md) · [Français](README.fr.md) · [Deutsch](README.de.md)

</div>

---

<p align="center"><img src="assets/fig-stats.svg" alt="WebToApp de un vistazo: 5 plataformas, 9 idiomas, 336 tests" width="760"></p>

## Qué obtienes

Introduce una URL —o sube tu propio `.html` / `.zip`— y segundos después obtienes un resultado instalable para todas las plataformas. Cada artefacto es una fina capa nativa que apunta a tu sitio, así que los paquetes se miden en **kilobytes, no megabytes**, y se descargan casi al instante.

Cada app generada vive en su propia página de descarga `/a/<id>`: opciones por plataforma, una sección plegable «Acerca de esta página» que el creador puede llenar con contenido real, y una capa comunitaria con comentarios y valoraciones por estrellas. Publícala como enlace público y además aparece en el **mercado de apps** para que todos la encuentren.

Open source · Gratis · Sin registro. Pruébalo en vivo en **[shiaho.sbs](https://shiaho.sbs)**.

---

## Capturas

<p align="center"><img src="assets/shots/landing.png" alt="Página inicial: pega un enlace y empieza — contadores en vivo de apps generadas, descargas y visitas" width="820"></p>
<p align="center"><em>Pega un enlace (o suelta un archivo HTML) — los contadores son en vivo.</em></p>

<p align="center"><img src="assets/shots/config-about.png" alt="Configuración de la app: nombre, descripción, texto de la sección Acerca de y hasta 3 imágenes auto-comprimidas" width="820"></p>
<p align="center"><em>Nombre, descripción de una línea y la sección Acerca de escrita por el creador con hasta 3 imágenes — lo que supere 800KB se comprime casi sin pérdida.</em></p>

<p align="center"><img src="assets/shots/config-platforms.png" alt="Color de tema, icono recuperado y ajustes por plataforma como el modo inmersivo de Android" width="820"></p>
<p align="center"><em>Color de tema e icono recuperados del sitio; ajustes por plataforma como el modo inmersivo de Android.</em></p>

<p align="center"><img src="assets/shots/config-publish.png" alt="Visibilidad del enlace y etiquetas obligatorias antes de generar" width="820"></p>
<p align="center"><em>Privado por defecto o público en el mercado — las etiquetas son obligatorias para que las apps sigan siendo descubribles.</em></p>

<p align="center"><img src="assets/shots/download-page.png" alt="Página de descarga generada: valoración, tarjeta de creador, comentarios y lista de instalación por plataforma" width="820"></p>
<p align="center"><em>La página de la app generada: lista de instalación a la derecha, valoración / creador / comentarios a la izquierda.</em></p>

<p align="center"><img src="assets/shots/about-fold.png" alt="La sección Acerca de expandida, mostrando texto del creador y una imagen subida" width="820"></p>
<p align="center"><em>La sección «Acerca de esta página» lleva el texto y las imágenes del creador — sin texto de relleno.</em></p>

<p align="center"><img src="assets/shots/market.png" alt="Mercado público de apps con atribución de creador, etiquetas, tiempo relativo y valoraciones en cada tarjeta" width="820"></p>
<p align="center"><em>El mercado público: tarjetas de creador, filtros por etiqueta, búsqueda y ordenación por más recientes / mejor valoradas / más descargadas / más visitadas.</em></p>

<p align="center"><img src="assets/shots/history.png" alt="Historial de builds por dispositivo con estadísticas de visitas, exportación e importación" width="820"></p>
<p align="center"><em>Tu historial queda ligado a la huella del dispositivo — con estadísticas de visitas, regenerar y exportar/importar entre dispositivos.</em></p>

---

## Cómo funciona

<p align="center"><img src="assets/fig-pipeline.svg" alt="Pipeline: entrada URL o HTML → análisis + recipe → cinco builds en paralelo → página de app con comunidad" width="800"></p>

1. **Entrada** — pega la URL de un sitio web, o sube un `.html` suelto / un `.zip` que contenga `index.html`. El HTML subido se hospeda en el servidor bajo `/a/<id>/site/...` y se empaqueta igual que una app de URL.
2. **Análisis + recipe** — el analizador descarga la página y extrae nombre, color de tema e icono (multi-candidato, gana la mayor resolución); todo lo necesario para la build queda fijado en un `recipe.json`.
3. **Builds en paralelo** — los cinco paquetes se construyen a la vez; si uno falla (p. ej. falta la toolchain de Android) solo esa plataforma se degrada.
4. **Página de app** — la página de descarga renderiza las entradas de instalación por plataforma, el contenido Acerca de del creador y el bloque de comunidad.

## Funciones

- **Dos modos de entrada**: URL de sitio web, o tu propio HTML (un `.html` o un `.zip` con `index.html` dentro) — hospedado y empaquetado igual que una app de URL.
- **Análisis del sitio**: nombre, color de tema, icono en la mejor resolución y recuento de anuncios/rastreadores/popups (estimaciones solo de exhibición).
- **Empaquetado multiplataforma**, una build → cinco artefactos:
  - **Android** — un WebView APK real e instalable (firmado v1+v2+v3), cada app con su **propio certificado de firma**.
  - **iOS / iPadOS** — un perfil Web Clip `.mobileconfig`, opcionalmente firmado con CMS usando un certificado de CA pública (instalación «sin firma»).
  - **macOS** — una ventana `.app` WKWebView autónoma (sin barra de direcciones ni navegador de terceros).
  - **Windows / Linux** — lanzadores ligeros `.bat` / `.desktop` que abren el navegador del sistema en modo app.
- **Sección Acerca de escrita por el creador**: texto enriquecido más hasta 3 imágenes en cada página de app. Las subidas se verifican por decodificación, se les quita el EXIF y se re-codifican a WebP — lo que supere 800KB se comprime casi sin pérdida en el servidor.
- **Comunidad sin cuentas**: la huella del dispositivo se convierte en una identidad pública persistente (`?u=N`) — nombre editable, bio en Markdown y avatar. Los creadores quedan acreditados en sus apps y tienen página de perfil pública.
- **Comentarios y valoraciones**: cada página de app tiene un hilo de comentarios con valoración opcional de 1–5 estrellas; los promedios se reflejan en las tarjetas del mercado.
- **Mercado público de apps**: filtros por etiqueta, búsqueda y ordenación por más recientes, mejor valoradas (promedio → cantidad), más descargadas o más visitadas — con marcas de tiempo relativas.
- **Cambio dinámico de URL en iOS**: el Web Clip apunta a `/a/<id>/launch`, así que la URL de destino puede cambiar en el servidor sin reinstalar.
- **Historial por dispositivo**: las builds se guardan contra la huella del dispositivo con estadísticas de visitas/descargas, regenerar y exportar/importar entre dispositivos. Borrar una entrada elimina la app por completo.
- **Limpieza automática**: las apps sin visitas durante 30 días se reclaman automáticamente.
- **Offload opcional a Cloudflare R2**: las descargas redirigen al CDN, ahorrando ancho de banda del origen.
- **UI multilingüe**: 9 idiomas — English, 简体中文, 日本語, العربية (RTL), Русский, Español, Português, Français, Deutsch — con las páginas de descarga generadas también localizadas.

## Comunidad sin registro

<p align="center"><img src="assets/fig-community.svg" alt="La huella del dispositivo se convierte en un ID público secuencial que desbloquea atribución de creador, perfiles, comentarios y valoraciones" width="800"></p>

No hay registro: la primera vez que aparece un dispositivo, su huella recibe un número público secuencial. Ese `#N` se convierte en un perfil real — define un nombre visible, una bio en Markdown y un avatar, y cada app que publiques lleva tu tarjeta de creador. Otros usuarios abren `?u=N` para ver tu perfil público y las apps que publicaste. Los comentarios admiten valoraciones por estrellas opcionales, y el mercado las refleja en cada tarjeta.

## Tamaño de la app

Cada paquete es una fina puerta de entrada a tu sitio — no incluye el contenido del sitio, así que los artefactos se miden en **kilobytes, no megabytes**.

<p align="center"><img src="assets/fig-sizes.svg" alt="Tamaños medidos: macOS 135KB, Android 21KB, iOS 4KB, Windows 1.2KB, Linux 0.7KB" width="760"></p>

| Plataforma | Paquete | Tamaño típico | Contenido |
| --- | --- | --- | --- |
| Android | `android.apk` | **~21 KB** | Un WebView APK real e instalable (firmado v1+v2+v3) |
| iOS / iPadOS | `ios.mobileconfig` | **~4 KB** | Un perfil de configuración Web Clip |
| macOS | `macos.zip` | **~135 KB** | Un bundle `.app` (ventana WKWebView nativa + icono) |
| Windows | `windows.zip` | **~1.2 KB** | Un lanzador `.bat` + ayudante de acceso directo + icono |
| Linux | `linux.tar.gz` | **~0.7 KB** | Una entrada `.desktop` + script de instalación + icono |

## Stack técnico

- Backend: Python + FastAPI + Uvicorn · almacenes SQLite (historial, tareas, comunidad)
- Frontend: HTML / CSS / JS puro — sin paso de build, servido directamente por el backend
- Empaquetado: Android SDK (aapt2 / d8 / apktool / apksigner / zipalign), Pillow, openssl
- CI: `pytest tests/` en Python 3.10 / 3.11 / 3.12 — **336 tests**

## Estructura del proyecto

```
.
├── index.html                 Página inicial + formulario de build
├── css/ js/ assets/           Assets estáticos del frontend
│   ├── js/i18n.js             Runtime i18n ligero (9 idiomas)
│   ├── js/i18n.strings.js     Todas las traducciones
│   ├── js/community.js        Comentarios / valoraciones / bloque de creador en las páginas de app
│   └── js/mdmini.js           Mini renderizador Markdown para bios
├── server/
│   ├── main.py                App FastAPI y rutas (35 endpoints)
│   ├── config.py              Configuración por variables de entorno
│   ├── html_site.py           Staging / validación / servicio de subidas HTML
│   ├── history_store.py       Historial por dispositivo + estadísticas de app/visitas (SQLite)
│   ├── community_store.py     Perfiles, creadores, comentarios, valoraciones (SQLite)
│   ├── task_store.py          Persistencia de la cola de builds (SQLite)
│   └── engine/
│       ├── analyzer.py        Análisis del sitio
│       ├── distiller.py       recipe → paquetes + página de descarga (núcleo)
│       ├── apk_builder.py     Build y firma del APK de Android
│       ├── mobileconfig_signer.py  Firma de perfiles iOS
│       ├── cache.py           Cachés de fetch/iconos
│       └── storage.py         Offload a Cloudflare R2
├── certs/                     Material de firma (las claves privadas no se commitean)
└── generated/                 Apps y datos generados en runtime (no se commitean)
```

## Inicio rápido

Requiere Python 3.10+. Construir el APK de Android necesita el Android SDK y `apktool` (degrada a un paquete PWA offline cuando faltan).

```bash
# 1. Crea un entorno virtual e instala las dependencias
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt

# 2. Configura (opcional, todo tiene valores por defecto)
cp .env.example .env
# Edita .env según necesites

# 3. Ejecuta
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Abre http://127.0.0.1:8000.

> No hacen falta variables de entorno para desarrollo local. Al desplegar en público, define `PUBLIC_BASE_URL`,
> si no, los iPhone no pueden abrir `localhost`. La lista completa está en [`.env.example`](../.env.example).

## Despliegue

> Para una guía de producción completa paso a paso (systemd, Nginx, HTTPS, Android/iOS, R2), consulta **[DEPLOY.md](DEPLOY.md)**.

En producción es habitual ejecutarlo bajo systemd, detrás de un proxy inverso Nginx:

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

Para la firma de perfiles iOS (instalación «sin firma»), consulta la configuración de certificados en [`certs/README.md`](../certs/README.md).

## Cómo funciona el offload a Cloudflare R2

Los instaladores generados pueden ser grandes, y servir cada descarga desde el origen consume su ancho de banda. Con R2 configurado:

1. **Tras cada build**, cada archivo de `generated/<app_id>/downloads/` se refleja en R2 bajo la clave `<app_id>/downloads/<filename>` (`server/engine/storage.py`), y las URLs públicas resultantes se escriben en el `recipe.json` de la app como mapa `downloads_cdn`.
2. **Al descargar**, `GET /a/<id>/download/<platform>` prefiere la URL CDN de `downloads_cdn` y devuelve un **redirect 302** a R2; si no existe, recurre a servir el archivo local en streaming. El origen gasta CPU en las builds, no ancho de banda en cada share o escaneo de QR.
3. **En la limpieza**, los objetos de una app bajo `<app_id>/` se eliminan de R2 junto con sus datos locales.

Si falta cualquier variable `R2_*` la función es no-op y las descargas se sirven localmente — nada se rompe. Las apps creadas antes de habilitar R2 se pueden migrar con `python -m server.scripts.backfill_r2`. Los pasos completos (bucket, token de API, acceso público, dominio personalizado, backfill) están en [DEPLOY.md §11](DEPLOY.md#11-cloudflare-r2-offload-optional).

## Notas de seguridad

- Todos los secretos (R2, Cloudflare, contraseñas de firma) se leen de variables de entorno; el repositorio no contiene credenciales reales.
- **Las claves privadas de firma (`certs/*.keystore`, `certs/app-keys/`) y los datos de runtime (`generated/`) están excluidos por `.gitignore` por defecto — nunca los commitees.**
- Cada app Android generada usa su propio certificado de firma independiente, lo que evita que la huella del certificado sea marcada en masa y permite actualizar la misma app in situ.
- Las imágenes «Acerca de» subidas por creadores se verifican por decodificación con Pillow, acotadas por límites de tamaño bruto / píxeles / cantidad, despojadas de metadatos y re-codificadas a WebP — nunca se sirven tal como se subieron.
- El texto generado por usuarios se escapa como HTML al renderizar; las rutas de medios por app solo admiten nombres de archivo generados por el servidor.

## Licencia

[MIT](../LICENSE)

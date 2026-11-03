<div align="center">

# WebToApp — Руководство по развёртыванию

[English](DEPLOY.md) · [简体中文](DEPLOY.zh.md) · [日本語](DEPLOY.ja.md) · [العربية](DEPLOY.ar.md) · **Русский** · [Español](DEPLOY.es.md) · [Português](DEPLOY.pt.md) · [Français](DEPLOY.fr.md) · [Deutsch](DEPLOY.de.md)

Пошаговое руководство по запуску WebToApp в продакшене.

</div>

---

## Содержание

1. [Требования](#1-требования)
2. [Получение кода](#2-получение-кода)
3. [Окружение Python](#3-окружение-python)
4. [Конфигурация](#4-конфигурация)
5. [Локальный запуск](#5-локальный-запуск)
   - [Docker](#docker)
6. [Запуск как служба (systemd)](#6-запуск-как-служба-systemd)
7. [Обратный прокси (Nginx)](#7-обратный-прокси-nginx)
8. [HTTPS](#8-https)
9. [Сборка Android APK (опционально)](#9-сборка-android-apk-опционально)
10. [Подпись профиля iOS (опционально)](#10-подпись-профиля-ios-опционально)
11. [Выгрузка в Cloudflare R2 (опционально)](#11-выгрузка-в-cloudflare-r2-опционально)
12. [Обновление](#12-обновление)
13. [Устранение неполадок](#13-устранение-неполадок)

---

## 1. Требования

- **Python 3.10+**
- Сервер Linux (любой дистрибутив). Для старта достаточно 1 vCPU / 1 ГБ ОЗУ.
- Доступ в интернет (анализатор загружает целевые сайты).
- Опционально, только для реальной сборки Android APK: **Android SDK** (`aapt2`, `d8`, `apksigner`, `zipalign`), **apktool**, **JDK** (`java` / `javac` / `keytool`). Без них Android откатывается к устанавливаемому PWA-пакету.
- Опционально, только для подписи iOS: **openssl** (есть практически на любом Linux).

Единственная обязательная зависимость — Python. Всё остальное опционально и деградирует мягко.

## 2. Получение кода

```bash
git clone https://github.com/shiaho777/WebToApp.git
cd WebToApp
```

## 3. Окружение Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

Устанавливаются четыре зависимости: `fastapi`, `uvicorn[standard]`, `httpx`, `Pillow`. Выгрузка в Cloudflare R2 (опционально) не требует дополнительных пакетов — см. §11.

## 4. Конфигурация

Вся конфигурация читается из переменных окружения — каждая опциональна и имеет разумное значение по умолчанию.

```bash
cp .env.example .env
# отредактируйте .env
```

| Переменная | Назначение | По умолчанию |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | Публичный origin, напр. `https://app.example.com`. Обязательна в продакшене, иначе iPhone попытается открыть `localhost`. | выводится из заголовка Host |
| `ANDROID_PACKAGE_PREFIX` | Префикс пакета Android по умолчанию. | `com.webtoapp` |
| `ANDROID_KEYSTORE_DIR` | Где хранятся keystore'ы подписи на каждое приложение. Держите ВНЕ любого публичного пути. | `certs/app-keys` |
| `DAILY_BUILD_QUOTA` | Дневной лимит сборок на устройство (`0` отключает). | `10` |
| `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` | Сертификат публичного CA для подписи профилей iOS. | не задано (без подписи, всё равно устанавливается) |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_PUBLIC_BASE_URL` | Выгрузка в Cloudflare R2 (см. §11). | не задано (раздача локально) |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` | Немедленный сброс кеша редиректа iOS `/launch` при смене URL. | не задано |

> **Никогда не коммитьте реальный `.env`.** По умолчанию он в .gitignore.

## 5. Локальный запуск

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Откройте <http://127.0.0.1:8000>. Для локальной разработки переменные окружения не нужны.

## Docker

Одна команда собирает образ и запускает сайт на порту 8000. В образ по умолчанию входят Python, JDK, Android SDK и apktool, поэтому пакеты Android — настоящие APK. Уже созданные приложения и ключи подписи сохраняются при пересборке.

```bash
cp .env.example .env
# Перед публикацией задайте PUBLIC_BASE_URL=https://your-domain.com.
docker compose up -d --build
```

Откройте <http://127.0.0.1:8000>. Первая сборка скачивает Android SDK с `dl.google.com` и apktool с GitHub. Нужен исходящий доступ и около 2 ГБ памяти.

Что сохраняется:

- том `webtoapp-generated` — приложения, история и база сообщества
- `./certs` — keystore Android для каждого приложения и необязательные PEM для iOS (`ios-cert.pem`, `ios-key.pem`, `ios-chain.pem`)

Поставьте обратный прокси на порт 8000. Прокси в частных сетях могут передавать `X-Forwarded-*`. Иначе задайте `DOCKER_TRUSTED_PROXY_CIDRS` в `.env`.

Образ поменьше, без Android-инструментов (Android станет PWA-zip):

```bash
WITH_ANDROID=0 docker compose up -d --build
```

Обновление:

```bash
git pull
docker compose up -d --build
```

## 6. Запуск как служба (systemd)

Храните секреты в защищённом env-файле, а не в самом юните:

```bash
# /path/to/WebToApp/webtoapp.env  (chmod 600)
PUBLIC_BASE_URL=https://your-domain.com
# при необходимости добавьте R2_* / IOS_* / CLOUDFLARE_*
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

> Оставьте `--workers 1`. Очередь сборки и in-memory лимитер рассчитаны на один процесс.

## 7. Обратный прокси (Nginx)

Приложение само раздаёт статический фронтенд, поэтому Nginx нужен лишь для проксирования на порт Uvicorn:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 25m;   # загрузка пользовательских иконок

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # сборка APK может занять время
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 8. HTTPS

iOS Web Clip и профили `.mobileconfig` требуют HTTPS. Два частых варианта:

**Вариант A — Cloudflare Tunnel** (без открытия входящих портов, бесплатный TLS):

```bash
cloudflared tunnel login
cloudflared tunnel create webtoapp
cloudflared tunnel route dns webtoapp your-domain.com
cloudflared tunnel run webtoapp
```

**Вариант B — Let's Encrypt на Nginx:**

```bash
sudo certbot --nginx -d your-domain.com
```

В любом случае задайте `PUBLIC_BASE_URL=https://your-domain.com`.

## 9. Сборка Android APK (опционально)

Чтобы выпускать настоящий устанавливаемый WebView APK, серверу нужны инструменты сборки Android:

- Android SDK с `aapt2`, `d8`, `apksigner`, `zipalign`
- `apktool`
- JDK с `java`, `javac`, `keytool`

Укажите SDK через `ANDROID_HOME` / `ANDROID_SDK_ROOT`, если он не определяется автоматически. Каждое сгенерированное приложение получает **собственный** сертификат подписи (в `ANDROID_KEYSTORE_DIR`), поэтому обновления ставятся поверх.

**Без SDK** генерация APK пропускается, и пользователи Android получают устанавливаемый PWA-пакет — всё остальное работает.

## 10. Подпись профиля iOS (опционально)

По умолчанию `.mobileconfig` для iOS не подписан (iOS всё равно установит, но покажет «Не проверено»). Чтобы iOS показывал ваш домен как источник, укажите сертификат публичного CA через `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` либо положите `certs/ios-cert.pem`, `certs/ios-key.pem`, `certs/ios-chain.pem`. Подпись использует системный `openssl`. См. [`certs/README.md`](../certs/README.md).

## 11. Выгрузка в Cloudflare R2 (опционально)

### Как это работает

Сгенерированные инсталляторы (APK / ZIP / `.mobileconfig`) бывают тяжёлыми, и раздача каждой загрузки с origin расходует его трафик. При включённом R2:

1. **После каждой сборки** каждый файл из `generated/<app_id>/downloads/` загружается в R2 по ключу `<app_id>/downloads/<имя_файла>` (см. `server/engine/storage.py`), а полученные публичные URL записываются в `recipe.json` приложения как карта `downloads_cdn`.
2. **При загрузке** `GET /a/<id>/download/<platform>` предпочитает CDN-URL из `downloads_cdn` и возвращает **редирект 302** на R2; если его нет — откатывается к локальному файлу. Так origin тратит CPU только при сборке, а не трафик при каждом шаринге или скане QR.
3. **При очистке** объекты приложения под `<app_id>/` удаляются из R2 вместе с локальными данными.

Если любая переменная `R2_*` не задана, функция превращается в no-op и загрузки раздаются локально — ничего не ломается. Приложения, собранные до включения R2, мигрируются через `python -m server.scripts.backfill_r2`.

> **Примечание по реализации:** R2 использует S3 API с аутентификацией по AWS Signature V4. Вместо тяжёлого стека `boto3`/`botocore` модуль `server/engine/storage.py` содержит собственную реализацию подписи SigV4 (только стандартная библиотека `hmac`/`hashlib`) и отправляет запросы через `httpx` — тот же HTTP-клиент, что уже использует приложение. Поэтому выгрузке в R2 **не нужен AWS SDK**; реализация подписи проверена на опубликованных AWS тестовых векторах SigV4 (`python -m server.engine.storage`).

### Настройка

1. В панели Cloudflare откройте **R2** и создайте бакет, напр. `webtoapp-downloads`.
2. **Manage R2 API Tokens → Create API Token** с правами **Object Read & Write**. Скопируйте **Access Key ID** и **Secret Access Key** (секрет показывается один раз).
3. Сделайте бакет публичным: **Settings → Public access**. Либо включите dev-URL **r2.dev** (`https://pub-xxxx.r2.dev`) для быстрого старта, либо добавьте **Custom Domain** (напр. `files.example.com`), чтобы получить ещё и кеширование на краю.
   > Кастомный домен должен быть на домене, управляемом **тем же аккаунтом Cloudflare**, что и бакет.
4. Задайте пять переменных в `webtoapp.env`:

   ```bash
   R2_ACCOUNT_ID=...            # ID аккаунта (hex)
   R2_BUCKET=webtoapp-downloads
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev   # или https://files.example.com
   ```
5. Перезапустите службу. Новые сборки теперь редиректят загрузки на R2.

> **r2.dev против кастомного домена:** `pub-xxxx.r2.dev` уже раздаётся с глобального края Cloudflare. Кастомный домен добавляет **кеширование** на краю (повторные загрузки того же файла отдаются из кеша без обращения к R2), что важнее при большем трафике.

### Backfill существующих приложений

Приложения, собранные до включения R2, всё ещё указывают на локальные файлы. Загрузите их артефакты в R2 и обновите `downloads_cdn` за один проход:

```bash
set -a; . ./webtoapp.env; set +a
venv/bin/python -m server.scripts.backfill_r2 --dry-run   # предпросмотр
venv/bin/python -m server.scripts.backfill_r2             # выполнить
```

Скрипт идемпотентен — повторный запуск безопасен.

## 12. Обновление

```bash
git pull
source venv/bin/activate
pip install -r server/requirements.txt   # если изменились зависимости
sudo systemctl restart webtoapp
```

Если вы меняли фронтенд-ассеты (`css/`, `js/`), обновите строку запроса `?v=` в `index.html`, чтобы браузеры взяли новые файлы вместо кешированных.

## 13. Устранение неполадок

| Симптом | Вероятная причина / решение |
| --- | --- |
| iPhone открывает страницу в Safari, а не на весь экран | Не задан `PUBLIC_BASE_URL` или это не HTTPS. |
| Загрузка Android — PWA-zip, а не APK | На сервере не установлены Android SDK / apktool (§9). |
| Загрузки всё ещё с origin | Отсутствует переменная `R2_*` или не было перезапуска. Для старых приложений запустите backfill (§11). |
| Профиль iOS показывает «Не проверено» | Профиль не подписан. Укажите сертификат публичного CA (§10). |
| `502 Bad Gateway` | Служба не запущена или неверный порт — `systemctl status webtoapp`. |
| Эндпоинт сборки возвращает `429` | Достигнут дневной лимит на устройство или лимит по IP. Настройте `DAILY_BUILD_QUOTA`. |

---

См. также [README](README.ru.md) для обзора проекта.

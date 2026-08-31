<div align="center">

# WebToApp — 部署指南

[English](DEPLOY.md) · **简体中文** · [日本語](DEPLOY.ja.md) · [العربية](DEPLOY.ar.md) · [Русский](DEPLOY.ru.md) · [Español](DEPLOY.es.md) · [Português](DEPLOY.pt.md) · [Français](DEPLOY.fr.md) · [Deutsch](DEPLOY.de.md)

一步步把 WebToApp 部署到生产环境。

</div>

---

## 目录

1. [环境要求](#1-环境要求)
2. [获取代码](#2-获取代码)
3. [Python 环境](#3-python-环境)
4. [配置](#4-配置)
5. [本地运行](#5-本地运行)
6. [作为服务运行（systemd）](#6-作为服务运行systemd)
7. [反向代理（Nginx）](#7-反向代理nginx)
8. [HTTPS](#8-https)
9. [安卓 APK 构建（可选）](#9-安卓-apk-构建可选)
10. [iOS 描述文件签名（可选）](#10-ios-描述文件签名可选)
11. [Cloudflare R2 卸载（可选）](#11-cloudflare-r2-卸载可选)
12. [更新](#12-更新)
13. [故障排查](#13-故障排查)

---

## 1. 环境要求

- **Python 3.10+**
- 一台 Linux 服务器（任意发行版）。1 核 / 1 GB 内存即可起步。
- 可访问外网（分析器需要抓取目标站点）。
- 可选，仅用于真实安卓 APK 构建：**Android SDK**（`aapt2`、`d8`、`apksigner`、`zipalign`）、**apktool**、**JDK**（`java` / `javac` / `keytool`）。没有它们时，安卓会回退为可安装的 PWA 包。
- 可选，仅用于 iOS 签名：**openssl**（几乎所有 Linux 都自带）。

唯一的硬性依赖是 Python，其余全部可选且会优雅降级。

## 2. 获取代码

```bash
git clone https://github.com/shiahonb777/WebToApp.git
cd WebToApp
```

## 3. Python 环境

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

这会安装 4 个运行时依赖：`fastapi`、`uvicorn[standard]`、`httpx`、`Pillow`。Cloudflare R2 卸载（可选）无需额外安装包——详见 §11。

## 4. 配置

所有配置都从环境变量读取——每一项都是可选的，且有合理默认值。

```bash
cp .env.example .env
# 按需编辑 .env
```

| 变量 | 用途 | 默认值 |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | 公网地址，如 `https://app.example.com`。生产环境必填，否则 iPhone 会去打开 `localhost`。 | 从 Host 头推断 |
| `ANDROID_PACKAGE_PREFIX` | 默认安卓包名前缀。 | `com.webtoapp` |
| `ANDROID_KEYSTORE_DIR` | 每应用签名 keystore 的存放目录。务必放在任何公开路径之外。 | `certs/app-keys` |
| `DAILY_BUILD_QUOTA` | 每设备每日构建上限（`0` 表示关闭）。 | `10` |
| `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` | 用于签名 iOS 描述文件的公开 CA 证书。 | 未设置（不签名，仍可安装） |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_PUBLIC_BASE_URL` | Cloudflare R2 卸载（见 §11）。 | 未设置（下载走本地） |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` | 切换 URL 时立即清除 iOS `/launch` 跳转的缓存。 | 未设置 |

> **切勿提交你真实的 `.env`。** 它默认已被 git 忽略。

## 5. 本地运行

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

打开 <http://127.0.0.1:8000>。本地开发不需要任何环境变量。

## 6. 作为服务运行（systemd）

把密钥放在权限受限的环境文件里，而不是写在 unit 内联：

```bash
# /path/to/WebToApp/webtoapp.env  （chmod 600）
PUBLIC_BASE_URL=https://your-domain.com
# 按需在此添加 R2_* / IOS_* / CLOUDFLARE_*
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

> 保持 `--workers 1`。构建队列和内存限流器都假设单进程运行。

## 7. 反向代理（Nginx）

应用自带静态前端，所以 Nginx 只需把所有请求转发到 Uvicorn 端口：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 25m;   # 自定义图标上传

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # APK 构建可能较慢
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 8. HTTPS

iOS Web Clip 和 `.mobileconfig` 描述文件必须走 HTTPS。两种常见方案：

**方案 A — Cloudflare Tunnel**（无需开放入站端口，免费 TLS）：

```bash
cloudflared tunnel login
cloudflared tunnel create webtoapp
# 把一个主机名路由到隧道，再指向 http://127.0.0.1:8000
cloudflared tunnel route dns webtoapp your-domain.com
cloudflared tunnel run webtoapp
```

**方案 B — Nginx 上的 Let's Encrypt：**

```bash
sudo certbot --nginx -d your-domain.com
```

无论哪种，都要设置 `PUBLIC_BASE_URL=https://your-domain.com`。

## 9. 安卓 APK 构建（可选）

要产出真实可安装的 WebView APK，服务器需要安卓构建工具：

- 带 `aapt2`、`d8`、`apksigner`、`zipalign` 的 Android SDK
- `apktool`
- 提供 `java`、`javac`、`keytool` 的 JDK

### 一键安装（Linux）

```bash
# 需要 root 或可写 /opt 与 /usr/local/bin
sudo bash server/scripts/install_android_sdk.sh
```

脚本默认安装到 `/opt/android-sdk`（platform 36 + build-tools 36.0.0），并把 `apktool` 放到
`server/engine/_android_tools/apktool.jar` + `/usr/local/bin/apktool`。

然后在环境文件中设置（systemd 的 `EnvironmentFile` 亦可）：

```bash
ANDROID_HOME=/opt/android-sdk
ANDROID_SDK_ROOT=/opt/android-sdk
PATH=/opt/android-sdk/build-tools/36.0.0:/opt/android-sdk/platform-tools:/usr/local/bin:$PATH
```

重启服务后访问 `/api/metrics`，应看到 `"android_apk": true`。

### 把历史 zip 降级包重打包成真 APK

若服务器曾经缺少 SDK，部分应用只有 `android.zip`。工具链就绪后可批量重建：

```bash
# 仅重建缺少 android.apk 的应用，并上传到 R2（若已配置）
python -m server.scripts.rebuild_android_apks

# 只重建前 20 个 / 指定 app
python -m server.scripts.rebuild_android_apks --limit 20
python -m server.scripts.rebuild_android_apks --app-id abcd1234
```

每个生成的应用都有**自己独立的**签名证书（存放在 `ANDROID_KEYSTORE_DIR`），因此更新可原地安装。

**没有 SDK 时**，跳过 APK 生成，安卓用户改为获得可安装的 PWA 包——其余功能照常工作。

## 10. iOS 描述文件签名（可选）

默认情况下 iOS 的 `.mobileconfig` 是未签名的（iOS 仍可安装，只是显示"未验证"）。要让 iOS 显示你的域名为来源，通过 `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` 提供公开 CA 证书，或放入 `certs/ios-cert.pem`、`certs/ios-key.pem`、`certs/ios-chain.pem`。签名使用系统 `openssl`。详见 [`certs/README.md`](../certs/README.md)。

## 11. Cloudflare R2 卸载（可选）

### 工作机制

生成的安装包（APK / ZIP / `.mobileconfig`）可能很大，每次下载都从源站发出会消耗其带宽。启用 R2 后：

1. **每次构建后**，`generated/<app_id>/downloads/` 里的每个文件都会以 `<app_id>/downloads/<文件名>` 为 key 上传到 R2（见 `server/engine/storage.py`），生成的公开 URL 会以 `downloads_cdn` 映射写入该应用的 `recipe.json`。
2. **下载时**，`GET /a/<id>/download/<platform>` 优先使用 `downloads_cdn` 里的 CDN URL，返回 **302 跳转**到 R2；若不存在，则回退为发送本地文件。于是源站只在构建时花 CPU，而不会在每次分享 / 扫码时消耗带宽。
3. **清理时**，应用被回收时，其在 R2 中 `<app_id>/` 下的对象也会一并删除。

只要任一 `R2_*` 变量未设置，整个功能就是空操作，下载走本地——不会出错。在启用 R2 之前构建的旧应用，可用 `python -m server.scripts.backfill_r2` 迁移。

> **实现说明：** R2 使用 S3 API，鉴权采用 AWS Signature V4。为避免引入庞大的 `boto3`/`botocore`，`server/engine/storage.py` 自带 SigV4 签名实现（仅用标准库 `hmac`/`hashlib`），并通过应用已有的 `httpx` 发送请求。因此 R2 卸载**无需 AWS SDK**；该签名实现已对照 AWS 官方 SigV4 测试向量校验（`python -m server.engine.storage`）。

### 配置步骤

1. 在 Cloudflare 控制台打开 **R2**，创建一个桶，例如 `webtoapp-downloads`。
2. **Manage R2 API Tokens → Create API Token**，权限选 **Object Read & Write**。复制 **Access Key ID** 和 **Secret Access Key**（密钥只显示一次）。
3. 把桶设为公开：桶 **Settings → Public access**。要么启用 **r2.dev** 开发地址（`https://pub-xxxx.r2.dev`）快速起步，要么添加 **自定义域名**（如 `files.example.com`）以额外获得边缘缓存。
   > 自定义域名必须属于**与桶同一个 Cloudflare 账号**所管理的域。
4. 在 `webtoapp.env` 里设置这 5 个变量：

   ```bash
   R2_ACCOUNT_ID=...            # 你的账号 ID（hex）
   R2_BUCKET=webtoapp-downloads
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev   # 或 https://files.example.com
   ```
5. 重启服务。新构建的下载现在会跳转到 R2。

> **r2.dev 与自定义域：** `pub-xxxx.r2.dev` 本身就已经从 Cloudflare 全球边缘发出。自定义域额外带来边缘**缓存**（同一文件的重复下载直接命中缓存、不回源 R2），流量越大越划算。

### 回填旧应用

启用 R2 之前构建的应用仍指向本地文件。一次性把它们的产物上传到 R2 并更新 `downloads_cdn`：

```bash
set -a; . ./webtoapp.env; set +a
venv/bin/python -m server.scripts.backfill_r2 --dry-run   # 预览
venv/bin/python -m server.scripts.backfill_r2             # 实际执行
```

脚本是幂等的——可安全重复运行。

## 12. 更新

```bash
git pull
source venv/bin/activate
pip install -r server/requirements.txt   # 若依赖有变化
sudo systemctl restart webtoapp
```

如果你改了前端资源（`css/`、`js/`），记得在 `index.html` 里把 `?v=` 版本号 bump 一下，让浏览器拉取新文件而非缓存。

## 13. 故障排查

| 现象 | 可能原因 / 解决 |
| --- | --- |
| iPhone 在 Safari 里打开页面而非全屏 | 未设置 `PUBLIC_BASE_URL`，或不是 HTTPS。 |
| 安卓下载是 PWA zip 而非 APK | 服务器未安装 Android SDK / apktool（见 §9）。 |
| 下载仍从源站发出 | 某个 `R2_*` 变量缺失，或设置后未重启。旧应用需跑回填（§11）。 |
| iOS 描述文件显示"未验证" | 描述文件未签名。提供公开 CA 证书（§10）。 |
| `502 Bad Gateway` | 服务未运行或端口不对——`systemctl status webtoapp`。 |
| 构建接口返回 `429` | 触发每设备每日配额或每 IP 限流。调整 `DAILY_BUILD_QUOTA`。 |

---

另见 [README](README.zh.md) 了解项目概览。

<div align="center">

<img src="../assets/site-logo.jpg" alt="WebToApp" width="120" height="120" style="border-radius: 24px;">

# WebToApp

**几秒钟把任意网站变成可安装的应用。**

输入一个链接，输出覆盖 **iPhone / iPad · Android · Windows · macOS · Linux** 的成品——还自带公开应用市场、创建者主页、评论和评分，全程无需注册。

[![在线演示](https://img.shields.io/badge/在线演示-shiaho.sbs-c97953?style=for-the-badge)](https://shiaho.sbs)
[![CI](https://img.shields.io/badge/CI-pytest%20336-059669?style=for-the-badge)](https://github.com/shiaho777/WebToApp/actions)
[![许可证: MIT](https://img.shields.io/badge/License-MIT-1e1914?style=for-the-badge)](../LICENSE)
[![平台](https://img.shields.io/badge/平台-5-736357?style=for-the-badge)](#你能得到什么)

[English](../README.md) · **简体中文** · [日本語](README.ja.md) · [العربية](README.ar.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Português](README.pt.md) · [Français](README.fr.md) · [Deutsch](README.de.md)

</div>

---

## 你能得到什么

输入一个网址——或者上传你自己的 `.html` / `.zip`——几秒钟后得到一个覆盖全平台的可安装成品。每个产物都只是指向你站点的轻量原生壳，所以体积按 **KB 而不是 MB** 计算，下载安装几乎瞬间完成。

每个生成的应用都有自己的下载页 `/a/<id>`：平台安装入口、可折叠的「关于本页」区块（创作者可以填入真实内容）、以及带评论和星级评分的社区层。以公链形式发布后，它还会出现在**应用市场**里供所有人发现。

开源 · 免费 · 无需登录。在线体验：**[shiaho.sbs](https://shiaho.sbs)**。

---

## 截图

<p align="center"><img src="assets/shots/landing.png" alt="落地页：粘贴链接即可开始——生成应用数、下载量、访问量实时计数" width="820"></p>
<p align="center"><em>粘贴链接（或拖入 HTML 文件）——计数器是实时数据。</em></p>

<p align="center"><img src="assets/shots/config-about.png" alt="应用配置：名称、描述、「关于本页」文本与最多 3 张自动压缩的图片" width="820"></p>
<p align="center"><em>名称、一句话描述，以及创作者自己写的「关于本页」内容，最多 3 张图——超过 800KB 自动近无损压缩。</em></p>

<p align="center"><img src="assets/shots/config-platforms.png" alt="主题色、恢复的图标与按平台的设置（如 Android 沉浸模式）" width="820"></p>
<p align="center"><em>主题色和图标自动从站点恢复；可按平台调设置，比如 Android 沉浸式全屏。</em></p>

<p align="center"><img src="assets/shots/config-publish.png" alt="生成前的链接可见性与必选标签" width="820"></p>
<p align="center"><em>默认私链或发布到市场——标签必选，保证应用可被发现。</em></p>

<p align="center"><img src="assets/shots/download-page.png" alt="生成的下载页：评分、创作者卡片、评论区与分平台安装列表" width="820"></p>
<p align="center"><em>生成的应用页：右侧安装列表，左侧评分 / 创作者 / 评论。</em></p>

<p align="center"><img src="assets/shots/about-fold.png" alt="展开的「关于本页」折叠区，显示创作者文本与上传图片" width="820"></p>
<p align="center"><em>「关于本页」折叠区承载创作者自己的图文——不再是口水话占位。</em></p>

<p align="center"><img src="assets/shots/market.png" alt="公链市场：每张卡片带创作者、标签、相对时间与评分" width="820"></p>
<p align="center"><em>公链市场：创作者卡片、标签筛选、搜索，以及最新 / 评分最高 / 下载最多 / 访问最多排序。</em></p>

<p align="center"><img src="assets/shots/history.png" alt="按设备的构建历史：访问统计、导出与导入" width="820"></p>
<p align="center"><em>历史记录保存在你的设备指纹下——带访问统计、重新生成、跨设备导出/导入。</em></p>

---

## 工作原理

<p align="center"><img src="assets/fig-pipeline.svg" alt="管线：URL 或 HTML 输入 → 分析 + recipe → 五平台并行构建 → 带社区的应用页" width="800"></p>

1. **输入**——粘贴网址，或上传单个 `.html` 文件 / 含 `index.html` 的 `.zip`。上传的 HTML 由服务器托管在 `/a/<id>/site/...` 下，打包流程与网址模式一致。
2. **分析 + recipe**——分析器抓取页面，提取名称、主题色和图标（多候选抓取、取最高分辨率），构建所需的一切固化进 `recipe.json`。
3. **并行构建**——五平台安装包同时构建；某一端失败（如缺 Android 工具链）只降级该端。
4. **应用页**——下载页渲染各平台安装项、创作者的「关于」内容和社区区块。

## 功能

- **两种输入方式**：网站链接，或你自己的 HTML（单个 `.html` 或含 `index.html` 的 `.zip`）——托管打包与网址应用一致。
- **站点分析**：名称、主题色、最高分辨率图标，以及广告/追踪器/弹窗统计（展示用估算）。
- **多平台打包**，一次构建 → 五个产物：
  - **Android**——真实可安装的 WebView APK（v1+v2+v3 签名），每个应用使用**独立签名证书**。
  - **iOS / iPadOS**——`.mobileconfig` Web Clip 描述文件，支持公共 CA 证书 CMS 签名（「免签」安装）。
  - **macOS**——独立 WKWebView `.app` 窗口（无地址栏，不依赖第三方浏览器）。
  - **Windows / Linux**——轻量 `.bat` / `.desktop` 启动器，以应用模式打开系统浏览器。
- **创作者「关于本页」**：应用页支持富文本加最多 3 张图片。上传内容经解码验证、剥离 EXIF 并重编码为 WebP——超过 800KB 由服务端近无损压缩。
- **无账号社区**：设备指纹即持久身份（`?u=N`）——可改名、Markdown 简介、头像。你的应用带创作者卡片，并拥有公开主页。
- **评论与评分**：每个应用页有评论区，可附 1–5 星评分；平均分汇总到市场卡片。
- **公链市场**：标签筛选、搜索，支持最新、评分最高（先均分后数量）、下载最多、访问最多排序——相对时间显示。
- **iOS 动态换链**：Web Clip 指向 `/a/<id>/launch`，后台改 URL 无需重装。
- **按设备历史**：构建记录绑定设备指纹，带访问/下载统计、重新生成、跨设备导出/导入。删除条目会彻底移除应用。
- **自动清理**：连续 30 天无访问的应用自动回收。
- **可选 Cloudflare R2 卸载**：下载 302 到 CDN，节省源站带宽。
- **多语言界面**：9 种语言——English、简体中文、日本語、العربية（RTL）、Русский、Español、Português、Français、Deutsch——生成的下载页同样本地化。

## 无需注册的社区

<p align="center"><img src="assets/fig-community.svg" alt="设备指纹变成顺序公开用户号，解锁创作者署名、主页、评论与评分" width="800"></p>

无需注册：设备指纹首次出现时即分配一个顺序公开编号。这个 `#N` 就是真实身份——设置显示名、Markdown 简介和头像后，你发布的每个应用都带创作者卡片。其他人打开 `?u=N` 就能看到你的公开主页和发布的应用。评论支持可选星级评分，并实时反映到市场卡片上。

## 应用体积

每个安装包都只是指向你站点的轻量入口——不打包站点内容，所以体积按 **KB 而不是 MB** 计算。

<p align="center"><img src="assets/fig-sizes.svg" alt="实测包体：macOS 135KB、Android 21KB、iOS 4KB、Windows 1.2KB、Linux 0.7KB" width="760"></p>

| 平台 | 包 | 典型体积 | 内容 |
| --- | --- | --- | --- |
| Android | `android.apk` | **~21 KB** | 真实可安装的 WebView APK（v1+v2+v3 签名） |
| iOS / iPadOS | `ios.mobileconfig` | **~4 KB** | Web Clip 描述文件 |
| macOS | `macos.zip` | **~135 KB** | `.app` 包（原生 WKWebView 窗口 + 图标） |
| Windows | `windows.zip` | **~1.2 KB** | `.bat` 启动器 + 桌面快捷方式助手 + 图标 |
| Linux | `linux.tar.gz` | **~0.7 KB** | `.desktop` 项 + 安装脚本 + 图标 |

## 技术栈

- 后端：Python + FastAPI + Uvicorn · SQLite 存储（历史、任务、社区）
- 前端：纯 HTML / CSS / JS——无构建步骤，由后端直接提供
- 打包：Android SDK（aapt2 / d8 / apktool / apksigner / zipalign）、Pillow、openssl
- CI：`pytest tests/`，覆盖 Python 3.10 / 3.11 / 3.12——**336 项测试**

## 项目结构

```
.
├── index.html                 落地页 + 构建表单
├── css/ js/ assets/           前端静态资源
│   ├── js/i18n.js             轻量 i18n 运行时（9 语言）
│   ├── js/i18n.strings.js     全部翻译
│   ├── js/community.js        应用页评论 / 评分 / 创作者区块
│   └── js/mdmini.js           简介用迷你 Markdown 渲染器
├── server/
│   ├── main.py                FastAPI 应用与路由（35 个端点）
│   ├── config.py              环境变量配置
│   ├── html_site.py           HTML 上传的暂存 / 校验 / 托管
│   ├── history_store.py       按设备历史 + 应用/访问统计（SQLite）
│   ├── community_store.py     资料、创作者、评论、评分（SQLite）
│   ├── task_store.py          构建任务队列持久化（SQLite）
│   └── engine/
│       ├── analyzer.py        站点分析
│       ├── distiller.py       recipe → 各平台包 + 下载页（核心）
│       ├── apk_builder.py     Android APK 构建与签名
│       ├── mobileconfig_signer.py  iOS 描述文件签名
│       ├── cache.py           抓取/图标缓存
│       └── storage.py         Cloudflare R2 卸载
├── certs/                     签名材料（私钥不入库）
└── generated/                 运行时生成的应用与数据（不入库）
```

## 快速开始

需要 Python 3.10+。构建 Android APK 需要 Android SDK 和 `apktool`（缺失时降级为 PWA 离线包）。

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt

# 2. 配置（可选，全部有默认值）
cp .env.example .env
# 按需编辑 .env

# 3. 运行
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000。

> 本地开发不需要任何环境变量。公网部署时请设置 `PUBLIC_BASE_URL`，
> 否则 iPhone 无法打开 `localhost`。完整列表见 [`.env.example`](../.env.example)。

## 部署

> 完整的生产部署教程（systemd、Nginx、HTTPS、Android/iOS、R2）见 **[DEPLOY.md](DEPLOY.md)**。

生产环境通常用 systemd 跑在 Nginx 反代之后：

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

iOS 描述文件签名（「免签」安装）的证书配置见 [`certs/README.md`](../certs/README.md)。

## Cloudflare R2 卸载的工作原理

生成的安装包可能不小，全从源站走下载会烧带宽。配置 R2 后：

1. **每次构建后**，`generated/<app_id>/downloads/` 下的所有文件镜像到 R2，键为 `<app_id>/downloads/<filename>`（`server/engine/storage.py`），公网 URL 写入该应用 `recipe.json` 的 `downloads_cdn` 映射。
2. **下载时**，`GET /a/<id>/download/<platform>` 优先取 `downloads_cdn` 里的 CDN 地址并 **302 重定向**到 R2；没有则回落到本地文件流。源站只在构建时花 CPU，不为每次分享和扫码烧带宽。
3. **清理时**，应用在 R2 上的 `<app_id>/` 前缀对象随本地数据一起删除。

任何 `R2_*` 变量未配置时该功能是空操作，下载走本地——不会出任何问题。启用 R2 之前构建的存量应用可用 `python -m server.scripts.backfill_r2` 迁移。完整配置步骤（存储桶、API 令牌、公开访问、自定义域名、回填）见 [DEPLOY.md §11](DEPLOY.md#11-cloudflare-r2-offload-可选)。

## 安全说明

- 所有密钥（R2、Cloudflare、签名密码）均从环境变量读取；仓库内不含任何真实凭证。
- **签名私钥（`certs/*.keystore`、`certs/app-keys/`）和运行时数据（`generated/`）默认被 `.gitignore` 排除——切勿提交。**
- 每个生成的 Android 应用使用独立签名证书，避免证书指纹被批量标记，也保证同一应用可原位升级。
- 创作者上传的「关于」图片经 Pillow 解码验证，受原始大小 / 像素数 / 数量上限约束，剥离全部元数据并重编码为 WebP——绝不按原样提供上传文件。
- 用户生成的文本渲染时全部 HTML 转义；应用内媒体路由只放行服务器生成的文件名。

## 许可证

[MIT](../LICENSE)

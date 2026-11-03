<div align="center">

# WebToApp — دليل النشر

[English](DEPLOY.md) · [简体中文](DEPLOY.zh.md) · [日本語](DEPLOY.ja.md) · **العربية** · [Русский](DEPLOY.ru.md) · [Español](DEPLOY.es.md) · [Português](DEPLOY.pt.md) · [Français](DEPLOY.fr.md) · [Deutsch](DEPLOY.de.md)

دليل خطوة بخطوة لتشغيل WebToApp في بيئة الإنتاج.

</div>

---

<div dir="rtl">

## المحتويات

1. [المتطلبات](#1-المتطلبات)
2. [الحصول على الكود](#2-الحصول-على-الكود)
3. [بيئة Python](#3-بيئة-python)
4. [الإعداد](#4-الإعداد)
5. [التشغيل محليًا](#5-التشغيل-محليًا)
   - [Docker](#docker)
6. [التشغيل كخدمة (systemd)](#6-التشغيل-كخدمة-systemd)
7. [الوكيل العكسي (Nginx)](#7-الوكيل-العكسي-nginx)
8. [HTTPS](#8-https)
9. [بناء Android APK (اختياري)](#9-بناء-android-apk-اختياري)
10. [توقيع ملف iOS (اختياري)](#10-توقيع-ملف-ios-اختياري)
11. [تفريغ Cloudflare R2 (اختياري)](#11-تفريغ-cloudflare-r2-اختياري)
12. [التحديث](#12-التحديث)
13. [استكشاف الأخطاء](#13-استكشاف-الأخطاء)

## 1. المتطلبات

- **Python 3.10+**
- خادم Linux (أي توزيعة). نواة واحدة / 1 جيجابايت رام تكفي للبداية.
- وصول إلى الإنترنت الخارجي (يقوم المحلّل بجلب المواقع المستهدفة).
- اختياري، فقط لبناء APK حقيقي لأندرويد: **Android SDK** (‏`aapt2`، `d8`، `apksigner`، `zipalign`)، و**apktool**، و**JDK** (‏`java` / `javac` / `keytool`). بدونها، يعود أندرويد إلى حزمة PWA قابلة للتثبيت.
- اختياري، فقط لتوقيع iOS: **openssl** (موجود في كل توزيعات Linux تقريبًا).

التبعية الإلزامية الوحيدة هي Python. كل ما عداها اختياري ويتراجع بسلاسة.

## 2. الحصول على الكود

</div>

```bash
git clone https://github.com/shiaho777/WebToApp.git
cd WebToApp
```

<div dir="rtl">

## 3. بيئة Python

</div>

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

<div dir="rtl">

يثبّت هذا التبعيات الأربع: ‏`fastapi`، `uvicorn[standard]`، `httpx`، `Pillow`. ‏تفريغ Cloudflare R2 (اختياري) لا يحتاج أي حزمة إضافية — انظر §11.

## 4. الإعداد

تُقرأ كل الإعدادات من متغيّرات البيئة — كلها اختيارية وبقيم افتراضية معقولة.

</div>

```bash
cp .env.example .env
# عدّل .env
```

<div dir="rtl">

| المتغيّر | الغرض | الافتراضي |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | الأصل العام، مثل `https://app.example.com`. مطلوب في الإنتاج وإلا حاول iPhone فتح `localhost`. | يُستنتج من ترويسة Host |
| `ANDROID_PACKAGE_PREFIX` | بادئة حزمة أندرويد الافتراضية. | `com.webtoapp` |
| `ANDROID_KEYSTORE_DIR` | مكان مخازن مفاتيح التوقيع لكل تطبيق. ضعه خارج أي مسار عام. | `certs/app-keys` |
| `DAILY_BUILD_QUOTA` | حد البناء اليومي لكل جهاز (`0` لتعطيله). | `10` |
| `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` | شهادة CA عامة لتوقيع ملفات iOS. | غير مضبوط (غير موقّع، قابل للتثبيت) |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_PUBLIC_BASE_URL` | تفريغ Cloudflare R2 (انظر §11). | غير مضبوط (التنزيلات محليًا) |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` | تفريغ فوري لذاكرة إعادة توجيه iOS `/launch` عند تبديل الرابط. | غير مضبوط |

> **لا تُودِع ملف `.env` الحقيقي أبدًا.** إنه متجاهَل في git افتراضيًا.

## 5. التشغيل محليًا

</div>

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

<div dir="rtl">

افتح <http://127.0.0.1:8000>. للتطوير المحلي لا تحتاج أي متغيّرات بيئة.

## Docker

أمر واحد يبني الصورة ويشغّل الموقع على المنفذ 8000. الصورة الافتراضية تتضمن Python وJDK وAndroid SDK وapktool، لذا حزم أندرويد هي APK حقيقية. التطبيقات المُنشأة ومفاتيح التوقيع تبقى بعد إعادة البناء.

</div>

```bash
cp .env.example .env
# قبل النشر اضبط PUBLIC_BASE_URL=https://your-domain.com.
docker compose up -d --build
```

<div dir="rtl">

افتح <http://127.0.0.1:8000>. البناء الأول ينزّل Android SDK من `dl.google.com` وapktool من GitHub. يلزم اتصال خارجي ونحو 2 غيغابايت من الذاكرة.

ما يُحفَظ:

- المجلد `webtoapp-generated` — التطبيقات والسجل وقاعدة المجتمع
- `./certs` — مفاتيح أندرويد لكل تطبيق وملفات PEM اختيارية لـ iOS (`ios-cert.pem` و`ios-key.pem` و`ios-chain.pem`)

ضع وكيلاً عكسياً أمام المنفذ 8000. الوكلاء على عناوين خاصة يُوثَقون لترويسات `X-Forwarded-*`. وإلا فاضبط `DOCKER_TRUSTED_PROXY_CIDRS` في `.env`.

صورة أصغر بلا سلسلة أندرويد (يصبح أندرويد ملف PWA مضغوطاً):

</div>

```bash
WITH_ANDROID=0 docker compose up -d --build
```

<div dir="rtl">

التحديث:

</div>

```bash
git pull
docker compose up -d --build
```

<div dir="rtl">

## 6. التشغيل كخدمة (systemd)

احفظ الأسرار في ملف بيئة محدود الصلاحيات بدلًا من كتابتها داخل الوحدة:

</div>

```bash
# /path/to/WebToApp/webtoapp.env  (chmod 600)
PUBLIC_BASE_URL=https://your-domain.com
# أضف R2_* / IOS_* / CLOUDFLARE_* حسب الحاجة
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

<div dir="rtl">

> أبقِ `--workers 1`. يفترض طابور البناء ومحدّد المعدل في الذاكرة عمليةً واحدة.

## 7. الوكيل العكسي (Nginx)

يقدّم التطبيق واجهته الثابتة بنفسه، لذا يكفي أن يمرّر Nginx كل شيء إلى منفذ Uvicorn:

</div>

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 25m;   # رفع الأيقونات المخصصة

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # قد يستغرق بناء APK وقتًا
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

<div dir="rtl">

## 8. HTTPS

تتطلب Web Clips على iOS وملفات `.mobileconfig` بروتوكول HTTPS. خياران شائعان:

**الخيار أ — Cloudflare Tunnel** (دون فتح منافذ واردة، TLS مجاني):

</div>

```bash
cloudflared tunnel login
cloudflared tunnel create webtoapp
cloudflared tunnel route dns webtoapp your-domain.com
cloudflared tunnel run webtoapp
```

<div dir="rtl">

**الخيار ب — Let's Encrypt على Nginx:**

</div>

```bash
sudo certbot --nginx -d your-domain.com
```

<div dir="rtl">

في الحالتين، اضبط `PUBLIC_BASE_URL=https://your-domain.com`.

## 9. بناء Android APK (اختياري)

لإنتاج APK حقيقي قابل للتثبيت بنمط WebView، يحتاج الخادم أدوات بناء أندرويد:

- Android SDK مع `aapt2`، `d8`، `apksigner`، `zipalign`
- `apktool`
- JDK يوفّر `java`، `javac`، `keytool`

وجّه التطبيق إلى الـ SDK عبر `ANDROID_HOME` / `ANDROID_SDK_ROOT` إن لم يُكتشف تلقائيًا. يحصل كل تطبيق مُولَّد على شهادة توقيع **خاصة به** (تُخزَّن في `ANDROID_KEYSTORE_DIR`)، لذا تُثبَّت التحديثات فوق بعضها.

**بدون الـ SDK**، يُتخطى إنشاء APK ويحصل مستخدمو أندرويد على حزمة PWA قابلة للتثبيت — وكل شيء آخر يستمر بالعمل.

## 10. توقيع ملف iOS (اختياري)

افتراضيًا يكون ملف `.mobileconfig` لـ iOS غير موقّع (يثبّته iOS لكنه يعرض "غير موثّق"). لإظهار نطاقك كمصدر، وفّر شهادة CA عامة عبر `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE`، أو ضع `certs/ios-cert.pem` و`certs/ios-key.pem` و`certs/ios-chain.pem`. يستخدم التوقيع `openssl` النظامي. انظر [`certs/README.md`](../certs/README.md).

## 11. تفريغ Cloudflare R2 (اختياري)

### كيف يعمل

قد تكون المُثبِّتات المُولَّدة (APK / ZIP / ‏`.mobileconfig`) كبيرة، وتقديم كل تنزيل من المصدر يستهلك عرض النطاق. عند تفعيل R2:

1. **بعد كل بناء**، يُرفع كل ملف في `generated/<app_id>/downloads/` إلى R2 بالمفتاح `<app_id>/downloads/<اسم-الملف>` (انظر `server/engine/storage.py`)، وتُكتب الروابط العامة الناتجة في `recipe.json` للتطبيق كخريطة `downloads_cdn`.
2. **عند التنزيل**، يفضّل `GET /a/<id>/download/<platform>` رابط CDN في `downloads_cdn` ويُعيد **إعادة توجيه 302** إلى R2؛ وإن غاب، يعود إلى بثّ الملف المحلي. وهكذا يُنفق المصدر معالجة أثناء البناء فقط، لا عرض نطاق عند كل مشاركة أو مسح QR.
3. **عند التنظيف**، تُحذف كائنات التطبيق تحت `<app_id>/` من R2 مع بياناته المحلية.

إن لم يُضبط أي متغيّر `R2_*` يصبح كل ذلك بلا أثر وتُقدَّم التنزيلات محليًا — لا شيء ينكسر. يمكن ترحيل التطبيقات القديمة المبنية قبل التفعيل عبر `python -m server.scripts.backfill_r2`.

> **ملاحظة حول التنفيذ:** يستخدم R2 واجهة S3 التي تُصادِق بتوقيع AWS Signature V4. بدلًا من جلب حزمة `boto3`/`botocore` الثقيلة، يتضمّن `server/engine/storage.py` مُوقِّع SigV4 خاصًّا به (بالمكتبة القياسية `hmac`/`hashlib` فقط) ويرسل الطلبات عبر `httpx` — وهو عميل HTTP الذي يستخدمه التطبيق أصلًا. لذا لا يحتاج تفريغ R2 إلى **أي AWS SDK**؛ وقد تم التحقق من المُوقِّع مقابل متجهات اختبار SigV4 المنشورة من AWS (‏`python -m server.engine.storage`).

### الإعداد

1. في لوحة Cloudflare، افتح **R2** وأنشئ حاوية، مثل `webtoapp-downloads`.
2. **Manage R2 API Tokens → Create API Token** بصلاحية **Object Read & Write**. انسخ **Access Key ID** و**Secret Access Key** (يُعرض السر مرة واحدة فقط).
3. اجعل الحاوية عامة: **Settings → Public access**. إمّا فعّل رابط التطوير **r2.dev** (‏`https://pub-xxxx.r2.dev`) للبدء السريع، أو أضف **نطاقًا مخصصًا** (مثل `files.example.com`) للحصول أيضًا على التخزين المؤقت عند الحافة.
   > يجب أن يكون النطاق المخصص ضمن نطاق يديره **نفس حساب Cloudflare** الخاص بالحاوية.
4. اضبط المتغيّرات الخمسة في `webtoapp.env`:

</div>

```bash
R2_ACCOUNT_ID=...            # معرّف الحساب (hex)
R2_BUCKET=webtoapp-downloads
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev   # أو https://files.example.com
```

<div dir="rtl">

5. أعد تشغيل الخدمة. تُعيد عمليات البناء الجديدة توجيه التنزيلات إلى R2.

> **r2.dev مقابل النطاق المخصص:** يقدّم `pub-xxxx.r2.dev` أصلًا من حافة Cloudflare العالمية. يضيف النطاق المخصص **تخزينًا مؤقتًا** عند الحافة (تُقدَّم التنزيلات المتكررة لنفس الملف من الذاكرة دون لمس R2)، وهو أنفع كلما زادت حركة المرور.

### ترحيل التطبيقات الموجودة

ما زالت التطبيقات المبنية قبل تفعيل R2 تشير إلى ملفات محلية. ارفع منتجاتها إلى R2 وحدّث `downloads_cdn` دفعة واحدة:

</div>

```bash
set -a; . ./webtoapp.env; set +a
venv/bin/python -m server.scripts.backfill_r2 --dry-run   # معاينة
venv/bin/python -m server.scripts.backfill_r2             # تنفيذ
```

<div dir="rtl">

السكربت عديم التأثير الجانبي — آمن لإعادة التشغيل.

## 12. التحديث

</div>

```bash
git pull
source venv/bin/activate
pip install -r server/requirements.txt   # إن تغيّرت التبعيات
sudo systemctl restart webtoapp
```

<div dir="rtl">

إن غيّرت أصول الواجهة (`css/`، `js/`)، حدّث سلسلة الاستعلام `?v=` في `index.html` ليجلب المتصفح الملفات الجديدة بدل المخزّنة.

## 13. استكشاف الأخطاء

| العَرَض | السبب المحتمل / الحل |
| --- | --- |
| يفتح iPhone الصفحة في Safari بدل ملء الشاشة | `PUBLIC_BASE_URL` غير مضبوط، أو ليس HTTPS. |
| تنزيل أندرويد عبارة عن zip لـ PWA لا APK | لم تُثبَّت Android SDK / apktool على الخادم (§9). |
| ما زالت التنزيلات تُقدَّم من المصدر | متغيّر `R2_*` ناقص، أو لم تُعد التشغيل بعد ضبطه. شغّل الترحيل للتطبيقات القديمة (§11). |
| يعرض ملف iOS "غير موثّق" | الملف غير موقّع. وفّر شهادة CA عامة (§10). |
| `502 Bad Gateway` | الخدمة لا تعمل أو المنفذ خاطئ — `systemctl status webtoapp`. |
| تُعيد نقطة البناء `429` | بلغت حصة الجهاز اليومية أو حد معدل الـ IP. اضبط `DAILY_BUILD_QUOTA`. |

انظر أيضًا [README](README.ar.md) لنظرة عامة على المشروع.

</div>

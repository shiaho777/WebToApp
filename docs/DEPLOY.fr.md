<div align="center">

# WebToApp — Guide de déploiement

[English](DEPLOY.md) · [简体中文](DEPLOY.zh.md) · [日本語](DEPLOY.ja.md) · [العربية](DEPLOY.ar.md) · [Русский](DEPLOY.ru.md) · [Español](DEPLOY.es.md) · [Português](DEPLOY.pt.md) · **Français** · [Deutsch](DEPLOY.de.md)

Guide pas à pas pour exécuter WebToApp en production.

</div>

---

## Sommaire

1. [Prérequis](#1-prérequis)
2. [Récupérer le code](#2-récupérer-le-code)
3. [Environnement Python](#3-environnement-python)
4. [Configuration](#4-configuration)
5. [Lancer en local](#5-lancer-en-local)
   - [Docker](#docker)
6. [Lancer en tant que service (systemd)](#6-lancer-en-tant-que-service-systemd)
7. [Proxy inverse (Nginx)](#7-proxy-inverse-nginx)
8. [HTTPS](#8-https)
9. [Build d'APK Android (optionnel)](#9-build-dapk-android-optionnel)
10. [Signature de profil iOS (optionnel)](#10-signature-de-profil-ios-optionnel)
11. [Déchargement vers Cloudflare R2 (optionnel)](#11-déchargement-vers-cloudflare-r2-optionnel)
12. [Mise à jour](#12-mise-à-jour)
13. [Dépannage](#13-dépannage)

---

## 1. Prérequis

- **Python 3.10+**
- Un serveur Linux (n'importe quelle distribution). 1 vCPU / 1 Go de RAM suffisent pour démarrer.
- Un accès internet sortant (l'analyseur récupère les sites cibles).
- Optionnel, seulement pour de vrais builds d'APK Android : **Android SDK** (`aapt2`, `d8`, `apksigner`, `zipalign`), **apktool**, un **JDK** (`java` / `javac` / `keytool`). Sans eux, Android se rabat sur un paquet PWA installable.
- Optionnel, seulement pour la signature iOS : **openssl** (présent sur quasiment tout Linux).

La seule dépendance obligatoire est Python. Tout le reste est optionnel et se dégrade en douceur.

## 2. Récupérer le code

```bash
git clone https://github.com/shiaho777/WebToApp.git
cd WebToApp
```

## 3. Environnement Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

Cela installe les quatre dépendances d'exécution : `fastapi`, `uvicorn[standard]`, `httpx`, `Pillow`. Le déchargement vers Cloudflare R2 (optionnel) ne nécessite aucun paquet supplémentaire — voir §11.

## 4. Configuration

Toute la configuration est lue depuis des variables d'environnement — chacune est optionnelle avec une valeur par défaut raisonnable.

```bash
cp .env.example .env
# éditez .env
```

| Variable | Rôle | Par défaut |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | Origine publique, ex. `https://app.example.com`. Obligatoire en production sinon l'iPhone tente d'ouvrir `localhost`. | déduite de l'en-tête Host |
| `ANDROID_PACKAGE_PREFIX` | Préfixe de package Android par défaut. | `com.webtoapp` |
| `ANDROID_KEYSTORE_DIR` | Où sont stockés les keystores de signature par app. À garder HORS de tout chemin public. | `certs/app-keys` |
| `DAILY_BUILD_QUOTA` | Limite de builds quotidienne par appareil (`0` désactive). | `10` |
| `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` | Certificat d'AC publique pour signer les profils iOS. | non défini (non signé, installable quand même) |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_PUBLIC_BASE_URL` | Déchargement vers Cloudflare R2 (voir §11). | non défini (téléchargements en local) |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` | Purge immédiate de la redirection iOS `/launch` lors d'un changement d'URL. | non défini |

> **Ne committez jamais votre vrai `.env`.** Il est ignoré par git par défaut.

## 5. Lancer en local

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Ouvrez <http://127.0.0.1:8000>. En développement local, aucune variable d'environnement n'est nécessaire.

## Docker

Une commande construit l'image et démarre le site sur le port 8000. L'image par défaut contient Python, un JDK, le SDK Android et apktool : les paquets Android sont de vrais APK. Les applis déjà générées et les clés de signature survivent à une reconstruction.

```bash
cp .env.example .env
# Avant de publier, réglez PUBLIC_BASE_URL=https://your-domain.com.
docker compose up -d --build
```

Ouvrez <http://127.0.0.1:8000>. Le premier build télécharge le SDK Android depuis `dl.google.com` et apktool depuis GitHub. Il faut un accès sortant et environ 2 Go de RAM.

Ce qui est conservé :

- le volume `webtoapp-generated` — applis, historique et base communautaire
- `./certs` — keystores Android par appli, et PEM iOS facultatifs (`ios-cert.pem`, `ios-key.pem`, `ios-chain.pem`)

Placez un reverse proxy devant le port 8000. Les proxys sur une adresse privée sont autorisés à envoyer `X-Forwarded-*`. Sinon, définissez `DOCKER_TRUSTED_PROXY_CIDRS` dans `.env`.

Image plus petite, sans la chaîne Android (Android devient un zip PWA) :

```bash
WITH_ANDROID=0 docker compose up -d --build
```

Mise à jour :

```bash
git pull
docker compose up -d --build
```

## 6. Lancer en tant que service (systemd)

Conservez les secrets dans un fichier d'environnement restreint plutôt qu'en ligne dans l'unité :

```bash
# /path/to/WebToApp/webtoapp.env  (chmod 600)
PUBLIC_BASE_URL=https://your-domain.com
# ajoutez R2_* / IOS_* / CLOUDFLARE_* au besoin
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

> Gardez `--workers 1`. La file de build et le limiteur de débit en mémoire supposent un seul processus.

## 7. Proxy inverse (Nginx)

L'app sert son propre frontend statique ; Nginx n'a donc qu'à tout relayer vers le port Uvicorn :

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 25m;   # envoi d'icônes personnalisées

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # un build d'APK peut prendre du temps
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 8. HTTPS

Les Web Clips iOS et les profils `.mobileconfig` exigent HTTPS. Deux options courantes :

**Option A — Cloudflare Tunnel** (aucun port entrant ouvert, TLS gratuit) :

```bash
cloudflared tunnel login
cloudflared tunnel create webtoapp
cloudflared tunnel route dns webtoapp your-domain.com
cloudflared tunnel run webtoapp
```

**Option B — Let's Encrypt sur Nginx :**

```bash
sudo certbot --nginx -d your-domain.com
```

Dans tous les cas, définissez `PUBLIC_BASE_URL=https://your-domain.com`.

## 9. Build d'APK Android (optionnel)

Pour produire un véritable APK WebView installable, le serveur a besoin des outils de build Android :

- Android SDK avec `aapt2`, `d8`, `apksigner`, `zipalign`
- `apktool`
- un JDK fournissant `java`, `javac`, `keytool`

Pointez l'app vers le SDK via `ANDROID_HOME` / `ANDROID_SDK_ROOT` s'il n'est pas détecté automatiquement. Chaque app générée reçoit son **propre** certificat de signature (dans `ANDROID_KEYSTORE_DIR`), de sorte que les mises à jour s'installent par-dessus.

**Sans le SDK**, la génération d'APK est ignorée et les utilisateurs Android reçoivent un paquet PWA installable — tout le reste fonctionne.

## 10. Signature de profil iOS (optionnel)

Par défaut, le `.mobileconfig` iOS n'est pas signé (iOS l'installe quand même mais affiche « Non vérifié »). Pour qu'iOS affiche votre domaine comme source, fournissez un certificat d'AC publique via `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE`, ou déposez `certs/ios-cert.pem`, `certs/ios-key.pem`, `certs/ios-chain.pem`. La signature utilise le `openssl` du système. Voir [`certs/README.md`](../certs/README.md).

## 11. Déchargement vers Cloudflare R2 (optionnel)

### Fonctionnement

Les installeurs générés (APK / ZIP / `.mobileconfig`) peuvent être lourds, et servir chaque téléchargement depuis l'origine consomme sa bande passante. Avec R2 activé :

1. **Après chaque build**, chaque fichier de `generated/<app_id>/downloads/` est envoyé vers R2 sous la clé `<app_id>/downloads/<nom>` (voir `server/engine/storage.py`), et les URL publiques obtenues sont écrites dans le `recipe.json` de l'app comme une carte `downloads_cdn`.
2. **Au téléchargement**, `GET /a/<id>/download/<platform>` privilégie l'URL CDN de `downloads_cdn` et renvoie une **redirection 302** vers R2 ; en son absence, il se rabat sur le fichier local. L'origine ne dépense donc du CPU que pendant les builds, pas de bande passante à chaque partage ou scan de QR.
3. **Au nettoyage**, les objets de l'app sous `<app_id>/` sont supprimés de R2 en même temps que ses données locales.

Si une variable `R2_*` manque, la fonctionnalité devient un no-op et les téléchargements sont servis en local — rien ne casse. Les apps créées avant l'activation de R2 se migrent avec `python -m server.scripts.backfill_r2`.

> **Note d'implémentation :** R2 parle l'API S3, qui s'authentifie avec AWS Signature V4. Plutôt que d'embarquer la lourde pile `boto3`/`botocore`, `server/engine/storage.py` fournit son propre signataire SigV4 (uniquement avec la bibliothèque standard `hmac`/`hashlib`) et envoie les requêtes via `httpx`, le client HTTP que l'app utilise déjà. Le déchargement vers R2 **ne nécessite donc aucun SDK AWS** ; le signataire est validé avec les vecteurs de test SigV4 publiés par AWS (`python -m server.engine.storage`).

### Mise en place

1. Dans le tableau de bord Cloudflare, ouvrez **R2** et créez un bucket, ex. `webtoapp-downloads`.
2. **Manage R2 API Tokens → Create API Token** avec la permission **Object Read & Write**. Copiez l'**Access Key ID** et le **Secret Access Key** (le secret n'est affiché qu'une fois).
3. Rendez le bucket public : **Settings → Public access**. Activez l'URL de développement **r2.dev** (`https://pub-xxxx.r2.dev`) pour démarrer vite, ou ajoutez un **domaine personnalisé** (ex. `files.example.com`) pour bénéficier aussi du cache en périphérie.
   > Un domaine personnalisé doit appartenir à un domaine géré par **le même compte Cloudflare** que le bucket.
4. Définissez les cinq variables dans `webtoapp.env` :

   ```bash
   R2_ACCOUNT_ID=...            # votre ID de compte (hex)
   R2_BUCKET=webtoapp-downloads
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev   # ou https://files.example.com
   ```
5. Redémarrez le service. Les nouveaux builds redirigent désormais les téléchargements vers R2.

> **r2.dev vs domaine personnalisé :** `pub-xxxx.r2.dev` est déjà servi depuis la périphérie mondiale de Cloudflare. Un domaine personnalisé ajoute du **cache** en périphérie (les téléchargements répétés du même fichier viennent du cache sans toucher R2), ce qui compte davantage à fort trafic.

### Backfill des apps existantes

Les apps construites avant l'activation de R2 pointent encore vers des fichiers locaux. Envoyez leurs artefacts vers R2 et mettez à jour leur `downloads_cdn` en une passe :

```bash
set -a; . ./webtoapp.env; set +a
venv/bin/python -m server.scripts.backfill_r2 --dry-run   # aperçu
venv/bin/python -m server.scripts.backfill_r2             # exécuter
```

Le script est idempotent — sûr à relancer.

## 12. Mise à jour

```bash
git pull
source venv/bin/activate
pip install -r server/requirements.txt   # si les dépendances ont changé
sudo systemctl restart webtoapp
```

Si vous avez modifié des ressources frontend (`css/`, `js/`), incrémentez la chaîne `?v=` dans `index.html` pour que les navigateurs récupèrent les nouveaux fichiers plutôt que ceux en cache.

## 13. Dépannage

| Symptôme | Cause probable / solution |
| --- | --- |
| L'iPhone ouvre la page dans Safari au lieu du plein écran | `PUBLIC_BASE_URL` non défini, ou pas en HTTPS. |
| Le téléchargement Android est un zip PWA, pas un APK | Android SDK / apktool non installés sur le serveur (§9). |
| Les téléchargements sont toujours servis par l'origine | Une variable `R2_*` manque, ou pas de redémarrage après les avoir définies. Lancez le backfill pour les anciennes apps (§11). |
| Le profil iOS affiche « Non vérifié » | Le profil n'est pas signé. Fournissez un certificat d'AC publique (§10). |
| `502 Bad Gateway` | Le service n'est pas lancé ou le port est mauvais — `systemctl status webtoapp`. |
| L'endpoint de build renvoie `429` | Quota quotidien par appareil ou limite par IP atteint. Ajustez `DAILY_BUILD_QUOTA`. |

---

Voir aussi le [README](README.fr.md) pour une vue d'ensemble du projet.

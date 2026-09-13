<div align="center">

<img src="../assets/site-logo.jpg" alt="WebToApp" width="120" height="120" style="border-radius: 24px;">

# WebToApp

**Transformez n'importe quel site web en app installable — en quelques secondes.**

Un lien entre, des produits finis sortent pour **iPhone / iPad · Android · Windows · macOS · Linux** — plus un marché public d'apps, des profils de créateur, des commentaires et des notes, le tout sans inscription.

[![Démo en direct](https://img.shields.io/badge/Démo_en_direct-shiaho.sbs-c97953?style=for-the-badge)](https://shiaho.sbs)
[![CI](https://img.shields.io/badge/CI-pytest%20336-059669?style=for-the-badge)](https://github.com/shiaho777/WebToApp/actions)
[![Licence : MIT](https://img.shields.io/badge/License-MIT-1e1914?style=for-the-badge)](../LICENSE)
[![Plateformes](https://img.shields.io/badge/Plateformes-5-736357?style=for-the-badge)](#ce-que-vous-obtenez)

[English](../README.md) · [简体中文](README.zh.md) · [日本語](README.ja.md) · [العربية](README.ar.md) · [Русский](README.ru.md) · [Español](README.es.md) · [Português](README.pt.md) · **Français** · [Deutsch](README.de.md)

</div>

---

<p align="center"><img src="assets/fig-stats.svg" alt="WebToApp en un coup d'œil : 5 plateformes, 9 langues, 336 tests" width="760"></p>

## Ce que vous obtenez

Entrez une URL — ou envoyez votre propre `.html` / `.zip` — et quelques secondes plus tard vous obtenez un résultat installable couvrant toutes les plateformes. Chaque artefact est une fine coque native pointant vers votre site : les paquets se mesurent en **kilooctets, pas en mégaoctets**, et se téléchargent presque instantanément.

Chaque app générée vit sur sa propre page de téléchargement `/a/<id>` : choix par plateforme, une section pliable « À propos de cette page » que le créateur peut remplir de vrai contenu, et une couche communautaire avec commentaires et notes par étoiles. Publiez-la en lien public et elle apparaît aussi sur le **marché d'apps** pour tout le monde.

Open source · Gratuit · Sans inscription. Essayez en direct sur **[shiaho.sbs](https://shiaho.sbs)**.

---

## Captures d'écran

<p align="center"><img src="assets/shots/landing.png" alt="Page d'accueil : collez un lien et démarrez — compteurs en direct des apps générées, téléchargements et visites" width="820"></p>
<p align="center"><em>Collez un lien (ou déposez un fichier HTML) — les compteurs sont en direct.</em></p>

<p align="center"><img src="assets/shots/config-about.png" alt="Configuration de l'app : nom, description, texte de la section À propos et jusqu'à 3 images auto-compressées" width="820"></p>
<p align="center"><em>Nom, description en une ligne et la section À propos rédigée par le créateur avec jusqu'à 3 images — tout ce qui dépasse 800 Ko est compressé quasiment sans perte.</em></p>

<p align="center"><img src="assets/shots/config-platforms.png" alt="Couleur de thème, icône récupérée et réglages par plateforme comme le mode immersif Android" width="820"></p>
<p align="center"><em>Couleur de thème et icône récupérées depuis le site ; réglages par plateforme comme le plein écran immersif d'Android.</em></p>

<p align="center"><img src="assets/shots/config-publish.png" alt="Visibilité du lien et tags obligatoires avant la génération" width="820"></p>
<p align="center"><em>Privé par défaut ou public sur le marché — les tags sont obligatoires pour que les apps restent découvrables.</em></p>

<p align="center"><img src="assets/shots/download-page.png" alt="Page de téléchargement générée : note, carte de créateur, commentaires et liste d'installation par plateforme" width="820"></p>
<p align="center"><em>La page de l'app générée : liste d'installation à droite, note / créateur / commentaires à gauche.</em></p>

<p align="center"><img src="assets/shots/about-fold.png" alt="La section À propos dépliée, montrant le texte du créateur et une image téléversée" width="820"></p>
<p align="center"><em>La section « À propos de cette page » porte le texte et les images du créateur — pas de remplissage générique.</em></p>

<p align="center"><img src="assets/shots/market.png" alt="Marché public d'apps avec attribution du créateur, tags, temps relatif et notes sur chaque carte" width="820"></p>
<p align="center"><em>Le marché public : cartes de créateur, filtres par tag, recherche et tri par plus récentes / mieux notées / plus téléchargées / plus visitées.</em></p>

<p align="center"><img src="assets/shots/history.png" alt="Historique de builds par appareil avec statistiques de visites, export et import" width="820"></p>
<p align="center"><em>Votre historique reste lié à l'empreinte de l'appareil — avec statistiques de visites, régénération et export/import entre appareils.</em></p>

---

## Comment ça marche

<p align="center"><img src="assets/fig-pipeline.svg" alt="Pipeline : entrée URL ou HTML → analyse + recipe → cinq builds en parallèle → page d'app avec communauté" width="800"></p>

1. **Entrée** — collez l'URL d'un site, ou envoyez un `.html` seul / un `.zip` contenant `index.html`. Le HTML envoyé est hébergé par le serveur sous `/a/<id>/site/...` et empaqueté exactement comme une app d'URL.
2. **Analyse + recipe** — l'analyseur récupère la page et en extrait nom, couleur de thème et icône (multi-candidats, la meilleure résolution gagne) ; tout ce dont la build a besoin est figé dans un `recipe.json`.
3. **Builds en parallèle** — les cinq paquets se construisent en même temps ; un échec sur l'un (ex. toolchain Android absente) ne dégrade que cette plateforme.
4. **Page d'app** — la page de téléchargement rend les entrées d'installation par plateforme, le contenu À propos du créateur et le bloc communauté.

## Fonctionnalités

- **Deux modes d'entrée** : URL de site, ou votre propre HTML (un `.html` ou un `.zip` contenant `index.html`) — hébergé et empaqueté comme n'importe quelle app d'URL.
- **Analyse du site** : nom, couleur de thème, icône en meilleure résolution et comptage pubs/trackers/popups (estimations à affichage seul).
- **Empaquetage multiplateforme**, une build → cinq artefacts :
  - **Android** — un vrai WebView APK installable (signé v1+v2+v3), chaque app avec son **propre certificat de signature**.
  - **iOS / iPadOS** — un profil Web Clip `.mobileconfig`, signable en CMS avec un certificat de CA publique (installation « sans signature »).
  - **macOS** — une fenêtre `.app` WKWebView autonome (pas de barre d'adresse, pas de navigateur tiers).
  - **Windows / Linux** — lanceurs légers `.bat` / `.desktop` ouvrant le navigateur système en mode app.
- **Section À propos rédigée par le créateur** : texte enrichi plus jusqu'à 3 images sur chaque page d'app. Les téléversements sont vérifiés par décodage, débarrassés de l'EXIF et ré-encodés en WebP — tout ce qui dépasse 800 Ko est compressé quasiment sans perte côté serveur.
- **Communauté sans comptes** : l'empreinte de l'appareil devient une identité publique persistante (`?u=N`) — nom modifiable, bio Markdown et avatar. Les créateurs sont crédités sur leurs apps et disposent d'une page de profil publique.
- **Commentaires et notes** : chaque page d'app a un fil de commentaires avec note optionnelle de 1–5 étoiles ; les moyennes remontent sur les cartes du marché.
- **Marché public d'apps** : filtres par tag, recherche et tri par plus récentes, mieux notées (moyenne → nombre), plus téléchargées ou plus visitées — avec horodatages relatifs.
- **Échange dynamique d'URL sur iOS** : le Web Clip pointe vers `/a/<id>/launch`, donc l'URL cible peut changer côté serveur sans réinstallation.
- **Historique par appareil** : les builds sont enregistrées contre l'empreinte de l'appareil avec stats de visites/téléchargements, régénération et export/import entre appareils. Supprimer une entrée retire complètement l'app.
- **Nettoyage automatique** : les apps sans visite pendant 30 jours sont récupérées automatiquement.
- **Offload Cloudflare R2 optionnel** : les téléchargements redirigent vers le CDN, épargnant la bande passante de l'origine.
- **UI multilingue** : 9 langues — English, 简体中文, 日本語, العربية (RTL), Русский, Español, Português, Français, Deutsch — avec les pages de téléchargement générées elles aussi localisées.

## Une communauté sans inscription

<p align="center"><img src="assets/fig-community.svg" alt="L'empreinte de l'appareil devient un ID public séquentiel qui débloque attribution du créateur, profils, commentaires et notes" width="800"></p>

Pas d'inscription : à la première apparition d'un appareil, son empreinte reçoit un numéro public séquentiel. Ce `#N` devient un vrai profil — définissez un nom d'affichage, une bio Markdown et un avatar, et chaque app que vous publiez porte votre carte de créateur. Les autres utilisateurs ouvrent `?u=N` pour voir votre profil public et les apps publiées. Les commentaires acceptent des notes par étoiles optionnelles, reflétées sur chaque carte du marché.

## Taille de l'app

Chaque paquet est une fine porte d'entrée vers votre site — il n'embarque aucun contenu du site, donc les artefacts se mesurent en **kilooctets, pas en mégaoctets**.

<p align="center"><img src="assets/fig-sizes.svg" alt="Tailles mesurées : macOS 135 Ko, Android 21 Ko, iOS 4 Ko, Windows 1,2 Ko, Linux 0,7 Ko" width="760"></p>

| Plateforme | Paquet | Taille typique | Contenu |
| --- | --- | --- | --- |
| Android | `android.apk` | **~21 Ko** | Un vrai WebView APK installable (signé v1+v2+v3) |
| iOS / iPadOS | `ios.mobileconfig` | **~4 Ko** | Un profil de configuration Web Clip |
| macOS | `macos.zip` | **~135 Ko** | Un bundle `.app` (fenêtre WKWebView native + icône) |
| Windows | `windows.zip` | **~1,2 Ko** | Un lanceur `.bat` + assistant de raccourci + icône |
| Linux | `linux.tar.gz` | **~0,7 Ko** | Une entrée `.desktop` + script d'installation + icône |

## Stack technique

- Backend : Python + FastAPI + Uvicorn · stores SQLite (historique, tâches, communauté)
- Frontend : HTML / CSS / JS pur — pas d'étape de build, servi directement par le backend
- Empaquetage : Android SDK (aapt2 / d8 / apktool / apksigner / zipalign), Pillow, openssl
- CI : `pytest tests/` sur Python 3.10 / 3.11 / 3.12 — **336 tests**

## Structure du projet

```
.
├── index.html                 Page d'accueil + formulaire de build
├── css/ js/ assets/           Assets statiques du frontend
│   ├── js/i18n.js             Runtime i18n léger (9 langues)
│   ├── js/i18n.strings.js     Toutes les traductions
│   ├── js/community.js        Commentaires / notes / bloc créateur sur les pages d'app
│   └── js/mdmini.js           Mini moteur de rendu Markdown pour les bios
├── server/
│   ├── main.py                App FastAPI et routes (35 endpoints)
│   ├── config.py              Configuration par variables d'environnement
│   ├── html_site.py           Staging / validation / service des uploads HTML
│   ├── history_store.py       Historique par appareil + stats app/visites (SQLite)
│   ├── community_store.py     Profils, créateurs, commentaires, notes (SQLite)
│   ├── task_store.py          Persistance de la file de builds (SQLite)
│   └── engine/
│       ├── analyzer.py        Analyse du site
│       ├── distiller.py       recipe → paquets + page de téléchargement (cœur)
│       ├── apk_builder.py     Build et signature de l'APK Android
│       ├── mobileconfig_signer.py  Signature des profils iOS
│       ├── cache.py           Caches de fetch/icônes
│       └── storage.py         Offload Cloudflare R2
├── certs/                     Matériel de signature (clés privées non commitées)
└── generated/                 Apps et données générées au runtime (non commitées)
```

## Démarrage rapide

Nécessite Python 3.10+. Construire l'APK Android demande l'Android SDK et `apktool` (repli sur un paquet PWA hors-ligne s'ils manquent).

```bash
# 1. Créez un environnement virtuel et installez les dépendances
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt

# 2. Configurez (optionnel, tout a des valeurs par défaut)
cp .env.example .env
# Modifiez .env selon vos besoins

# 3. Lancez
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Ouvrez http://127.0.0.1:8000.

> Aucune variable d'environnement n'est requise pour le développement local. Pour un déploiement public, définissez `PUBLIC_BASE_URL`,
> sinon les iPhone ne peuvent pas ouvrir `localhost`. La liste complète est dans [`.env.example`](../.env.example).

## Déploiement

> Pour un guide de production complet pas à pas (systemd, Nginx, HTTPS, Android/iOS, R2), voir **[DEPLOY.md](DEPLOY.md)**.

En production, on le fait souvent tourner sous systemd, derrière un reverse proxy Nginx :

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

Pour la signature des profils iOS (installation « sans signature »), voir la configuration des certificats dans [`certs/README.md`](../certs/README.md).

## Comment fonctionne l'offload Cloudflare R2

Les installeurs générés peuvent être volumineux, et servir chaque téléchargement depuis l'origine consume sa bande passante. Avec R2 configuré :

1. **Après chaque build**, chaque fichier de `generated/<app_id>/downloads/` est mis en miroir sur R2 sous la clé `<app_id>/downloads/<filename>` (`server/engine/storage.py`), et les URLs publiques résultantes sont écrites dans le `recipe.json` de l'app comme map `downloads_cdn`.
2. **Au téléchargement**, `GET /a/<id>/download/<platform>` préfère l'URL CDN de `downloads_cdn` et renvoie une **redirection 302** vers R2 ; à défaut, il sert le fichier local en streaming. L'origine dépense du CPU pendant les builds, pas de la bande passante à chaque partage ou scan de QR.
3. **Au nettoyage**, les objets d'une app sous `<app_id>/` sont supprimés de R2 en même temps que ses données locales.

Si une variable `R2_*` manque, la fonctionnalité est no-op et les téléchargements sont servis localement — rien ne casse. Les apps créées avant l'activation de R2 peuvent être migrées avec `python -m server.scripts.backfill_r2`. Les étapes complètes (bucket, token d'API, accès public, domaine personnalisé, backfill) sont dans [DEPLOY.md §11](DEPLOY.md#11-cloudflare-r2-offload-optional).

## Notes de sécurité

- Tous les secrets (R2, Cloudflare, mots de passe de signature) sont lus depuis des variables d'environnement ; le dépôt ne contient aucune vraie credential.
- **Les clés privées de signature (`certs/*.keystore`, `certs/app-keys/`) et les données de runtime (`generated/`) sont exclues par `.gitignore` par défaut — ne les committez jamais.**
- Chaque app Android générée utilise son propre certificat de signature indépendant, ce qui évite que l'empreinte du certificat soit signalée en masse et garantit que la même app peut être mise à jour in situ.
- Les images « À propos » téléversées par les créateurs sont vérifiées par décodage avec Pillow, bornées par des plafonds de taille brute / pixels / nombre, débarrassées de leurs métadonnées et ré-encodées en WebP — jamais servies telles qu'envoyées.
- Le texte généré par les utilisateurs est échappé en HTML au rendu ; les routes de média par app n'acceptent que les noms de fichiers générés par le serveur.

## Licence

[MIT](../LICENSE)

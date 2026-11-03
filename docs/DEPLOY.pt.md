<div align="center">

# WebToApp — Guia de implantação

[English](DEPLOY.md) · [简体中文](DEPLOY.zh.md) · [日本語](DEPLOY.ja.md) · [العربية](DEPLOY.ar.md) · [Русский](DEPLOY.ru.md) · [Español](DEPLOY.es.md) · **Português** · [Français](DEPLOY.fr.md) · [Deutsch](DEPLOY.de.md)

Guia passo a passo para rodar o WebToApp em produção.

</div>

---

## Conteúdo

1. [Requisitos](#1-requisitos)
2. [Obter o código](#2-obter-o-código)
3. [Ambiente Python](#3-ambiente-python)
4. [Configuração](#4-configuração)
5. [Rodar localmente](#5-rodar-localmente)
   - [Docker](#docker)
6. [Rodar como serviço (systemd)](#6-rodar-como-serviço-systemd)
7. [Proxy reverso (Nginx)](#7-proxy-reverso-nginx)
8. [HTTPS](#8-https)
9. [Build de APK Android (opcional)](#9-build-de-apk-android-opcional)
10. [Assinatura de perfil iOS (opcional)](#10-assinatura-de-perfil-ios-opcional)
11. [Offload para Cloudflare R2 (opcional)](#11-offload-para-cloudflare-r2-opcional)
12. [Atualizar](#12-atualizar)
13. [Resolução de problemas](#13-resolução-de-problemas)

---

## 1. Requisitos

- **Python 3.10+**
- Um servidor Linux (qualquer distribuição). 1 vCPU / 1 GB de RAM bastam para começar.
- Acesso de saída à internet (o analisador busca os sites alvo).
- Opcional, só para builds reais de APK Android: **Android SDK** (`aapt2`, `d8`, `apksigner`, `zipalign`), **apktool**, um **JDK** (`java` / `javac` / `keytool`). Sem eles, o Android recorre a um pacote PWA instalável.
- Opcional, só para assinatura iOS: **openssl** (presente em praticamente qualquer Linux).

A única dependência obrigatória é o Python. Todo o resto é opcional e degrada com elegância.

## 2. Obter o código

```bash
git clone https://github.com/shiaho777/WebToApp.git
cd WebToApp
```

## 3. Ambiente Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

Isso instala as quatro dependências de runtime: `fastapi`, `uvicorn[standard]`, `httpx`, `Pillow`. O offload para o Cloudflare R2 (opcional) não precisa de nenhum pacote adicional — veja a §11.

## 4. Configuração

Toda a configuração é lida de variáveis de ambiente — cada uma é opcional com um padrão sensato.

```bash
cp .env.example .env
# edite o .env
```

| Variável | Finalidade | Padrão |
| --- | --- | --- |
| `PUBLIC_BASE_URL` | Origem pública, ex. `https://app.example.com`. Obrigatória em produção, senão o iPhone tenta abrir `localhost`. | inferida do cabeçalho Host |
| `ANDROID_PACKAGE_PREFIX` | Prefixo padrão do pacote Android. | `com.webtoapp` |
| `ANDROID_KEYSTORE_DIR` | Onde ficam os keystores de assinatura por app. Mantenha FORA de qualquer caminho público. | `certs/app-keys` |
| `DAILY_BUILD_QUOTA` | Limite diário de builds por dispositivo (`0` desativa). | `10` |
| `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE` | Certificado de CA pública para assinar perfis iOS. | não definido (sem assinatura, mesmo assim instalável) |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` / `R2_PUBLIC_BASE_URL` | Offload para Cloudflare R2 (ver §11). | não definido (downloads locais) |
| `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ZONE_ID` | Purga imediata do redirecionamento iOS `/launch` ao trocar a URL. | não definido |

> **Nunca faça commit do seu `.env` real.** Ele é ignorado pelo git por padrão.

## 5. Rodar localmente

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Abra <http://127.0.0.1:8000>. Para desenvolvimento local não precisa de variáveis de ambiente.

## Docker

Um comando constrói a imagem e sobe o site na porta 8000. A imagem padrão inclui Python, um JDK, o Android SDK e o apktool, então os pacotes Android são APKs de verdade. Apps gerados e chaves de assinatura sobrevivem a uma reconstrução.

```bash
cp .env.example .env
# Antes de publicar, defina PUBLIC_BASE_URL=https://your-domain.com.
docker compose up -d --build
```

Abra <http://127.0.0.1:8000>. A primeira build baixa o Android SDK de `dl.google.com` e o apktool do GitHub. É preciso saída para a internet e cerca de 2 GB de RAM.

O que fica guardado:

- o volume `webtoapp-generated` — apps, histórico e o banco da comunidade
- `./certs` — keystores Android por app e PEMs iOS opcionais (`ios-cert.pem`, `ios-key.pem`, `ios-chain.pem`)

Coloque um proxy reverso na porta 8000. Proxies em endereços privados podem enviar `X-Forwarded-*`. Caso contrário, defina `DOCKER_TRUSTED_PROXY_CIDRS` no `.env`.

Imagem menor, sem a cadeia Android (Android vira um zip PWA):

```bash
WITH_ANDROID=0 docker compose up -d --build
```

Atualizar:

```bash
git pull
docker compose up -d --build
```

## 6. Rodar como serviço (systemd)

Guarde os segredos num arquivo de ambiente restrito, não inline na unidade:

```bash
# /path/to/WebToApp/webtoapp.env  (chmod 600)
PUBLIC_BASE_URL=https://your-domain.com
# adicione R2_* / IOS_* / CLOUDFLARE_* conforme necessário
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

> Mantenha `--workers 1`. A fila de build e o limitador de taxa em memória assumem um único processo.

## 7. Proxy reverso (Nginx)

O app serve seu próprio frontend estático, então o Nginx só precisa encaminhar tudo para a porta do Uvicorn:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 25m;   # upload de ícones personalizados

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;   # builds de APK podem demorar
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 8. HTTPS

Web Clips iOS e perfis `.mobileconfig` exigem HTTPS. Duas opções comuns:

**Opção A — Cloudflare Tunnel** (sem abrir portas de entrada, TLS grátis):

```bash
cloudflared tunnel login
cloudflared tunnel create webtoapp
cloudflared tunnel route dns webtoapp your-domain.com
cloudflared tunnel run webtoapp
```

**Opção B — Let's Encrypt no Nginx:**

```bash
sudo certbot --nginx -d your-domain.com
```

Em qualquer caso, defina `PUBLIC_BASE_URL=https://your-domain.com`.

## 9. Build de APK Android (opcional)

Para produzir um APK WebView real e instalável, o servidor precisa das ferramentas de build do Android:

- Android SDK com `aapt2`, `d8`, `apksigner`, `zipalign`
- `apktool`
- um JDK fornecendo `java`, `javac`, `keytool`

Aponte o app para o SDK com `ANDROID_HOME` / `ANDROID_SDK_ROOT` se não for detectado automaticamente. Cada app gerado recebe seu **próprio** certificado de assinatura (em `ANDROID_KEYSTORE_DIR`), então atualizações instalam por cima.

**Sem o SDK**, a geração de APK é ignorada e os usuários Android recebem um pacote PWA instalável — todo o resto continua funcionando.

## 10. Assinatura de perfil iOS (opcional)

Por padrão o `.mobileconfig` do iOS não é assinado (o iOS ainda instala, mas mostra "Não verificado"). Para o iOS exibir seu domínio como origem, forneça um certificado de CA pública via `IOS_CERT_FILE` / `IOS_KEY_FILE` / `IOS_CHAIN_FILE`, ou coloque `certs/ios-cert.pem`, `certs/ios-key.pem`, `certs/ios-chain.pem`. A assinatura usa o `openssl` do sistema. Ver [`certs/README.md`](../certs/README.md).

## 11. Offload para Cloudflare R2 (opcional)

### Como funciona

Os instaladores gerados (APK / ZIP / `.mobileconfig`) podem ser pesados, e servir cada download a partir da origem consome sua banda. Com o R2 ativado:

1. **Após cada build**, cada arquivo em `generated/<app_id>/downloads/` é enviado ao R2 com a chave `<app_id>/downloads/<nome>` (ver `server/engine/storage.py`), e as URLs públicas resultantes são gravadas no `recipe.json` do app como um mapa `downloads_cdn`.
2. **No download**, `GET /a/<id>/download/<platform>` prefere a URL de CDN em `downloads_cdn` e retorna um **redirecionamento 302** ao R2; se ausente, recorre a servir o arquivo local. Assim a origem gasta CPU ao construir, não banda a cada compartilhamento ou leitura de QR.
3. **Na limpeza**, os objetos do app sob `<app_id>/` são removidos do R2 junto com seus dados locais.

Se qualquer variável `R2_*` faltar, o recurso vira no-op e os downloads são servidos localmente — nada quebra. Apps criados antes de ativar o R2 são migrados com `python -m server.scripts.backfill_r2`.

> **Nota de implementação:** O R2 fala a API do S3, que autentica com AWS Signature V4. Em vez de incluir a pesada pilha `boto3`/`botocore`, o `server/engine/storage.py` traz seu próprio assinador SigV4 (apenas com a biblioteca padrão `hmac`/`hashlib`) e envia as requisições via `httpx`, o mesmo cliente HTTP que a app já usa. Por isso o offload para R2 **não precisa do SDK da AWS**; o assinador é validado com os vetores de teste SigV4 publicados pela AWS (`python -m server.engine.storage`).

### Configuração

1. No painel do Cloudflare, abra **R2** e crie um bucket, ex. `webtoapp-downloads`.
2. **Manage R2 API Tokens → Create API Token** com permissão **Object Read & Write**. Copie o **Access Key ID** e o **Secret Access Key** (o segredo é mostrado uma única vez).
3. Torne o bucket público: **Settings → Public access**. Ative a URL de desenvolvimento **r2.dev** (`https://pub-xxxx.r2.dev`) para começar rápido, ou adicione um **domínio personalizado** (ex. `files.example.com`) para ter também cache na borda.
   > Um domínio personalizado precisa estar num domínio gerenciado pela **mesma conta Cloudflare** do bucket.
4. Defina as cinco variáveis em `webtoapp.env`:

   ```bash
   R2_ACCOUNT_ID=...            # seu ID de conta (hex)
   R2_BUCKET=webtoapp-downloads
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev   # ou https://files.example.com
   ```
5. Reinicie o serviço. Novos builds agora redirecionam os downloads ao R2.

> **r2.dev vs domínio personalizado:** `pub-xxxx.r2.dev` já é servido pela borda global do Cloudflare. Um domínio personalizado adiciona **cache** na borda (downloads repetidos do mesmo arquivo vêm do cache sem tocar o R2), o que importa mais com mais tráfego.

### Backfill de apps existentes

Apps construídos antes de ativar o R2 ainda apontam para arquivos locais. Envie seus artefatos ao R2 e atualize o `downloads_cdn` numa só passada:

```bash
set -a; . ./webtoapp.env; set +a
venv/bin/python -m server.scripts.backfill_r2 --dry-run   # pré-visualizar
venv/bin/python -m server.scripts.backfill_r2             # executar
```

O script é idempotente — seguro para reexecutar.

## 12. Atualizar

```bash
git pull
source venv/bin/activate
pip install -r server/requirements.txt   # se as dependências mudaram
sudo systemctl restart webtoapp
```

Se você alterou recursos do frontend (`css/`, `js/`), incremente a string `?v=` no `index.html` para os navegadores buscarem os arquivos novos em vez dos em cache.

## 13. Resolução de problemas

| Sintoma | Causa provável / solução |
| --- | --- |
| O iPhone abre a página no Safari em vez de tela cheia | `PUBLIC_BASE_URL` não definida, ou não é HTTPS. |
| O download do Android é um zip de PWA, não um APK | Android SDK / apktool não instalados no servidor (§9). |
| Downloads ainda servidos pela origem | Falta uma variável `R2_*`, ou você não reiniciou após defini-las. Rode o backfill para apps antigos (§11). |
| O perfil iOS mostra "Não verificado" | O perfil não está assinado. Forneça um certificado de CA pública (§10). |
| `502 Bad Gateway` | O serviço não está rodando ou a porta está errada — `systemctl status webtoapp`. |
| O endpoint de build retorna `429` | Cota diária por dispositivo ou limite por IP atingido. Ajuste `DAILY_BUILD_QUOTA`. |

---

Veja também o [README](README.pt.md) para uma visão geral do projeto.

<div align="center">

<img src="../assets/site-logo.jpg" alt="WebToApp" width="120" height="120" style="border-radius: 24px;">

# WebToApp

**Transforme qualquer site num app instalável — em segundos.**

Um link entra, saem produtos prontos para **iPhone / iPad · Android · Windows · macOS · Linux** — além de um mercado público de apps, perfis de criador, comentários e avaliações, tudo sem cadastro.

[![Demo ao vivo](https://img.shields.io/badge/Demo_ao_vivo-shiaho.sbs-c97953?style=for-the-badge)](https://shiaho.sbs)
[![CI](https://img.shields.io/badge/CI-pytest%20336-059669?style=for-the-badge)](https://github.com/shiaho777/WebToApp/actions)
[![Licença: MIT](https://img.shields.io/badge/License-MIT-1e1914?style=for-the-badge)](../LICENSE)
[![Plataformas](https://img.shields.io/badge/Plataformas-5-736357?style=for-the-badge)](#o-que-você-recebe)

[English](../README.md) · [简体中文](README.zh.md) · [日本語](README.ja.md) · [العربية](README.ar.md) · [Русский](README.ru.md) · [Español](README.es.md) · **Português** · [Français](README.fr.md) · [Deutsch](README.de.md)

</div>

---

## O que você recebe

Cole uma URL — ou envie o seu próprio `.html` / `.zip` — e segundos depois recebe um resultado instalável para todas as plataformas. Cada artefato é uma fina camada nativa apontando para o seu site, por isso os pacotes são medidos em **kilobytes, não megabytes**, e baixam quase instantaneamente.

Cada app gerada vive na sua própria página de download `/a/<id>`: opções por plataforma, uma seção dobrável «Sobre esta página» que o criador pode preencher com conteúdo real, e uma camada comunitária com comentários e avaliações por estrelas. Publique como link público e ela também aparece no **mercado de apps** para todos descobrirem.

Open source · Grátis · Sem cadastro. Experimente ao vivo em **[shiaho.sbs](https://shiaho.sbs)**.

---

## Capturas de tela

<p align="center"><img src="assets/shots/landing.png" alt="Página inicial: cole um link e comece — contadores ao vivo de apps geradas, downloads e visitas" width="820"></p>
<p align="center"><em>Cole um link (ou solte um arquivo HTML) — os contadores são ao vivo.</em></p>

<p align="center"><img src="assets/shots/config-about.png" alt="Configuração do app: nome, descrição, texto da seção Sobre e até 3 imagens auto-comprimidas" width="820"></p>
<p align="center"><em>Nome, descrição de uma linha e a seção Sobre escrita pelo criador com até 3 imagens — o que passar de 800KB é comprimido quase sem perda.</em></p>

<p align="center"><img src="assets/shots/config-platforms.png" alt="Cor de tema, ícone recuperado e ajustes por plataforma como o modo imersivo do Android" width="820"></p>
<p align="center"><em>Cor de tema e ícone recuperados do site; ajustes por plataforma como o modo imersivo do Android.</em></p>

<p align="center"><img src="assets/shots/config-publish.png" alt="Visibilidade do link e tags obrigatórias antes de gerar" width="820"></p>
<p align="center"><em>Privado por padrão ou público no mercado — as tags são obrigatórias para manter os apps descobríveis.</em></p>

<p align="center"><img src="assets/shots/download-page.png" alt="Página de download gerada: avaliação, cartão de criador, comentários e lista de instalação por plataforma" width="820"></p>
<p align="center"><em>A página do app gerado: lista de instalação à direita, avaliação / criador / comentários à esquerda.</em></p>

<p align="center"><img src="assets/shots/about-fold.png" alt="A seção Sobre expandida, mostrando texto do criador e uma imagem enviada" width="820"></p>
<p align="center"><em>A seção «Sobre esta página» carrega o texto e as imagens do criador — sem texto de enchimento.</em></p>

<p align="center"><img src="assets/shots/market.png" alt="Mercado público de apps com atribuição de criador, tags, tempo relativo e avaliações em cada cartão" width="820"></p>
<p align="center"><em>O mercado público: cartões de criador, filtros por tag, busca e ordenação por mais recentes / melhor avaliados / mais baixados / mais visitados.</em></p>

<p align="center"><img src="assets/shots/history.png" alt="Histórico de builds por dispositivo com estatísticas de visitas, exportação e importação" width="820"></p>
<p align="center"><em>O seu histórico fica ligado à impressão digital do dispositivo — com estatísticas de visitas, regenerar e exportar/importar entre dispositivos.</em></p>

---

## Como funciona

<p align="center"><img src="assets/fig-pipeline.svg" alt="Pipeline: entrada URL ou HTML → análise + recipe → cinco builds em paralelo → página do app com comunidade" width="800"></p>

1. **Entrada** — cole a URL de um site, ou envie um `.html` solto / um `.zip` contendo `index.html`. O HTML enviado é hospedado pelo servidor em `/a/<id>/site/...` e empacotado exatamente como um app de URL.
2. **Análise + recipe** — o analisador busca a página e extrai nome, cor de tema e ícone (multi-candidato, a maior resolução vence); tudo o que a build precisa fica fixado num `recipe.json`.
3. **Builds em paralelo** — os cinco pacotes são construídos ao mesmo tempo; uma falha num deles (ex.: toolchain Android ausente) degrada apenas aquela plataforma.
4. **Página do app** — a página de download renderiza as entradas de instalação por plataforma, o conteúdo Sobre do criador e o bloco de comunidade.

## Funcionalidades

- **Dois modos de entrada**: URL de site, ou o seu próprio HTML (um `.html` ou um `.zip` com `index.html` dentro) — hospedado e empacotado como qualquer app de URL.
- **Análise do site**: nome, cor de tema, ícone na melhor resolução e contagem de anúncios/rastreadores/popups (estimativas apenas para exibição).
- **Empacotamento multiplataforma**, uma build → cinco artefatos:
  - **Android** — um WebView APK real e instalável (assinado v1+v2+v3), cada app com o seu **próprio certificado de assinatura**.
  - **iOS / iPadOS** — um perfil Web Clip `.mobileconfig`, opcionalmente assinado via CMS com certificado de CA pública (instalação «sem assinatura»).
  - **macOS** — uma janela `.app` WKWebView autónoma (sem barra de endereço, sem navegador de terceiros).
  - **Windows / Linux** — launchers leves `.bat` / `.desktop` que abrem o navegador do sistema em modo app.
- **Seção Sobre escrita pelo criador**: rich text mais até 3 imagens em cada página de app. Os uploads são verificados por decodificação, têm EXIF removido e são re-codificados para WebP — o que passar de 800KB é comprimido quase sem perda no servidor.
- **Comunidade sem contas**: a impressão digital do dispositivo vira uma identidade pública persistente (`?u=N`) — nome editável, bio em Markdown e avatar. Criadores são creditados nos seus apps e têm uma página de perfil pública.
- **Comentários e avaliações**: cada página de app tem um fio de comentários com avaliação opcional de 1–5 estrelas; as médias aparecem nos cartões do mercado.
- **Mercado público de apps**: filtros por tag, busca e ordenação por mais recentes, melhor avaliados (média → contagem), mais baixados ou mais visitados — com tempos relativos.
- **Troca dinâmica de URL no iOS**: o Web Clip aponta para `/a/<id>/launch`, então a URL de destino pode mudar no servidor sem reinstalação.
- **Histórico por dispositivo**: builds são guardadas contra a impressão digital do dispositivo com estatísticas de visitas/downloads, regenerar e exportar/importar entre dispositivos. Apagar uma entrada remove o app por completo.
- **Limpeza automática**: apps sem visitas por 30 dias são recolhidas automaticamente.
- **Offload opcional para Cloudflare R2**: downloads redirecionam para o CDN, poupando a banda da origem.
- **UI multilíngue**: 9 idiomas — English, 简体中文, 日本語, العربية (RTL), Русский, Español, Português, Français, Deutsch — com as páginas de download geradas também localizadas.

## Comunidade sem cadastro

<p align="center"><img src="assets/fig-community.svg" alt="A impressão digital do dispositivo vira um ID público sequencial que desbloqueia atribuição de criador, perfis, comentários e avaliações" width="800"></p>

Não há registo: na primeira vez que um dispositivo aparece, a sua impressão digital recebe um número público sequencial. Esse `#N` torna-se um perfil real — defina um nome de exibição, uma bio em Markdown e um avatar, e cada app que publicar traz o seu cartão de criador. Outros utilizadores abrem `?u=N` para ver o seu perfil público e os apps publicados. Os comentários aceitam avaliações por estrelas opcionais, refletidas em cada cartão do mercado.

## Tamanho do app

Cada pacote é uma fina porta de entrada para o seu site — não inclui o conteúdo do site, por isso os artefatos medem-se em **kilobytes, não megabytes**.

<p align="center"><img src="assets/fig-sizes.svg" alt="Tamanhos medidos: macOS 135KB, Android 21KB, iOS 4KB, Windows 1.2KB, Linux 0.7KB" width="760"></p>

| Plataforma | Pacote | Tamanho típico | Conteúdo |
| --- | --- | --- | --- |
| Android | `android.apk` | **~21 KB** | Um WebView APK real e instalável (assinado v1+v2+v3) |
| iOS / iPadOS | `ios.mobileconfig` | **~4 KB** | Um perfil de configuração Web Clip |
| macOS | `macos.zip` | **~135 KB** | Um bundle `.app` (janela WKWebView nativa + ícone) |
| Windows | `windows.zip` | **~1.2 KB** | Um launcher `.bat` + auxiliar de atalho + ícone |
| Linux | `linux.tar.gz` | **~0.7 KB** | Uma entrada `.desktop` + script de instalação + ícone |

## Stack técnica

- Backend: Python + FastAPI + Uvicorn · stores SQLite (histórico, tarefas, comunidade)
- Frontend: HTML / CSS / JS puro — sem passo de build, servido diretamente pelo backend
- Empacotamento: Android SDK (aapt2 / d8 / apktool / apksigner / zipalign), Pillow, openssl
- CI: `pytest tests/` em Python 3.10 / 3.11 / 3.12 — **336 testes**

## Estrutura do projeto

```
.
├── index.html                 Página inicial + formulário de build
├── css/ js/ assets/           Assets estáticos do frontend
│   ├── js/i18n.js             Runtime i18n leve (9 idiomas)
│   ├── js/i18n.strings.js     Todas as traduções
│   ├── js/community.js        Comentários / avaliações / bloco de criador nas páginas de app
│   └── js/mdmini.js           Mini renderizador Markdown para bios
├── server/
│   ├── main.py                App FastAPI e rotas (35 endpoints)
│   ├── config.py              Configuração por variáveis de ambiente
│   ├── html_site.py           Staging / validação / serviço de uploads HTML
│   ├── history_store.py       Histórico por dispositivo + estatísticas de app/visitas (SQLite)
│   ├── community_store.py     Perfis, criadores, comentários, avaliações (SQLite)
│   ├── task_store.py          Persistência da fila de builds (SQLite)
│   └── engine/
│       ├── analyzer.py        Análise do site
│       ├── distiller.py       recipe → pacotes + página de download (núcleo)
│       ├── apk_builder.py     Build e assinatura do APK Android
│       ├── mobileconfig_signer.py  Assinatura de perfis iOS
│       ├── cache.py           Caches de fetch/ícones
│       └── storage.py         Offload para Cloudflare R2
├── certs/                     Material de assinatura (chaves privadas não são comitadas)
└── generated/                 Apps e dados gerados em runtime (não comitados)
```

## Início rápido

Requer Python 3.10+. Construir o APK Android precisa do Android SDK e do `apktool` (degrada para um pacote PWA offline quando faltam).

```bash
# 1. Crie um ambiente virtual e instale as dependências
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt

# 2. Configure (opcional, tudo tem valores padrão)
cp .env.example .env
# Edite o .env conforme necessário

# 3. Execute
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Abra http://127.0.0.1:8000.

> Não são necessárias variáveis de ambiente para desenvolvimento local. Ao publicar em produção, defina `PUBLIC_BASE_URL`,
> caso contrário os iPhone não conseguem abrir `localhost`. A lista completa está em [`.env.example`](../.env.example).

## Deployment

> Para um guia de produção completo passo a passo (systemd, Nginx, HTTPS, Android/iOS, R2), veja **[DEPLOY.md](DEPLOY.md)**.

Em produção é comum correr sob systemd, atrás de um reverse proxy Nginx:

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

Para a assinatura de perfis iOS (instalação «sem assinatura»), veja a configuração de certificados em [`certs/README.md`](../certs/README.md).

## Como funciona o offload para Cloudflare R2

Os instaladores gerados podem ser grandes, e servir cada download a partir da origem gasta a sua banda. Com o R2 configurado:

1. **Após cada build**, cada ficheiro em `generated/<app_id>/downloads/` é espelhado para o R2 sob a chave `<app_id>/downloads/<filename>` (`server/engine/storage.py`), e os URLs públicos resultantes são escritos no `recipe.json` do app como mapa `downloads_cdn`.
2. **No download**, `GET /a/<id>/download/<platform>` prefere o URL CDN em `downloads_cdn` e devolve um **redirect 302** para o R2; se ausente, recorre ao streaming do ficheiro local. A origem gasta CPU nas builds, não banda em cada partilha ou leitura de QR.
3. **Na limpeza**, os objetos de um app sob `<app_id>/` são removidos do R2 junto com os dados locais.

Se qualquer variável `R2_*` não estiver definida a funcionalidade é no-op e os downloads são servidos localmente — nada quebra. Apps criadas antes de ativar o R2 podem ser migradas com `python -m server.scripts.backfill_r2`. Os passos completos (bucket, token de API, acesso público, domínio personalizado, backfill) estão em [DEPLOY.md §11](DEPLOY.md#11-cloudflare-r2-offload-optional).

## Notas de segurança

- Todos os segredos (R2, Cloudflare, palavras-passe de assinatura) são lidos de variáveis de ambiente; o repositório não contém credenciais reais.
- **As chaves privadas de assinatura (`certs/*.keystore`, `certs/app-keys/`) e os dados de runtime (`generated/`) estão excluídos pelo `.gitignore` por padrão — nunca os comita.**
- Cada app Android gerada usa o seu próprio certificado de assinatura independente, o que evita que a impressão digital do certificado seja sinalizada em massa e garante que a mesma app pode ser atualizada in situ.
- As imagens «Sobre» enviadas por criadores são verificadas por decodificação com Pillow, limitadas por tetos de tamanho bruto / píxeis / quantidade, despojadas de metadados e re-codificadas para WebP — nunca são servidas como foram enviadas.
- O texto gerado por utilizadores é escapado como HTML ao renderizar; as rotas de média por app só permitem nomes de ficheiro gerados pelo servidor.

## Licença

[MIT](../LICENSE)

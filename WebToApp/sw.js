'use strict';

const CACHE_NAME = 'webtoapp-shell-v1';
const SHELL_KEY = new URL(self.registration.scope).pathname;
const SHELL_ASSET_PREFIXES = ['/css/', '/js/', '/assets/'];
const SHELL_ASSET_FILES = ['/manifest.webmanifest'];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    try {
      const response = await fetch(new Request(SHELL_KEY, { cache: 'reload' }));
      if (response && response.ok) {
        const html = await response.clone().text();
        await cache.put(SHELL_KEY, response);
        await cacheShellAssets(cache, html);
      }
    } catch (_err) {
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.indexOf('webtoapp-shell-') === 0 && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
      .then(() => pruneStaleAssets())
      .then(() => self.clients.claim())
  );
});

async function pruneStaleAssets() {
  try {
    const cache = await caches.open(CACHE_NAME);
    const shell = await cache.match(SHELL_KEY);
    if (!shell) return;
    const html = await shell.text();
    const keep = new Set(shellAssetUrls(html));
    const requests = await cache.keys();
    await Promise.all(requests.map(async (request) => {
      const url = new URL(request.url);
      if (url.origin !== self.location.origin) return;
      if (!isShellAsset(url.pathname)) return;
      if (!url.searchParams.has('v')) return;
      if (!keep.has(request.url)) await cache.delete(request);
    }));
  } catch (_err) {
  }
}

function isExcluded(pathname) {
  return pathname.indexOf('/api/') === 0
    || pathname.indexOf('/a/') === 0
    || pathname.indexOf('/generated/') === 0
    || pathname === '/sw.js'
    || pathname === SHELL_KEY + 'sw.js';
}

function isShellAsset(pathname) {
  return SHELL_ASSET_PREFIXES.some((prefix) => pathname.indexOf(prefix) === 0)
    || SHELL_ASSET_FILES.indexOf(pathname) !== -1;
}

function shellAssetUrls(html) {
  const urls = new Set();
  const re = /(?:src|href)="([^"]+)"/g;
  let match;
  while ((match = re.exec(html))) {
    let url;
    try {
      url = new URL(match[1], self.location.origin);
    } catch (_err) {
      continue;
    }
    if (url.origin === self.location.origin && isShellAsset(url.pathname)) {
      urls.add(url.href);
    }
  }
  return Array.from(urls);
}

function cacheShellAssets(cache, html) {
  return Promise.allSettled(shellAssetUrls(html).map((url) => {
    const isManifest = SHELL_ASSET_FILES.includes(new URL(url).pathname);
    const request = new Request(url, { cache: isManifest ? 'reload' : 'default' });
    return cache.add(request);
  }));
}

async function refreshShell(request) {
  const response = await fetch(request);
  if (!response || !response.ok) return response;

  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(SHELL_KEY);
  const html = await response.clone().text();
  const oldHtml = cached ? await cached.text() : null;

  if (html !== oldHtml) {
    await cache.put(SHELL_KEY, response.clone());
    await cacheShellAssets(cache, html);
  }
  return response;
}

function navigationResponse(event) {
  const network = refreshShell(event.request).catch(() => null);
  event.waitUntil(network);

  return (async () => {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(SHELL_KEY);
    if (cached) return cached;
    return (await network) || Response.error();
  })();
}

function staleWhileRevalidate(event) {
  const network = fetch(event.request).then((response) => {
    if (response && response.ok) {
      const copy = response.clone();
      caches.open(CACHE_NAME)
        .then((cache) => cache.put(event.request, copy))
        .catch(() => {});
    }
    return response;
  }).catch(() => null);

  event.waitUntil(network);

  return (async () => {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(event.request);
    if (cached) return cached;
    return (await network) || Response.error();
  })();
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (isExcluded(url.pathname)) return;

  if (request.mode === 'navigate') {
    if (url.pathname === SHELL_KEY) {
      event.respondWith(navigationResponse(event));
    }
    return;
  }

  if (isShellAsset(url.pathname)) {
    event.respondWith(staleWhileRevalidate(event));
  }
});

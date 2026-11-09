/* WebToApp main-site shell cache.
   Repeat visits should not wait for the CDN round-trip. This worker caches
   the entry HTML and the static shell assets only. API calls, generated app
   pages and download pages always go to the network. */
'use strict';

const CACHE_NAME = 'wta-shell-v1';
const SHELL_KEY = '/';
const NETWORK_TIMEOUT_MS = 600;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.add(new Request(SHELL_KEY, { cache: 'reload' })))
      .catch(() => {})
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.indexOf('wta-shell-') === 0 && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

function isExcluded(pathname) {
  return pathname.indexOf('/api/') === 0
    || pathname.indexOf('/a/') === 0
    || pathname.indexOf('/generated/') === 0
    || pathname === '/sw.js';
}

function isShellAsset(pathname) {
  return pathname.indexOf('/css/') === 0
    || pathname.indexOf('/js/') === 0
    || pathname.indexOf('/assets/') === 0
    || pathname === '/manifest.webmanifest';
}

function navigationResponse(event) {
  const network = fetch(event.request).then((response) => {
    if (response && response.ok) {
      // Clone before any await: the page starts consuming the original body
      // as soon as this response is returned.
      const copy = response.clone();
      caches.open(CACHE_NAME)
        .then((cache) => cache.put(SHELL_KEY, copy))
        .catch(() => {});
    }
    return response;
  }).catch(() => null);

  // Called synchronously from the fetch event, before any await, so the
  // worker stays alive while the background refresh finishes.
  event.waitUntil(network);

  return (async () => {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(SHELL_KEY);
    if (!cached) return (await network) || Response.error();

    // Prefer a fast fresh response; otherwise paint the cached shell and let
    // the network request update it for the next navigation.
    const timeout = new Promise((resolve) => {
      setTimeout(() => resolve(null), NETWORK_TIMEOUT_MS);
    });
    const fresh = await Promise.race([network, timeout]);
    return (fresh && fresh.ok) ? fresh : cached;
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
    if (url.pathname === '/' || url.pathname === '/index.html') {
      event.respondWith(navigationResponse(event));
    }
    return;
  }

  if (isShellAsset(url.pathname)) {
    event.respondWith(staleWhileRevalidate(event));
  }
});

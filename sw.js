/* WebToApp main-site shell cache.
   Repeat visits should paint instantly, not wait for the CDN round-trip.
   This worker caches the entry HTML and the static shell assets only.
   API calls, generated app pages and download pages always go to the network. */
'use strict';

// v3: the retention notice reverted to 30 days and the 72-hour line was
// dropped from announcements.js. Bumping the bucket is what actually makes
// installed clients drop the old shell HTML + the cached notice file they
// were still serving from wta-shell-v2.
const CACHE_NAME = 'wta-shell-v3';
const SHELL_KEY = '/';
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
        await Promise.allSettled(shellAssetUrls(html).map((url) => cache.add(url)));
      }
    } catch (_err) {
      // The first navigation will populate the cache if precaching fails.
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.indexOf('wta-shell-') === 0 && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      ))
      .then(() => pruneStaleAssets())
      .then(() => self.clients.claim())
  );
});

// SWR entries are keyed by the full URL including ?v=, so every version bump
// used to leave the old asset in the bucket forever. Drop versioned entries
// whose exact URL is no longer referenced by the current shell HTML. Entries
// WITHOUT a ?v= (e.g. lazily loaded language files cached by SWR) are kept —
// they are not superseded by a version bump.
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
    // Pruning is best-effort; a failure must not block activation.
  }
}

function isExcluded(pathname) {
  return pathname.indexOf('/api/') === 0
    || pathname.indexOf('/a/') === 0
    || pathname.indexOf('/generated/') === 0
    || pathname === '/sw.js';
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

async function refreshShell(request) {
  const response = await fetch(request);
  if (!response || !response.ok) return response;

  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(SHELL_KEY);
  const html = await response.clone().text();
  const oldHtml = cached ? await cached.text() : null;

  // Only rewrite the cache and refetch assets when the HTML actually changed.
  if (html !== oldHtml) {
    await cache.put(SHELL_KEY, response.clone());
    await Promise.allSettled(shellAssetUrls(html).map((url) => cache.add(url)));
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
    if (url.pathname === '/' || url.pathname === '/index.html') {
      event.respondWith(navigationResponse(event));
    }
    return;
  }

  if (isShellAsset(url.pathname)) {
    event.respondWith(staleWhileRevalidate(event));
  }
});

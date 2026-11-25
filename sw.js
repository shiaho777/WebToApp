'use strict';

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    try {
      const keys = await caches.keys();
      await Promise.all(keys.filter((key) => key.startsWith('wta-shell-')).map((key) => caches.delete(key)));
    } finally {
      await self.registration.unregister();
    }
  })());
});

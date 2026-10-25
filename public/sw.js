// Minimal no-op service worker to prevent stale clients from receiving 404 responses.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

// Оффлайн-кэш: игра — один файл, поэтому кладём его целиком вместе с иконками.
// Версию поднимать при каждой выкладке, иначе телефон покажет старую сборку.
const V = 'frog-29.09-1053';
const FILES = ['./', './index.html', './manifest.webmanifest',
  './icons/icon-192.png', './icons/icon-512.png', './icons/icon-maskable-192.png', './icons/icon-maskable-512.png', './icons/apple-touch-icon.png'];
self.addEventListener('install', e => { e.waitUntil(caches.open(V).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
    if (res.ok && new URL(e.request.url).origin === location.origin) { const cp = res.clone(); caches.open(V).then(c => c.put(e.request, cp)); }
    return res;
  }).catch(() => caches.match('./index.html'))));
});

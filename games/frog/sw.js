// Оффлайн-кэш: игра — один файл, поэтому кладём его целиком вместе с иконками.
// Версию поднимать при каждой выкладке, иначе телефон покажет старую сборку.
const V = 'frog-21.10-1548';
const FILES = ['./', './index.html', './manifest.webmanifest',
  './icons/icon-192.png', './icons/icon-512.png', './icons/icon-maskable-192.png', './icons/icon-maskable-512.png', './icons/apple-touch-icon.png'];
// addAll ходит в сеть, но через обычный кэш браузера, а страница игры отдаётся
// с max-age=600. Поэтому новый воркер мог положить в свежий кэш СТАРУЮ страницу:
// версия поменялась, игра осталась прежней, и понять это со стороны невозможно.
// cache: 'reload' заставляет взять всё заново, минуя кэш браузера.
self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const c = await caches.open(V);
    await Promise.all(FILES.map(async f => {
      const r = await fetch(f, {cache: 'reload'});
      if (r.ok) await c.put(f, r);
    }));
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(res => {
    if (res.ok && new URL(e.request.url).origin === location.origin) { const cp = res.clone(); caches.open(V).then(c => c.put(e.request, cp)); }
    return res;
  }).catch(() => caches.match('./index.html'))));
});

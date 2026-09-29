// Регистрация сервис-воркера: отдельным файлом, чтобы тесты и скриншотер по-прежнему брали единственный <script> игры.
if ('serviceWorker' in navigator) addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));

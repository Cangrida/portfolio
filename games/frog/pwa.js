// Регистрация сервис-воркера: отдельным файлом, чтобы тесты и скриншотер по-прежнему брали единственный <script> игры.
// Когда новый воркер забирает управление, свежая сборка уже лежит в кэше, а на экране
// по-прежнему старая: окно нарисовано раньше. Сообщаем об этом игре, она сама покажет
// полоску «есть новая версия» между забегами. Молча перезагружать нельзя, убьёт забег.
if ('serviceWorker' in navigator) addEventListener('load', () => {
  navigator.serviceWorker.register('sw.js').then(() => {
    let had = !!navigator.serviceWorker.controller; // при самой первой установке управления ещё нет, и это не обновление
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (had) dispatchEvent(new Event('frog:update-ready'));
      had = true;
    });
  }).catch(() => {});
});

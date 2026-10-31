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

// Кнопка «Поставить на телефон».
//
// Её тут не было никогда, и это была дыра: на сайте стоят две кнопки, «играть»
// и «поставить», но вторая просто открывала ту же игру. Что страница ставится
// на телефон, знал только браузер, который прячет это в своём меню. Галя
// 31.10 справедливо спросила, почему обе ведут в одно и то же.
//
// Chrome и прочие на андроиде дают событие beforeinstallprompt: перехватываем
// его и показываем свою кнопку. Сафари на айфоне такого события не даёт вообще,
// поэтому там вместо кнопки подсказка, куда жать в самом сафари.
//
// Плашка живёт только на стартовом экране: первое касание игры её убирает,
// иначе она висела бы поверх забега.
(() => {
  const RU = (navigator.language || '').toLowerCase().startsWith('ru');
  const stoit = matchMedia('(display-mode: standalone)').matches
             || matchMedia('(display-mode: fullscreen)').matches
             || navigator.standalone;
  if (stoit || location.search.includes('noinstall')) return;

  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  let gotov = null, plashka = null;

  // Цвет свой, не выдуманный: красный снят с банки, которая тонет под лягушкой.
  // Жёлтый тут занят кнопкой «Играть», второй жёлтой плашкой глаз сбивается,
  // а зелёный Галя сравнила с красным и 31.10 выбрала красный.
  const CVETA = {kras: '#e02424', zel: '#4aa808'};
  const demo = (location.search.match(/installdemo=(\w+)/) || [])[1];
  const FON = CVETA[demo] || CVETA.kras;

  const pokazat = (tekst, knopka) => {
    if (plashka) return;
    plashka = document.createElement('button');
    plashka.type = 'button';
    plashka.textContent = tekst;
    // width:auto обязателен: у игры в стилях кнопки на всю ширину, без этого
    // плашка растягивается поперёк экрана и накрывает полоску высоты.
    plashka.style.cssText = `position:fixed;left:50%;transform:translateX(-50%);bottom:74px;
      z-index:9999;width:auto;max-width:92vw;box-sizing:border-box;padding:11px 20px;border:0;border-radius:999px;
      font:600 15px/1.25 system-ui,sans-serif;color:#fff;background:${FON};
      box-shadow:0 6px 18px rgba(0,0,0,.35);cursor:${knopka ? 'pointer' : 'default'};
      -webkit-tap-highlight-color:transparent`;
    plashka.addEventListener('pointerdown', e => e.stopPropagation());
    plashka.addEventListener('click', async e => {
      e.stopPropagation();
      if (!gotov) return;                       // подсказка для сафари: жать некуда
      gotov.prompt();
      await gotov.userChoice;
      gotov = null; ubrat();
    });
    document.body.appendChild(plashka);
    addEventListener('pointerdown', ubrat, {once: true});   // игра началась, плашка не нужна
  };
  const ubrat = () => { if (plashka) { plashka.remove(); plashka = null; } };

  addEventListener('beforeinstallprompt', e => {
    e.preventDefault(); gotov = e;
    pokazat(RU ? 'Поставить на телефон' : 'Install on phone', true);
  });
  addEventListener('appinstalled', ubrat);

  if (ios) pokazat(RU ? 'Поставить на телефон: «Поделиться» → «На экран „Домой“»'
                      : 'Install: Share → Add to Home Screen', false);
  // Для снимка экрана: ?installdemo рисует плашку без настоящего события браузера.
  if (location.search.includes('installdemo')) pokazat(RU ? 'Поставить на телефон' : 'Install on phone', true);
})();

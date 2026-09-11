import io,re,sys
s=io.open('index.html',encoding='utf-8').read()
r=s
def sub(a,b,where=r):
    global r
    if a not in r: sys.exit('не найдено: '+a[:60])
    r=r.replace(a,b,1)

sub('<html lang="ru">','<html lang="en">')
sub('<title>Галина Гольтяпина — Портфолио</title>','<title>Galina Goltyapina — Portfolio</title>')
sub('<meta name="description" content="Галина Гольтяпина (Cangrida) — 2D/3D-художник, аниматор и иллюстратор. 7+ лет в геймдеве: иллюстрация, Spine-анимация, 3D в Blender, Game UI. Портфолио и онлайн-выставка.">',
    '<meta name="description" content="Galina Goltyapina (Cangrida) is a 2D/3D artist, animator and illustrator. 7+ years in game development: illustration, Spine animation, 3D in Blender, game UI. Portfolio and online exhibition.">')
sub('<meta name="author" content="Галина Гольтяпина">','<meta name="author" content="Galina Goltyapina">')
sub('<link rel="canonical" href="https://cangrida.com/">','<link rel="canonical" href="https://cangrida.com/en.html">')
sub('<meta property="og:url" content="https://cangrida.com/">','<meta property="og:url" content="https://cangrida.com/en.html">')
sub('<meta property="og:title" content="Галина Гольтяпина — 2D/3D Artist · Animator · Illustrator">',
    '<meta property="og:title" content="Galina Goltyapina — 2D/3D Artist · Animator · Illustrator">')
sub('<meta property="og:description" content="Портфолио художника: иллюстрация, Spine-анимация, 3D в Blender, Game UI. 7+ лет в геймдеве. Онлайн-выставка 2026.">',
    '<meta property="og:description" content="Artist portfolio: illustration, Spine animation, 3D in Blender, game UI. 7+ years in game development. Online exhibition 2026.">')
sub('<meta property="og:locale" content="ru_RU">','<meta property="og:locale" content="en_US">')
sub('<meta property="og:locale:alternate" content="en_US">','<meta property="og:locale:alternate" content="ru_RU">')
sub('<link rel="alternate" hreflang="ru" href="https://cangrida.com/">',
    '<link rel="alternate" hreflang="ru" href="https://cangrida.com/">')
# английский по умолчанию на этой странице
sub('</head>','    <script>window.PAGE_LANG = "en";</script>\n</head>')
# пометка, что файл собран скриптом
r=r.replace('<!DOCTYPE html>','<!DOCTYPE html>\n<!-- Файл собран скриптом build-en.sh из index.html. Руками не править. -->',1)
io.open('en.html','w',encoding='utf-8').write(r)

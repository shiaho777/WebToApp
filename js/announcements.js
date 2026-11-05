/* WebToApp notices.
   This is the only place a notice is written. The page shows one small
   button in the top bar. A click opens a short panel; the text scrolls
   inside that panel.

   To add one: put a new object at the top of NOTICES (newest first).
   publishedAt is UTC, ISO-8601. Give title and paragraphs for every
   language in CHROME's list. Missing text falls back to English, then
   Chinese. Keep paragraphs as short sentences. */
(function () {
  'use strict';

  var LANGS = ['en', 'zh', 'ja', 'ar', 'ru', 'es', 'pt', 'fr', 'de'];

  var CHROME = {
    en: { kicker: 'Notices', heading: 'What changed' },
    zh: { kicker: '公告', heading: '站点通知' },
    ja: { kicker: 'お知らせ', heading: '変更のお知らせ' },
    ar: { kicker: 'إعلانات', heading: 'ما الذي تغيّر' },
    ru: { kicker: 'Объявления', heading: 'Что изменилось' },
    es: { kicker: 'Avisos', heading: 'Qué cambió' },
    pt: { kicker: 'Avisos', heading: 'O que mudou' },
    fr: { kicker: 'Annonces', heading: 'Ce qui a changé' },
    de: { kicker: 'Hinweise', heading: 'Was sich geändert hat' }
  };

  var NOTICES = [
    {
      "id": "2026-11-05-site-refresh",
      "publishedAt": "2026-11-05T16:30:00Z",
      "title": {
        "en": "A calmer homepage, cleaner market and no ads",
        "zh": "首页更简洁，市场信息更完整，广告已移除",
        "ja": "ホームを整理、マーケットを充実、広告を廃止",
        "ar": "صفحة رئيسية أهدأ وسوق أوضح وبلا إعلانات",
        "ru": "Спокойнее главная, понятнее рынок, без рекламы",
        "es": "Inicio más limpio, mercado más claro y sin anuncios",
        "pt": "Início mais limpo, mercado mais claro e sem anúncios",
        "fr": "Accueil plus sobre, marché plus clair, sans publicité",
        "de": "Ruhigere Startseite, klarerer Markt, keine Werbung"
      },
      "paragraphs": {
        "en": [
          "The homepage is back to one centered column: paste a link, pick URL or HTML, and generate. The device preview experiment has been removed.",
          "Market cards show the publish time, visit count and download count again, and you can keep loading more apps.",
          "Ads and the privacy page are gone. The site no longer loads AdSense, and generated download pages no longer include ad scripts.",
          "App download pages now use the same centered layout, with a five-platform card grid and dark mode."
        ],
        "zh": [
          "首页回到单列居中：粘贴链接，选择网址或 HTML，然后生成。之前的设备预览功能已经移除。",
          "市场卡片重新显示发布时间、访问量和下载量，也可以继续加载更多应用。",
          "广告和隐私说明页已移除。站点不再加载 AdSense，生成的下载页也不再包含广告脚本。",
          "应用下载页也换成了同样的居中布局，五个平台改成卡片网格，并支持暗色模式。"
        ],
        "ja": [
          "ホームは中央揃えの1列に戻りました。リンクを貼り、URLかHTMLを選んで生成するだけです。デバイスプレビューは削除しました。",
          "マーケットのカードに公開日時・アクセス数・ダウンロード数が戻り、さらに多くのアプリを読み込めます。",
          "広告とプライバシーページを削除しました。サイトはAdSenseを読み込まず、生成されたダウンロードページにも広告スクリプトはありません。",
          "アプリのダウンロードページも同じ中央揃えのレイアウトになり、5プラットフォームのカードグリッドとダークモードに対応しました。"
        ],
        "ar": [
          "عادت الصفحة الرئيسية إلى عمود واحد في الوسط: الصق رابطاً، اختر URL أو HTML، ثم أنشئ. أُزيلت معاينة الجهاز التجريبية.",
          "تعرض بطاقات السوق وقت النشر وعدد الزيارات والتنزيلات مجدداً، ويمكنك تحميل المزيد من التطبيقات.",
          "أُزيلت الإعلانات وصفحة الخصوصية. لم يعد الموقع يحمّل AdSense، ولم تعد صفحات التنزيل المُنشأة تتضمن نصوصاً إعلانية.",
          "تستخدم صفحات تنزيل التطبيقات الآن التخطيط المركزي نفسه، مع شبكة بطاقات للمنصات الخمس ووضع داكن."
        ],
        "ru": [
          "Главная снова одна колонка по центру: вставьте ссылку, выберите URL или HTML и создайте приложение. Экспериментальный предпросмотр устройства убран.",
          "Карточки рынка снова показывают дату публикации, посещения и загрузки, а список можно загружать дальше.",
          "Реклама и страница конфиденциальности удалены. Сайт больше не загружает AdSense, а созданные страницы загрузки не содержат рекламных скриптов.",
          "Страницы загрузки приложений теперь используют тот же центрированный макет, сетку из пяти платформ и тёмную тему."
        ],
        "es": [
          "La portada vuelve a una sola columna centrada: pega un enlace, elige URL o HTML y genera. La vista previa del dispositivo se ha eliminado.",
          "Las fichas del mercado vuelven a mostrar la fecha de publicación, las visitas y las descargas, y puedes seguir cargando apps.",
          "Los anuncios y la página de privacidad ya no están. El sitio no carga AdSense y las páginas de descarga generadas ya no incluyen scripts de anuncios.",
          "Las páginas de descarga de apps usan ahora el mismo diseño centrado, con una cuadrícula de cinco plataformas y modo oscuro."
        ],
        "pt": [
          "A página inicial voltou a uma coluna centralizada: cole um link, escolha URL ou HTML e gere. A prévia do dispositivo foi removida.",
          "Os cards do mercado voltaram a mostrar a data de publicação, as visitas e os downloads, e você pode continuar carregando apps.",
          "Os anúncios e a página de privacidade foram removidos. O site não carrega mais o AdSense e as páginas de download geradas não incluem scripts de anúncios.",
          "As páginas de download dos apps agora usam o mesmo layout centralizado, com uma grade de cinco plataformas e modo escuro."
        ],
        "fr": [
          "L’accueil revient à une seule colonne centrée : collez un lien, choisissez URL ou HTML, puis générez. L’aperçu d’appareil a été retiré.",
          "Les fiches du marché affichent de nouveau la date de publication, les visites et les téléchargements, et vous pouvez charger plus d’apps.",
          "Les annonces et la page de confidentialité ont disparu. Le site ne charge plus AdSense et les pages de téléchargement générées n’incluent plus de scripts publicitaires.",
          "Les pages de téléchargement des apps utilisent désormais la même mise en page centrée, avec une grille de cinq plateformes et un mode sombre."
        ],
        "de": [
          "Die Startseite ist wieder eine zentrierte Spalte: Link einfügen, URL oder HTML wählen, fertig. Die Gerätevorschau wurde entfernt.",
          "Marktkarten zeigen wieder Veröffentlichungsdatum, Aufrufe und Downloads; weitere Apps lassen sich nachladen.",
          "Werbung und Datenschutzseite sind weg. Die Website lädt kein AdSense mehr, und generierte Download-Seiten enthalten keine Werbeskripte.",
          "App-Download-Seiten nutzen jetzt dasselbe zentrierte Layout, mit einem Kartenraster für fünf Plattformen und Dark Mode."
        ]
      }
    },
    {
      id: '2026-10-13-market-icons',
      publishedAt: '2026-10-13T16:00:00Z',
      title: {
        en: 'Market cleanup: duplicate apps and flat icons',
        zh: '市场整理：重复应用和纯色图标',
        ja: '市場の整理：重複アプリと単色アイコン',
        ar: 'ترتيب السوق: التطبيقات المكررة والأيقونات أحادية اللون',
        ru: 'Разбор рынка: дубликаты и однотонные значки',
        es: 'Limpieza del mercado: apps repetidas e iconos planos',
        pt: 'Limpeza do mercado: apps repetidos e ícones chapados',
        fr: 'Rangement du marché : doublons et icônes unies',
        de: 'Markt aufgeräumt: doppelte Apps und flache Symbole'
      },
      paragraphs: {
        en: [
          'On 13 October 2026 we tidied the public market.',
          'When one person had several public apps with the same name, the same address, the same uploaded icon, or the same page content, we kept only the newest. The earlier ones have left the market. Their download links still open, and we are not putting those copies back.',
          'An icon that is 90% one color, including a near-purple block, cannot be used. We removed those pictures. The white square on a card is the empty icon slot, not a white icon we drew.',
          'If your app is still listed and the icon slot is empty, rebuild it with a picture that has a real design before 20 October 2026, 16:00 UTC. If it is still empty or still a flat color then, the app leaves the market. A flat icon found later gets the same seven days from the day we notice it.'
        ],
        zh: [
          '2026年10月13日，我们整理了公开市场。',
          '同一个人名下，名字、网址、自己上传的图标或页面内容相同的应用，只保留最新的一条。更早的那些已经退出市场，下载链接还能打开，这次不会再放回去。',
          '一种颜色占到画面 90% 以上的图标不能用，接近纯紫的色块也算。这些图已经拿掉。卡片上的白块是空出来的图标位置，不是我们换成了白色图标。',
          '图标被拿掉、应用还在市场上的，请在 2026年10月20日 16:00（UTC）前重新生成，换上一张有图案的图。到那时如果还是空的，或者仍是这种纯色图，应用会退出市场。以后新发现的纯色图标，从发现那天起同样给 7 天。'
        ],
        ja: [
          '2026年10月13日、公開市場を整理しました。',
          '同じ人が出した公開アプリで、名前・アドレス・アップロードしたアイコン・ページ内容が同じものは、いちばん新しい一つだけ残しました。それより前のものは市場から外れています。ダウンロードリンクは開きます。戻す予定はありません。',
          '画面の90%以上が一つの色のアイコンは使えません。紫に近いベタ塗りも同じです。その画像は外しました。カードの白い四角は空いた枠で、白いアイコンに描き替えたのではありません。',
          'アイコンが外れたまま市場に残っているアプリは、2026年10月20日 16:00（UTC）までに、模様のある画像で作り直してください。その時点で空のまま、または単色のままだと市場から外れます。このあと見つかった単色アイコンも、見つかった日から7日です。'
        ],
        ar: [
          'في 13 أكتوبر 2026 رتّبنا السوق العام.',
          'إذا نشر الشخص نفسه عدة تطبيقات عامة بالاسم نفسه أو العنوان نفسه أو الأيقونة المرفوعة نفسها أو المحتوى نفسه، أبقينا الأحدث فقط. الأقدم خرج من السوق. رابط التنزيل ما زال يفتح، ولن نعيد تلك النسخ.',
          'الأيقونة التي يشغل لون واحد 90% من صورتها لا تُستخدم، بما في ذلك الكتلة القريبة من البنفسجي. أزلنا هذه الصور. المربع الأبيض على البطاقة مكان فارغ، وليس أيقونة بيضاء رسمناها.',
          'إذا بقي تطبيقك في السوق وخانة الأيقونة فارغة، أعد بناءه بصورة فيها رسم قبل 20 أكتوبر 2026 الساعة 16:00 بالتوقيت العالمي. إن بقيت فارغة أو بلون واحد عندها، يخرج التطبيق من السوق. أي أيقونة مسطحة نكتشفها لاحقًا تأخذ الأيام السبعة نفسها من يوم اكتشافها.'
        ],
        ru: [
          '13 октября 2026 мы привели публичный рынок в порядок.',
          'Если у одного человека было несколько публичных приложений с тем же именем, адресом, загруженным значком или содержимым страницы, мы оставили только самое новое. Более ранние ушли с рынка. Ссылки на скачивание открываются, возвращать эти копии мы не будем.',
          'Значок, на 90% состоящий из одного цвета, включая почти фиолетовую плашку, использовать нельзя. Такие картинки сняты. Белый квадрат на карточке — пустое место под значок, а не белый значок, который мы нарисовали.',
          'Если приложение всё ещё в рынке, а место значка пустое, соберите его заново с настоящим рисунком до 20 октября 2026, 16:00 UTC. Если к этому времени значка нет или он снова однотонный, приложение уйдёт с рынка. Однотонный значок, найденный позже, получает те же семь дней с дня, когда мы его заметили.'
        ],
        es: [
          'El 13 de octubre de 2026 ordenamos el mercado público.',
          'Si una persona tenía varias apps públicas con el mismo nombre, la misma dirección, el mismo icono subido o el mismo contenido, dejamos solo la más nueva. Las anteriores salieron del mercado. El enlace de descarga sigue abriendo, y no vamos a devolver esas copias.',
          'Un icono que es un 90% de un solo color, incluido un bloque casi morado, no se puede usar. Quitamos esas imágenes. El cuadrado blanco de la ficha es el hueco vacío, no un icono blanco que hayamos pintado.',
          'Si tu app sigue en el mercado y el hueco está vacío, vuelve a generarla con un dibujo de verdad antes del 20 de octubre de 2026, 16:00 UTC. Si entonces sigue vacío o sigue siendo un color plano, la app sale del mercado. Un icono plano que encontremos más adelante tiene los mismos siete días desde el día en que lo veamos.'
        ],
        pt: [
          'Em 13 de outubro de 2026 arrumamos o mercado público.',
          'Quando a mesma pessoa tinha vários apps públicos com o mesmo nome, o mesmo endereço, o mesmo ícone enviado ou o mesmo conteúdo, ficou só o mais novo. Os anteriores saíram do mercado. O link de download continua abrindo, e essas cópias não voltam.',
          'Um ícone em que uma cor ocupa 90% da imagem não pode ser usado, inclusive um bloco quase roxo. Essas imagens foram retiradas. O quadrado branco no card é o espaço vazio, não um ícone branco que tenhamos desenhado.',
          'Se o seu app continua no mercado e o espaço do ícone está vazio, gere de novo com um desenho de verdade até 20 de outubro de 2026, 16:00 UTC. Se nessa hora ainda estiver vazio ou ainda for uma cor chapada, o app sai do mercado. Um ícone chapado encontrado depois ganha os mesmos sete dias a partir do dia em que o virmos.'
        ],
        fr: [
          'Le 13 octobre 2026, le marché public a été rangé.',
          'Quand une même personne avait plusieurs apps publiques avec le même nom, la même adresse, la même icône envoyée ou le même contenu, seule la plus récente est restée. Les plus anciennes ont quitté le marché. Le lien de téléchargement s’ouvre encore, et ces copies ne reviennent pas.',
          'Une icône dont 90 % est d’une seule couleur, y compris un aplat presque violet, ne peut pas servir. Ces images ont été retirées. Le carré blanc sur la fiche est l’emplacement vide, pas une icône blanche que nous aurions dessinée.',
          'Si votre app est encore au marché et que l’emplacement est vide, régénérez-la avec un vrai dessin avant le 20 octobre 2026, 16:00 UTC. S’il est encore vide ou encore d’une couleur unie à ce moment-là, l’app quitte le marché. Une icône unie trouvée plus tard a les mêmes sept jours à partir du jour où nous la voyons.'
        ],
        de: [
          'Am 13. Oktober 2026 haben wir den öffentlichen Markt aufgeräumt.',
          'Hatte dieselbe Person mehrere öffentliche Apps mit demselben Namen, derselben Adresse, demselben hochgeladenen Symbol oder demselben Inhalt, ist nur die neueste geblieben. Die älteren haben den Markt verlassen. Der Download-Link geht noch auf, und diese Kopien kommen nicht zurück.',
          'Ein Symbol, das zu 90 % aus einer Farbe besteht, auch ein fast lilafarbener Block, kann nicht verwendet werden. Diese Bilder sind weg. Das weiße Quadrat auf der Karte ist der leere Platz, kein weißes Symbol, das wir gezeichnet hätten.',
          'Wenn deine App noch im Markt steht und der Platz leer ist, erstelle sie bis zum 20. Oktober 2026, 16:00 UTC neu mit einem echten Bild. Ist er dann noch leer oder wieder einfarbig, verlässt die App den Markt. Ein später gefundenes flaches Symbol bekommt dieselben sieben Tage ab dem Tag, an dem wir es sehen.'
        ]
      }
    }
  ];

  function pick(map, lang) {
    if (!map) return null;
    if (map[lang]) return map[lang];
    if (map.en) return map.en;
    return map.zh || null;
  }

  function esc(text) {
    return String(text == null ? '' : text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function dateLabel(iso) {
    var day = String(iso || '').slice(0, 10);
    return day || '';
  }

  function render() {
    var wrap = document.getElementById('nav-notices') || document.querySelector('.nav-notices');
    var btn = document.getElementById('notices-btn');
    var title = document.getElementById('notices-title');
    var scroll = document.getElementById('notices-scroll');
    if (!wrap || !btn || !title || !scroll) return;
    var lang = (window.I18n && LANGS.indexOf(window.I18n.current) !== -1) ? window.I18n.current : 'en';
    var chrome = CHROME[lang] || CHROME.en;
    if (!NOTICES.length) {
      wrap.hidden = true;
      return;
    }
    wrap.hidden = false;
    btn.setAttribute('aria-label', chrome.heading);
    btn.title = chrome.heading;
    title.textContent = chrome.heading;
    var closeBtn = document.getElementById('notices-close');
    if (closeBtn) closeBtn.setAttribute('aria-label', lang === 'zh' ? '关闭' : 'Close');
    scroll.innerHTML = '<ol class="nav-notices-list">' + NOTICES.map(function (notice) {
      var heading = pick(notice.title, lang) || notice.id;
      var paragraphs = pick(notice.paragraphs, lang) || [];
      var body = paragraphs.map(function (paragraph) {
        return '<p>' + esc(paragraph) + '</p>';
      }).join('');
      return '' +
        '<li class="nav-notices-item">' +
          '<time class="nav-notices-date" datetime="' + esc(notice.publishedAt) + '">' + esc(dateLabel(notice.publishedAt)) + '</time>' +
          '<h3>' + esc(heading) + '</h3>' +
          body +
        '</li>';
    }).join('') + '</ol>';
  }

  function bind() {
    var btn = document.getElementById('notices-btn');
    var panel = document.getElementById('notices-panel');
    var closeBtn = document.getElementById('notices-close');
    if (!btn || !panel || btn.dataset.bound === '1') return;
    btn.dataset.bound = '1';

    function isOpen() {
      return !panel.classList.contains('hidden');
    }

    function setOpen(open) {
      panel.classList.toggle('hidden', !open);
      panel.hidden = !open;
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    btn.addEventListener('click', function (event) {
      event.stopPropagation();
      setOpen(!isOpen());
    });
    if (closeBtn) {
      closeBtn.addEventListener('click', function (event) {
        event.stopPropagation();
        setOpen(false);
        btn.focus();
      });
    }
    panel.addEventListener('click', function (event) {
      event.stopPropagation();
    });
    document.addEventListener('click', function () {
      if (isOpen()) setOpen(false);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && isOpen()) {
        setOpen(false);
        btn.focus();
      }
    });
  }

  function start() {
    bind();
    render();
  }

  window.WTA_NOTICES = NOTICES;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
  window.addEventListener('i18n:changed', render);
})();

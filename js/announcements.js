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

  var LANGS = ['en', 'zh', 'ja', 'ko', 'ar', 'ru', 'es', 'pt', 'fr', 'de'];

  var CHROME = {
    en: { kicker: 'Notices', heading: 'What changed' },
    zh: { kicker: '公告', heading: '站点通知' },
    ja: { kicker: 'お知らせ', heading: '変更のお知らせ' },
    ko: { kicker: '공지', heading: '변경 사항' },
    ar: { kicker: 'إعلانات', heading: 'ما الذي تغيّر' },
    ru: { kicker: 'Объявления', heading: 'Что изменилось' },
    es: { kicker: 'Avisos', heading: 'Qué cambió' },
    pt: { kicker: 'Avisos', heading: 'O que mudou' },
    fr: { kicker: 'Annonces', heading: 'Ce qui a changé' },
    de: { kicker: 'Hinweise', heading: 'Was sich geändert hat' }
  };

  var NOTICES = [
    {
      "id": "2026-11-18-anti-abuse",
      "publishedAt": "2026-11-18T01:30:00Z",
      "title": {
        "en": "Staying fast and free: new anti-abuse defenses",
        "zh": "更快更稳的免费服务：反滥用加固上线",
        "ja": "速さと無料を守る：不正利用対策を強化",
        "ko": "빠르고 무료로 유지: 악용 방지 강화",
        "ar": "أسرع ومجاني دائماً: دفاعات جديدة ضد إساءة الاستخدام",
        "ru": "Быстро и бесплатно: новая защита от злоупотреблений",
        "es": "Rápido y gratis: nuevas defensas contra el abuso",
        "pt": "Rápido e grátis: novas defesas contra abuso",
        "fr": "Rapide et gratuit : nouvelles défenses anti-abus",
        "de": "Schnell und kostenlos: neue Schutzmaßnahmen gegen Missbrauch"
      },
      "paragraphs": {
        "en": [
          "WebToApp stays free with no accounts and no captchas. To keep it that way under abuse, we added defenses that cost attackers — not you.",
          "Builds now carry an invisible proof-of-work: your browser solves a tiny puzzle in the background before submitting. Normal use feels the same; mass automated abuse becomes expensive.",
          "The puzzle gets harder only when the service is under load, so real users are barely affected while attackers are slowed down.",
          "Fair-use budgets now cap total builds per hour, per IP per day, and per website per day — so a flood of junk can't crowd out real creators.",
          "Every build tool now has a time limit, and the service is fenced at the system level. One stuck job can no longer slow everyone else down."
        ],
        "zh": [
          "WebToApp 继续免费、无账号、无验证码。为了在滥用之下守住这一点，我们加了让攻击者付出代价、而不是让你付出代价的防护。",
          "生成现在带一道隐形工作量证明：浏览器在提交前于后台解一道小题。正常使用几乎无感，批量自动化滥用则变得昂贵。",
          "只有在服务承压时题目才会变难，真实用户几乎不受影响，攻击者却被拖慢。",
          "新增公平使用额度：每小时总生成数、每 IP 每日、每个网址每日都有上限，垃圾洪流挤不掉真实创作者。",
          "每个构建工具都有了时限，服务也在系统层面加了围栏。一个卡住的任务不再拖慢所有人。"
        ],
        "ja": [
          "WebToApp はアカウント不要・CAPTCHA なしの無料を続けます。不正利用の下でもそれを守るため、あなたではなく攻撃者にコストを負わせる防御を追加しました。",
          "生成には見えないプルーフ・オブ・ワークが付きます。ブラウザが送信前にバックグラウンドで小さなパズルを解きます。通常利用はほぼ変わらず、大量の自動滥用は高コストになります。",
          "パズルはサービスが高負荷のときだけ難しくなるので、実ユーザーはほぼ影響を受けず、攻撃者は遅くなります。",
          "公正利用の上限を追加：毎時の総生成数、IP あたり毎日、サイトあたり毎日。ジャンクの洪水が本物のクリエイターを押し出せなくなります。",
          "すべてのビルドツールに時間制限が付き、サービスはシステムレベルで隔離されました。一つの停止したジョブが全体を遅くすることはもうありません。"
        ],
        "ko": [
          "WebToApp는 계정 없이, 캡차 없이 무료로 유지됩니다. 악용 속에서도 이를 지키기 위해, 여러분이 아닌 공격자에게 비용을 부과하는 방어를 추가했습니다.",
          "이제 생성에는 보이지 않는 작업 증명이 붙습니다. 브라우저가 제출 전 백그라운드에서 작은 퍼즐을 풉니다. 일반 사용은 거의 그대로이고, 대량 자동 악용은 비싸집니다.",
          "퍼즐은 서비스에 부하가 걸릴 때만 어려워지므로, 실제 사용자는 거의 영향이 없고 공격자는 느려집니다.",
          "공정 사용 한도를 추가했습니다: 시간당 총 생성 수, IP당 일일, 웹사이트당 일일. 쓰레기 홍수가 진짜 창작자를 밀어내지 못합니다.",
          "모든 빌드 도구에 시간 제한이 붙었고, 서비스는 시스템 수준에서 격리되었습니다. 멈춘 작업 하나가 모두를 느리게 하지 못합니다."
        ],
        "ar": [
          "يبقى WebToApp مجانياً بلا حسابات وبلا رموز تحقق. وللحفاظ على ذلك تحت إساءة الاستخدام، أضفنا دفاعات تُكلّف المهاجمين — لا أنت.",
          "تحمل عمليات الإنشاء الآن إثبات عمل غير مرئي: يحل متصفحك لغزاً صغيراً في الخلفية قبل الإرسال. الاستخدام العادي يبدو كما هو، بينما تصبح الإساءة الآلية الجماعية مكلفة.",
          "يصعب اللغز فقط عندما يكون الخدمة تحت الضغط، فلا يتأثر المستخدمون الحقيقيون إلا قليلاً بينما يتباطأ المهاجمون.",
          "أضفنا حدود استخدام عادل: إجمالي الإنشاءات في الساعة، ولكل IP يومياً، ولكل موقع يومياً — فلا يزاحم فيضان المحتوى غير المرغوب المبدعين الحقيقيين.",
          "أصبح لكل أداة بناء حد زمني، وتم تسييج الخدمة على مستوى النظام. لم تعد مهمة واحدة عالقة تبطئ الجميع."
        ],
        "ru": [
          "WebToApp остаётся бесплатным, без аккаунтов и без капч. Чтобы сохранить это при злоупотреблениях, мы добавили защиту, которая стоит дорого атакующим — а не вам.",
          "Теперь каждая сборка несёт невидимое доказательство работы: браузер решает маленькую головоломку в фоне перед отправкой. Обычное использование почти не меняется, а массовые автоматические злоупотребления становятся дорогими.",
          "Головоломка усложняется только когда сервис под нагрузкой, поэтому реальные пользователи почти не затронуты, а атакующие замедляются.",
          "Добавлены лимиты честного использования: всего сборок в час, на IP в день и на сайт в день — поток мусора не вытеснит настоящих авторов.",
          "У каждого инструмента сборки теперь есть лимит времени, а сервис ограждён на уровне системы. Одна зависшая задача больше не замедляет всех."
        ],
        "es": [
          "WebToApp sigue gratis, sin cuentas y sin captchas. Para mantenerlo así bajo abuso, añadimos defensas que cuestan a los atacantes — no a ti.",
          "Las generaciones llevan ahora una prueba de trabajo invisible: tu navegador resuelve un pequeño puzzle en segundo plano antes de enviar. El uso normal se siente igual; el abuso automatizado masivo se vuelve caro.",
          "El puzzle solo se vuelve más difícil cuando el servicio está bajo carga, así que los usuarios reales apenas se ven afectados mientras los atacantes se ralentizan.",
          "Añadimos límites de uso justo: generaciones totales por hora, por IP al día y por sitio web al día — una avalancha de basura no desplaza a los creadores reales.",
          "Cada herramienta de construcción tiene ahora un límite de tiempo, y el servicio está cercado a nivel de sistema. Un trabajo atascado ya no ralentiza a todos."
        ],
        "pt": [
          "O WebToApp continua grátis, sem contas e sem captchas. Para manter isso sob abuso, adicionamos defesas que custam aos atacantes — não a você.",
          "As gerações agora carregam uma prova de trabalho invisível: seu navegador resolve um pequeno quebra-cabeça em segundo plano antes de enviar. O uso normal parece o mesmo; o abuso automatizado em massa fica caro.",
          "O quebra-cabeça só fica mais difícil quando o serviço está sob carga, então usuários reais quase não são afetados enquanto atacantes desaceleram.",
          "Adicionamos limites de uso justo: gerações totais por hora, por IP por dia e por site por dia — uma enxurrada de lixo não desloca os criadores reais.",
          "Cada ferramenta de build agora tem um limite de tempo, e o serviço está cercado no nível do sistema. Um trabalho travado não desacelera mais todos."
        ],
        "fr": [
          "WebToApp reste gratuit, sans compte et sans captcha. Pour le préserver sous abus, nous avons ajouté des défenses qui coûtent aux attaquants — pas à vous.",
          "Les générations portent désormais une preuve de travail invisible : votre navigateur résout un petit puzzle en arrière-plan avant l’envoi. L’usage normal semble identique ; l’abus automatisé massif devient coûteux.",
          "Le puzzle ne se durcit que lorsque le service est sous charge, donc les vrais utilisateurs sont à peine affectés tandis que les attaquants ralentissent.",
          "Nous avons ajouté des budgets d’usage équitable : générations totales par heure, par IP par jour et par site par jour — un déluge de déchets n’évince plus les vrais créateurs.",
          "Chaque outil de build a désormais une limite de temps, et le service est clôturé au niveau système. Une tâche bloquée ne ralentit plus tout le monde."
        ],
        "de": [
          "WebToApp bleibt kostenlos, ohne Konten und ohne Captchas. Um das unter Missbrauch zu bewahren, haben wir Schutzmaßnahmen eingebaut, die Angreifer etwas kosten — nicht dich.",
          "Builds tragen jetzt einen unsichtbaren Arbeitsnachweis: Dein Browser löst im Hintergrund ein kleines Rätsel, bevor er sendet. Normale Nutzung fühlt sich gleich an; massenhafter automatisierter Missbrauch wird teuer.",
          "Das Rätsel wird nur schwieriger, wenn der Dienst unter Last steht, also sind echte Nutzer kaum betroffen, während Angreifer verlangsamt werden.",
          "Wir haben Fair-Use-Budgets eingebaut: Builds pro Stunde insgesamt, pro IP pro Tag und pro Website pro Tag — eine Flut aus Müll verdrängt keine echten Creator mehr.",
          "Jedes Build-Tool hat jetzt ein Zeitlimit, und der Dienst ist auf Systemebene eingezäunt. Ein hängender Job verlangsamt nicht mehr alle."
        ]
      }
    },
    {
      "id": "2026-11-16-speed-and-icons",
      "publishedAt": "2026-11-16T14:30:00Z",
      "title": {
        "en": "Faster builds, full market search and a new icon policy",
        "zh": "构建提速、市场搜索补全，图标新规上线",
        "ja": "ビルド高速化、マーケット検索の完全対応、アイコン新ルール",
        "ko": "빌드 속도 개선, 마켓 검색 완전 지원, 새 아이콘 정책",
        "ar": "بناء أسرع وبحث شامل في السوق وسياسة أيقونات جديدة",
        "ru": "Быстрее сборка, полный поиск по рынку и новая политика значков",
        "es": "Generación más rápida, búsqueda completa y nueva política de iconos",
        "pt": "Geração mais rápida, busca completa e nova política de ícones",
        "fr": "Génération plus rapide, recherche complète et nouvelle politique d’icônes",
        "de": "Schnellere Builds, vollständige Marktsuche und neue Symbol-Regeln"
      },
      "paragraphs": {
        "en": [
          "Builds are faster and steadier: heavy work no longer blocks other visitors, the build queue has a fair cap, and history imports run in the background.",
          "Market search and the rating board now cover every public app, not just the newest ones — older apps are findable again.",
          "The first screen loads lighter: only your language is downloaded instead of all ten, and notices render when you open them.",
          "New icon policy: publishing to the market now requires a usable icon. Flat or missing icons are rejected at publish time, with a clear upload prompt.",
          "Apps already on the market whose icon fails the check get 48 hours to upload a real picture before they leave the market. The old 7-day window is gone.",
          "Under the hood: Android rebuilds are quicker, icon fetching stops as soon as a perfect icon is found, and CDN uploads retry instead of failing silently."
        ],
        "zh": [
          "构建更快更稳：重活不再阻塞其他访客，生成队列有了公平上限，历史导入改在后台执行。",
          "市场搜索和评分榜现在覆盖全部公开应用，不再只有最新的一批——老应用也能被搜到了。",
          "首屏加载更轻：只下载你使用的语言而不是全部十种，公告点开时才渲染。",
          "图标新规：公开到市场必须有可用图标。纯色或缺失的图标会在公开时被拒绝，并给出明确的上传引导。",
          "已在市场上、图标未通过检查的应用，有 48 小时上传一张有图案的图，逾期退出市场。旧的 7 天窗口已取消。",
          "底层改进：Android 重建更快，图标抓取拿到合格图标即停止，CDN 上传失败会自动重试而不是悄悄丢掉。"
        ],
        "ja": [
          "ビルドが速く安定しました。重い処理が他の訪問者をブロックしなくなり、生成キューに公平な上限を設け、履歴インポートはバックグラウンドで実行されます。",
          "マーケット検索と評価ボードがすべての公開アプリを対象にするようになりました。最新分だけでなく、古いアプリも見つかります。",
          "最初の画面が軽くなりました。10言語すべてではなく使用中の言語だけをダウンロードし、お知らせは開いたときに描画されます。",
          "アイコン新ルール：マーケットへの公開には使えるアイコンが必須です。単色や欠落したアイコンは公開時に拒否され、明確なアップロード案内が表示されます。",
          "すでにマーケットにあり検査に通らないアイコンのアプリは、48時間以内に模様のある画像を上げてください。過ぎると市場から外れます。旧7日間の猶予は廃止されました。",
          "内部改善：Androidの再ビルドが速くなり、アイコン取得は合格アイコンが見つかると即停止し、CDNアップロードは黙って失敗せず再試行します。"
        ],
        "ko": [
          "빌드가 더 빠르고 안정적입니다. 무거운 작업이 다른 방문자를 차단하지 않고, 생성 대기열에 공정한 상한이 생겼으며, 기록 가져오기는 백그라운드에서 실행됩니다.",
          "마켓 검색과 평점 보드가 모든 공개 앱을 대상으로 합니다. 최신 앱만이 아니라 오래된 앱도 찾을 수 있습니다.",
          "첫 화면이 더 가벼워졌습니다. 열 개 언어 전체가 아니라 사용 중인 언어만 다운로드하고, 공지는 열 때 렌더링됩니다.",
          "새 아이콘 정책: 마켓 공개에는 사용 가능한 아이콘이 필수입니다. 단색이거나 없는 아이콘은 공개 시 거부되며 명확한 업로드 안내가 표시됩니다.",
          "이미 마켓에 있고 검사에 통과하지 못한 아이콘의 앱은 48시간 안에 실제 이미지를 업로드해야 하며, 기한이 지나면 마켓에서 제외됩니다. 기존 7일 유예는 폐지되었습니다.",
          "내부 개선: Android 재빌드가 빨라지고, 아이콘 가져오기는 합격 아이콘을 찾으면 즉시 멈추며, CDN 업로드는 조용히 실패하지 않고 재시도합니다."
        ],
        "ar": [
          "أصبح البناء أسرع وأكثر استقراراً: لم تعد العمليات الثقيلة تعيق الزوار الآخرين، ولطابور الإنشاء حد عادل، ويعمل استيراد السجل في الخلفية.",
          "يغطي بحث السوق ولوحة التقييمات الآن كل التطبيقات العامة، وليس الأحدث فقط — يمكن العثور على التطبيقات القديمة مجدداً.",
          "أصبحت الشاشة الأولى أخف: تُنزَّل لغتك فقط بدل اللغات العشر كلها، وتُعرض الإعلانات عند فتحها.",
          "سياسة الأيقونات الجديدة: النشر في السوق يتطلب أيقونة صالحة. تُرفض الأيقونات أحادية اللون أو المفقودة عند النشر مع إرشاد واضح للرفع.",
          "الت التطبيقات الموجودة في السوق والتي لا تجتاز أيقونتها الفحص مهلة 48 ساعة لرفع صورة فيها رسم، وإلا خرجت من السوق. أُلغيت مهلة الأيام السبعة القديمة.",
          "تحسينات داخلية: إعادة بناء Android أسرع، ويتوقف جلب الأيقونات فور العثور على أيقونة مناسبة، وتُعاد محاولات رفع CDN بدل الفشل بصمت."
        ],
        "ru": [
          "Сборка стала быстрее и стабильнее: тяжёлые операции больше не блокируют других посетителей, у очереди генерации появился честный лимит, а импорт истории выполняется в фоне.",
          "Поиск по рынку и доска рейтингов теперь охватывают все публичные приложения, а не только новейшие — старые приложения снова находятся.",
          "Первый экран стал легче: загружается только ваш язык вместо всех десяти, а объявления отрисовываются при открытии.",
          "Новая политика значков: для публикации на рынке нужен пригодный значок. Однотонные или отсутствующие значки отклоняются при публикации с понятной подсказкой загрузить изображение.",
          "Приложения уже на рынке, чей значок не прошёл проверку, получают 48 часов на загрузку настоящего рисунка, иначе покидают рынок. Прежнее окно в 7 дней отменено.",
          "Под капотом: пересборка Android быстрее, загрузка значков останавливается сразу после нахождения подходящего, а загрузки на CDN повторяются при сбое, а не теряются молча."
        ],
        "es": [
          "La generación es más rápida y estable: el trabajo pesado ya no bloquea a otros visitantes, la cola tiene un límite justo y la importación del historial se ejecuta en segundo plano.",
          "La búsqueda del mercado y el panel de valoraciones cubren todas las apps públicas, no solo las más nuevas: las antiguas vuelven a ser encontrables.",
          "La primera pantalla carga más ligera: solo se descarga tu idioma en lugar de los diez, y los avisos se renderizan al abrirlos.",
          "Nueva política de iconos: publicar en el mercado requiere un icono válido. Los iconos planos o ausentes se rechazan al publicar, con una guía clara para subir una imagen.",
          "Las apps ya en el mercado cuyo icono no pasa la revisión tienen 48 horas para subir un dibujo de verdad antes de salir del mercado. La antigua ventana de 7 días desaparece.",
          "Entre bastidores: las regeneraciones de Android son más rápidas, la búsqueda de iconos se detiene en cuanto encuentra uno válido y las subidas al CDN se reintentan en vez de fallar en silencio."
        ],
        "pt": [
          "A geração está mais rápida e estável: o trabalho pesado não bloqueia mais outros visitantes, a fila tem um limite justo e a importação do histórico roda em segundo plano.",
          "A busca do mercado e o painel de avaliações cobrem todos os apps públicos, não só os mais novos — os antigos voltam a ser encontrados.",
          "A primeira tela carrega mais leve: só o seu idioma é baixado em vez dos dez, e os avisos são renderizados ao abrir.",
          "Nova política de ícones: publicar no mercado exige um ícone válido. Ícones de cor única ou ausentes são rejeitados na publicação, com uma orientação clara de envio.",
          "Apps já no mercado cujo ícone não passa na verificação têm 48 horas para enviar um desenho de verdade antes de sair do mercado. A antiga janela de 7 dias acabou.",
          "Nos bastidores: regenerações Android mais rápidas, a busca de ícones para assim que encontra um válido e os envios ao CDN são repetidos em vez de falhar em silêncio."
        ],
        "fr": [
          "La génération est plus rapide et plus stable : les tâches lourdes ne bloquent plus les autres visiteurs, la file a une limite équitable et l’import de l’historique s’exécute en arrière-plan.",
          "La recherche du marché et le classement des notes couvrent toutes les applications publiques, pas seulement les plus récentes — les anciennes sont de nouveau trouvables.",
          "Le premier écran est plus léger : seule votre langue est téléchargée au lieu des dix, et les annonces s’affichent à l’ouverture.",
          "Nouvelle politique d’icônes : publier sur le marché exige une icône valide. Les icônes unies ou manquantes sont refusées à la publication, avec un guide clair pour envoyer une image.",
          "Les applications déjà sur le marché dont l’icône échoue au contrôle ont 48 heures pour envoyer un vrai dessin avant de quitter le marché. L’ancienne fenêtre de 7 jours est supprimée.",
          "En coulisses : les régénérations Android sont plus rapides, la recherche d’icônes s’arrête dès qu’une icône valide est trouvée, et les envois au CDN sont réessayés au lieu d’échouer en silence."
        ],
        "de": [
          "Builds sind schneller und stabiler: schwere Arbeit blockiert andere Besucher nicht mehr, die Warteschlange hat ein faires Limit, und der Historien-Import läuft im Hintergrund.",
          "Marktsuche und Bewertungsboard decken jetzt alle öffentlichen Apps ab, nicht nur die neuesten — ältere Apps sind wieder auffindbar.",
          "Der erste Bildschirm lädt leichter: nur deine Sprache wird geladen statt aller zehn, und Hinweise werden erst beim Öffnen gerendert.",
          "Neue Symbol-Regeln: Für die Veröffentlichung im Markt ist ein brauchbares Symbol Pflicht. Einfarbige oder fehlende Symbole werden beim Veröffentlichen abgelehnt, mit klarer Upload-Anleitung.",
          "Apps bereits im Markt, deren Symbol die Prüfung nicht besteht, haben 48 Stunden Zeit, ein echtes Bild hochzuladen, sonst verlassen sie den Markt. Das alte 7-Tage-Fenster entfällt.",
          "Unter der Haube: Android-Neubuilds sind schneller, die Symbol-Suche stoppt sofort bei einem brauchbaren Treffer, und CDN-Uploads werden bei Fehlern wiederholt statt still zu scheitern."
        ]
      }
    },
    {
      "id": "2026-11-06-faster-homepage",
      "publishedAt": "2026-11-06T06:20:00Z",
      "title": {
        "en": "Faster homepage, Korean support and market language filters",
        "zh": "首页更快、韩语上线、市场支持语言筛选",
        "ja": "ホーム高速化、韓国語対応、マーケットの言語フィルター",
        "ko": "홈 속도 개선, 한국어 지원, 마켓 언어 필터",
        "ar": "صفحة أسرع ودعم الكورية ومرشح لغة السوق",
        "ru": "Быстрее главная, корейский язык и фильтр рынка по языку",
        "es": "Portada más rápida, coreano y filtro de idioma del mercado",
        "pt": "Início mais rápido, coreano e filtro de idioma do mercado",
        "fr": "Accueil plus rapide, coréen et filtre de langue du marché",
        "de": "Schnellere Startseite, Koreanisch und Sprachfilter im Markt"
      },
      "paragraphs": {
        "en": [
          "Korean is now available: the main site, download pages, PWA, notices and community can all switch to Korean.",
          "The market now has language categories and a language filter. Existing apps were classified by their page language, so you can filter for Chinese, English, Korean and more.",
          "The first screen is faster: the hero and stats no longer wait for a scroll animation, fonts load asynchronously, and translations such as Chinese are applied as soon as the page is parsed.",
          "Stats, history and market data now start loading before the main script runs. History and market show placeholders first, then fill in when the data arrives.",
          "The market loads the next page automatically as you scroll near the bottom, so the manual “Load more” click is no longer required.",
          "Your last stats, history and market page are cached on this device for 24 hours. A repeat visit shows them immediately while fresh data is fetched in the background."
        ],
        "zh": [
          "新增韩语支持：主站、下载页、PWA、公告和社区现在都可以切换到韩语。",
          "应用市场新增语言分类和语言筛选。现有应用已按页面语言归类，市场里可以直接筛选中文、英语、韩语等语言。",
          "首页首屏更快：标题和统计不再等滚动动画，字体改为异步加载，中文等翻译也会在页面解析后立即应用。",
          "统计、历史和市场数据会在主脚本运行前就开始请求，「你的应用」和市场先显示占位骨架，数据到了再填入。",
          "市场滚动到接近底部会自动加载下一页，不再需要手动点「加载更多」。",
          "最近一次的统计、历史和市场首页会在这台设备上缓存 24 小时。再次打开时先立即显示，再在后台刷新。"
        ],
        "ja": [
          "韓国語に対応しました。メインサイト、ダウンロードページ、PWA、お知らせ、コミュニティを韓国語に切り替えられます。",
          "マーケットに言語分類と言語フィルターを追加しました。既存アプリをページの言語で分類し、中国語・英語・韓国語などで絞り込めます。",
          "最初の画面が速くなりました。ヒーローと統計はスクロールアニメーションを待たず、フォントは非同期で読み込み、中国語などの翻訳はページ解析後すぐに適用されます。",
          "統計・履歴・マーケットのデータをメインスクリプトの実行前に取得し始めます。「あなたのアプリ」とマーケットは先にプレースホルダーを表示し、データが届き次第埋まります。",
          "マーケットは下までスクロールすると次のページを自動で読み込むため、「もっと見る」を手動で押す必要はありません。",
          "直近の統計・履歴・マーケットの1ページ目はこの端末に24時間キャッシュされます。再訪問時はすぐに表示し、裏で最新データに更新します。"
        ],
        "ko": [
          "한국어를 지원합니다. 메인 사이트, 다운로드 페이지, PWA, 공지, 커뮤니티를 모두 한국어로 전환할 수 있습니다.",
          "마켓에 언어 분류와 언어 필터를 추가했습니다. 기존 앱을 페이지 언어로 분류해 중국어, 영어, 한국어 등으로 필터링할 수 있습니다.",
          "첫 화면이 더 빨라졌습니다. 히어로와 통계는 스크롤 애니메이션을 기다리지 않고, 글꼴은 비동기로 불러오며, 중국어 등의 번역은 페이지 파싱 직후 적용됩니다.",
          "통계, 기록, 마켓 데이터를 메인 스크립트 실행 전에 요청하기 시작합니다. 내 앱과 마켓은 자리 표시자를 먼저 보여 주고 데이터가 도착하면 채웁니다.",
          "마켓은 아래로 스크롤하면 다음 페이지를 자동으로 불러오므로 '더 보기'를 직접 누를 필요가 없습니다.",
          "최근 통계, 기록, 마켓 첫 페이지는 이 기기에 24시간 동안 캐시됩니다. 다시 방문하면 즉시 보여 주고 백그라운드에서 최신 데이터로 갱신합니다."
        ],
        "ar": [
          "أصبحت اللغة الكورية متاحة: يمكن تحويل الموقع الرئيسي وصفحات التنزيل وتطبيق PWA والإعلانات والمجتمع إلى الكورية.",
          "أضفنا تصنيفات اللغات ومرشح اللغة إلى السوق. صُنّفت التطبيقات الحالية حسب لغة صفحتها، ويمكنك التصفية حسب الصينية أو الإنجليزية أو الكورية وغيرها.",
          "أصبحت الشاشة الأولى أسرع: لم يعد العنوان والإحصاءات ينتظران حركة التمرير، وتُحمّل الخطوط بشكل غير متزامن، وتُطبَّق الترجمات مثل الصينية فور تحليل الصفحة.",
          "تبدأ الإحصاءات والسجل وبيانات السوق بالتحميل قبل تشغيل البرنامج النصي الرئيسي. يعرض قسم تطبيقاتك والسوق عناصر مكانية أولاً ثم يملؤها عند وصول البيانات.",
          "يحمّل السوق الصفحة التالية تلقائياً عند التمرير قرب الأسفل، لذا لم تعد بحاجة إلى النقر على «تحميل المزيد».",
          "تُخزَّن آخر إحصاءات وسجل وصفحة سوق أولى على هذا الجهاز لمدة 24 ساعة. عند الزيارة التالية تظهر فوراً ثم تُحدَّث في الخلفية."
        ],
        "ru": [
          "Добавлена поддержка корейского: основной сайт, страницы загрузки, PWA, объявления и сообщество можно переключить на корейский.",
          "На рынке появились языковые категории и фильтр по языку. Существующие приложения разобраны по языку страницы, поэтому можно фильтровать китайский, английский, корейский и другие.",
          "Первый экран стал быстрее: заголовок и статистика больше не ждут анимации прокрутки, шрифты загружаются асинхронно, а переводы вроде китайского применяются сразу после разбора страницы.",
          "Статистика, история и данные рынка начинают загружаться до запуска основного скрипта. История и рынок сначала показывают заглушки, а затем заполняются при поступлении данных.",
          "Рынок автоматически подгружает следующую страницу при прокрутке вниз, так что вручную нажимать «Загрузить ещё» больше не нужно.",
          "Последние статистика, история и первая страница рынка кэшируются на этом устройстве на 24 часа. При повторном визите они показываются сразу, а свежие данные загружаются в фоне."
        ],
        "es": [
          "El coreano ya está disponible: el sitio principal, las páginas de descarga, la PWA, los avisos y la comunidad se pueden cambiar a coreano.",
          "El mercado ahora tiene categorías y filtro por idioma. Las apps existentes se clasificaron por el idioma de su página, así que puedes filtrar por chino, inglés, coreano y más.",
          "La primera pantalla es más rápida: el título y las estadísticas ya no esperan una animación de desplazamiento, las fuentes cargan de forma asíncrona y traducciones como el chino se aplican en cuanto se analiza la página.",
          "Las estadísticas, el historial y los datos del mercado empiezan a cargarse antes de ejecutar el script principal. Tus apps y el mercado muestran marcadores primero y se rellenan cuando llegan los datos.",
          "El mercado carga la página siguiente automáticamente al desplazarte cerca del final, así que ya no hace falta pulsar «Cargar más».",
          "Las últimas estadísticas, el historial y la primera página del mercado se guardan en este dispositivo durante 24 horas. En una nueva visita se muestran al instante y se actualizan en segundo plano."
        ],
        "pt": [
          "O coreano já está disponível: o site principal, as páginas de download, o PWA, os avisos e a comunidade podem ser alterados para coreano.",
          "O mercado agora tem categorias e filtro por idioma. Os apps existentes foram classificados pelo idioma da página, então você pode filtrar por chinês, inglês, coreano e outros.",
          "A primeira tela ficou mais rápida: o título e as estatísticas não esperam mais uma animação de rolagem, as fontes carregam de forma assíncrona e traduções como o chinês são aplicadas assim que a página é analisada.",
          "As estatísticas, o histórico e os dados do mercado começam a carregar antes de executar o script principal. Seus apps e o mercado mostram marcadores primeiro e são preenchidos quando os dados chegam.",
          "O mercado carrega a próxima página automaticamente ao rolar perto do fim, então não é mais preciso clicar em «Carregar mais».",
          "As últimas estatísticas, o histórico e a primeira página do mercado ficam em cache neste dispositivo por 24 horas. Numa nova visita, aparecem na hora e são atualizados em segundo plano."
        ],
        "fr": [
          "Le coréen est désormais disponible : le site principal, les pages de téléchargement, la PWA, les annonces et la communauté peuvent passer en coréen.",
          "Le marché dispose maintenant de catégories et d’un filtre par langue. Les apps existantes ont été classées selon la langue de leur page, vous pouvez donc filtrer le chinois, l’anglais, le coréen et d’autres.",
          "Le premier écran est plus rapide : le titre et les statistiques n’attendent plus une animation de défilement, les polices se chargent en asynchrone et les traductions comme le chinois s’appliquent dès l’analyse de la page.",
          "Les statistiques, l’historique et les données du marché commencent à se charger avant l’exécution du script principal. Vos apps et le marché affichent d’abord des repères, puis se remplissent à l’arrivée des données.",
          "Le marché charge automatiquement la page suivante quand vous approchez du bas, plus besoin de cliquer sur « Charger plus ».",
          "Les dernières statistiques, l’historique et la première page du marché sont mis en cache sur cet appareil pendant 24 heures. Lors d’une nouvelle visite, ils s’affichent immédiatement puis se mettent à jour en arrière-plan."
        ],
        "de": [
          "Koreanisch ist jetzt verfügbar: Hauptseite, Download-Seiten, PWA, Hinweise und Community lassen sich auf Koreanisch umstellen.",
          "Der Markt hat jetzt Sprachkategorien und einen Sprachfilter. Bestehende Apps wurden nach der Sprache ihrer Seite einsortiert, sodass du nach Chinesisch, Englisch, Koreanisch und weiteren filtern kannst.",
          "Der erste Bildschirm ist schneller: Titel und Statistiken warten nicht mehr auf eine Scroll-Animation, Schriften laden asynchron und Übersetzungen wie Chinesisch werden direkt nach dem Parsen der Seite angewendet.",
          "Statistiken, Verlauf und Marktdaten beginnen schon vor dem Hauptskript zu laden. Deine Apps und der Markt zeigen zuerst Platzhalter und füllen sich, sobald die Daten da sind.",
          "Der Markt lädt die nächste Seite beim Scrollen nahe dem Ende automatisch, ein Klick auf „Mehr laden“ ist nicht mehr nötig.",
          "Die letzten Statistiken, der Verlauf und die erste Marktseite werden 24 Stunden lang auf diesem Gerät zwischengespeichert. Beim nächsten Besuch erscheinen sie sofort und werden im Hintergrund aktualisiert."
        ]
      }
    },
    {
      "id": "2026-11-05-site-refresh",
      "publishedAt": "2026-11-05T16:30:00Z",
      "title": {
        "en": "A calmer homepage, cleaner market and no ads",
        "zh": "首页更简洁，市场信息更完整，广告已移除",
        "ja": "ホームを整理、マーケットを充実、広告を廃止",
        "ko": "홈을 정리하고 마켓을 보강했으며 광고를 없앴습니다",
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
        "ko": [
          "홈페이지가 다시 한 열 가운데 정렬로 돌아왔습니다. 링크를 붙여넣고 URL 또는 HTML을 선택해 생성하세요. 기기 미리보기 실험은 제거했습니다.",
          "마켓 카드에 게시 시간, 방문 수, 다운로드 수가 다시 표시되며 앱을 더 불러올 수 있습니다.",
          "광고와 개인정보 안내 페이지가 제거되었습니다. 사이트는 더 이상 AdSense를 불러오지 않으며, 생성된 다운로드 페이지에도 광고 스크립트가 없습니다.",
          "앱 다운로드 페이지도 같은 가운데 정렬 레이아웃을 사용하며, 5개 플랫폼 카드 그리드와 다크 모드를 지원합니다."
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
        ko: '마켓 정리: 중복 앱과 단색 아이콘',
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
        ko: [
          '2026년 10월 13일, 공개 마켓을 정리했습니다.',
          '같은 사람이 같은 이름, 주소, 업로드한 아이콘 또는 페이지 내용으로 여러 공개 앱을 올린 경우 가장 최신 것만 남겼습니다. 이전 앱은 마켓에서 내려갔습니다. 다운로드 링크는 계속 열리며, 해당 사본은 다시 올리지 않습니다.',
          '한 색상이 화면의 90% 이상을 차지하는 아이콘은 사용할 수 없습니다. 거의 보라색인 단색 블록도 포함됩니다. 해당 이미지는 제거했습니다. 카드의 흰 사각형은 비어 있는 아이콘 자리이며, 흰 아이콘으로 바꾼 것이 아닙니다.',
          '아이콘이 제거된 채 마켓에 남아 있는 앱은 2026년 10월 20일 16:00(UTC)까지 실제 디자인이 있는 이미지로 다시 생성하세요. 그때까지 비어 있거나 여전히 단색이면 앱은 마켓에서 제외됩니다. 이후 발견되는 단색 아이콘도 발견일로부터 7일이 주어집니다.'
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

  // The panel body (2 notices x 10 languages of DOM) is built on first open,
  // not at startup — most visits never open it. Chrome (button label/title)
  // stays eager so the nav looks complete on first paint.
  var bodyRendered = false;

  function renderChrome() {
    var wrap = document.getElementById('nav-notices') || document.querySelector('.nav-notices');
    var btn = document.getElementById('notices-btn');
    var title = document.getElementById('notices-title');
    if (!wrap || !btn || !title) return;
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
  }

  function renderBody() {
    var scroll = document.getElementById('notices-scroll');
    if (!scroll || !NOTICES.length) return;
    var lang = (window.I18n && LANGS.indexOf(window.I18n.current) !== -1) ? window.I18n.current : 'en';
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
    bodyRendered = true;
  }

  function render() {
    renderChrome();
    if (bodyRendered) renderBody();
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
      var willOpen = !isOpen();
      if (willOpen && !bodyRendered) renderBody();
      setOpen(willOpen);
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
    renderChrome();
  }

  window.WTA_NOTICES = NOTICES;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
  window.addEventListener('i18n:changed', render);
})();

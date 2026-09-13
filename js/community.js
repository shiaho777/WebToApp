/* ============================================================
   WebToApp — community widget for generated download pages.
   Renders the creator card, the creator's other public apps,
   comments and ratings into the mount points emitted by
   distiller.render_download_page. Self-contained: bootstraps the
   shared device fingerprint, carries its own 9-language strings,
   and re-renders when the page's <html lang> changes.
   Requires /js/mdmini.js (window.wtaMd) loaded before this file.
   ============================================================ */
(function () {
  'use strict';

  var FP_KEY = 'webtoapp-device-fingerprint-v1';
  var FP_COOKIE = 'webtoapp_device_fingerprint';
  var LANG_KEY = 'webtoapp-lang-v1';
  var SUPPORTED = ['en', 'zh', 'ja', 'ar', 'ru', 'es', 'pt', 'fr', 'de'];

  var STRINGS = {
    en: {
      creator: 'Creator', moreApps: 'More from this creator', anonymous: 'Anonymous',
      joined: 'Joined', comments: 'Comments', noComments: 'No comments yet — be the first.',
      writeComment: 'Write a comment…', yourRating: 'Rating', optional: 'optional',
      submit: 'Post', postFailed: 'Post failed — try again.', del: 'Delete',
      deleted: 'Comment deleted', noRating: 'No ratings yet', visit: 'Open'
    },
    zh: {
      creator: '作者', moreApps: 'TA 的其他应用', anonymous: '匿名用户',
      joined: '加入于', comments: '评论', noComments: '还没有评论，来抢沙发。',
      writeComment: '写下你的评论…', yourRating: '评分', optional: '可选',
      submit: '发布', postFailed: '发布失败，请重试。', del: '删除',
      deleted: '评论已删除', noRating: '暂无评分', visit: '打开'
    },
    ja: {
      creator: '作者', moreApps: 'この作者の他のアプリ', anonymous: '匿名',
      joined: '登録', comments: 'コメント', noComments: 'まだコメントはありません。',
      writeComment: 'コメントを書く…', yourRating: '評価', optional: '任意',
      submit: '投稿', postFailed: '投稿に失敗しました。', del: '削除',
      deleted: '削除しました', noRating: '評価はまだありません', visit: '開く'
    },
    ar: {
      creator: 'المنشئ', moreApps: 'تطبيقات أخرى من نفس المنشئ', anonymous: 'مجهول',
      joined: 'انضم', comments: 'التعليقات', noComments: 'لا توجد تعليقات بعد.',
      writeComment: 'اكتب تعليقاً…', yourRating: 'التقييم', optional: 'اختياري',
      submit: 'نشر', postFailed: 'فشل النشر، حاول مجدداً.', del: 'حذف',
      deleted: 'تم حذف التعليق', noRating: 'لا تقييمات بعد', visit: 'فتح'
    },
    ru: {
      creator: 'Автор', moreApps: 'Другие приложения автора', anonymous: 'Аноним',
      joined: 'С нами с', comments: 'Комментарии', noComments: 'Комментариев пока нет.',
      writeComment: 'Написать комментарий…', yourRating: 'Оценка', optional: 'необязательно',
      submit: 'Отправить', postFailed: 'Не удалось отправить.', del: 'Удалить',
      deleted: 'Комментарий удалён', noRating: 'Оценок пока нет', visit: 'Открыть'
    },
    es: {
      creator: 'Autor', moreApps: 'Más apps de este autor', anonymous: 'Anónimo',
      joined: 'Desde', comments: 'Comentarios', noComments: 'Aún no hay comentarios.',
      writeComment: 'Escribe un comentario…', yourRating: 'Valoración', optional: 'opcional',
      submit: 'Publicar', postFailed: 'Error al publicar.', del: 'Eliminar',
      deleted: 'Comentario eliminado', noRating: 'Sin valoraciones', visit: 'Abrir'
    },
    pt: {
      creator: 'Autor', moreApps: 'Mais apps deste autor', anonymous: 'Anônimo',
      joined: 'Desde', comments: 'Comentários', noComments: 'Ainda não há comentários.',
      writeComment: 'Escreva um comentário…', yourRating: 'Avaliação', optional: 'opcional',
      submit: 'Publicar', postFailed: 'Falha ao publicar.', del: 'Excluir',
      deleted: 'Comentário excluído', noRating: 'Sem avaliações', visit: 'Abrir'
    },
    fr: {
      creator: 'Auteur', moreApps: 'Autres apps de cet auteur', anonymous: 'Anonyme',
      joined: 'Depuis', comments: 'Commentaires', noComments: 'Pas encore de commentaires.',
      writeComment: 'Écrire un commentaire…', yourRating: 'Note', optional: 'optionnel',
      submit: 'Publier', postFailed: 'Échec de la publication.', del: 'Supprimer',
      deleted: 'Commentaire supprimé', noRating: 'Pas encore de notes', visit: 'Ouvrir'
    },
    de: {
      creator: 'Autor', moreApps: 'Weitere Apps dieses Autors', anonymous: 'Anonym',
      joined: 'Seit', comments: 'Kommentare', noComments: 'Noch keine Kommentare.',
      writeComment: 'Kommentar schreiben…', yourRating: 'Bewertung', optional: 'optional',
      submit: 'Senden', postFailed: 'Senden fehlgeschlagen.', del: 'Löschen',
      deleted: 'Kommentar gelöscht', noRating: 'Noch keine Bewertungen', visit: 'Öffnen'
    }
  };

  function lang() {
    var l = (document.documentElement.lang || '').toLowerCase();
    var base = l.split('-')[0];
    if (SUPPORTED.indexOf(base) !== -1) return base;
    try {
      var s = localStorage.getItem(LANG_KEY);
      if (s && SUPPORTED.indexOf(s) !== -1) return s;
    } catch (_e) { /* ignore */ }
    return 'en';
  }

  function t(key) {
    var tb = STRINGS[lang()] || STRINGS.en;
    return tb[key] != null ? tb[key] : STRINGS.en[key];
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Same fingerprint bootstrap as js/app.v5.js — shared origin, so the
  // identity is seamless between the landing page and download pages.
  function ensureFingerprint() {
    function syncCookie(value) {
      if (!value) return;
      var secure = location.protocol === 'https:' ? '; Secure' : '';
      document.cookie = FP_COOKIE + '=' + encodeURIComponent(value) + '; Max-Age=31536000; Path=/; SameSite=Lax' + secure;
    }
    try {
      var existing = localStorage.getItem(FP_KEY);
      if (existing) { syncCookie(existing); return; }
      var bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      var created = Array.prototype.map.call(bytes, function (b) { return b.toString(16).padStart(2, '0'); }).join('');
      localStorage.setItem(FP_KEY, created);
      syncCookie(created);
    } catch (_e) {
      syncCookie('volatile-' + Date.now().toString(16));
    }
  }

  function avatarHtml(profile, cls) {
    if (profile && profile.avatar_url) {
      return '<img class="' + cls + '" src="' + esc(profile.avatar_url) + '" alt="" loading="lazy">';
    }
    var label = '#';
    if (profile && profile.name) label = profile.name.charAt(0).toUpperCase();
    else if (profile && profile.user_num) label = '#' + profile.user_num;
    return '<span class="' + cls + ' avatar-fallback" aria-hidden="true">' + esc(label) + '</span>';
  }

  function starsHtml(rating) {
    var r = Math.max(0, Math.min(5, Math.round(rating || 0)));
    var s = '';
    for (var i = 1; i <= 5; i++) s += '<span class="star' + (i <= r ? ' on' : '') + '">★</span>';
    return '<span class="stars">' + s + '</span>';
  }

  function fmtDate(iso) {
    try {
      var d = new Date(iso);
      if (isNaN(d)) return '';
      return d.toLocaleDateString(document.documentElement.lang || 'en-US');
    } catch (_e) { return ''; }
  }

  var appId = window.WTA_APP_ID || (location.pathname.match(/\/a\/([A-Za-z0-9_-]{4,64})/) || [])[1];
  var data = null;
  var pickedRating = 0;

  function profileLink(num) {
    return '/' + '?u=' + encodeURIComponent(num);
  }

  function renderCreator(c) {
    var box = document.getElementById('creator-card');
    if (!box) return;
    if (!c) { box.innerHTML = ''; box.parentNode.style.display = 'none'; return; }
    box.parentNode.style.display = '';
    var name = c.name || (t('anonymous') + ' #' + c.user_num);
    box.innerHTML =
      '<a class="creator-head" href="' + profileLink(c.user_num) + '">' +
        avatarHtml(c, 'creator-avatar') +
        '<span class="creator-meta">' +
          '<span class="creator-label">' + esc(t('creator')) + '</span>' +
          '<span class="creator-name">' + esc(name) + ' <em class="creator-num">#' + c.user_num + '</em></span>' +
        '</span></a>' +
      (c.bio_md ? '<div class="creator-bio">' + window.wtaMd(c.bio_md) + '</div>' : '');
  }

  function renderOtherApps(apps) {
    var wrap = document.getElementById('creator-apps');
    if (!wrap) return;
    if (!apps || !apps.length) { wrap.style.display = 'none'; return; }
    wrap.style.display = '';
    var html = '<div class="section-label">' + esc(t('moreApps')) + '</div><div class="other-apps">';
    apps.forEach(function (a) {
      html += '<a class="other-app" href="' + esc(a.public_path || ('/a/' + a.app_id)) + '">' +
        (a.icon_url ? '<img src="' + esc(a.icon_url) + '" alt="" loading="lazy">' : '<span class="other-app-dot"></span>') +
        '<span class="other-app-name">' + esc(a.name || a.app_id) + '</span></a>';
    });
    wrap.innerHTML = html + '</div>';
  }

  function renderComments() {
    var list = document.getElementById('comments-list');
    if (!list) return;
    var items = (data && data.comments) || [];
    if (!items.length) {
      list.innerHTML = '<p class="comments-empty">' + esc(t('noComments')) + '</p>';
      return;
    }
    list.innerHTML = items.map(function (cm) {
      var prof = { user_num: cm.user_num, name: cm.name, avatar_url: cm.avatar_url };
      var name = cm.name || (t('anonymous') + ' #' + cm.user_num);
      return '<div class="comment" data-cid="' + cm.id + '">' +
        '<div class="comment-head">' +
        '<a class="comment-head-link" href="' + profileLink(cm.user_num) + '">' + avatarHtml(prof, 'comment-avatar') +
        '<span class="comment-who"><b>' + esc(name) + '</b> <em class="creator-num">#' + cm.user_num + '</em>' +
        (cm.rating ? ' ' + starsHtml(cm.rating) : '') +
        '</span></a>' +
        '<span class="comment-when">' + esc(fmtDate(cm.created_at)) + '</span>' +
        (cm.mine ? '<button class="comment-del" data-del="' + cm.id + '">' + esc(t('del')) + '</button>' : '') +
        '</div>' +
        '<div class="comment-body">' + esc(cm.body).replace(/\n/g, '<br>') + '</div>' +
        '</div>';
    }).join('');
  }

  function renderRating() {
    var el = document.getElementById('app-rating');
    if (!el || !data) return;
    if (data.rating_count) {
      el.innerHTML = starsHtml(data.rating_avg) +
        '<span class="rating-num">' + data.rating_avg.toFixed(1) + '</span>' +
        '<span class="rating-cnt">(' + data.rating_count + ')</span>';
    } else {
      el.innerHTML = '<span class="rating-none">' + esc(t('noRating')) + '</span>';
    }
  }

  function starPicker() {
    var wrap = document.getElementById('rating-picker');
    if (!wrap) return;
    wrap.innerHTML = '<span class="picker-label">' + esc(t('yourRating')) +
      ' <em>(' + esc(t('optional')) + ')</em></span>' +
      [1, 2, 3, 4, 5].map(function (i) {
        return '<button type="button" class="pick-star' + (i <= pickedRating ? ' on' : '') + '" data-star="' + i + '">★</button>';
      }).join('');
  }

  function chrome() {
    var title = document.getElementById('comments-title');
    if (title) title.textContent = t('comments');
    var ta = document.getElementById('comment-body');
    if (ta) ta.placeholder = t('writeComment');
    var btn = document.querySelector('#comment-form button[type=submit]');
    if (btn) btn.textContent = t('submit');
  }

  function renderAll() {
    chrome();
    renderCreator(data && data.creator);
    renderOtherApps(data && data.other_apps);
    renderRating();
    renderComments();
    starPicker();
  }

  function load() {
    if (!appId) return;
    fetch('/api/apps/' + encodeURIComponent(appId) + '/community')
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d) { data = d; renderAll(); } })
      .catch(function () { /* leave placeholders */ });
  }

  function bind() {
    var picker = document.getElementById('rating-picker');
    if (picker) picker.addEventListener('click', function (e) {
      var b = e.target.closest('[data-star]');
      if (!b) return;
      pickedRating = Number(b.dataset.star) || 0;
      starPicker();
    });
    var form = document.getElementById('comment-form');
    if (form) form.addEventListener('submit', function (e) {
      e.preventDefault();
      var ta = document.getElementById('comment-body');
      var body = (ta.value || '').trim();
      if (!body) return;
      var btn = form.querySelector('button[type=submit]');
      btn.disabled = true;
      fetch('/api/apps/' + encodeURIComponent(appId) + '/comments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body: body, rating: pickedRating || null })
      }).then(function (r) {
        if (!r.ok) throw new Error('post failed');
        return r.json();
      }).then(function () {
        ta.value = '';
        pickedRating = 0;
        load();
      }).catch(function () {
        alert(t('postFailed'));
      }).finally(function () {
        btn.disabled = false;
      });
    });
    var list = document.getElementById('comments-list');
    if (list) list.addEventListener('click', function (e) {
      var b = e.target.closest('[data-del]');
      if (!b || !confirm(t('del') + '?')) return;
      fetch('/api/comments/' + b.dataset.del, { method: 'DELETE' })
        .then(function (r) { if (r.ok) load(); });
    });
  }

  // Re-render on language switch — the page's switcher mutates <html lang>.
  var lastLang = lang();
  new MutationObserver(function () {
    if (lang() !== lastLang) { lastLang = lang(); renderAll(); }
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });

  ensureFingerprint();
  bind();
  load();
})();

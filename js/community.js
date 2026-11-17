/* ============================================================
   WebToApp — community widget for generated download pages.
   Renders the creator card, the creator's other public apps,
   comments and ratings into the mount points emitted by
   distiller.render_download_page. Self-contained: bootstraps the
   shared device fingerprint, carries its own 10-language strings,
   and re-renders when the page's <html lang> changes.
   Requires /js/mdmini.js (window.wtaMd) loaded before this file.
   ============================================================ */
(function () {
  'use strict';

  var FP_KEY = 'webtoapp-device-fingerprint-v1';
  var FP_COOKIE = 'webtoapp_device_fingerprint';
  var LANG_KEY = 'webtoapp-lang-v1';
  var SUPPORTED = ['en', 'zh', 'ja', 'ko', 'ar', 'ru', 'es', 'pt', 'fr', 'de'];

  var STRINGS = {
    en: {
      creator: 'Creator', moreApps: 'More from this creator', anonymous: 'Anonymous',
      joined: 'Joined', comments: 'Comments', noComments: 'No comments yet — be the first.',
      writeComment: 'Write a comment…', yourRating: 'Rating', optional: 'optional',
      submit: 'Post', postFailed: 'Post failed — try again.', del: 'Delete',
      deleted: 'Comment deleted', noRating: 'No ratings yet', visit: 'Open',
      report: 'Report this app', reportTitle: 'Report this app',
      reportPrompt: 'Why are you reporting this app? (phishing, malware, illegal content…)',
      reportSubmit: 'Submit report', reportCancel: 'Cancel',
      reportThanks: 'Report submitted — thank you. Our team will review it.',
      reportFailed: 'Report failed — try again later.'
    },
    zh: {
      creator: '作者', moreApps: 'TA 的其他应用', anonymous: '匿名用户',
      joined: '加入于', comments: '评论', noComments: '还没有评论，来抢沙发。',
      writeComment: '写下你的评论…', yourRating: '评分', optional: '可选',
      submit: '发布', postFailed: '发布失败，请重试。', del: '删除',
      deleted: '评论已删除', noRating: '暂无评分', visit: '打开',
      report: '举报此应用', reportTitle: '举报此应用',
      reportPrompt: '为什么要举报这个应用？（钓鱼、恶意软件、违法内容……）',
      reportSubmit: '提交举报', reportCancel: '取消',
      reportThanks: '举报已提交，谢谢你。我们会尽快审核。',
      reportFailed: '举报失败，请稍后再试。'
    },
    ja: {
      creator: '作者', moreApps: 'この作者の他のアプリ', anonymous: '匿名',
      joined: '登録', comments: 'コメント', noComments: 'まだコメントはありません。',
      writeComment: 'コメントを書く…', yourRating: '評価', optional: '任意',
      submit: '投稿', postFailed: '投稿に失敗しました。', del: '削除',
      deleted: '削除しました', noRating: '評価はまだありません', visit: '開く',
      report: 'このアプリを報告', reportTitle: 'このアプリを報告',
      reportPrompt: '報告理由を教えてください（フィッシング、マルウェア、違法コンテンツなど）。',
      reportSubmit: '報告を送信', reportCancel: 'キャンセル',
      reportThanks: '報告を受け付けました。ありがとうございます。確認します。',
      reportFailed: '報告に失敗しました。後でもう一度お試しください。'
    },
    ar: {
      creator: 'المنشئ', moreApps: 'تطبيقات أخرى من نفس المنشئ', anonymous: 'مجهول',
      joined: 'انضم', comments: 'التعليقات', noComments: 'لا توجد تعليقات بعد.',
      writeComment: 'اكتب تعليقاً…', yourRating: 'التقييم', optional: 'اختياري',
      submit: 'نشر', postFailed: 'فشل النشر، حاول مجدداً.', del: 'حذف',
      deleted: 'تم حذف التعليق', noRating: 'لا تقييمات بعد', visit: 'فتح',
      report: 'الإبلاغ عن هذا التطبيق', reportTitle: 'الإبلاغ عن هذا التطبيق',
      reportPrompt: 'لماذا تُبلغ عن هذا التطبيق؟ (تصيّد، برمجيات خبيثة، محتوى غير قانوني…)',
      reportSubmit: 'إرسال البلاغ', reportCancel: 'إلغاء',
      reportThanks: 'تم إرسال البلاغ — شكراً لك. سيراجعه فريقنا.',
      reportFailed: 'فشل إرسال البلاغ — حاول لاحقاً.'
    },
    ru: {
      creator: 'Автор', moreApps: 'Другие приложения автора', anonymous: 'Аноним',
      joined: 'С нами с', comments: 'Комментарии', noComments: 'Комментариев пока нет.',
      writeComment: 'Написать комментарий…', yourRating: 'Оценка', optional: 'необязательно',
      submit: 'Отправить', postFailed: 'Не удалось отправить.', del: 'Удалить',
      deleted: 'Комментарий удалён', noRating: 'Оценок пока нет', visit: 'Открыть',
      report: 'Пожаловаться на приложение', reportTitle: 'Пожаловаться на приложение',
      reportPrompt: 'Почему вы жалуетесь? (фишинг, вредоносное ПО, незаконный контент…)',
      reportSubmit: 'Отправить жалобу', reportCancel: 'Отмена',
      reportThanks: 'Жалоба отправлена — спасибо. Мы её рассмотрим.',
      reportFailed: 'Не удалось отправить жалобу — попробуйте позже.'
    },
    es: {
      creator: 'Autor', moreApps: 'Más apps de este autor', anonymous: 'Anónimo',
      joined: 'Desde', comments: 'Comentarios', noComments: 'Aún no hay comentarios.',
      writeComment: 'Escribe un comentario…', yourRating: 'Valoración', optional: 'opcional',
      submit: 'Publicar', postFailed: 'Error al publicar.', del: 'Eliminar',
      deleted: 'Comentario eliminado', noRating: 'Sin valoraciones', visit: 'Abrir',
      report: 'Reportar esta app', reportTitle: 'Reportar esta app',
      reportPrompt: '¿Por qué reportas esta app? (phishing, malware, contenido ilegal…)',
      reportSubmit: 'Enviar reporte', reportCancel: 'Cancelar',
      reportThanks: 'Reporte enviado — gracias. Nuestro equipo lo revisará.',
      reportFailed: 'Error al enviar el reporte — inténtalo más tarde.'
    },
    pt: {
      creator: 'Autor', moreApps: 'Mais apps deste autor', anonymous: 'Anônimo',
      joined: 'Desde', comments: 'Comentários', noComments: 'Ainda não há comentários.',
      writeComment: 'Escreva um comentário…', yourRating: 'Avaliação', optional: 'opcional',
      submit: 'Publicar', postFailed: 'Falha ao publicar.', del: 'Excluir',
      deleted: 'Comentário excluído', noRating: 'Sem avaliações', visit: 'Abrir',
      report: 'Denunciar este app', reportTitle: 'Denunciar este app',
      reportPrompt: 'Por que você está denunciando? (phishing, malware, conteúdo ilegal…)',
      reportSubmit: 'Enviar denúncia', reportCancel: 'Cancelar',
      reportThanks: 'Denúncia enviada — obrigado. Nossa equipe vai analisar.',
      reportFailed: 'Falha ao enviar a denúncia — tente mais tarde.'
    },
    fr: {
      creator: 'Auteur', moreApps: 'Autres apps de cet auteur', anonymous: 'Anonyme',
      joined: 'Depuis', comments: 'Commentaires', noComments: 'Pas encore de commentaires.',
      writeComment: 'Écrire un commentaire…', yourRating: 'Note', optional: 'optionnel',
      submit: 'Publier', postFailed: 'Échec de la publication.', del: 'Supprimer',
      deleted: 'Commentaire supprimé', noRating: 'Pas encore de notes', visit: 'Ouvrir',
      report: 'Signaler cette app', reportTitle: 'Signaler cette app',
      reportPrompt: 'Pourquoi signalez-vous cette app ? (hameçonnage, logiciel malveillant, contenu illégal…)',
      reportSubmit: 'Envoyer le signalement', reportCancel: 'Annuler',
      reportThanks: 'Signalement envoyé — merci. Notre équipe va l’examiner.',
      reportFailed: 'Échec du signalement — réessayez plus tard.'
    },
    de: {
      creator: 'Autor', moreApps: 'Weitere Apps dieses Autors', anonymous: 'Anonym',
      joined: 'Seit', comments: 'Kommentare', noComments: 'Noch keine Kommentare.',
      writeComment: 'Kommentar schreiben…', yourRating: 'Bewertung', optional: 'optional',
      submit: 'Senden', postFailed: 'Senden fehlgeschlagen.', del: 'Löschen',
      deleted: 'Kommentar gelöscht', noRating: 'Noch keine Bewertungen', visit: 'Öffnen',
      report: 'Diese App melden', reportTitle: 'Diese App melden',
      reportPrompt: 'Warum meldest du diese App? (Phishing, Schadsoftware, illegale Inhalte…)',
      reportSubmit: 'Meldung senden', reportCancel: 'Abbrechen',
      reportThanks: 'Meldung gesendet — danke. Unser Team prüft sie.',
      reportFailed: 'Meldung fehlgeschlagen — versuche es später erneut.'
    },
    ko: {
      creator: '제작자', moreApps: '이 제작자의 다른 앱', anonymous: '익명',
      joined: '가입', comments: '댓글', noComments: '아직 댓글이 없습니다. 첫 댓글을 남겨 보세요.',
      writeComment: '댓글을 입력하세요…', yourRating: '평점', optional: '선택',
      submit: '게시', postFailed: '게시 실패, 다시 시도하세요.', del: '삭제',
      deleted: '댓글이 삭제되었습니다', noRating: '아직 평점 없음', visit: '열기',
      report: '이 앱 신고', reportTitle: '이 앱 신고',
      reportPrompt: '신고 사유를 알려 주세요 (피싱, 악성코드, 불법 콘텐츠 등).',
      reportSubmit: '신고 제출', reportCancel: '취소',
      reportThanks: '신고가 접수되었습니다 — 감사합니다. 검토하겠습니다.',
      reportFailed: '신고에 실패했습니다 — 나중에 다시 시도하세요.'
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

  function renderReport() {
    var btn = document.getElementById('report-app');
    if (btn) btn.textContent = t('report');
  }

  function openReportForm() {
    var wrap = document.querySelector('.report-wrap');
    if (!wrap || document.getElementById('report-form')) return;
    var form = document.createElement('form');
    form.id = 'report-form';
    form.className = 'comment-form';
    form.innerHTML =
      '<div class="section-label">' + esc(t('reportTitle')) + '</div>' +
      '<textarea id="report-reason" rows="3" maxlength="1000" placeholder="' + esc(t('reportPrompt')) + '"></textarea>' +
      '<div style="display:flex;gap:8px;justify-content:flex-end">' +
        '<button type="button" id="report-cancel" class="comment-del">' + esc(t('reportCancel')) + '</button>' +
        '<button type="submit">' + esc(t('reportSubmit')) + '</button>' +
      '</div>';
    wrap.appendChild(form);
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var reason = (document.getElementById('report-reason').value || '').trim();
      if (!reason) return;
      var btn = form.querySelector('button[type=submit]');
      btn.disabled = true;
      fetch('/api/apps/' + encodeURIComponent(appId) + '/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason })
      }).then(function (r) {
        if (!r.ok) throw new Error('report failed');
        form.remove();
        if (window.WtaUI) window.WtaUI.toast(t('reportThanks'), { type: 'success' });
        else alert(t('reportThanks'));
      }).catch(function () {
        btn.disabled = false;
        if (window.WtaUI) window.WtaUI.toast(t('reportFailed'), { type: 'error' });
        else alert(t('reportFailed'));
      });
    });
    document.getElementById('report-cancel').addEventListener('click', function () {
      form.remove();
    });
    document.getElementById('report-reason').focus();
  }

  function renderAll() {
    chrome();
    renderCreator(data && data.creator);
    renderOtherApps(data && data.other_apps);
    renderRating();
    renderComments();
    starPicker();
    renderReport();
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
        if (window.WtaUI) window.WtaUI.toast(t('postFailed'), { type: 'error' });
        else alert(t('postFailed'));
      }).finally(function () {
        btn.disabled = false;
      });
    });
    var list = document.getElementById('comments-list');
    if (list) list.addEventListener('click', function (e) {
      var b = e.target.closest('[data-del]');
      if (!b) return;
      var asked = window.WtaUI
        ? window.WtaUI.confirm(t('del') + '?', { danger: true })
        : Promise.resolve(confirm(t('del') + '?'));
      asked.then(function (ok) {
        if (!ok) return;
        fetch('/api/comments/' + b.dataset.del, { method: 'DELETE' })
          .then(function (r) { if (r.ok) load(); });
      });
    });
  }

  var reportBtn = document.getElementById('report-app');
  if (reportBtn) reportBtn.addEventListener('click', openReportForm);

  // Re-render on language switch — the page's switcher mutates <html lang>.
  var lastLang = lang();
  new MutationObserver(function () {
    if (lang() !== lastLang) { lastLang = lang(); renderAll(); }
  }).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });

  ensureFingerprint();
  bind();
  load();
})();

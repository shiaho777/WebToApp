/* ============================================================
   WebToApp — mdmini: tiny safe Markdown subset -> HTML
   Escape first, then reintroduce a few inline constructs:
     **bold**  *italic*  `code`  [text](https://url)  line breaks
   Everything else (raw HTML, images, iframes, js: links) stays
   inert text. Exposed as window.wtaMd.
   ============================================================ */
(function () {
  'use strict';

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function safeHref(url) {
    var u = String(url || '').trim();
    return /^(https?:)?\/\//i.test(u) || /^https?:/i.test(u) ? u : null;
  }

  function render(src) {
    var html = escapeHtml(src);
    // `code`
    html = html.replace(/`([^`\n]+)`/g, function (_m, code) {
      return '<code>' + code + '</code>';
    });
    // **bold**
    html = html.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
    // *italic*
    html = html.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
    // [text](url) — http(s) only; everything else renders as text
    html = html.replace(/\[([^\]\n]+)\]\(([^)\s]+)\)/g, function (_m, text, url) {
      var href = safeHref(url.replace(/&amp;/g, '&'));
      if (!href) return text;
      return '<a href="' + escapeHtml(href) + '" target="_blank" rel="noopener noreferrer">' + text + '</a>';
    });
    return html.replace(/\n/g, '<br>');
  }

  window.wtaMd = render;
})();

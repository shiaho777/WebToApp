/* ============================================================
   WebToApp — Lightweight i18n runtime
   Zero dependencies. Loaded BEFORE app.v5.js.

   Usage:
     I18n.t('key', { param: value })   -> translated string
     I18n.setLanguage('en')            -> switch language
     I18n.locale()                     -> BCP47 locale for Intl/toLocaleString
     window event 'i18n:changed'       -> fired on language switch
   HTML wiring:
     data-i18n="key"                   -> sets textContent
     data-i18n-placeholder="key"       -> sets placeholder
     data-i18n-aria-label="key"        -> sets aria-label
     data-i18n-title="key"             -> sets title
     data-i18n-alt="key"               -> sets alt
   ============================================================ */
(function () {
  'use strict';

  var STORE_KEY = 'webtoapp-lang-v1';
  var SUPPORTED = ['en', 'zh', 'ja', 'ar', 'ru', 'es', 'pt', 'fr', 'de'];
  var RTL = ['ar'];
  var LOCALES = {
    en: 'en-US', zh: 'zh-CN', ja: 'ja-JP', ar: 'ar',
    ru: 'ru-RU', es: 'es-ES', pt: 'pt-BR', fr: 'fr-FR', de: 'de-DE'
  };
  // Native language names for the switcher.
  var NATIVE_NAMES = {
    en: 'English', zh: '中文', ja: '日本語', ar: 'العربية', ru: 'Русский',
    es: 'Español', pt: 'Português', fr: 'Français', de: 'Deutsch'
  };

  // Translation tables are attached to this object below (see i18n.*.js loaded
  // inline). To keep everything dependency-free and avoid a flash of
  // untranslated content, all languages live in this single file.
  var TRANSLATIONS = {};

  function detect() {
    // An explicit user choice (from the switcher) always wins and persists.
    try {
      var saved = window.localStorage.getItem(STORE_KEY);
      if (saved && SUPPORTED.indexOf(saved) !== -1) return saved;
    } catch (_e) { /* ignore */ }
    // First visit: follow the browser/OS language preference list in order,
    // matching an exact tag first then the base subtag ('zh-TW' -> 'zh').
    var prefs = [];
    try {
      if (navigator.languages && navigator.languages.length) {
        prefs = navigator.languages;
      } else if (navigator.language || navigator.userLanguage) {
        prefs = [navigator.language || navigator.userLanguage];
      }
    } catch (_e) { /* ignore */ }
    for (var i = 0; i < prefs.length; i++) {
      var tag = String(prefs[i] || '').toLowerCase();
      if (!tag) continue;
      if (SUPPORTED.indexOf(tag) !== -1) return tag;
      var base = tag.split('-')[0];
      if (SUPPORTED.indexOf(base) !== -1) return base;
    }
    return 'en';
  }

  var current = detect();

  function table() {
    return TRANSLATIONS[current] || TRANSLATIONS.en || {};
  }

  function t(key, params) {
    var tbl = table();
    var val = tbl[key];
    if (val == null) {
      var en = TRANSLATIONS.en || {};
      val = (en[key] != null) ? en[key] : key;
    }
    if (params) {
      val = String(val).replace(/\{(\w+)\}/g, function (m, k) {
        return (params[k] != null) ? params[k] : m;
      });
    }
    return val;
  }

  function locale() {
    return LOCALES[current] || 'en-US';
  }

  function setMeta(attr, name, content) {
    var el = document.querySelector('meta[' + attr + '="' + name + '"]');
    if (el) el.setAttribute('content', content);
  }

  function applyTranslations(root) {
    root = root || document;
    root.querySelectorAll('[data-i18n]').forEach(function (el) {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    root.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      el.setAttribute('placeholder', t(el.getAttribute('data-i18n-placeholder')));
    });
    root.querySelectorAll('[data-i18n-aria-label]').forEach(function (el) {
      el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria-label')));
    });
    root.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      el.setAttribute('title', t(el.getAttribute('data-i18n-title')));
    });
    root.querySelectorAll('[data-i18n-alt]').forEach(function (el) {
      el.setAttribute('alt', t(el.getAttribute('data-i18n-alt')));
    });
  }

  function applyDocumentChrome() {
    document.documentElement.lang = (current === 'zh') ? 'zh-CN' : current;
    document.documentElement.dir = (RTL.indexOf(current) !== -1) ? 'rtl' : 'ltr';
  }

  function applyMeta() {
    document.title = t('meta.title');
    setMeta('name', 'description', t('meta.description'));
    setMeta('property', 'og:title', t('meta.ogTitle'));
    setMeta('property', 'og:description', t('meta.ogDescription'));
  }

  function setLanguage(lang) {
    if (SUPPORTED.indexOf(lang) === -1) return;
    current = lang;
    try { window.localStorage.setItem(STORE_KEY, lang); } catch (_e) { /* ignore */ }
    applyDocumentChrome();
    applyTranslations(document);
    applyMeta();
    window.dispatchEvent(new CustomEvent('i18n:changed', { detail: { lang: lang } }));
  }

  // Public API
  window.I18n = {
    t: t,
    locale: locale,
    setLanguage: setLanguage,
    applyTranslations: applyTranslations,
    register: function (lang, tableObj) { TRANSLATIONS[lang] = tableObj; },
    supported: SUPPORTED.slice(),
    rtl: RTL.slice(),
    nativeNames: NATIVE_NAMES,
    get current() { return current; }
  };

  // Apply <html lang/dir> immediately to minimize layout flash; full apply
  // happens once the DOM is ready (translations are registered just below).
  applyDocumentChrome();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { setLanguage(current); });
  } else {
    setLanguage(current);
  }
})();

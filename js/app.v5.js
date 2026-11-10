/* ============================================================
   WebToApp — Frontend Logic
   Zero dependencies. Every function earns its place.
   ============================================================ */

(function () {
  'use strict';

  // --- Short-lived render cache ---
  // The APIs are fast at the origin but can spend seconds behind the CDN.
  // Paint the last real response immediately, then replace it with fresh data.
  const RENDER_CACHE_PREFIX = 'webtoapp-render-cache-v1:';
  const RENDER_CACHE_TTL_MS = 24 * 60 * 60 * 1000;

  function readRenderCache(name) {
    try {
      const raw = window.localStorage.getItem(RENDER_CACHE_PREFIX + name);
      if (!raw) return null;
      const entry = JSON.parse(raw);
      if (!entry || typeof entry.ts !== 'number') return null;
      if (Date.now() - entry.ts > RENDER_CACHE_TTL_MS) return null;
      return entry.value;
    } catch (_err) {
      return null;
    }
  }

  function writeRenderCache(name, value) {
    try {
      window.localStorage.setItem(RENDER_CACHE_PREFIX + name, JSON.stringify({ ts: Date.now(), value }));
    } catch (_err) {
      // Storage may be unavailable or full; the cache is optional.
    }
  }

  // --- Counter Animation ---
  const reducedMotionQuery = window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : null;

  function animateCount(el, target, duration = 1800) {
    const fmt = (n) => n.toLocaleString('en-US');
    if (reducedMotionQuery && reducedMotionQuery.matches) {
      el.textContent = fmt(target);
      return;
    }
    const start = performance.now();
    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = fmt(Math.floor(target * eased));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  const animatedCounters = new WeakSet();
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        const target = parseInt(e.target.dataset.count);
        if (!Number.isNaN(target) && !animatedCounters.has(e.target)) {
          animateCount(e.target, target);
          animatedCounters.add(e.target);
        }
        counterObserver.unobserve(e.target);
      }
    });
  }, { threshold: 0.5 });
  document.querySelectorAll('[data-count]').forEach(el => counterObserver.observe(el));

  function paintHomepageStats(stats, animate) {
    const mappings = [
      ['stat-generated-apps', stats.generatedApps],
      ['stat-downloads', stats.downloads],
      ['stat-views', stats.views],
    ];
    mappings.forEach(([id, value]) => {
      const el = document.getElementById(id);
      if (!el || Number.isNaN(Number(value))) return;
      const target = Number(value);
      el.dataset.count = String(target);
      if (animate) {
        el.textContent = '0';
        animatedCounters.delete(el);
        animateCount(el, target);
      } else {
        el.textContent = target.toLocaleString('en-US');
      }
      // A painted (cached) value must not be animated from zero later.
      animatedCounters.add(el);
    });
  }

  async function loadHomepageStats() {
    const cached = readRenderCache('stats');
    if (cached) paintHomepageStats(cached, false);
    try {
      const prefetched = takePrefetch('stats');
      const res = prefetched ? await prefetched : await fetch('/api/stats');
      if (!res.ok) throw new Error('Failed to load stats');
      const stats = await res.json();
      paintHomepageStats(stats, !cached);
      writeRenderCache('stats', stats);
    } catch (_err) {
      // Leave the cached/zero values in place rather than inventing numbers.
    }
  }
  loadHomepageStats();

  // --- DOM refs ---
  const urlInput = document.getElementById('url-input');
  const distillBtn = document.getElementById('distill-btn');
  const workspace = document.getElementById('workspace');
  const analysisBody = document.getElementById('analysis-body');
  const analysisStatus = document.getElementById('analysis-status');
  const appNameInput = document.getElementById('app-name');
  const appDescInput = document.getElementById('app-desc');
  const aboutTextInput = document.getElementById('about-text');
  const aboutImagesInput = document.getElementById('about-images-input');
  const aboutImagesName = document.getElementById('about-images-name');
  const aboutImagesPreview = document.getElementById('about-images-preview');
  const aboutImagesClear = document.getElementById('about-images-clear');
  const appNameSourceNote = document.getElementById('app-name-source-note');
  const appColorInput = document.getElementById('app-color');
  const customIconInput = document.getElementById('custom-icon-input');
  const customIconFileName = document.getElementById('custom-icon-file-name');
  const customIconPreview = document.getElementById('custom-icon-preview');
  const customIconPlaceholder = document.getElementById('custom-icon-placeholder');
  const customIconClearBtn = document.getElementById('custom-icon-clear');
  const androidVersionNameInput = document.getElementById('android-version-name');
  const androidVersionCodeInput = document.getElementById('android-version-code');
  const androidPackagePrefixInput = document.getElementById('android-package-prefix');
  const immersiveFullscreenInput = document.getElementById('feature-immersive-fullscreen');
  const desktopModeInput = document.getElementById('feature-desktop-mode');
  const windowsWidthInput = document.getElementById('windows-window-width');
  const windowsHeightInput = document.getElementById('windows-window-height');
  const windowsMaximizedInput = document.getElementById('windows-window-maximized');
  const linuxWidthInput = document.getElementById('linux-window-width');
  const linuxHeightInput = document.getElementById('linux-window-height');
  const linuxMaximizedInput = document.getElementById('linux-window-maximized');
  const colorHex = document.getElementById('color-hex');
  const generateBtn = document.getElementById('generate-btn');
  const resultPanel = document.getElementById('result-panel');
  const appLink = document.getElementById('app-link');
  const copyBtn = document.getElementById('copy-btn');
  const previewFrame = document.getElementById('preview-frame');
  const previewUrl = document.getElementById('preview-url');
  const previewOpenBtn = document.getElementById('preview-open-btn');
  const configPanel = document.getElementById('config-panel');
  const configGrid = configPanel ? configPanel.querySelector('.config-grid') : null;
  const buildProgress = document.getElementById('build-progress');
  const buildProgressFill = document.getElementById('build-progress-fill');
  const buildProgressElapsed = document.getElementById('build-progress-elapsed');
  const buildSteps = document.getElementById('build-steps');
  const buildPlatforms = document.getElementById('build-platforms');
  const buildError = document.getElementById('build-error');
  const buildErrorText = document.getElementById('build-error-text');
  const buildRetryBtn = document.getElementById('build-retry-btn');
  const resultPlatforms = document.getElementById('result-platforms');
  const historyList = document.getElementById('history-list');
  const historyEmpty = document.getElementById('history-empty');
  const historyExportBtn = document.getElementById('history-export-btn');
  const historyImportBtn = document.getElementById('history-import-btn');
  const historyImportInput = document.getElementById('history-import-input');
  const historyManageBtn = document.getElementById('history-manage-btn');
  const visibilityPrivateBtn = document.getElementById('visibility-private-btn');
  const visibilityPublicBtn = document.getElementById('visibility-public-btn');
  const tagsPicker = document.getElementById('tags-picker');
  const tagCustomInput = document.getElementById('tag-custom-input');
  const marketList = document.getElementById('market-list');
  const marketEmpty = document.getElementById('market-empty');
  const marketSearchInput = document.getElementById('market-search');
  const marketSortSelect = document.getElementById('market-sort');
  const marketLanguageSelect = document.getElementById('market-language');
  const marketCount = document.getElementById('market-count');
  const profileBtn = document.getElementById('profile-btn');
  const profileBtnAvatar = document.getElementById('profile-btn-avatar');
  const profileBtnIcon = document.getElementById('profile-btn-icon');
  const profileModal = document.getElementById('profile-modal');
  const profileClose = document.getElementById('profile-close');
  const profileAvatarImg = document.getElementById('profile-avatar');
  const profileAvatarFallback = document.getElementById('profile-avatar-fallback');
  const avatarUploadBtn = document.getElementById('avatar-upload-btn');
  const avatarFile = document.getElementById('avatar-file');
  const profileNameView = document.getElementById('profile-name-view');
  const profileNumEl = document.getElementById('profile-num');
  const profileVisBadge = document.getElementById('profile-vis-badge');
  const profileJoinedEl = document.getElementById('profile-joined');
  const profileBioView = document.getElementById('profile-bio-view');
  const profileMsg = document.getElementById('profile-msg');
  const profileEditForm = document.getElementById('profile-edit');
  const profileNameInput = document.getElementById('profile-name-input');
  const profileBioInput = document.getElementById('profile-bio-input');
  const profileEditCancel = document.getElementById('profile-edit-cancel');
  const profileEditBtn = document.getElementById('profile-edit-btn');
  const profileAppsLabel = document.getElementById('profile-apps-label');
  const profileAppsEl = document.getElementById('profile-apps');
  const historySelectBar = document.getElementById('history-select-bar');
  const historySelectAll = document.getElementById('history-select-all');
  const historySelectCount = document.getElementById('history-select-count');
  const historyDeleteSelectedBtn = document.getElementById('history-delete-selected-btn');
  const historyCancelSelectBtn = document.getElementById('history-cancel-select-btn');
  const historyToggleBtn = document.getElementById('history-toggle-btn');
  const modeUrlBtn = document.getElementById('mode-url-btn');
  const modeHtmlBtn = document.getElementById('mode-html-btn');
  const urlInputWrap = document.getElementById('url-input-wrap');
  const htmlInputWrap = document.getElementById('html-input-wrap');
  const htmlFileInput = document.getElementById('html-file-input');
  const htmlDropzone = document.getElementById('html-dropzone');
  const htmlFileLabel = document.getElementById('html-file-label');
  const htmlFileHint = document.getElementById('html-file-hint');
  let currentUrl = '';
  let inputMode = 'url'; // 'url' | 'html'
  let htmlFile = null;
  let pendingAutoScrollTimer = null;
  let customIconDataUrl = '';
  // About-fold images: null = untouched (rebuilds keep stored images),
  // [] = user cleared, [...] = replacement data URLs (max 3).
  let aboutImageDataUrls = null;
  let detectedIconDataUrl = '';
  let restoreIconDataUrl = '';
  let restoreIconLabel = '';
  let restoreIconFileName = '';
  let lastHistoryItems = [];
  let historySelectMode = false;
  let historyExpanded = false;
  const HISTORY_PREVIEW_COUNT = 5;
  const historySelected = new Set();
  let currentVisibility = 'public';
  const selectedTags = new Set();

  // --- App language picker ---
  const LANGUAGES = [
    { code: 'en', name: 'English' },
    { code: 'zh', name: '中文' },
    { code: 'ja', name: '日本語' },
    { code: 'ko', name: '한국어' },
    { code: 'ar', name: 'العربية' },
    { code: 'ru', name: 'Русский' },
    { code: 'es', name: 'Español' },
    { code: 'pt', name: 'Português' },
    { code: 'fr', name: 'Français' },
    { code: 'de', name: 'Deutsch' },
  ];
  const LANGUAGE_CODES = new Set(LANGUAGES.map((item) => item.code));
  const langPrimaryGrid = document.getElementById('lang-primary-grid');
  const langAdditionalGrid = document.getElementById('lang-additional-grid');
  const langAdditionalWrap = document.getElementById('lang-additional-wrap');
  const langMultilingual = document.getElementById('lang-multilingual');
  const languagePicker = document.getElementById('language-picker');
  const initialUiLanguage = window.I18n && window.I18n.current;
  let primaryLanguage = LANGUAGE_CODES.has(initialUiLanguage) ? initialUiLanguage : 'en';
  let multilingual = false;
  const additionalLanguages = new Set();

  function languageLabel(code) {
    if (code === 'mul') return t('language.mul');
    if (code === 'other') return t('language.other');
    if (code === 'und') return t('language.und');
    const found = LANGUAGES.find((item) => item.code === code);
    return found ? found.name : code;
  }

  function currentLanguages() {
    return multilingual ? [primaryLanguage, ...Array.from(additionalLanguages)] : [primaryLanguage];
  }

  function hasValidLanguages() {
    return !multilingual || additionalLanguages.size > 0;
  }

  function renderLanguagePicker() {
    if (langPrimaryGrid) {
      langPrimaryGrid.querySelectorAll('[data-lang]').forEach((chip) => {
        chip.setAttribute('aria-pressed', chip.dataset.lang === primaryLanguage ? 'true' : 'false');
      });
    }
    if (langMultilingual) {
      langMultilingual.checked = multilingual;
      const disabled = primaryLanguage === 'und';
      langMultilingual.disabled = disabled;
      const label = langMultilingual.closest('.lang-multi-toggle');
      if (label) label.classList.toggle('is-disabled', disabled);
    }
    if (langAdditionalWrap) langAdditionalWrap.classList.toggle('hidden', !multilingual);
    if (langAdditionalGrid) {
      langAdditionalGrid.querySelectorAll('[data-add-lang]').forEach((chip) => {
        const code = chip.dataset.addLang;
        chip.setAttribute('aria-pressed', additionalLanguages.has(code) ? 'true' : 'false');
        chip.disabled = code === primaryLanguage;
      });
    }
  }

  function setLanguageSelection(codes) {
    const list = Array.isArray(codes) ? codes.map((code) => String(code || '').toLowerCase()) : [];
    const validPrimary = list.find((code) => LANGUAGE_CODES.has(code) || code === 'other' || code === 'und');
    primaryLanguage = validPrimary || 'en';
    additionalLanguages.clear();
    list.forEach((code) => {
      if (code !== primaryLanguage && (LANGUAGE_CODES.has(code) || code === 'other')) {
        additionalLanguages.add(code);
      }
    });
    multilingual = additionalLanguages.size > 0 && primaryLanguage !== 'und';
    if (!multilingual) additionalLanguages.clear();
    renderLanguagePicker();
  }

  if (langPrimaryGrid) {
    langPrimaryGrid.addEventListener('click', (event) => {
      const chip = event.target.closest('[data-lang]');
      if (!chip) return;
      primaryLanguage = chip.dataset.lang;
      additionalLanguages.delete(primaryLanguage);
      if (primaryLanguage === 'und') {
        multilingual = false;
        additionalLanguages.clear();
      }
      renderLanguagePicker();
    });
  }
  if (langAdditionalGrid) {
    langAdditionalGrid.addEventListener('click', (event) => {
      const chip = event.target.closest('[data-add-lang]');
      if (!chip || chip.disabled) return;
      const code = chip.dataset.addLang;
      if (additionalLanguages.has(code)) additionalLanguages.delete(code);
      else additionalLanguages.add(code);
      renderLanguagePicker();
    });
  }
  if (langMultilingual) {
    langMultilingual.addEventListener('change', () => {
      if (primaryLanguage === 'und') {
        langMultilingual.checked = false;
        return;
      }
      multilingual = langMultilingual.checked;
      if (!multilingual) additionalLanguages.clear();
      renderLanguagePicker();
    });
  }
  renderLanguagePicker();
  // edit_token is the only proof of app ownership — visibility/URL edits
  // require it server-side, so persist it across reloads like the fingerprint.
  const EDIT_TOKENS_KEY = 'webtoapp-edit-tokens-v1';
  let editTokens = {};
  try { editTokens = JSON.parse(localStorage.getItem(EDIT_TOKENS_KEY) || '{}') || {}; } catch (e) { editTokens = {}; }
  function saveEditTokens() {
    try { localStorage.setItem(EDIT_TOKENS_KEY, JSON.stringify(editTokens)); } catch (e) {}
  }
  let restoreIconButtonLabel = '';
  let deviceFingerprint = '';
  const DEVICE_STORAGE_KEY = 'webtoapp-device-fingerprint-v1';
  const DEVICE_COOKIE_KEY = 'webtoapp_device_fingerprint';
  const t = (key, params) => (window.I18n ? window.I18n.t(key, params) : key);
  const locale = () => (window.I18n ? window.I18n.locale() : 'en-US');
  function takePrefetch(name) {
    const bucket = window.__wtaPrefetch;
    if (!bucket || !bucket[name]) return null;
    const promise = bucket[name];
    try { delete bucket[name]; } catch (_err) { bucket[name] = null; }
    return promise;
  }
  restoreIconButtonLabel = t('icon.noRestore');

  function normalizeFeatureOptions(raw) {
    const options = raw && typeof raw === 'object' ? raw : {};
    const immersiveFullscreen = options['feature-immersive-fullscreen'] === true || options.feature_immersive_fullscreen === true;
    const desktopMode = options['feature-desktop-mode'] === true || options.feature_desktop_mode === true;
    const windowOpts = {};
    ['windows', 'linux'].forEach((prefix) => {
      windowOpts[`${prefix}-window-width`] = sanitizeWindowSize(
        options[`${prefix}-window-width`] != null ? options[`${prefix}-window-width`] : options[`${prefix}_window_width`]
      );
      windowOpts[`${prefix}-window-height`] = sanitizeWindowSize(
        options[`${prefix}-window-height`] != null ? options[`${prefix}-window-height`] : options[`${prefix}_window_height`]
      );
      windowOpts[`${prefix}-window-maximized`] =
        options[`${prefix}-window-maximized`] === true || options[`${prefix}_window_maximized`] === true;
    });
    return {
      immersiveFullscreen,
      desktopMode,
      ...windowOpts,
    };
  }

  function applyFeatureOptionsToForm(raw) {
    const options = normalizeFeatureOptions(raw);
    immersiveFullscreenInput.checked = options.immersiveFullscreen;
    desktopModeInput.checked = options.desktopMode;
    syncInputValue(windowsWidthInput, options['windows-window-width'] ? String(options['windows-window-width']) : '');
    syncInputValue(windowsHeightInput, options['windows-window-height'] ? String(options['windows-window-height']) : '');
    windowsMaximizedInput.checked = options['windows-window-maximized'];
    syncInputValue(linuxWidthInput, options['linux-window-width'] ? String(options['linux-window-width']) : '');
    syncInputValue(linuxHeightInput, options['linux-window-height'] ? String(options['linux-window-height']) : '');
    linuxMaximizedInput.checked = options['linux-window-maximized'];
  }

  function collectFeatureOptions() {
    const featureOptions = normalizeFeatureOptions({
      'feature-immersive-fullscreen': immersiveFullscreenInput.checked,
      'feature-desktop-mode': desktopModeInput.checked,
      'windows-window-width': windowsWidthInput.value,
      'windows-window-height': windowsHeightInput.value,
      'windows-window-maximized': windowsMaximizedInput.checked,
      'linux-window-width': linuxWidthInput.value,
      'linux-window-height': linuxHeightInput.value,
      'linux-window-maximized': linuxMaximizedInput.checked,
    });
    return {
      'feature-immersive-fullscreen': featureOptions.immersiveFullscreen,
      'feature-desktop-mode': featureOptions.desktopMode,
      'windows-window-width': featureOptions['windows-window-width'],
      'windows-window-height': featureOptions['windows-window-height'],
      'windows-window-maximized': featureOptions['windows-window-maximized'],
      'linux-window-width': featureOptions['linux-window-width'],
      'linux-window-height': featureOptions['linux-window-height'],
      'linux-window-maximized': featureOptions['linux-window-maximized'],
    };
  }

  function cancelPendingAutoScroll() {
    if (pendingAutoScrollTimer) {
      clearTimeout(pendingAutoScrollTimer);
      pendingAutoScrollTimer = null;
    }
  }

  function isMostlyInViewport(el, threshold = 0.7) {
    if (!el) return true;
    const rect = el.getBoundingClientRect();
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
    const visibleTop = Math.max(rect.top, 0);
    const visibleBottom = Math.min(rect.bottom, viewportHeight);
    const visibleHeight = Math.max(0, visibleBottom - visibleTop);
    const targetHeight = Math.max(1, Math.min(rect.height, viewportHeight));
    return (visibleHeight / targetHeight) >= threshold;
  }

  function scheduleGentleScroll(el, options = {}) {
    cancelPendingAutoScroll();
    const delay = options.delay || 0;
    pendingAutoScrollTimer = window.setTimeout(() => {
      pendingAutoScrollTimer = null;
      if (!el || isMostlyInViewport(el, options.threshold || 0.7)) return;
      el.scrollIntoView({ behavior: 'smooth', block: options.block || 'start' });
    }, delay);
  }

  function sanitizeAndroidVersionName(value) {
    const cleaned = String(value || '').replace(/[^0-9A-Za-z._-]/g, '').replace(/^[._-]+|[._-]+$/g, '');
    return cleaned || '1.0.0';
  }

  function sanitizeAndroidVersionCode(value) {
    if (value === null || value === undefined) return '';
    if (String(value).trim() === '') return '';
    const parsed = parseInt(String(value || '').trim(), 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : '';
  }

  // Desktop shell window dimension (px). '' = browser default (no flag).
  function sanitizeWindowSize(value) {
    if (value === null || value === undefined) return '';
    if (String(value).trim() === '') return '';
    const parsed = parseInt(String(value).trim(), 10);
    if (!Number.isFinite(parsed)) return '';
    return Math.max(320, Math.min(7680, parsed));
  }

  function sanitizeAndroidPackagePrefix(value) {
    const raw = String(value || '').toLowerCase();
    const parts = raw.split('.').map((chunk) => {
      let token = chunk.replace(/[^a-z0-9_]/g, '');
      if (!token) return '';
      if (/^[0-9]/.test(token)) token = `p${token}`;
      return token;
    }).filter(Boolean);
    return parts.length >= 2 ? parts.join('.') : 'com.webtoapp';
  }

  function getDeviceFingerprint() {
    function syncFingerprintCookie(value) {
      if (!value) return;
      const secure = window.location.protocol === 'https:' ? '; Secure' : '';
      document.cookie = `${DEVICE_COOKIE_KEY}=${encodeURIComponent(value)}; Max-Age=31536000; Path=/; SameSite=Lax${secure}`;
    }
    try {
      const existing = window.localStorage.getItem(DEVICE_STORAGE_KEY);
      if (existing) {
        syncFingerprintCookie(existing);
        return existing;
      }
      const bytes = new Uint8Array(16);
      window.crypto.getRandomValues(bytes);
      const created = Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
      window.localStorage.setItem(DEVICE_STORAGE_KEY, created);
      syncFingerprintCookie(created);
      return created;
    } catch (_err) {
      const fallback = `volatile-${Date.now().toString(16)}`;
      syncFingerprintCookie(fallback);
      return fallback;
    }
  }

  function apiHeaders() {
    return {
      'Content-Type': 'application/json',
      'X-Device-Fingerprint': deviceFingerprint,
    };
  }

  // Multipart uploads must not carry a JSON Content-Type; the browser sets
  // the multipart boundary itself.
  function apiUploadHeaders() {
    return { 'X-Device-Fingerprint': deviceFingerprint };
  }

  function apiErrorMessage(detail, fallbackKey) {
    if (detail && typeof detail === 'object') {
      if (detail.code) {
        const translated = t(detail.code, { msg: detail.message || '' });
        if (translated !== detail.code) return translated;
      }
      if (detail.message) return String(detail.message);
      return t(fallbackKey);
    }
    if (typeof detail === 'string' && detail) return detail;
    return t(fallbackKey);
  }

  function setInputMode(mode) {
    inputMode = mode === 'html' ? 'html' : 'url';
    modeUrlBtn.classList.toggle('active', inputMode === 'url');
    modeHtmlBtn.classList.toggle('active', inputMode === 'html');
    urlInputWrap.classList.toggle('hidden', inputMode === 'html');
    htmlInputWrap.classList.toggle('hidden', inputMode !== 'html');
  }

  // --- Platform tabs (per-platform settings) ---
  // Only Android currently exposes extra knobs (they drive the real APK
  // build); the other panels document their fixed shells + shared-settings
  // reuse. IDs of the Android inputs are unchanged so the submit path below
  // keeps working untouched.
  const platformTabs = Array.from(document.querySelectorAll('[data-platform-tab]'));
  const platformPanels = Array.from(document.querySelectorAll('[data-platform-panel]'));
  function selectPlatformTab(name, focusTab) {
    const target = String(name || 'android');
    platformTabs.forEach((tab) => {
      const active = tab.dataset.platformTab === target;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', active ? 'true' : 'false');
      tab.tabIndex = active ? 0 : -1;
      if (active && focusTab) tab.focus();
    });
    platformPanels.forEach((panel) => {
      panel.hidden = panel.dataset.platformPanel !== target;
    });
  }
  platformTabs.forEach((tab) => {
    tab.addEventListener('click', () => selectPlatformTab(tab.dataset.platformTab, false));
    tab.addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault();
      const dir = e.key === 'ArrowRight' ? 1 : -1;
      const rtl = document.documentElement.dir === 'rtl';
      const next = platformTabs[(platformTabs.indexOf(tab) + (rtl ? -dir : dir) + platformTabs.length) % platformTabs.length];
      if (next) selectPlatformTab(next.dataset.platformTab, true);
    });
  });

  function formatBytes(bytes) {
    const n = Number(bytes || 0);
    if (n >= 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
    if (n >= 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${n} B`;
  }

  function resetHtmlFile() {
    htmlFile = null;
    htmlFileInput.value = '';
    htmlDropzone.classList.remove('has-file');
    htmlFileLabel.textContent = t('mode.htmlPick');
    htmlFileHint.textContent = t('mode.htmlHint');
  }

  async function attachHistoryItem(appId) {
    const value = String(appId || '').trim();
    if (!value) return null;
    const res = await fetch(`/api/history/attach/${encodeURIComponent(value)}`, {
      method: 'POST',
      headers: apiHeaders(),
    });
    if (!res.ok) throw new Error('attach failed');
    return res.json();
  }

  function formatHistoryTime(value) {
    if (!value) return t('history.justNow');
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return t('history.justNow');
    return date.toLocaleString(locale(), {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function getAbsoluteUrl(pathOrUrl) {
    if (!pathOrUrl) return '';
    try {
      return new URL(pathOrUrl, window.location.origin).toString();
    } catch (_err) {
      return String(pathOrUrl || '');
    }
  }

  function escapeHtml(value) {
    return String(value || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function fillIconPreview(dataUrl, label) {
    if (dataUrl) {
      customIconDataUrl = dataUrl;
      customIconPreview.src = dataUrl;
      customIconPreview.parentElement.classList.add('has-image');
      customIconPlaceholder.textContent = label || t('icon.refilled');
      syncRestoreIconButton();
      return;
    }
    customIconDataUrl = '';
    customIconInput.value = '';
    if (customIconFileName) customIconFileName.textContent = t('config.noFileChosen');
    customIconPreview.removeAttribute('src');
    customIconPreview.parentElement.classList.remove('has-image');
    customIconPlaceholder.textContent = t('config.iconAutoFetch');
    syncRestoreIconButton();
  }

  function syncRestoreIconButton() {
    if (!customIconClearBtn) return;
    if (restoreIconDataUrl) {
      customIconClearBtn.textContent = restoreIconButtonLabel;
      customIconClearBtn.disabled = false;
      return;
    }
    if (customIconDataUrl) {
      customIconClearBtn.textContent = t('icon.clear');
      customIconClearBtn.disabled = false;
      return;
    }
    customIconClearBtn.textContent = t('icon.noRestore');
    customIconClearBtn.disabled = true;
  }

  function setRestoreIconState(dataUrl, options = {}) {
    restoreIconDataUrl = String(dataUrl || '').trim();
    restoreIconLabel = String(options.label || '').trim();
    restoreIconFileName = String(options.fileName || '').trim();
    restoreIconButtonLabel = String(options.buttonLabel || t('icon.noRestore')).trim() || t('icon.noRestore');
    syncRestoreIconButton();
  }

  function nameSourceLabel(source) {
    const key = String(source || '').trim();
    const known = ['site_name', 'application_name', 'apple_mobile_web_app_title',
      'title_host_match', 'title_first_part', 'title_full', 'host_fallback'];
    return known.indexOf(key) !== -1 ? t('nameSource.' + key) : t('nameSource.default');
  }

  function updateAppNameSourceNote(source, suggestedName) {
    if (!appNameSourceNote) return;
    if (!suggestedName) {
      appNameSourceNote.textContent = t('config.appNameNote');
      return;
    }
    if (!source) {
      appNameSourceNote.textContent = t('note.currentRefilled');
      return;
    }
    const label = nameSourceLabel(source);
    appNameSourceNote.textContent = t('note.filledBy', { source: label });
  }

  function syncInputValue(input, value) {
    const text = value == null ? '' : String(value);
    input.value = text;
    input.setAttribute('value', text);
  }

  let historyQuery = '';
  let historySort = 'newest';

  function historyHostOf(item) {
    const raw = item.target_url || (item.recipe && item.recipe.url) || '';
    try {
      return new URL(raw).hostname.replace(/^www\./, '');
    } catch (_err) {
      return String(raw || '');
    }
  }

  function visibleHistoryItems() {
    const q = historyQuery.trim().toLowerCase();
    let list = lastHistoryItems.slice();
    if (q) {
      list = list.filter((item) => {
        const haystack = `${item.name || ''} ${item.target_url || ''} ${(item.tags || []).join(' ')}`.toLowerCase();
        return haystack.includes(q);
      });
    }
    if (historySort === 'visits') {
      list.sort((a, b) => Number(b.visit_count || 0) - Number(a.visit_count || 0));
    } else if (historySort === 'downloads') {
      list.sort((a, b) => Number(b.download_count || 0) - Number(a.download_count || 0));
    } else {
      list.sort((a, b) => String(b.updated_at || '').localeCompare(String(a.updated_at || '')));
    }
    return list;
  }

  function renderHistory(items) {
    lastHistoryItems = Array.isArray(items) ? items : [];
    const filtered = visibleHistoryItems();
    historyList.innerHTML = '';
    historyList.removeAttribute('aria-busy');
    historyEmpty.classList.toggle('hidden', filtered.length > 0);
    const emptyText = historyEmpty.querySelector('p');
    if (emptyText) {
      const key = lastHistoryItems.length && !filtered.length ? 'history.noMatches' : 'history.empty';
      emptyText.setAttribute('data-i18n', key);
      emptyText.textContent = t(key);
    }
    historyList.classList.toggle('selecting', historySelectMode);
    updateHistorySelectBar();
    updateHistoryToggle(filtered.length);
    if (!filtered.length) return;

    // Collapsed by default to keep the page short; selection mode always
    // renders everything so bulk clean-up can reach every entry.
    const visibleList = (historySelectMode || historyExpanded || historyQuery.trim())
      ? filtered
      : filtered.slice(0, HISTORY_PREVIEW_COUNT);
    const fragment = document.createDocumentFragment();
    visibleList.forEach((item) => {
      const row = document.createElement('article');
      const appId = item.app_id || '';
      const publicPath = getAbsoluteUrl(item.public_path || `/a/${appId}`);
      const host = historyHostOf(item);
      const breakdown = item.visit_breakdown || {};
      const downloadBreakdown = item.download_breakdown || {};
      const platformChips = Object.entries(downloadBreakdown)
        .filter(([, count]) => Number(count || 0) > 0)
        .map(([platform, count]) => `<span class="detail-chip">${escapeHtml(platform)} ${Number(count).toLocaleString(locale())}</span>`)
        .join('');
      const iconHtml = item.icon_url
        ? `<img src="${escapeHtml(item.icon_url)}" alt="" loading="lazy" decoding="async">`
        : `<span class="app-row-letter" aria-hidden="true">${escapeHtml((item.name || appId || '?').charAt(0).toUpperCase())}</span>`;
      const isHtmlApp = !!(item.recipe && item.recipe.source_type === 'html');
      const isPublic = item.visibility === 'public';
      const visibilityAction = isPublic ? t('history.makePrivate') : t('history.makePublic');
      row.className = 'app-row';
      row.classList.toggle('selected', historySelected.has(appId));
      row.classList.toggle('is-public', isPublic);
      row.dataset.appId = appId;
      row._historyItem = item;
      row.innerHTML = `
        <label class="app-row-check">
          <input type="checkbox" data-select="${escapeHtml(appId)}" ${historySelected.has(appId) ? 'checked' : ''}>
        </label>
        <div class="app-row-icon">${iconHtml}</div>
        <div class="app-row-main" data-expand tabindex="0" role="button" aria-expanded="false">
          <div class="app-row-title">
            <span class="app-row-name">${escapeHtml(item.name || appId)}</span>
            <span class="pill ${isPublic ? 'pill-public' : 'pill-private'}">${escapeHtml(isPublic ? t('history.visibilityPublic') : t('history.visibilityPrivate'))}</span>
            ${isHtmlApp ? `<span class="pill">${escapeHtml(t('history.badgeHtml'))}</span>` : ''}
            <span class="pill pill-lang">${escapeHtml(languageLabel(item.language_category || 'und'))}</span>
          </div>
          <div class="app-row-sub">
            ${host ? `<span class="app-row-host">${escapeHtml(host)}</span><span aria-hidden="true">·</span>` : ''}
            <span>${escapeHtml(relTime(item.updated_at))}</span>
          </div>
          ${item.icon_review_deadline ? `<p class="app-row-warn">${escapeHtml(t('history.iconReview', { deadline: formatDeadline(item.icon_review_deadline) }))}</p>` : ''}
        </div>
        <div class="app-row-metrics">
          <span class="metric" title="${escapeHtml(t('history.visitsLabel'))}">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="2.6"/></svg>
            ${Number(item.visit_count || 0).toLocaleString(locale())}
          </span>
          <span class="metric" title="${escapeHtml(t('history.downloadsLabel'))}">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M4 20h16"/></svg>
            ${Number(item.download_count || 0).toLocaleString(locale())}
          </span>
        </div>
        <div class="app-row-actions">
          <button class="app-row-open" type="button" data-open="${escapeHtml(publicPath)}">${escapeHtml(t('market.open'))}</button>
          <button class="icon-btn app-row-menu-btn" type="button" data-row-menu aria-haspopup="menu" aria-expanded="false" aria-label="${escapeHtml(t('history.more'))}">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.7"/><circle cx="12" cy="12" r="1.7"/><circle cx="19" cy="12" r="1.7"/></svg>
          </button>
          <div class="row-menu hidden" role="menu">
            <button type="button" role="menuitem" data-copy="${escapeHtml(publicPath)}">${escapeHtml(t('history.copyLink'))}</button>
            <button type="button" role="menuitem" data-edit="${escapeHtml(appId)}">${escapeHtml(t('history.editForm'))}</button>
            <button type="button" role="menuitem" data-regenerate="${escapeHtml(appId)}">${escapeHtml(t('history.regenerate'))}</button>
            <button type="button" role="menuitem" data-visibility-toggle="${escapeHtml(appId)}">${escapeHtml(visibilityAction)}</button>
            <button type="button" role="menuitem" class="danger" data-delete="${escapeHtml(appId)}">${escapeHtml(t('history.delete'))}</button>
          </div>
        </div>
        <div class="app-row-detail" hidden>
          <div class="detail-grid">
            <div class="detail-item"><span>${escapeHtml(t('history.rowLanding'))}</span><strong>${Number(breakdown.landing || 0).toLocaleString(locale())}</strong></div>
            <div class="detail-item"><span>${escapeHtml(t('history.rowInstall'))}</span><strong>${Number(breakdown.install || 0).toLocaleString(locale())}</strong></div>
            <div class="detail-item"><span>${escapeHtml(t('history.rowPwa'))}</span><strong>${Number(breakdown.pwa || 0).toLocaleString(locale())}</strong></div>
            <div class="detail-item"><span>${escapeHtml(t('history.rowLaunch'))}</span><strong>${Number(breakdown.launch || 0).toLocaleString(locale())}</strong></div>
          </div>
          <div class="detail-platforms">
            <span class="detail-label">${escapeHtml(t('history.rowPlatform'))}</span>
            ${platformChips || `<span class="detail-chip muted">${escapeHtml(t('history.none'))}</span>`}
          </div>
        </div>
      `;
      fragment.appendChild(row);
    });
    historyList.appendChild(fragment);
  }

  async function loadHistory() {
    // Only the initial load may paint the cached list. Reloads after a
    // delete/visibility change must not flash the pre-action rows.
    const cached = lastHistoryItems.length ? null : readRenderCache('history');
    if (cached && Array.isArray(cached.items)) renderHistory(cached.items);
    try {
      const prefetched = takePrefetch('history');
      let res;
      try {
        res = prefetched ? await prefetched : await fetch('/api/history', {
          headers: { 'X-Device-Fingerprint': deviceFingerprint },
        });
      } catch (_err) {
        res = await fetch('/api/history', {
          headers: { 'X-Device-Fingerprint': deviceFingerprint },
        });
      }
      if (!res.ok) throw new Error('failed');
      const data = await res.json();
      const items = data.items || [];
      renderHistory(items);
      writeRenderCache('history', { items });
      return items;
    } catch (_err) {
      if (!cached) renderHistory([]);
      return cached && Array.isArray(cached.items) ? cached.items : [];
    }
  }

  // --- Public market ---
  let marketSearchTimer = null;
  let marketRequestSeq = 0;
  let marketAbort = null;
  const marketError = document.getElementById('market-error');
  const marketRetryBtn = document.getElementById('market-retry');

  let lastMarketItems = [];
  let marketHasMore = false;
  const marketLoadMoreBtn = document.getElementById('market-load-more');

  function marketHostOf(item) {
    try {
      return new URL(item.target_url || '').hostname.replace(/^www\./, '');
    } catch (_err) {
      return String(item.target_url || '');
    }
  }

  function renderMarket(items, append) {
    const list = Array.isArray(items) ? items : [];
    lastMarketItems = append ? lastMarketItems.concat(list) : list;
    if (!append) marketList.innerHTML = '';
    marketEmpty.classList.toggle('hidden', lastMarketItems.length > 0);
    const emptyText = marketEmpty.querySelector('p');
    if (emptyText) {
      const activeTag = document.querySelector('.market-tab.active');
      const filtering = !!marketSearchInput.value.trim()
        || !!(activeTag && activeTag.dataset.marketTag)
        || !!(marketLanguageSelect && marketLanguageSelect.value);
      const key = !lastMarketItems.length && filtering ? 'market.noMatches' : 'market.empty';
      emptyText.setAttribute('data-i18n', key);
      emptyText.textContent = t(key);
    }
    const fragment = document.createDocumentFragment();
    list.forEach((item) => {
      const publicPath = getAbsoluteUrl(item.public_path || `/a/${item.app_id}`);
      const tags = Array.isArray(item.tags) ? item.tags.slice(0, 4) : [];
      const tagChips = tags.map((tag) => `<span class="market-tag">${escapeHtml(tag)}</span>`).join('');
      const langChip = `<span class="market-tag market-lang">${escapeHtml(languageLabel(item.language_category || 'und'))}</span>`;
      const iconHtml = item.icon_url
        ? `<img src="${escapeHtml(item.icon_url)}" alt="" loading="lazy" decoding="async">`
        : `<span class="market-card-letter" aria-hidden="true">${escapeHtml((item.name || item.app_id || '?').charAt(0).toUpperCase())}</span>`;
      const creatorAvatar = item.creator_avatar_url
        ? `<img class="market-creator-avatar" src="${escapeHtml(item.creator_avatar_url)}" alt="" loading="lazy">`
        : `<span class="market-creator-avatar avatar-fallback" aria-hidden="true">${escapeHtml((item.creator_name || '#').charAt(0).toUpperCase())}</span>`;
      const creatorHtml = item.creator_num
        ? `<a class="market-creator" href="/?u=${encodeURIComponent(item.creator_num)}" data-user-num="${encodeURIComponent(item.creator_num)}">
             ${creatorAvatar}<span class="market-creator-name">${escapeHtml(item.creator_name || t('profile.anon'))}</span>
           </a>`
        : '';
      const ratingHtml = item.rating_count
        ? `<span class="market-card-rating"><span class="market-star">★</span>${Number(item.rating_avg).toFixed(1)}<span class="market-rating-cnt">(${Number(item.rating_count).toLocaleString(locale())})</span></span>`
        : `<span class="market-card-rating is-empty"><span class="market-star market-star-off">★</span><span class="market-rating-cnt">${escapeHtml(t('market.noRatings'))}</span></span>`;
      const createdIso = item.created_at || item.updated_at || '';
      const publishedRel = relTime(createdIso);
      const publishedAbs = absoluteTime(createdIso);
      const visits = Number(item.visit_count || 0).toLocaleString(locale());
      const downloads = Number(item.download_count || 0).toLocaleString(locale());
      const card = document.createElement('article');
      card.className = 'market-card';
      card.innerHTML = `
        <div class="market-card-head">
          <div class="market-card-icon">${iconHtml}</div>
          <div class="market-card-heading">
            <h3 class="market-card-name">${escapeHtml(item.name || item.app_id)}</h3>
            <p class="market-card-host">
              <span class="market-card-host-name">${escapeHtml(marketHostOf(item))}</span>
              ${publishedRel ? `<span class="market-card-dot" aria-hidden="true">·</span><span class="market-card-time" title="${escapeHtml(publishedAbs)}">${escapeHtml(publishedRel)}</span>` : ''}
            </p>
          </div>
          ${ratingHtml}
        </div>
        ${item.description ? `<p class="market-card-desc">${escapeHtml(item.description)}</p>` : ''}
        <div class="market-card-tags">${langChip}${tagChips}</div>
        ${item.icon_review_deadline ? `<span class="market-icon-review">${escapeHtml(t('market.iconReview'))}</span>` : ''}
        <div class="market-card-foot">
          ${creatorHtml || `<span class="market-card-anon">${escapeHtml(t('profile.anon'))}</span>`}
          <span class="market-card-stats">
            <span class="market-card-stat" title="${escapeHtml(t('market.visits', { n: visits }))}">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="2.6"/></svg>
              ${visits}
            </span>
            <span class="market-card-stat" title="${escapeHtml(t('market.downloads', { n: downloads }))}">
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M4 20h16"/></svg>
              ${downloads}
            </span>
          </span>
        </div>
        <button class="market-card-open" type="button" data-open="${escapeHtml(publicPath)}">${escapeHtml(t('market.open'))}</button>
      `;
      fragment.appendChild(card);
    });
    marketList.appendChild(fragment);
    if (marketLoadMoreBtn) marketLoadMoreBtn.classList.toggle('hidden', !marketHasMore);
  }

  function formatDeadline(iso) {
    const ts = Date.parse(iso || '');
    if (!ts) return String(iso || '');
    try {
      return new Intl.DateTimeFormat(locale(), {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone: 'UTC',
      }).format(ts) + ' UTC';
    } catch (_err) {
      return String(iso);
    }
  }

  function relTime(iso) {
    const ts = Date.parse(iso || '');
    if (!ts) return '';
    const s = Math.max(0, (Date.now() - ts) / 1000);
    if (s < 60) return t('time.justNow');
    const m = Math.floor(s / 60);
    if (m < 60) return t('time.minutesAgo', { n: m });
    const h = Math.floor(m / 60);
    if (h < 24) return t('time.hoursAgo', { n: h });
    const d = Math.floor(h / 24);
    if (d < 30) return t('time.daysAgo', { n: d });
    const mo = Math.floor(d / 30.44);
    if (mo < 12) return t('time.monthsAgo', { n: mo });
    return t('time.yearsAgo', { n: Math.floor(mo / 12) });
  }

  function absoluteTime(iso) {
    const ts = Date.parse(iso || '');
    if (!ts) return '';
    try {
      return new Intl.DateTimeFormat(locale(), {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(ts);
    } catch (_err) {
      return String(iso || '');
    }
  }

  const MARKET_PAGE_SIZE = 24;

  async function loadMarket(options = {}) {
    const append = options.append === true;
    const activeTab = document.querySelector('.market-tab.active');
    const tag = activeTab ? activeTab.dataset.marketTag : '';
    const params = new URLSearchParams();
    if (tag) params.set('tag', tag);
    if (marketSearchInput.value.trim()) params.set('search', marketSearchInput.value.trim());
    if (marketLanguageSelect && marketLanguageSelect.value) params.set('language', marketLanguageSelect.value);
    params.set('sort', marketSortSelect.value || 'newest');
    params.set('limit', String(MARKET_PAGE_SIZE));
    params.set('offset', String(append ? lastMarketItems.length : 0));
    const defaultQuery = !append
      && !tag
      && !marketSearchInput.value.trim()
      && !(marketLanguageSelect && marketLanguageSelect.value)
      && (marketSortSelect.value || 'newest') === 'newest';
    const cached = defaultQuery ? readRenderCache('market') : null;
    const cachedItems = cached && Array.isArray(cached.items) ? cached.items : null;
    // Only the newest request may paint: a slow response for an older query
    // must not overwrite results the user has already moved past.
    const seq = ++marketRequestSeq;
    if (marketAbort) marketAbort.abort();
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    marketAbort = controller;
    marketList.setAttribute('aria-busy', 'true');
    if (marketLoadMoreBtn) marketLoadMoreBtn.disabled = true;
    if (cachedItems && cachedItems.length) {
      marketHasMore = cached.has_more === true;
      marketCount.textContent = t('market.count', { n: cached.total != null ? cached.total : cachedItems.length });
      marketError.classList.add('hidden');
      renderMarket(cachedItems, false);
    }
    try {
      const prefetched = defaultQuery ? takePrefetch('market') : null;
      let res;
      try {
        res = prefetched ? await prefetched : await fetch(`/api/market?${params.toString()}`, controller ? { signal: controller.signal } : undefined);
      } catch (_err) {
        res = await fetch(`/api/market?${params.toString()}`, controller ? { signal: controller.signal } : undefined);
      }
      if (!res.ok) throw new Error('market failed');
      const data = await res.json();
      if (seq !== marketRequestSeq) return;
      const items = data.items || [];
      marketHasMore = data.has_more === true;
      marketCount.textContent = t('market.count', { n: data.total != null ? data.total : items.length });
      marketError.classList.add('hidden');
      renderMarket(items, append);
      if (defaultQuery) {
        writeRenderCache('market', { items, total: data.total, has_more: marketHasMore });
      }
    } catch (err) {
      if (seq !== marketRequestSeq || (err && err.name === 'AbortError')) return;
      if (append && lastMarketItems.length) {
        notify(t('market.loadFailed'), 'error');
      } else if (cachedItems && cachedItems.length) {
        // Keep the cached cards visible; the retry button still works.
        marketError.classList.remove('hidden');
      } else {
        marketCount.textContent = '';
        marketHasMore = false;
        renderMarket([]);
        marketEmpty.classList.add('hidden');
        marketError.classList.remove('hidden');
      }
    } finally {
      if (seq === marketRequestSeq) {
        marketList.removeAttribute('aria-busy');
        marketAbort = null;
        if (marketLoadMoreBtn) marketLoadMoreBtn.disabled = false;
      }
    }
  }

  marketList.addEventListener('click', (event) => {
    const creatorLink = event.target.closest('a.market-creator');
    if (creatorLink && creatorLink.dataset.userNum) {
      event.preventDefault();
      openProfileViaLink(Number(creatorLink.dataset.userNum));
      return;
    }
    const btn = event.target.closest('[data-open]');
    if (btn) window.open(btn.dataset.open, '_blank', 'noopener,noreferrer');
  });

  const marketTabs = Array.from(document.querySelectorAll('.market-tab'));
  function selectMarketTab(tab) {
    marketTabs.forEach((el) => {
      const active = el === tab;
      el.classList.toggle('active', active);
      el.setAttribute('role', 'tab');
      el.setAttribute('aria-selected', active ? 'true' : 'false');
    });
  }
  selectMarketTab(marketTabs.find((el) => el.classList.contains('active')) || marketTabs[0]);
  marketTabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      if (tab.classList.contains('active')) return;
      selectMarketTab(tab);
      loadMarket();
    });
  });

  marketSearchInput.addEventListener('input', () => {
    if (marketSearchTimer) clearTimeout(marketSearchTimer);
    marketSearchTimer = setTimeout(() => loadMarket(), 250);
  });

  marketSortSelect.addEventListener('change', () => loadMarket());
  if (marketLanguageSelect) marketLanguageSelect.addEventListener('change', () => loadMarket());
  if (marketRetryBtn) marketRetryBtn.addEventListener('click', () => loadMarket());
  if (marketLoadMoreBtn) marketLoadMoreBtn.addEventListener('click', () => loadMarket({ append: true }));
  if (marketLoadMoreBtn && 'IntersectionObserver' in window) {
    const marketMoreObserver = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      if (!marketHasMore) return;
      if (marketList.getAttribute('aria-busy') === 'true') return;
      loadMarket({ append: true });
    }, { rootMargin: '320px' });
    marketMoreObserver.observe(marketLoadMoreBtn);
  }

  async function recoverHistoryFromPageContext() {
    const candidates = new Set();
    const currentLink = appLink && appLink.value ? appLink.value : '';
    const currentUrl = previewOpenBtn && previewOpenBtn.dataset ? previewOpenBtn.dataset.href : '';
    [currentLink, currentUrl, window.location.href].forEach((value) => {
      const match = String(value || '').match(/\/a\/([a-f0-9]{8})(?:[/?#]|$)/i);
      if (match) candidates.add(match[1]);
    });
    if (!candidates.size) return [];
    for (const appId of candidates) {
      try {
        await attachHistoryItem(appId);
      } catch (_err) {
        // Ignore failed recovery attempts; the app may no longer exist.
      }
    }
    return loadHistory();
  }

  deviceFingerprint = getDeviceFingerprint();
  loadHistory().then((items) => {
    if (!items.length) {
      recoverHistoryFromPageContext();
    }
  });
  loadMarket();

  // --- User profile (fingerprint identity → sequential user_num) ---
  const PROFILE_CACHE_KEY = 'webtoapp-profile-v1';
  let profileSelfNum = null;
  let profileViewingSelf = true;
  let profileViewedNum = null;

  function profileCacheRead() {
    try { return JSON.parse(localStorage.getItem(PROFILE_CACHE_KEY)) || null; } catch (_e) { return null; }
  }

  function profileCacheWrite(profile) {
    try {
      localStorage.setItem(PROFILE_CACHE_KEY, JSON.stringify({
        user_num: profile.user_num, name: profile.name || '', avatar_url: profile.avatar_url || null,
      }));
    } catch (_e) { /* ignore */ }
  }

  function paintNavAvatar(profile) {
    if (!profile) return;
    profileSelfNum = profile.user_num;
    if (profile.avatar_url) {
      profileBtnAvatar.src = profile.avatar_url;
      profileBtnAvatar.classList.remove('hidden');
      profileBtnIcon.classList.add('hidden');
    }
  }

  function profileShowMessage(msg) {
    profileMsg.textContent = msg || '';
  }

  function profileSetAvatar(url, name, num) {
    const has = !!url;
    profileAvatarImg.classList.toggle('hidden', !has);
    profileAvatarFallback.classList.toggle('hidden', has);
    if (has) {
      profileAvatarImg.src = url;
    } else {
      // Show the sequential #N as the fallback identity — every user's page
      // is visually distinct even when they never set a name or avatar.
      profileAvatarFallback.textContent = num ? `#${num}` : (name || '#').charAt(0).toUpperCase();
    }
  }

  function profileRenderApps(apps, mine) {
    const list = Array.isArray(apps) ? apps : [];
    profileAppsEl.innerHTML = list.length
      ? list.map((a) => {
          const path = a.public_path || `/a/${a.app_id}`;
          const icon = a.icon_url
            ? `<img src="${escapeHtml(a.icon_url)}" alt="" loading="lazy">`
            : '<span class="profile-app-dot"></span>';
          const visKey = a.visibility === 'private' ? 'history.visibilityPrivate'
            : a.visibility === 'public' ? 'history.visibilityPublic' : '';
          const vis = mine && visKey
            ? `<em class="profile-app-vis">${escapeHtml(t(visKey))}</em>` : '';
          return `<a class="profile-app" href="${escapeHtml(path)}" target="_blank" rel="noopener noreferrer">${icon}<span>${escapeHtml(a.name || a.app_id)}</span>${vis}</a>`;
        }).join('')
      : `<p class="profile-apps-empty">${escapeHtml(t('profile.noApps'))}</p>`;
  }

  function profileRender(profile, apps, mine) {
    if (!profile) return;
    const name = profile.name || t('profile.anon');
    profileNameView.textContent = name;
    profileNumEl.textContent = `#${profile.user_num}`;
    profileJoinedEl.textContent = profile.created_at
      ? t('profile.joined', { d: new Date(profile.created_at).toLocaleDateString(locale()) })
      : '';
    profileSetAvatar(profile.avatar_url, name, profile.user_num);
    profileVisBadge.textContent = t('profile.publicView');
    profileVisBadge.classList.toggle('hidden', mine);
    profileBioView.innerHTML = profile.bio_md ? window.wtaMd(profile.bio_md) : '';
    profileAppsLabel.textContent = t(mine ? 'profile.myApps' : 'profile.publicApps');
    profileRenderApps(apps, mine);
    avatarUploadBtn.classList.toggle('hidden', !mine);
    profileEditBtn.classList.toggle('hidden', !mine);
    profileEditForm.classList.add('hidden');
    profileShowMessage('');
  }

  function profileUrlFor(num) {
    const sp = new URLSearchParams(window.location.search);
    if (num == null) sp.delete('u');
    else sp.set('u', String(num));
    const q = sp.toString();
    return window.location.pathname + (q ? `?${q}` : '');
  }

  function openProfileViaLink(num) {
    history.pushState({}, '', profileUrlFor(num));
    openProfile(num);
  }

  let profileReturnFocus = null;
  let profileLoadSeq = 0;

  function hideProfileModal() {
    if (profileModal.classList.contains('hidden')) return;
    profileModal.classList.add('hidden');
    profileLoadSeq += 1;
    const back = profileReturnFocus;
    profileReturnFocus = null;
    if (back && typeof back.focus === 'function' && document.contains(back)) back.focus();
  }

  function closeProfileModal() {
    hideProfileModal();
    if (new URLSearchParams(window.location.search).has('u')) {
      history.pushState({}, '', profileUrlFor(null));
    }
  }

  async function openProfile(num) {
    if (profileModal.classList.contains('hidden')) {
      profileReturnFocus = document.activeElement;
      profileModal.classList.remove('hidden');
      profileClose.focus();
    }
    profileShowMessage('');
    const mine = num == null || (profileSelfNum != null && Number(num) === profileSelfNum);
    profileViewingSelf = mine;
    profileViewedNum = mine ? null : Number(num);
    const seq = ++profileLoadSeq;
    try {
      const res = await fetch(mine ? '/api/me' : `/api/users/${encodeURIComponent(num)}`);
      if (!res.ok) throw new Error('load failed');
      const data = await res.json();
      if (seq !== profileLoadSeq) return;
      if (mine && data.profile) {
        profileCacheWrite(data.profile);
        paintNavAvatar(data.profile);
      }
      profileRender(data.profile, data.apps, mine);
    } catch (_err) {
      if (seq !== profileLoadSeq) return;
      profileNameView.textContent = '—';
      profileAppsEl.innerHTML = '';
      profileShowMessage(t('profile.loadFailed'));
    }
  }

  function notify(message, type) {
    if (window.WtaUI) window.WtaUI.toast(message, { type: type || 'info' });
    else window.alert(message);
  }

  function ask(message, options) {
    if (window.WtaUI) return window.WtaUI.confirm(message, options);
    return Promise.resolve(window.confirm(message));
  }

  function flashLabel(button, text, ms) {
    if (!button.dataset.label) button.dataset.label = button.textContent;
    button.textContent = text;
    window.clearTimeout(Number(button.dataset.flashTimer || 0));
    button.dataset.flashTimer = String(window.setTimeout(() => {
      button.textContent = button.dataset.label;
      delete button.dataset.label;
      delete button.dataset.flashTimer;
    }, ms || 1600));
  }

  function copyPlainText(text) {
    const legacy = () => new Promise((resolve, reject) => {
      const area = document.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.insetInlineStart = '-9999px';
      document.body.appendChild(area);
      area.select();
      try {
        const ok = document.execCommand('copy');
        area.remove();
        if (ok) resolve();
        else reject(new Error('copy failed'));
      } catch (err) {
        area.remove();
        reject(err);
      }
    });
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(() => legacy());
    }
    return legacy();
  }

  function initQqGroup() {
    const btn = document.getElementById('qq-group-btn');
    const panel = document.getElementById('qq-group-panel');
    const closeBtn = document.getElementById('qq-group-close');
    const copyBtn = document.getElementById('qq-group-copy');
    const numberEl = document.getElementById('qq-group-number');
    const statusEl = document.getElementById('qq-group-status');
    if (!btn || !panel || !closeBtn || !copyBtn || !numberEl || !statusEl) return;

    let statusTimer = 0;
    const isOpen = () => !panel.classList.contains('hidden');

    function clearStatus() {
      window.clearTimeout(statusTimer);
      statusTimer = 0;
      statusEl.textContent = '';
      statusEl.classList.remove('is-failed');
    }

    function showStatus(message, failed) {
      window.clearTimeout(statusTimer);
      statusEl.textContent = message;
      statusEl.classList.toggle('is-failed', !!failed);
      statusTimer = window.setTimeout(clearStatus, 2000);
    }

    function openPanel() {
      panel.classList.remove('hidden');
      btn.setAttribute('aria-expanded', 'true');
      const join = panel.querySelector('.community-link');
      if (join) join.focus();
    }

    function closePanel(restoreFocus) {
      if (!isOpen()) return;
      panel.classList.add('hidden');
      btn.setAttribute('aria-expanded', 'false');
      clearStatus();
      if (restoreFocus) btn.focus();
    }

    btn.addEventListener('click', (event) => {
      event.stopPropagation();
      if (isOpen()) closePanel(false);
      else openPanel();
    });

    closeBtn.addEventListener('click', () => closePanel(true));

    document.addEventListener('click', (event) => {
      if (!isOpen()) return;
      if (panel.contains(event.target) || btn.contains(event.target)) return;
      closePanel(false);
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && isOpen()) {
        event.preventDefault();
        closePanel(true);
      }
    });

    panel.addEventListener('focusout', (event) => {
      if (!isOpen()) return;
      const next = event.relatedTarget;
      if (!next || panel.contains(next) || next === btn) return;
      closePanel(false);
    });

    copyBtn.addEventListener('click', () => {
      const number = (numberEl.textContent || '').trim();
      copyPlainText(number).then(() => {
        showStatus(t('nav.qqCopied'), false);
      }).catch(() => {
        showStatus(t('nav.qqCopyFailed'), true);
      });
    });

    window.addEventListener('i18n:changed', () => {
      if (!statusEl.textContent) return;
      statusEl.textContent = statusEl.classList.contains('is-failed')
        ? t('nav.qqCopyFailed')
        : t('nav.qqCopied');
    });
  }

  function initProfile() {
    // Paint the cached avatar instantly, then refresh in the background —
    // otherwise the nav button shows the generic icon on every page load
    // until the user opens the panel.
    const cachedProfile = profileCacheRead();
    if (cachedProfile) paintNavAvatar(cachedProfile);
    const prefetchedMe = takePrefetch('me');
    (prefetchedMe || fetch('/api/me')).then((r) => (r.ok ? r.json() : null)).then((d) => {
      if (d && d.profile) {
        profileCacheWrite(d.profile);
        paintNavAvatar(d.profile);
      }
    }).catch(() => {});
    initQqGroup();
    profileBtn.addEventListener('click', () => openProfile(null));
    profileClose.addEventListener('click', () => closeProfileModal());
    profileModal.addEventListener('click', (e) => {
      if (e.target === profileModal) closeProfileModal();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape' || e.defaultPrevented) return;
      if (profileModal.classList.contains('hidden')) return;
      e.preventDefault();
      closeProfileModal();
    });
    profileEditBtn.addEventListener('click', () => {
      profileNameInput.value = profileNameView.textContent === t('profile.anon') ? '' : profileNameView.textContent;
      profileBioInput.value = '';
      profileEditForm.classList.remove('hidden');
      profileEditBtn.classList.add('hidden');
      profileMsg.textContent = '';
      fetch('/api/me').then((r) => r.json()).then((d) => {
        if (d.profile) {
          profileNameInput.value = d.profile.name || '';
          profileBioInput.value = d.profile.bio_md || '';
        }
      }).catch(() => {});
    });
    profileEditCancel.addEventListener('click', () => {
      profileEditForm.classList.add('hidden');
      profileEditBtn.classList.remove('hidden');
    });
    profileEditForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const saveBtn = profileEditForm.querySelector('button[type=submit]');
      if (saveBtn && saveBtn.disabled) return;
      if (saveBtn) saveBtn.disabled = true;
      try {
        const res = await fetch('/api/me/profile', {
          method: 'POST',
          headers: apiHeaders(),
          body: JSON.stringify({ name: profileNameInput.value.trim(), bio_md: profileBioInput.value }),
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          profileShowMessage(t('profile.saved'));
          profileEditForm.classList.add('hidden');
          profileEditBtn.classList.remove('hidden');
          openProfile(null);
        } else {
          profileShowMessage(t(`profile.${data.detail || 'invalid_name'}`));
        }
      } catch (_err) {
        notify(t('profile.saveFailed'), 'error');
      } finally {
        if (saveBtn) saveBtn.disabled = false;
      }
    });
    avatarUploadBtn.addEventListener('click', () => avatarFile.click());
    avatarFile.addEventListener('change', async () => {
      const file = avatarFile.files && avatarFile.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('file', file);
      avatarUploadBtn.disabled = true;
      try {
        const res = await fetch('/api/me/avatar', { method: 'POST', body: fd });
        if (!res.ok) throw new Error('avatar failed');
        const data = await res.json();
        profileSetAvatar(data.avatar_url, profileNameView.textContent, profileSelfNum);
        const merged = profileCacheRead() || { user_num: profileSelfNum };
        merged.avatar_url = data.avatar_url;
        profileCacheWrite(merged);
        paintNavAvatar(merged);
      } catch (_err) {
        profileShowMessage(t('profile.avatarFailed'));
        notify(t('profile.avatarFailed'), 'error');
      } finally {
        avatarUploadBtn.disabled = false;
        avatarFile.value = '';
      }
    });
    // ?u=N opens that user's public profile (linked from market/app pages).
    const u = new URLSearchParams(window.location.search).get('u');
    if (u && /^\d+$/.test(u)) openProfile(Number(u));
    // Back/forward between profiles and the landing view stays in-page.
    window.addEventListener('popstate', () => {
      const pu = new URLSearchParams(window.location.search).get('u');
      if (pu && /^\d+$/.test(pu)) openProfile(Number(pu));
      else hideProfileModal();
    });
  }

  // Called after the declarations above — the const/let bindings must be
  // initialized before initProfile touches them (TDZ otherwise).
  initProfile();

  async function applyHistoryItemToForm(item) {
    const recipe = item.recipe || {};
    const featureOptions = recipe.options || item.options || {};
    currentUrl = item.target_url || recipe.url || '';
    syncInputValue(urlInput, currentUrl);
    syncInputValue(appNameInput, item.name || recipe.name || '');
    syncInputValue(appDescInput, recipe.description || '');
    const storedAbout = recipe.about || {};
    syncInputValue(aboutTextInput, storedAbout.text || '');
    // Stored about images can't be re-loaded into a file input; show them
    // as previews and leave the untouched sentinel so the build keeps them.
    const storedImgs = (storedAbout.images || []).filter((n) => /^about-\d\.webp$/.test(n));
    if (storedImgs.length) {
      aboutImageDataUrls = null;
      aboutImagesPreview.innerHTML = storedImgs
        .map((n) => `<img src="/a/${encodeURIComponent(item.app_id)}/about/${n}" alt="" loading="lazy" decoding="async">`)
        .join('');
      aboutImagesName.textContent = t('config.aboutImagesCount', { n: storedImgs.length });
    } else {
      aboutImageDataUrls = null;
      aboutImagesPreview.innerHTML = '';
      aboutImagesName.textContent = t('config.noFileChosen');
    }
    updateAppNameSourceNote('', item.name || recipe.name || '');
    const color = item.color || recipe.color || '#7c3aed';
    syncInputValue(appColorInput, color);
    colorHex.textContent = color;
    syncInputValue(
      androidVersionNameInput,
      sanitizeAndroidVersionName(String(item.android_version_name || recipe.android_version_name || '1.0.0'))
    );
    const previousVersionCode = sanitizeAndroidVersionCode(item.android_version_code || recipe.android_version_code || '');
    syncInputValue(androidVersionCodeInput, '');
    androidVersionCodeInput.placeholder = previousVersionCode
      ? t('versionCode.lastValue', { n: previousVersionCode })
      : t('config.versionCodePlaceholder');
    syncInputValue(
      androidPackagePrefixInput,
      sanitizeAndroidPackagePrefix(item.android_package_prefix || recipe.android_package_prefix || 'com.webtoapp')
    );
    applyFeatureOptionsToForm(featureOptions);
    // Rebuild tag/visibility state — a rebuild must keep the stored values
    // or the user silently re-publishes untagged/private.
    selectedTags.clear();
    (recipe.tags || item.tags || []).forEach((tag) => {
      if (!selectedTags.has(tag)) selectedTags.add(tag);
      if (!tagsPicker.querySelector(`.tag-chip[data-tag="${CSS.escape(tag)}"]`)) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'tag-chip';
        btn.dataset.tag = tag;
        btn.textContent = tag;
        tagsPicker.querySelector('.tags-builtins').appendChild(btn);
      }
    });
    refreshTagChips();
    setLanguageSelection(recipe.languages || (recipe.language ? [recipe.language] : ['und']));
    setVisibility(recipe.visibility || item.visibility || 'private');
    if (item.icon_url) {
      try {
        const iconRes = await fetch(item.icon_url);
        if (!iconRes.ok) throw new Error('icon fetch failed');
        const iconBlob = await iconRes.blob();
        const iconDataUrl = await readFileAsDataUrl(iconBlob);
        detectedIconDataUrl = '';
        setRestoreIconState(iconDataUrl, {
          label: t('icon.recovered'),
          fileName: t('icon.recoveredFile'),
          buttonLabel: t('icon.restoreCurrent'),
        });
        fillIconPreview(iconDataUrl, t('icon.recovered'));
        if (customIconFileName) customIconFileName.textContent = t('icon.recoveredFile');
      } catch (_err) {
        detectedIconDataUrl = '';
        setRestoreIconState('', {});
        fillIconPreview('', '');
      }
    } else {
        detectedIconDataUrl = '';
        setRestoreIconState('', {});
        fillIconPreview('', '');
    }
    showRecoveredAnalysisResults(item);
    workspace.classList.remove('hidden');
  }

  // --- Build progress ---
  const BUILD_STEP_ORDER = ['queued', 'fetching_icon', 'writing_shell', 'building_platforms', 'uploading_cdn'];
  const BUILD_STAGE_STEP = {
    queued: 'queued',
    starting: 'queued',
    running: 'fetching_icon',
    fetching_icon: 'fetching_icon',
    writing_shell: 'writing_shell',
    building_platforms: 'building_platforms',
    platform_done: 'building_platforms',
    platform_error: 'building_platforms',
    uploading_cdn: 'uploading_cdn',
    done: 'uploading_cdn',
  };
  const BUILD_PLATFORMS = ['android', 'ios', 'windows', 'macos', 'linux'];
  const PLATFORM_LABELS = { android: 'Android', ios: 'iOS', windows: 'Windows', macos: 'macOS', linux: 'Linux' };
  const buildProgressTitle = document.getElementById('build-progress-title');
  const buildProgressLive = document.getElementById('build-progress-live');
  let buildInFlight = false;
  let buildStartedAt = 0;
  let buildClock = null;
  let buildPercentShown = 0;
  let lastPlatformStatus = {};
  let lastAnnouncedStep = '';

  function formatElapsed(ms) {
    const total = Math.max(0, Math.round(ms / 1000));
    if (total < 60) return `${total}s`;
    return `${Math.floor(total / 60)}m ${String(total % 60).padStart(2, '0')}s`;
  }

  function tickBuildClock() {
    if (buildProgressElapsed) buildProgressElapsed.textContent = formatElapsed(Date.now() - buildStartedAt);
  }

  function stopBuildClock() {
    window.clearInterval(buildClock);
    buildClock = null;
    tickBuildClock();
  }

  function setBuildLocked(locked) {
    buildInFlight = locked;
    if (configGrid) {
      configGrid.inert = locked;
      configGrid.classList.toggle('is-locked', locked);
      configGrid.setAttribute('aria-busy', locked ? 'true' : 'false');
    }
    generateBtn.disabled = locked;
    generateBtn.textContent = locked ? t('build.buttonBusy') : t('config.generateBtn');
  }

  function setBuildStep(stepKey, failed) {
    if (!buildSteps) return;
    const activeIndex = BUILD_STEP_ORDER.indexOf(stepKey);
    buildSteps.querySelectorAll('li[data-step]').forEach((li) => {
      const i = BUILD_STEP_ORDER.indexOf(li.dataset.step);
      let state = 'pending';
      if (i < activeIndex) state = 'done';
      else if (i === activeIndex) state = failed ? 'error' : 'active';
      li.dataset.state = state;
      if (i === activeIndex) li.setAttribute('aria-current', 'step');
      else li.removeAttribute('aria-current');
      if (i === activeIndex && !failed && buildProgressLive && lastAnnouncedStep !== stepKey) {
        lastAnnouncedStep = stepKey;
        buildProgressLive.textContent = li.textContent.trim();
      }
    });
  }

  function setPlatformStates(stepKey) {
    if (!buildPlatforms) return;
    const stepIdx = BUILD_STEP_ORDER.indexOf(stepKey);
    const platformIdx = BUILD_STEP_ORDER.indexOf('building_platforms');
    buildPlatforms.querySelectorAll('li[data-platform]').forEach((li) => {
      const raw = lastPlatformStatus[li.dataset.platform];
      let state = raw === 'done' || raw === 'error' ? raw : 'pending';
      if (state === 'pending' && stepIdx === platformIdx) state = 'active';
      if (state === 'pending' && stepIdx > platformIdx) state = 'done';
      li.dataset.state = state;
    });
  }

  function buildPercent(stepKey, progress) {
    if (stepKey === 'fetching_icon') return 12;
    if (stepKey === 'writing_shell') return 22;
    if (stepKey === 'uploading_cdn') return 94;
    if (stepKey === 'building_platforms') {
      const total = Number(progress && progress.total) || BUILD_PLATFORMS.length;
      const done = Math.min(Number(progress && progress.done) || 0, total);
      return 28 + Math.round((done / total) * 60);
    }
    return 4;
  }

  function updateBuildProgress(stage, progress) {
    if (!buildProgress) return;
    const stepKey = BUILD_STAGE_STEP[stage] || 'fetching_icon';
    const statusMap = progress && progress.platform_status;
    if (statusMap && Object.keys(statusMap).length) lastPlatformStatus = { ...statusMap };
    setBuildStep(stepKey, false);
    setPlatformStates(stepKey);
    buildPercentShown = Math.max(buildPercentShown, buildPercent(stepKey, progress));
    if (buildProgressFill) buildProgressFill.style.width = `${buildPercentShown}%`;
    buildProgress.dataset.step = stepKey;
  }

  function startBuildProgress() {
    setBuildLocked(true);
    if (!buildProgress) return;
    lastPlatformStatus = {};
    lastAnnouncedStep = '';
    buildPercentShown = 0;
    buildProgress.classList.remove('hidden', 'is-failed');
    if (buildError) buildError.classList.add('hidden');
    if (buildErrorText) buildErrorText.textContent = '';
    if (buildProgressTitle) buildProgressTitle.textContent = t('build.title');
    buildStartedAt = Date.now();
    tickBuildClock();
    window.clearInterval(buildClock);
    buildClock = window.setInterval(tickBuildClock, 1000);
    updateBuildProgress('queued', null);
  }

  function finishBuildProgress() {
    stopBuildClock();
    setBuildLocked(false);
    if (buildProgress) buildProgress.classList.add('hidden');
  }

  function failBuildProgress(message) {
    stopBuildClock();
    setBuildLocked(false);
    if (!buildProgress) return;
    buildProgress.classList.remove('hidden');
    buildProgress.classList.add('is-failed');
    setBuildStep(buildProgress.dataset.step || 'queued', true);
    if (buildProgressTitle) buildProgressTitle.textContent = t('build.failedTitle');
    if (buildErrorText) buildErrorText.textContent = message || t('err.generateFailed');
    if (buildError) buildError.classList.remove('hidden');
    scheduleGentleScroll(buildProgress, { block: 'nearest', threshold: 0.3, delay: 60 });
  }

  function renderResultPlatforms(platformErrors) {
    if (!resultPlatforms) return;
    const errors = platformErrors || {};
    resultPlatforms.innerHTML = BUILD_PLATFORMS.map((p) => {
      const label = escapeHtml(PLATFORM_LABELS[p]);
      if (Object.prototype.hasOwnProperty.call(errors, p)) {
        return `<span class="platform-tag is-error" title="${escapeHtml(String(errors[p] || ''))}">${label} · ${escapeHtml(t('build.platformFailed'))}</span>`;
      }
      return `<span class="platform-tag is-ready">${label}</span>`;
    }).join('');
  }

  async function generateAppFromCurrentForm() {
    if (buildInFlight) throw new Error(t('build.busy'));
    startBuildProgress();
    try {
      const data = await runBuildRequest();
      renderResultPlatforms(data && data.platform_errors);
      finishBuildProgress();
      return data;
    } catch (err) {
      failBuildProgress(err && err.message);
      throw err;
    }
  }

  async function runBuildRequest() {
    const options = {};
    const versionName = sanitizeAndroidVersionName(androidVersionNameInput.value);
    const versionCode = sanitizeAndroidVersionCode(androidVersionCodeInput.value);
    const packagePrefix = sanitizeAndroidPackagePrefix(androidPackagePrefixInput.value);
    syncInputValue(androidVersionNameInput, versionName);
    syncInputValue(androidVersionCodeInput, versionCode ? String(versionCode) : '');
    syncInputValue(androidPackagePrefixInput, packagePrefix);
    options['android-version-name'] = versionName;
    if (versionCode) options['android-version-code'] = versionCode;
    options['android-package-prefix'] = packagePrefix;
    if (customIconDataUrl) options['custom-icon-data-url'] = customIconDataUrl;
    Object.assign(options, collectFeatureOptions());
    if (selectedTags.size > 0) options['tags'] = Array.from(selectedTags);
    options['visibility'] = currentVisibility;
    options['language'] = primaryLanguage;
    options['languages'] = currentLanguages();
    const appDesc = (appDescInput.value || '').trim();
    if (appDesc) options['description'] = appDesc;
    options['about-text'] = aboutTextInput.value || '';
    if (aboutImageDataUrls !== null) options['about-images'] = aboutImageDataUrls;

    let submitRes;
    if (inputMode === 'html') {
      if (!htmlFile) throw new Error(t('err.htmlNoFile'));
      const form = new FormData();
      form.append('file', htmlFile, htmlFile.name);
      form.append('name', appNameInput.value);
      form.append('color', appColorInput.value);
      form.append('display', 'fullscreen');
      form.append('orientation', 'any');
      form.append('options', JSON.stringify(options));
      submitRes = await fetch('/api/distill/html', {
        method: 'POST',
        headers: apiUploadHeaders(),
        body: form,
      });
    } else {
      submitRes = await fetch('/api/distill', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({
          url: currentUrl,
          name: appNameInput.value,
          color: appColorInput.value,
          display: 'fullscreen',
          orientation: 'any',
          options: options,
        }),
      });
    }
    if (!submitRes.ok) {
      const err = await submitRes.json().catch(() => null);
      throw new Error(apiErrorMessage(err && err.detail, 'err.generateFailed'));
    }
    const task = await submitRes.json();
    if (!task.task_id) throw new Error(t('err.taskSubmitFailed'));

    updateBuildProgress('queued', null);
    let data = null;
    {
      let attempts = 0;
      let transientFailures = 0;
      const MAX_TRANSIENT_FAILURES = 5;
      while (attempts < 240) {
        attempts += 1;
        await sleep(attempts <= 8 ? 400 : 800 + transientFailures * 600);
        let pollRes;
        try {
          pollRes = await fetch(`/api/distill/${encodeURIComponent(task.task_id)}`, {
            headers: apiHeaders(),
          });
        } catch (_err) {
          transientFailures += 1;
          if (transientFailures >= MAX_TRANSIENT_FAILURES) throw new Error(t('analysis.failed.network'));
          continue;
        }
        if (pollRes.status === 502 || pollRes.status === 503 || pollRes.status === 504) {
          transientFailures += 1;
          if (transientFailures >= MAX_TRANSIENT_FAILURES) throw new Error(t('err.generateFailed'));
          continue;
        }
        transientFailures = 0;
        if (pollRes.status === 404) throw new Error(t('err.taskMissing'));
        if (!pollRes.ok) {
          let message = '';
          try {
            const err = await pollRes.json();
            message = apiErrorMessage(err && err.detail, 'err.generateFailed');
          } catch (_err) {}
          throw new Error(message || t('err.generateFailed'));
        }
        const payload = await pollRes.json();
        if (payload && payload.status && payload.task_id) {
          updateBuildProgress(payload.stage || payload.status, payload.progress);
          continue;
        }
        data = payload;
        break;
      }
    }
    if (!data) throw new Error(t('err.generateTimeout'));

    if (data.app_id && data.edit_token) { editTokens[data.app_id] = data.edit_token; saveEditTokens(); }
    const installLink = `${location.origin}${data.url}`;
    appLink.value = installLink;
    previewUrl.textContent = installLink;
    previewFrame.src = installLink;
    previewOpenBtn.dataset.href = installLink;
    resultPanel.classList.remove('hidden');
    const androidMeta = data.android || {};
    let note = document.getElementById('android-fallback-note');
    if (!note) {
      note = document.createElement('p');
      note.id = 'android-fallback-note';
      note.className = 'result-note';
      if (resultPanel) resultPanel.appendChild(note);
    }
    if (androidMeta.fallback && !androidMeta.apk) {
      note.textContent = t('result.androidFallback');
      note.classList.remove('hidden');
    } else {
      note.textContent = '';
      note.classList.add('hidden');
    }
    let solidNote = document.getElementById('solid-icon-note');
    if (!solidNote) {
      solidNote = document.createElement('p');
      solidNote.id = 'solid-icon-note';
      solidNote.className = 'result-note';
      if (resultPanel) resultPanel.appendChild(solidNote);
    }
    if (data.icon_rejected === 'solid') {
      solidNote.textContent = t('result.solidIcon');
      solidNote.classList.remove('hidden');
    } else {
      solidNote.textContent = '';
      solidNote.classList.add('hidden');
    }
    await loadHistory();
    scheduleGentleScroll(resultPanel, { block: 'nearest', threshold: 0.45, delay: 180 });
    return data;
  }

  // --- Color picker sync ---
  appColorInput.addEventListener('input', () => { colorHex.textContent = appColorInput.value; });
  ['wheel', 'touchstart', 'pointerdown', 'keydown'].forEach((eventName) => {
    window.addEventListener(eventName, cancelPendingAutoScroll, { passive: true });
  });
  customIconInput.addEventListener('change', async () => {
    const file = customIconInput.files && customIconInput.files[0];
    if (!file) return;
    try {
      customIconDataUrl = await readFileAsDataUrl(file);
      if (customIconFileName) customIconFileName.textContent = file.name;
      customIconPreview.src = customIconDataUrl;
      customIconPreview.parentElement.classList.add('has-image');
      customIconPlaceholder.textContent = file.name;
      syncRestoreIconButton();
    } catch (_err) {
      customIconDataUrl = '';
      customIconInput.value = '';
      if (customIconFileName) customIconFileName.textContent = t('icon.readFailed');
      customIconPreview.removeAttribute('src');
      customIconPreview.parentElement.classList.remove('has-image');
      customIconPlaceholder.textContent = t('icon.readFailed');
      syncRestoreIconButton();
    }
  });
  customIconClearBtn.addEventListener('click', () => {
    if (restoreIconDataUrl) {
      fillIconPreview(restoreIconDataUrl, restoreIconLabel || t('icon.recovered'));
      if (customIconFileName) customIconFileName.textContent = restoreIconFileName || t('icon.recovered');
      syncRestoreIconButton();
      return;
    }
    fillIconPreview('', '');
    syncRestoreIconButton();
  });
  androidVersionNameInput.addEventListener('blur', () => {
    androidVersionNameInput.value = sanitizeAndroidVersionName(androidVersionNameInput.value);
  });
  androidVersionCodeInput.addEventListener('blur', () => {
    const sanitized = sanitizeAndroidVersionCode(androidVersionCodeInput.value);
    androidVersionCodeInput.value = sanitized ? String(sanitized) : '';
  });
  androidPackagePrefixInput.addEventListener('blur', () => {
    androidPackagePrefixInput.value = sanitizeAndroidPackagePrefix(androidPackagePrefixInput.value);
  });

  async function compressImageFile(file) {
    // Anything already under the cap goes through untouched; larger files
    // are downscaled through canvas until WebP q90 fits inside 800KB.
    const LIMIT = 800 * 1024;
    if (file.size <= LIMIT) return file;
    const bmp = await createImageBitmap(file);
    let scale = Math.min(1, 2048 / Math.max(bmp.width, bmp.height, 1));
    while (scale > 0.04) {
      const w = Math.max(1, Math.round(bmp.width * scale));
      const h = Math.max(1, Math.round(bmp.height * scale));
      const cv = document.createElement('canvas');
      cv.width = w;
      cv.height = h;
      cv.getContext('2d').drawImage(bmp, 0, 0, w, h);
      let q = 0.9;
      let blob = await new Promise((r) => cv.toBlob(r, 'image/webp', q));
      while (blob && blob.size > LIMIT && q > 0.55) {
        q -= 0.12;
        blob = await new Promise((r) => cv.toBlob(r, 'image/webp', q));
      }
      if (blob && blob.size <= LIMIT) return blob;
      scale *= 0.65;
    }
    return file;  // give up — the server-side pass will still re-encode
  }

  function renderAboutImagesPreview() {
    const list = aboutImageDataUrls || [];
    aboutImagesPreview.innerHTML = list
      .map((d) => `<img src="${d}" alt="" loading="lazy" decoding="async">`)
      .join('');
    aboutImagesName.textContent = list.length
      ? t('config.aboutImagesCount', { n: list.length })
      : t('config.noFileChosen');
  }

  aboutImagesInput.addEventListener('change', async () => {
    const files = Array.from(aboutImagesInput.files || []).slice(0, 3);
    aboutImageDataUrls = [];
    try {
      for (const file of files) {
        const blob = await compressImageFile(file);
        aboutImageDataUrls.push(await readFileAsDataUrl(blob));
      }
    } catch (_err) {
      aboutImageDataUrls = null;
      aboutImagesInput.value = '';
      aboutImagesName.textContent = t('icon.readFailed');
      return;
    }
    renderAboutImagesPreview();
  });
  aboutImagesClear.addEventListener('click', () => {
    aboutImageDataUrls = [];
    aboutImagesInput.value = '';
    renderAboutImagesPreview();
  });
  [windowsWidthInput, windowsHeightInput, linuxWidthInput, linuxHeightInput].forEach((input) => {
    input.addEventListener('blur', () => {
      const sanitized = sanitizeWindowSize(input.value);
      input.value = sanitized ? String(sanitized) : '';
    });
  });

  // --- URL Validation ---
  function isValidUrl(str) {
    try { const u = new URL(str.startsWith('http') ? str : 'https://' + str); return !!u.hostname.includes('.'); } catch { return false; }
  }

  function normalizeUrl(str) {
    return str.startsWith('http') ? str : 'https://' + str;
  }

  // --- Distill Flow ---
  distillBtn.addEventListener('click', () => {
    if (inputMode === 'html') {
      if (!htmlFile) {
        notify(t('err.htmlNoFile'), 'error');
        return;
      }
      scheduleGentleScroll(workspace, { block: 'start', threshold: 0.55, delay: 120 });
      return;
    }
    startDistill();
  });
  urlInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && inputMode === 'url') startDistill(); });
  modeUrlBtn.addEventListener('click', () => setInputMode('url'));
  modeHtmlBtn.addEventListener('click', () => setInputMode('html'));

  // --- Visibility + tags (build form) ---
  function setVisibility(value) {
    currentVisibility = value;
    visibilityPrivateBtn.classList.toggle('active', value === 'private');
    visibilityPublicBtn.classList.toggle('active', value === 'public');
  }

  function refreshTagChips() {
    tagsPicker.querySelectorAll('.tag-chip').forEach((chip) => {
      chip.classList.toggle('active', selectedTags.has(chip.dataset.tag));
    });
  }

  visibilityPrivateBtn.addEventListener('click', () => setVisibility('private'));
  visibilityPublicBtn.addEventListener('click', () => setVisibility('public'));

  tagsPicker.addEventListener('click', (event) => {
    const chip = event.target.closest('.tag-chip');
    if (!chip) return;
    const tag = chip.dataset.tag;
    if (selectedTags.has(tag)) selectedTags.delete(tag); else selectedTags.add(tag);
    refreshTagChips();
  });

  tagCustomInput.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    const value = event.target.value.trim().replace(/\s+/g, ' ').slice(0, 24);
    if (!value || selectedTags.has(value)) { event.target.value = ''; return; }
    if (selectedTags.size >= 5) return;
    selectedTags.add(value);
    event.target.value = '';
    if (!tagsPicker.querySelector(`.tag-chip[data-tag="${CSS.escape(value)}"]`)) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'tag-chip';
      btn.dataset.tag = value;
      btn.textContent = value;
      tagsPicker.querySelector('.tags-builtins').appendChild(btn);
    }
    refreshTagChips();
  });
  htmlFileInput.addEventListener('change', () => {
    const file = htmlFileInput.files && htmlFileInput.files[0];
    if (!file) return;
    selectHtmlFile(file);
  });
  ['dragover', 'dragenter'].forEach((eventName) => {
    htmlDropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      htmlDropzone.classList.add('dragover');
    });
  });
  ['dragleave', 'drop'].forEach((eventName) => {
    htmlDropzone.addEventListener(eventName, () => htmlDropzone.classList.remove('dragover'));
  });
  htmlDropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) selectHtmlFile(file);
  });

  async function selectHtmlFile(file) {
    htmlFile = file;
    htmlFileLabel.textContent = file.name;
    htmlFileHint.textContent = `${formatBytes(file.size)} · ${t('mode.htmlHint')}`;
    htmlDropzone.classList.add('has-file');
    await startHtmlAnalyze(file);
  }

  async function startHtmlAnalyze(file) {
    let data = null;
    let uploadError = null;
    try {
      const form = new FormData();
      form.append('file', file, file.name);
      const res = await fetch('/api/analyze/html', {
        method: 'POST',
        headers: apiUploadHeaders(),
        body: form,
      });
      if (res.ok) {
        data = await res.json();
      } else {
        const err = await res.json().catch(() => null);
        uploadError = apiErrorMessage(err && err.detail, 'err.generateFailed');
      }
    } catch (_err) {
      // Network failure: fall through to a local, file-name-only prefill.
    }
    if (uploadError) {
      notify(uploadError, 'error');
      resetHtmlFile();
      return;
    }
    if (!data) {
      data = {
        sourceType: 'html',
        name: file.name.replace(/\.(html?|zip)$/i, ''),
        color: '',
        iconDataUrl: '',
        fileCount: 0,
        totalBytes: file.size,
      };
    }
    workspace.classList.remove('hidden');
    resultPanel.classList.add('hidden');
    showHtmlAnalysisResults(data);
    scheduleGentleScroll(workspace, { block: 'start', threshold: 0.55, delay: 120 });
  }

  function showHtmlAnalysisResults(data) {
    analysisStatus.textContent = t('analysis.statusDone');
    analysisStatus.className = 'status-badge done';
    const suggestedName = String(data.name || '').trim()
      || (htmlFile ? htmlFile.name.replace(/\.(html?|zip)$/i, '') : '');
    if (suggestedName) {
      syncInputValue(appNameInput, suggestedName);
      updateAppNameSourceNote(data.name ? 'title_full' : '', suggestedName);
    }
    const themeColor = String(data.color || '').trim();
    if (/^#[0-9a-fA-F]{3,8}$/.test(themeColor)) {
      syncInputValue(appColorInput, themeColor);
      colorHex.textContent = themeColor.toUpperCase();
    }
    if (data.iconDataUrl) {
      detectedIconDataUrl = String(data.iconDataUrl);
      setRestoreIconState(detectedIconDataUrl, {
        label: t('icon.autoFetched'),
        fileName: t('icon.autoFetchedFile'),
        buttonLabel: t('icon.restoreAutoFetch'),
      });
      fillIconPreview(detectedIconDataUrl, t('icon.autoFetched'));
      if (customIconFileName) customIconFileName.textContent = t('icon.autoFetchedFile');
    } else {
      detectedIconDataUrl = '';
      setRestoreIconState('', {});
      fillIconPreview('', '');
    }
    analysisBody.innerHTML = `
      <div class="analysis-results">
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.suggestedName'))}</span><span class="value good">${escapeHtml(suggestedName || t('analysis.notSaved'))}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.iconStatus'))}</span><span class="value ${data.iconDataUrl ? 'good' : 'info'}">${escapeHtml(data.iconDataUrl ? t('analysis.iconAutoFetched') : t('analysis.iconNotDetected'))}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.htmlFiles'))}</span><span class="value info">${Number(data.fileCount || 0).toLocaleString(locale())}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.htmlTotalSize'))}</span><span class="value info">${escapeHtml(formatBytes(data.totalBytes || 0))}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.htmlSource'))}</span><span class="value info">${escapeHtml(t('analysis.htmlSourceValue'))}</span></div>
      </div>`;
  }

  let urlInvalidTimer = null;
  function clearUrlInvalid() {
    clearTimeout(urlInvalidTimer);
    urlInputWrap.classList.remove('is-invalid');
    urlInput.removeAttribute('aria-invalid');
  }
  function markUrlInvalid() {
    clearTimeout(urlInvalidTimer);
    urlInputWrap.classList.add('is-invalid');
    urlInput.setAttribute('aria-invalid', 'true');
    urlInput.focus();
    urlInvalidTimer = setTimeout(clearUrlInvalid, 2400);
  }
  urlInput.addEventListener('input', clearUrlInvalid);

  async function startDistill() {
    const raw = urlInput.value.trim();
    if (!raw || !isValidUrl(raw)) {
      markUrlInvalid();
      return;
    }

    const url = normalizeUrl(raw);
    currentUrl = url;
    workspace.classList.remove('hidden');
    resultPanel.classList.add('hidden');
    analysisStatus.textContent = t('analysis.statusAnalyzing');
    analysisStatus.className = 'status-badge';
    analysisBody.innerHTML = `<div class="analysis-loader"><div class="loader-bar"></div><p id="loader-text">${escapeHtml(t('analysis.fetching'))}</p></div>`;
    scheduleGentleScroll(workspace, { block: 'start', threshold: 0.55, delay: 120 });

    const steps = [
      t('analysis.stepFetch'),
      t('analysis.stepDom'),
      t('analysis.stepDesign'),
      t('analysis.stepOptimize'),
    ];
    let stepIndex = 0;
    const loaderTimer = setInterval(() => {
      const loader = document.getElementById('loader-text');
      if (!loader) return;
      loader.textContent = steps[Math.min(stepIndex, steps.length - 1)];
      stepIndex += 1;
    }, 450);

    let data;
    let failureReason = '';
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      if (res.ok) {
        data = await res.json();
      } else {
        const err = await res.json().catch(() => null);
        failureReason = apiErrorMessage(err && err.detail, 'analysis.failed.generic');
      }
    } catch (_err) {
      failureReason = t('analysis.failed.network');
    } finally {
      clearInterval(loaderTimer);
    }

    if (!data) {
      data = simulateAnalysis(url);
      data.analysisFailed = true;
      data.failureReason = failureReason || t('analysis.failed.generic');
    }
    showAnalysisResults(data);
  }

  function simulateAnalysis(url) {
    const host = new URL(url).hostname.replace('www.', '');
    const suggestedName = host.split('.')[0].charAt(0).toUpperCase() + host.split('.')[0].slice(1);
    return {
      title: suggestedName,
      suggestedName,
      suggestedNameSource: 'host_fallback',
      url: url,
      host: host,
      favicon: `https://www.google.com/s2/favicons?domain=${host}&sz=64`,
      faviconDataUrl: '',
      themeColor: '#7c3aed',
      // Analysis didn't run (fetch failed) — show N/A rather than fabricated
      // numbers. Previously this returned random ad/tracker counts, which
      // misled users about sites we never actually inspected.
      originalSize: 'N/A',
      distilledSize: 'N/A',
      speedBoost: 'N/A',
    };
  }

  function buildRecoveredAnalysisData(item) {
    const recipe = item && item.recipe && typeof item.recipe === 'object' ? item.recipe : {};
    const targetUrl = String(item.target_url || recipe.url || '').trim();
    let host = '';
    try {
      host = new URL(targetUrl).hostname.replace(/^www\./i, '');
    } catch (_err) {}
    const suggestedName = String(item.name || recipe.name || host || item.app_id || '').trim();
    const title = String(
      recipe.title
      || recipe.site_title
      || recipe.site_name
      || suggestedName
      || host
    ).trim();
    const suggestedNameSource = String(
      recipe.suggestedNameSource
      || recipe.suggested_name_source
      || recipe.name_source
      || ''
    ).trim();
    return {
      title,
      suggestedName,
      suggestedNameSource,
      host,
      targetUrl,
      hasIcon: !!item.icon_url || !!recipe.custom_icon_uploaded,
    };
  }

  function showRecoveredAnalysisResults(item) {
    const data = buildRecoveredAnalysisData(item || {});
    analysisStatus.textContent = t('analysis.statusRecovered');
    analysisStatus.className = 'status-badge done';
    analysisBody.innerHTML = `
      <div class="analysis-results">
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.siteTitle'))}</span><span class="value info">${escapeHtml(data.title || t('analysis.notSaved'))}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.suggestedName'))}</span><span class="value good">${escapeHtml(data.suggestedName || t('analysis.notSaved'))}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.nameSource'))}</span><span class="value info">${escapeHtml(data.suggestedNameSource ? nameSourceLabel(data.suggestedNameSource) : t('analysis.fromHistory'))}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.iconStatus'))}</span><span class="value ${data.hasIcon ? 'good' : 'info'}">${escapeHtml(data.hasIcon ? t('analysis.iconRecovered') : t('analysis.iconNotSaved'))}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.targetUrl'))}</span><span class="value info">${escapeHtml(data.targetUrl || data.host || t('analysis.notSaved'))}</span></div>
      </div>
      <div class="analysis-actions">
        <button id="reanalyze-btn" class="btn-secondary" type="button">${escapeHtml(t('analysis.reanalyze'))}</button>
      </div>`;
    const reanalyzeBtn = document.getElementById('reanalyze-btn');
    if (reanalyzeBtn) {
      reanalyzeBtn.addEventListener('click', async () => {
        reanalyzeBtn.disabled = true;
        reanalyzeBtn.textContent = t('analysis.reanalyzing');
        try {
          await startDistill();
        } finally {
          reanalyzeBtn.disabled = false;
          reanalyzeBtn.textContent = t('analysis.reanalyze');
        }
      });
    }
  }

  function showAnalysisResults(data) {
    analysisStatus.textContent = data.analysisFailed ? t('analysis.statusFailed') : t('analysis.statusDone');
    analysisStatus.className = data.analysisFailed ? 'status-badge warn' : 'status-badge done';
    const title = String(data.title || data.host || '').trim();
    const suggestedName = String(data.suggestedName || data.siteName || data.title || data.host || '').trim();
    const suggestedNameSource = String(data.suggestedNameSource || '').trim();
    const suggestedNameSourceLabel = nameSourceLabel(suggestedNameSource);
    const themeColor = String(data.themeColor || '#7c3aed').trim() || '#7c3aed';
    syncInputValue(appNameInput, suggestedName);
    updateAppNameSourceNote(suggestedNameSource, suggestedName);
    syncInputValue(appColorInput, themeColor);
    colorHex.textContent = themeColor.toUpperCase();
    if (data.faviconDataUrl) {
      detectedIconDataUrl = String(data.faviconDataUrl);
      setRestoreIconState(detectedIconDataUrl, {
        label: t('icon.autoFetched'),
        fileName: t('icon.autoFetchedFile'),
        buttonLabel: t('icon.restoreAutoFetch'),
      });
      fillIconPreview(String(data.faviconDataUrl), t('icon.autoFetched'));
      if (customIconFileName) customIconFileName.textContent = t('icon.autoFetchedFile');
    } else {
      detectedIconDataUrl = '';
      setRestoreIconState('', {});
      fillIconPreview('', '');
    }

    if (data.analysisFailed) {
      analysisBody.innerHTML = `
        <div class="analysis-results">
          <div class="analysis-item analysis-notice">
            <span class="value warn">${escapeHtml(data.failureReason)}</span>
          </div>
          <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.suggestedName'))}</span><span class="value info">${escapeHtml(suggestedName)}</span></div>
          <div class="analysis-item analysis-hint">
            <span class="value info">${escapeHtml(t('analysis.failed.hint'))}</span>
          </div>
        </div>`;
      return;
    }

    if (data.authProtected) {
      // Site sits behind an auth proxy (Authelia / Cloudflare Access). The
      // server can't see the real page, so don't show the usual (empty)
      // ad/tracker stats — show an explanatory notice and point the user at
      // the manual name/icon fields. The generated app itself is unaffected:
      // the user authenticates inside the WebView on first launch.
      const providerLabel = data.authProvider === 'cloudflare_access'
        ? t('analysis.authProvider.cloudflare')
        : t('analysis.authProvider.authelia');
      analysisBody.innerHTML = `
        <div class="analysis-results">
          <div class="analysis-item analysis-notice">
            <span class="value warn">${escapeHtml(t('analysis.authProtected.notice', { provider: providerLabel }))}</span>
          </div>
          <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.suggestedName'))}</span><span class="value good">${escapeHtml(suggestedName)}</span></div>
          <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.nameSource'))}</span><span class="value info">${escapeHtml(suggestedNameSourceLabel)}</span></div>
          <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.iconStatus'))}</span><span class="value info">${escapeHtml(t('analysis.authProtected.iconHint'))}</span></div>
          <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.originalSize'))}</span><span class="value">${escapeHtml(String(data.originalSize))}</span></div>
          <div class="analysis-item analysis-hint">
            <span class="value info">${escapeHtml(t('analysis.authProtected.appWorks'))}</span>
          </div>
        </div>`;
      return;
    }

    analysisBody.innerHTML = `
      <div class="analysis-results">
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.siteTitle'))}</span><span class="value info">${escapeHtml(title)}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.suggestedName'))}</span><span class="value good">${escapeHtml(suggestedName)}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.nameSource'))}</span><span class="value info">${escapeHtml(suggestedNameSourceLabel)}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.iconStatus'))}</span><span class="value ${data.faviconDataUrl ? 'good' : 'info'}">${escapeHtml(data.faviconDataUrl ? t('analysis.iconAutoFetched') : t('analysis.iconNotDetected'))}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.originalSize'))}</span><span class="value">${escapeHtml(String(data.originalSize))}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.distilledSize'))}</span><span class="value good">${escapeHtml(String(data.distilledSize))}</span></div>
        <div class="analysis-item"><span class="label">${escapeHtml(t('analysis.speedBoost'))}</span><span class="value good">${escapeHtml(String(data.speedBoost))}</span></div>
      </div>`;
  }

  // --- Generate App ---

  async function handleGenerateClick() {
    if (buildInFlight) return;
    if (selectedTags.size === 0) {
      notify(t('err.tagsRequired'), 'error');
      tagsPicker.scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }
    if (!hasValidLanguages()) {
      notify(t('err.languageRequired'), 'error');
      if (languagePicker) languagePicker.scrollIntoView({ block: 'center', behavior: 'smooth' });
      return;
    }
    try {
      await generateAppFromCurrentForm();
    } catch (_err) {
      // failBuildProgress() already shows the error inline with a retry button.
    }
  }

  generateBtn.addEventListener('click', handleGenerateClick);
  if (buildRetryBtn) buildRetryBtn.addEventListener('click', handleGenerateClick);

  syncRestoreIconButton();

  // --- Copy Link ---
  copyBtn.addEventListener('click', () => {
    copyPlainText(appLink.value)
      .then(() => flashLabel(copyBtn, t('result.copied'), 2000))
      .catch(() => {
        appLink.focus();
        appLink.select();
        notify(t('err.copyManual'), 'error');
      });
  });

  previewOpenBtn.addEventListener('click', () => {
    const href = previewOpenBtn.dataset.href;
    if (!href) return;
    window.open(href, '_blank', 'noopener,noreferrer');
  });

  function closeRowMenus(except) {
    historyList.querySelectorAll('.row-menu').forEach((menu) => {
      if (menu === except) return;
      menu.classList.add('hidden');
      const btn = menu.parentElement.querySelector('[data-row-menu]');
      if (btn) btn.setAttribute('aria-expanded', 'false');
    });
  }

  historyList.addEventListener('click', async (event) => {
    const row = event.target.closest('.app-row');
    const item = row && row._historyItem;
    if (historySelectMode) {
      const id = (item && item.app_id) || '';
      if (!id) return;
      const box = event.target.closest('input[data-select]');
      if (box) {
        if (box.checked) historySelected.add(id); else historySelected.delete(id);
      } else if (historySelected.has(id)) {
        historySelected.delete(id);
      } else {
        historySelected.add(id);
      }
      renderHistory(lastHistoryItems);
      return;
    }

    const menuBtn = event.target.closest('[data-row-menu]');
    if (menuBtn && row) {
      const menu = row.querySelector('.row-menu');
      const willOpen = menu.classList.contains('hidden');
      closeRowMenus(willOpen ? menu : null);
      menu.classList.toggle('hidden', !willOpen);
      menu.classList.remove('is-up');
      if (willOpen && menu.getBoundingClientRect().bottom > window.innerHeight - 8) {
        menu.classList.add('is-up');
      }
      menuBtn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      return;
    }

    const expandEl = event.target.closest('[data-expand]');
    if (expandEl && row) {
      const detail = row.querySelector('.app-row-detail');
      const willOpen = detail.hasAttribute('hidden');
      detail.toggleAttribute('hidden', !willOpen);
      row.classList.toggle('is-expanded', willOpen);
      expandEl.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      return;
    }

    const target = event.target.closest('[data-open], [data-copy], [data-edit], [data-regenerate], [data-visibility-toggle], [data-delete]');
    if (!target) {
      closeRowMenus();
      return;
    }
    closeRowMenus();

    if (target.dataset.delete) {
      const appId = target.dataset.delete;
      const name = (item && (item.name || item.app_id)) || appId;
      if (!(await ask(t('history.confirmDelete', { name }), { danger: true }))) return;
      try {
        target.disabled = true;
        const res = await fetch(`/api/history/${encodeURIComponent(appId)}`, {
          method: 'DELETE',
          headers: { 'X-Device-Fingerprint': deviceFingerprint },
        });
        if (!res.ok) throw new Error('delete failed');
        const data = await res.json();
        delete editTokens[appId];
        saveEditTokens();
        renderHistory((data.history && data.history.items) || []);
        loadMarket();
        notify(t('history.deleted'), 'success');
      } catch (_err) {
        notify(t('err.removeRetry'), 'error');
      } finally {
        target.disabled = false;
      }
      return;
    }
    if (target.dataset.visibilityToggle) {
      const appId = target.dataset.visibilityToggle;
      const current = item && item.visibility === 'public' ? 'public' : 'private';
      const next = current === 'public' ? 'private' : 'public';
      try {
        target.disabled = true;
        const res = await fetch(`/api/history/${encodeURIComponent(appId)}/visibility`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Device-Fingerprint': deviceFingerprint },
          body: JSON.stringify({ visibility: next, edit_token: editTokens[appId] || '' }),
        });
        if (!res.ok) {
          const detail = await res.json().catch(() => ({}));
          const code = typeof detail.detail === 'string' ? detail.detail : '';
          if (res.status === 409 && code === 'duplicate_public_app') {
            throw new Error(t('err.duplicatePublic'));
          }
          if (res.status === 409 && code === 'icon_review_expired') {
            throw new Error(t('err.iconReviewExpired'));
          }
          throw new Error(code || 'visibility failed');
        }
        const data = await res.json();
        renderHistory((data.history && data.history.items) || []);
        loadMarket();
      } catch (err) {
        notify(err.message || t('err.visibilityRetry'), 'error');
      } finally {
        target.disabled = false;
      }
      return;
    }
    if (target.dataset.open) {
      window.open(target.dataset.open, '_blank', 'noopener,noreferrer');
      return;
    }
    if (target.dataset.edit) {
      if (!item) return;
      await applyHistoryItemToForm(item);
      scheduleGentleScroll(workspace, { block: 'start', threshold: 0.55, delay: 80 });
      return;
    }
    if (target.dataset.regenerate) {
      if (!item) return;
      if (buildInFlight) {
        notify(t('build.busy'), 'info');
        return;
      }
      try {
        target.disabled = true;
        target.textContent = t('history.regenerating');
        await applyHistoryItemToForm(item);
        if (buildProgress) scheduleGentleScroll(buildProgress, { block: 'center', threshold: 0.55, delay: 80 });
        await generateAppFromCurrentForm();
      } catch (_err) {
        notify(t('err.regenerateRetry'), 'error');
      } finally {
        target.disabled = false;
        target.textContent = t('history.regenerate');
      }
      return;
    }
    if (target.dataset.copy) {
      try {
        await copyPlainText(target.dataset.copy);
        flashLabel(target, t('history.copied'), 1600);
      } catch (_err) {
        notify(t('err.copyManual'), 'error');
      }
      return;
    }
  });

  historyList.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const expandEl = event.target.closest('[data-expand]');
    if (!expandEl) return;
    event.preventDefault();
    expandEl.click();
  });

  document.addEventListener('click', (event) => {
    if (event.target.closest('.row-menu') || event.target.closest('[data-row-menu]')) return;
    closeRowMenus();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    closeRowMenus();
    if (historyMorePanel && !historyMorePanel.classList.contains('hidden')) {
      historyMorePanel.classList.add('hidden');
      historyMoreBtn.setAttribute('aria-expanded', 'false');
      historyMoreBtn.focus();
    }
  });

  const historySearchInput = document.getElementById('history-search');
  const historySortSelect = document.getElementById('history-sort');
  const historyMoreBtn = document.getElementById('history-more-btn');
  const historyMorePanel = document.getElementById('history-more-panel');

  if (historySearchInput) {
    historySearchInput.addEventListener('input', () => {
      historyQuery = historySearchInput.value;
      renderHistory(lastHistoryItems);
    });
  }
  if (historySortSelect) {
    historySortSelect.addEventListener('change', () => {
      historySort = historySortSelect.value || 'newest';
      renderHistory(lastHistoryItems);
    });
  }
  if (historyMoreBtn && historyMorePanel) {
    historyMoreBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      const willOpen = historyMorePanel.classList.contains('hidden');
      historyMorePanel.classList.toggle('hidden', !willOpen);
      historyMoreBtn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    });
    document.addEventListener('click', (event) => {
      if (historyMorePanel.classList.contains('hidden')) return;
      if (historyMorePanel.contains(event.target) || historyMoreBtn.contains(event.target)) return;
      historyMorePanel.classList.add('hidden');
      historyMoreBtn.setAttribute('aria-expanded', 'false');
    });
  }

  function updateHistorySelectBar() {
    const visible = visibleHistoryItems();
    historySelectCount.textContent = t('history.selectedCount', { n: String(historySelected.size) });
    historyDeleteSelectedBtn.disabled = historySelected.size === 0;
    historySelectAll.checked = visible.length > 0
      && visible.every((entry) => historySelected.has(entry.app_id || ''));
    historySelectAll.indeterminate = historySelected.size > 0 && !historySelectAll.checked;
  }

  function updateHistoryToggle(total) {
    // While searching every match is rendered, so "show all" would lie.
    const show = total > HISTORY_PREVIEW_COUNT && !historySelectMode && !historyQuery.trim();
    historyToggleBtn.classList.toggle('hidden', !show);
    historyToggleBtn.textContent = historyExpanded
      ? t('history.showLess')
      : t('history.showAll', { n: String(total) });
  }

  historyToggleBtn.addEventListener('click', () => {
    historyExpanded = !historyExpanded;
    renderHistory(lastHistoryItems);
  });

  function setHistorySelectMode(on) {
    historySelectMode = on;
    if (!on) historySelected.clear();
    historySelectBar.classList.toggle('hidden', !on);
    historyManageBtn.classList.toggle('hidden', on);
    historyExportBtn.classList.toggle('hidden', on);
    historyImportBtn.classList.toggle('hidden', on);
    if (historyMoreBtn) {
      historyMoreBtn.classList.toggle('hidden', on);
      if (on && historyMorePanel) {
        historyMorePanel.classList.add('hidden');
        historyMoreBtn.setAttribute('aria-expanded', 'false');
      }
    }
    renderHistory(lastHistoryItems);
  }

  historyManageBtn.addEventListener('click', () => setHistorySelectMode(true));
  historyCancelSelectBtn.addEventListener('click', () => setHistorySelectMode(false));

  historySelectAll.addEventListener('change', () => {
    const visible = visibleHistoryItems();
    historySelected.clear();
    if (historySelectAll.checked) {
      visible.forEach((entry) => historySelected.add(entry.app_id || ''));
    }
    renderHistory(lastHistoryItems);
  });

  historyDeleteSelectedBtn.addEventListener('click', async () => {
    const ids = Array.from(historySelected);
    if (!ids.length) return;
    if (!(await ask(t('history.confirmDeleteBulk', { n: String(ids.length) }), { danger: true }))) return;
    try {
      historyDeleteSelectedBtn.disabled = true;
      const res = await fetch('/api/history/delete-bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Device-Fingerprint': deviceFingerprint },
        body: JSON.stringify({ app_ids: ids }),
      });
      if (!res.ok) throw new Error('bulk delete failed');
      setHistorySelectMode(false);
      await loadHistory();
      loadMarket();
    } catch (_err) {
      notify(t('err.removeRetry'), 'error');
    } finally {
      historyDeleteSelectedBtn.disabled = false;
    }
  });

  historyExportBtn.addEventListener('click', async () => {
    try {
      const res = await fetch('/api/history/export', {
        headers: { 'X-Device-Fingerprint': deviceFingerprint },
      });
      if (!res.ok) throw new Error('export failed');
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const href = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = href;
      link.download = `webtoapp-history-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(href);
    } catch (_err) {
      notify(t('err.exportRetry'), 'error');
    }
  });

  historyImportBtn.addEventListener('click', () => {
    historyImportInput.click();
  });

  historyImportInput.addEventListener('change', async () => {
    const file = historyImportInput.files && historyImportInput.files[0];
    if (!file) return;
    try {
      const text = await file.text();
      const payload = JSON.parse(text);
      const res = await fetch('/api/history/import', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('import failed');
      const data = await res.json();
      renderHistory((data.history && data.history.items) || []);
      notify(t('history.importDone', { imported: data.imported, restored: data.restored }), 'success');
    } catch (_err) {
      notify(t('err.importFormat'), 'error');
    } finally {
      historyImportInput.value = '';
    }
  });

  // --- Recipe Cards ---
  document.querySelectorAll('.recipe-card').forEach(card => {
    card.addEventListener('click', () => {
      const url = card.dataset.url;
      if (url) {
        urlInput.value = url;
        cancelPendingAutoScroll();
        if (window.scrollY > 120) {
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
        setTimeout(startDistill, 500);
      }
    });
  });

  // --- Nav scroll effect ---
  const nav = document.getElementById('nav');
  let navScrolled = null;
  let navTicking = false;
  function syncNavScrolled() {
    navTicking = false;
    const scrolled = window.scrollY > 50;
    if (scrolled === navScrolled) return;
    navScrolled = scrolled;
    nav.classList.toggle('is-scrolled', scrolled);
  }
  window.addEventListener('scroll', () => {
    if (navTicking) return;
    navTicking = true;
    window.requestAnimationFrame(syncNavScrolled);
  }, { passive: true });
  syncNavScrolled();

  // --- Util ---
  function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(reader.error || new Error('file read failed'));
      reader.readAsDataURL(file);
    });
  }

  // --- Language switcher ---
  (function initLanguageSwitcher() {
    const select = document.getElementById('lang-select');
    if (!select || !window.I18n) return;
    window.I18n.supported.forEach((lang) => {
      const opt = document.createElement('option');
      opt.value = lang;
      opt.textContent = window.I18n.nativeNames[lang] || lang;
      select.appendChild(opt);
    });
    select.value = window.I18n.current;
    select.addEventListener('change', () => {
      window.I18n.setLanguage(select.value);
    });
    // Re-render dynamic (JS-generated) content whenever the language changes.
    window.addEventListener('i18n:changed', () => {
      select.value = window.I18n.current;
      if (lastHistoryItems.length) renderHistory(lastHistoryItems);
      if (lastMarketItems.length) renderMarket(lastMarketItems);
      if (!profileModal.classList.contains('hidden')) {
        openProfile(profileViewingSelf ? null : profileViewedNum);
      }
    });
  })();

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

})();

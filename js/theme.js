(function () {
  'use strict';

  const key = 'webtoapp-theme';
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
  const root = document.documentElement;
  const themeColor = document.querySelector('meta[name="theme-color"]');
  const lightColor = themeColor?.content;
  const labels = {
    en: { appearance: 'Appearance', system: 'System', light: 'Light', dark: 'Dark' },
    zh: { appearance: '外观', system: '跟随系统', light: '浅色', dark: '深色' },
    ja: { appearance: '外観', system: 'システムに合わせる', light: 'ライト', dark: 'ダーク' },
    ko: { appearance: '화면 모드', system: '시스템 설정', light: '라이트', dark: '다크' },
    ar: { appearance: 'المظهر', system: 'حسب النظام', light: 'فاتح', dark: 'داكن' },
    ru: { appearance: 'Оформление', system: 'Как в системе', light: 'Светлое', dark: 'Тёмное' },
    es: { appearance: 'Apariencia', system: 'Sistema', light: 'Claro', dark: 'Oscuro' },
    pt: { appearance: 'Aparência', system: 'Sistema', light: 'Claro', dark: 'Escuro' },
    fr: { appearance: 'Apparence', system: 'Système', light: 'Clair', dark: 'Sombre' },
    de: { appearance: 'Darstellung', system: 'System', light: 'Hell', dark: 'Dunkel' },
  };
  let preference = 'system';
  let picker;

  function syncPicker() {
    if (!picker) return;
    const lang = root.lang.toLowerCase().split('-')[0];
    const text = labels[lang] || labels.en;
    const trigger = picker.querySelector('summary');
    trigger.setAttribute('aria-label', text.appearance);
    trigger.title = text.appearance;
    picker.querySelector('.theme-options').setAttribute('aria-label', text.appearance);
    picker.querySelectorAll('[data-theme-choice]').forEach((button) => {
      const choice = button.dataset.themeChoice;
      button.textContent = text[choice];
      button.setAttribute('aria-pressed', String(choice === preference));
    });
  }

  function applyTheme() {
    const dark = preference === 'dark' || (preference === 'system' && systemTheme.matches);
    root.dataset.theme = dark ? 'dark' : 'light';
    if (themeColor) themeColor.content = dark ? '#14181e' : lightColor;
    syncPicker();
  }

  function readPreference() {
    try {
      const stored = localStorage.getItem(key);
      preference = stored === 'light' || stored === 'dark' ? stored : 'system';
    } catch (_error) {}
    applyTheme();
  }

  readPreference();
  if (typeof systemTheme.addEventListener === 'function') systemTheme.addEventListener('change', applyTheme);
  else systemTheme.addListener(applyTheme);
  window.addEventListener('storage', (event) => {
    if (event.key === key || event.key === null) readPreference();
  });
  window.addEventListener('pageshow', readPreference);
  window.addEventListener('i18n:changed', syncPicker);

  document.addEventListener('DOMContentLoaded', () => {
    picker = document.querySelector('.theme-picker');
    if (!picker) return;
    const trigger = picker.querySelector('summary');
    syncPicker();
    picker.hidden = false;

    picker.addEventListener('click', (event) => {
      const choice = event.target.closest('[data-theme-choice]');
      if (!choice) return;
      preference = choice.dataset.themeChoice;
      try { localStorage.setItem(key, preference); } catch (_error) {}
      applyTheme();
      picker.open = false;
      trigger.focus();
    });
    document.addEventListener('click', (event) => {
      if (picker.open && !picker.contains(event.target)) picker.open = false;
    });
    picker.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape' || !picker.open) return;
      picker.open = false;
      trigger.focus();
    });
  });
})();

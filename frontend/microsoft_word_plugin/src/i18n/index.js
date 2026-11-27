import { ref } from 'vue';
import { I18N_KEY, LANGUAGE_STORAGE_KEY, normalizeLocale, resolveTranslation } from '../../../shared/js/i18n.mjs';

let storedLocale = '';
try {
  storedLocale = window.localStorage.getItem(LANGUAGE_STORAGE_KEY) || '';
} catch (_) {
  storedLocale = '';
}

export const locale = ref(normalizeLocale(storedLocale));

export function setLocale(value) {
  const nextLocale = normalizeLocale(value);
  locale.value = nextLocale;
  document.documentElement.lang = nextLocale;
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLocale);
  } catch (_) {
    // Some Office hosts can disable localStorage; backend settings remain the fallback.
  }
}

export function t(key, params = {}) {
  const template = resolveTranslation(locale.value, key);
  return Object.entries(params).reduce(
    (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
    String(template)
  );
}

export const i18n = {
  install(app) {
    app.config.globalProperties.$t = t;
    const translations = { locale, setLocale, t };
    app.provide('i18n', translations);
    app.provide(I18N_KEY, translations);
    setLocale(locale.value);
  }
};

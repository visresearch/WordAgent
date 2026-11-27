import { ref } from 'vue';
import { I18N_KEY, LANGUAGE_STORAGE_KEY, normalizeLocale, resolveTranslation, useI18n as useSharedI18n } from '../../../shared/js/i18n.mjs';

function initialLocale() {
  try {
    const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (stored) {
      return normalizeLocale(stored);
    }
  } catch (error) {
    console.warn('[i18n] Unable to read the stored language:', error);
  }
  return normalizeLocale(navigator.language || 'zh-CN');
}

export const locale = ref(initialLocale());

export function t(key, params = {}) {
  const value = resolveTranslation(locale.value, key);
  return String(value).replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? `{${name}}`));
}

export function setLocale(value) {
  const nextLocale = normalizeLocale(value);
  locale.value = nextLocale;
  document.documentElement.lang = nextLocale;
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLocale);
  } catch (error) {
    console.warn('[i18n] Unable to store the selected language:', error);
  }
}

export function useI18n() {
  return useSharedI18n({ locale, setLocale, t });
}

export const i18n = {
  install(app) {
    app.config.globalProperties.$t = t;
    app.provide(I18N_KEY, { locale, setLocale, t });
    setLocale(locale.value);
  }
};

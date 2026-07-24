import { ref } from 'vue';
import enUS from '../locales/en-US.js';
import zhCN from '../locales/zh-CN.js';

const STORAGE_KEY = 'wence-interface-language';
const messages = { 'zh-CN': zhCN, 'en-US': enUS };

function normalizeLocale(value) {
  return value === 'en-US' ? 'en-US' : 'zh-CN';
}

let storedLocale = '';
try {
  storedLocale = window.localStorage.getItem(STORAGE_KEY) || '';
} catch (_) {
  storedLocale = '';
}

export const locale = ref(normalizeLocale(storedLocale));

export function setLocale(value) {
  const nextLocale = normalizeLocale(value);
  locale.value = nextLocale;
  document.documentElement.lang = nextLocale;
  try {
    window.localStorage.setItem(STORAGE_KEY, nextLocale);
  } catch (_) {
    // Some Office hosts can disable localStorage; backend settings remain the fallback.
  }
}

export function t(key, params = {}) {
  const resolve = (source) => key.split('.').reduce((value, part) => value?.[part], source);
  const template = resolve(messages[locale.value]) ?? resolve(messages['zh-CN']) ?? key;
  return Object.entries(params).reduce(
    (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
    String(template)
  );
}

export const i18n = {
  install(app) {
    app.config.globalProperties.$t = t;
    app.provide('i18n', { locale, setLocale, t });
    setLocale(locale.value);
  }
};

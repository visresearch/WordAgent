import { inject, ref } from 'vue';
import enUS from '../locales/en-US.js';
import zhCN from '../locales/zh-CN.js';

const STORAGE_KEY = 'wence-interface-language';
const messages = { 'en-US': enUS, 'zh-CN': zhCN };
const I18N_KEY = Symbol('wence-i18n');

function normalizeLocale(value) {
  return String(value || '').toLowerCase().startsWith('en') ? 'en-US' : 'zh-CN';
}

function initialLocale() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return normalizeLocale(stored);
  } catch (error) {
    console.warn('[i18n] Unable to read the stored language:', error);
  }
  return normalizeLocale(navigator.language || 'zh-CN');
}

export const locale = ref(initialLocale());

function resolveMessage(source, key) {
  return key.split('.').reduce((value, part) => value?.[part], source);
}

export function t(key, params = {}) {
  const value = resolveMessage(messages[locale.value], key)
    ?? resolveMessage(messages['zh-CN'], key)
    ?? key;
  return String(value).replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? `{${name}}`));
}

export function setLocale(value) {
  const nextLocale = normalizeLocale(value);
  locale.value = nextLocale;
  document.documentElement.lang = nextLocale;
  try {
    localStorage.setItem(STORAGE_KEY, nextLocale);
  } catch (error) {
    console.warn('[i18n] Unable to store the selected language:', error);
  }
}

export function useI18n() {
  return inject(I18N_KEY, { locale, setLocale, t });
}

export const i18n = {
  install(app) {
    app.config.globalProperties.$t = t;
    app.provide(I18N_KEY, { locale, setLocale, t });
    setLocale(locale.value);
  }
};

import { inject, ref } from 'vue';
import enUS from '../locales/en-US.js';
import idID from '../locales/id-ID.js';
import zhCN from '../locales/zh-CN.js';
import jaJP from '../locales/ja-JP.js';
import koKR from '../locales/ko-KR.js';
import viVN from '../locales/vi-VN.js';
import pluginLocales from './plugin-locales.js';

const STORAGE_KEY = 'wence-interface-language';
const messages = { 'en-US': enUS, 'id-ID': idID, 'zh-CN': zhCN, 'ja-JP': jaJP, 'ko-KR': koKR, 'vi-VN': viVN };
for (const [code, strings] of Object.entries(pluginLocales)) {
  messages[code].settings.tabs.plugin = strings.title;
  messages[code].settings.pluginTitle = strings.title;
  messages[code].settings.pluginDesc = strings.desc;
  messages[code].plugin = strings;
}
const I18N_KEY = Symbol('wence-i18n');

function normalizeLocale(value) {
  if (!value) {
    return 'en-US';
  }
  const normalized = String(value).toLowerCase();
  if (normalized === 'en-us' || normalized.startsWith('en')) {
    return 'en-US';
  }
  if (normalized === 'id-id' || normalized === 'id' || normalized.startsWith('id')) {
    return 'id-ID';
  }
  if (normalized === 'ja-jp' || normalized === 'ja' || normalized.startsWith('ja')) {
    return 'ja-JP';
  }
  if (normalized === 'ko-kr' || normalized === 'ko' || normalized.startsWith('ko')) {
    return 'ko-KR';
  }
  if (normalized === 'vi-vn' || normalized === 'vi' || normalized.startsWith('vi')) {
    return 'vi-VN';
  }
  return 'zh-CN';
}

function initialLocale() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return normalizeLocale(stored);
    }
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

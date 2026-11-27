import { inject } from 'vue';
import enUS from '../locales/en-US.js';
import idID from '../locales/id-ID.js';
import jaJP from '../locales/ja-JP.js';
import koKR from '../locales/ko-KR.js';
import viVN from '../locales/vi-VN.js';
import zhCN from '../locales/zh-CN.js';

export const I18N_KEY = Symbol('wence-i18n');
export const LANGUAGE_STORAGE_KEY = 'wence-interface-language';

const messages = { 'en-US': enUS, 'id-ID': idID, 'ja-JP': jaJP, 'ko-KR': koKR, 'vi-VN': viVN, 'zh-CN': zhCN };

export function normalizeLocale(value) {
  if (!value) return 'en-US';
  const normalized = String(value).toLowerCase();
  if (normalized.startsWith('en')) return 'en-US';
  if (normalized.startsWith('id')) return 'id-ID';
  if (normalized.startsWith('ja')) return 'ja-JP';
  if (normalized.startsWith('ko')) return 'ko-KR';
  if (normalized.startsWith('vi')) return 'vi-VN';
  return 'zh-CN';
}

export function resolveTranslation(locale, key) {
  const resolve = (source) => key.split('.').reduce((value, part) => value?.[part], source);
  return resolve(messages[locale]) ?? resolve(messages['zh-CN']) ?? key;
}

export function useI18n(fallback) {
  return inject(I18N_KEY, fallback);
}

<template>
  <div class="general-setting-container">
    <!-- 标题区 -->
    <div class="section-header">
      <svg
        class="section-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
      <div class="section-title-group">
        <h2 class="section-title">
          {{ $t('general.title') }}
        </h2>
        <p class="section-subtitle">
          {{ $t('general.subtitle') }}
        </p>
      </div>
    </div>

    <div class="setting-row">
      <span class="setting-label">{{ $t('general.language') }}</span>
      <div
        ref="languagePicker"
        class="language-picker"
        @keydown.esc="closeLanguageMenu"
      >
        <button
          type="button"
          class="language-trigger"
          :class="{ open: languageMenuOpen }"
          aria-haspopup="listbox"
          :aria-expanded="languageMenuOpen"
          @click="toggleLanguageMenu"
        >
          <span>{{ selectedLanguageLabel }}</span>
          <span class="language-chevron" aria-hidden="true"></span>
        </button>
        <div v-if="languageMenuOpen" class="language-menu" role="listbox">
          <button
            type="button"
            class="language-option"
            :class="{ selected: localSettings.language === 'zh-CN' }"
            role="option"
            :aria-selected="localSettings.language === 'zh-CN'"
            @click="selectLanguage('zh-CN')"
          >
            {{ $t('general.simplifiedChinese') }}
          </button>
          <button
            type="button"
            class="language-option"
            :class="{ selected: localSettings.language === 'en-US' }"
            role="option"
            :aria-selected="localSettings.language === 'en-US'"
            @click="selectLanguage('en-US')"
          >
            {{ $t('general.english') }}
          </button>
        </div>
      </div>
    </div>

    <!-- 启动时显示AI面板 -->
    <div class="setting-row">
      <span class="setting-label">{{ $t('general.showPanel') }}</span>
      <label class="switch">
        <input v-model="localSettings.showPanelOnStart" type="checkbox" @change="emitChange" />
        <span class="slider"></span>
      </label>
    </div>

    <!-- 网络代理 独立 section -->
    <div class="section-divider"></div>

    <div class="section-header">
      <svg
        class="section-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M2 12h20" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
      <div class="section-title-group">
        <h2 class="section-title">
          {{ $t('general.proxyTitle') }}
        </h2>
        <p class="section-subtitle">
          {{ $t('general.proxySubtitle') }}
        </p>
      </div>
    </div>

    <div class="proxy-section">
      <div class="setting-row" style="border-bottom: none; padding-bottom: 8px;">
        <span class="setting-label">{{ $t('general.enableProxy') }}</span>
        <label class="switch">
          <input v-model="localSettings.proxy.enabled" type="checkbox" @change="emitChange" />
          <span class="slider"></span>
        </label>
      </div>
      <div class="proxy-inputs" :class="{ disabled: !localSettings.proxy.enabled }">
        <div class="proxy-row">
          <div class="input-group flex-grow">
            <label class="input-label">{{ $t('general.proxyHost') }}</label>
            <input
              v-model="localSettings.proxy.host"
              type="text"
              class="text-input"
              placeholder="127.0.0.1"
              :disabled="!localSettings.proxy.enabled"
              @input="emitChange"
            />
          </div>
          <div class="input-group port-input">
            <label class="input-label">{{ $t('general.port') }}</label>
            <input
              v-model.number="localSettings.proxy.port"
              type="number"
              class="text-input"
              placeholder="7897"
              min="1"
              max="65535"
              :disabled="!localSettings.proxy.enabled"
              @input="emitChange"
            />
          </div>
        </div>
        <p class="proxy-hint">
          {{ $t('general.proxyHint') }}
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { setLocale, t } from '../../i18n/index.js';

export default {
  name: 'GeneralSetting',
  props: {
    settings: {
      type: Object,
      required: true
    }
  },
  emits: ['update:settings'],
  setup(props, { emit }) {
    const languagePicker = ref(null);
    const languageMenuOpen = ref(false);
    const localSettings = ref({
      language: props.settings.language ?? 'zh-CN',
      showPanelOnStart: props.settings.showPanelOnStart ?? true,
      proofreadMode: props.settings.proofreadMode ?? 'revision',
      proxy: {
        enabled: props.settings.proxy?.enabled ?? false,
        host: props.settings.proxy?.host ?? '',
        port: props.settings.proxy?.port ?? 0
      }
    });

    watch(() => props.settings, (newVal) => {
      localSettings.value.language = newVal.language ?? 'zh-CN';
      localSettings.value.showPanelOnStart = newVal.showPanelOnStart ?? true;
      localSettings.value.proofreadMode = newVal.proofreadMode ?? 'revision';
      localSettings.value.proxy.enabled = newVal.proxy?.enabled ?? false;
      localSettings.value.proxy.host = newVal.proxy?.host ?? '';
      localSettings.value.proxy.port = newVal.proxy?.port ?? 7897;
    }, { deep: true });

    const emitChange = () => {
      emit('update:settings', {
        language: localSettings.value.language,
        showPanelOnStart: localSettings.value.showPanelOnStart,
        proofreadMode: localSettings.value.proofreadMode,
        proxy: { ...localSettings.value.proxy }
      });
    };

    const selectedLanguageLabel = computed(() => (
      localSettings.value.language === 'en-US'
        ? t('general.english')
        : t('general.simplifiedChinese')
    ));

    const closeLanguageMenu = () => {
      languageMenuOpen.value = false;
    };

    const toggleLanguageMenu = () => {
      languageMenuOpen.value = !languageMenuOpen.value;
    };

    const selectLanguage = (language) => {
      localSettings.value.language = language;
      setLocale(language);
      emitChange();
      closeLanguageMenu();
    };

    const handleOutsideClick = (event) => {
      if (languagePicker.value && !languagePicker.value.contains(event.target)) {
        closeLanguageMenu();
      }
    };

    onMounted(() => document.addEventListener('mousedown', handleOutsideClick));
    onBeforeUnmount(() => document.removeEventListener('mousedown', handleOutsideClick));

    return {
      languagePicker,
      languageMenuOpen,
      localSettings,
      selectedLanguageLabel,
      emitChange,
      closeLanguageMenu,
      toggleLanguageMenu,
      selectLanguage
    };
  }
};
</script>

<style scoped>
.general-setting-container {
  padding: 0;
}

/* 标题区 */
.section-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f0f0;
}

.section-icon {
  width: 24px;
  height: 24px;
  color: #667eea;
  flex-shrink: 0;
  margin-top: 2px;
}

.section-title-group {
  flex: 1;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: #2c3e50;
}

.section-subtitle {
  font-size: 13px;
  color: #7f8c8d;
  margin: 0;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.setting-label {
  font-size: 14px;
  color: #333;
}

.language-picker {
  position: relative;
  width: 148px;
  flex-shrink: 0;
}

.language-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 34px;
  padding: 0 11px;
  border: 1px solid #d8dce3;
  border-radius: 6px;
  background: #fff;
  color: #333;
  font-size: 13px;
  cursor: pointer;
  text-align: left;
}

.language-trigger:hover,
.language-trigger:focus,
.language-trigger.open {
  border-color: #667eea;
  outline: none;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.12);
}

.language-chevron {
  width: 7px;
  height: 7px;
  margin: -3px 2px 0 10px;
  border-right: 1.5px solid #667085;
  border-bottom: 1.5px solid #667085;
  transform: rotate(45deg);
  transition: transform 0.16s ease;
}

.language-trigger.open .language-chevron {
  margin-top: 3px;
  transform: rotate(225deg);
}

.language-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 30;
  width: 100%;
  padding: 4px;
  border: 1px solid #d8dce3;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 8px 20px rgba(31, 41, 55, 0.14);
  box-sizing: border-box;
}

.language-option {
  display: block;
  width: 100%;
  min-height: 32px;
  padding: 7px 9px;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #333;
  font-size: 13px;
  line-height: 18px;
  text-align: left;
  cursor: pointer;
}

.language-option:hover,
.language-option:focus {
  background: #f3f5f9;
  outline: none;
}

.language-option.selected {
  background: #eef1ff;
  color: #4f5fca;
  font-weight: 500;
}

/* 开关样式 */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.switch input:checked + .slider {
  background-color: #667eea;
}

.switch input:checked + .slider:before {
  transform: translateX(20px);
}

/* 设置组 */
.setting-group {
  margin-top: 24px;
}

.group-title {
  font-size: 14px;
  color: #333;
  margin-bottom: 16px;
  font-weight: 500;
}

/* 单选按钮组 */
.radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.radio-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.radio-item:hover {
  border-color: #d0d0d0;
}

.radio-item.active {
  border-color: #667eea;
  background: #f8faff;
}

.radio-item input {
  display: none;
}

.radio-circle {
  width: 18px;
  height: 18px;
  border: 2px solid #d0d0d0;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 2px;
  position: relative;
  transition: all 0.2s;
}

.radio-item.active .radio-circle {
  border-color: #667eea;
}

.radio-item.active .radio-circle::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
}

.radio-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.radio-title {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.radio-desc {
  font-size: 12px;
  color: #888;
}

/* 代理设置 */
.proxy-section {
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px 16px;
}

.proxy-inputs {
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: opacity 0.2s;
}

.proxy-inputs.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.proxy-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.flex-grow {
  flex: 1;
}

.port-input {
  width: 90px;
  flex-shrink: 0;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.input-label {
  font-size: 13px;
  color: #555;
  font-weight: 500;
}

.text-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 13px;
  color: #333;
  background: #fafafa;
  outline: none;
  transition: border-color 0.2s, background-color 0.2s;
  box-sizing: border-box;
}

.text-input:focus {
  border-color: #667eea;
  background: white;
}

.text-input:disabled {
  background: #f5f5f5;
  color: #aaa;
  cursor: not-allowed;
}

.text-input::placeholder {
  color: #bbb;
}

/* 隐藏 number input 的上下箭头 */
.text-input[type="number"]::-webkit-inner-spin-button,
.text-input[type="number"]::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.text-input[type="number"] {
  -moz-appearance: textfield;
}

.proxy-hint {
  font-size: 12px;
  color: #999;
  margin: 4px 0 0 0;
  line-height: 1.5;
}

/* section 分隔线 */
.section-divider {
  height: 1px;
  background: #e8e8e8;
  margin: 32px 0;
}
</style>

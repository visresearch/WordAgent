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
          基础设置
        </h2>
        <p class="section-subtitle">
          配置应用的启动行为和显示模式
        </p>
      </div>
    </div>

    <!-- 启动时显示AI面板 -->
    <div class="setting-row">
      <span class="setting-label">启动时显示AI面板</span>
      <label class="switch">
        <input v-model="localSettings.showPanelOnStart" type="checkbox" @change="emitChange" />
        <span class="slider"></span>
      </label>
    </div>

    <!-- 校对显示模式 -->
    <div class="setting-group">
      <div class="group-title">
        校对显示模式
      </div>
      <div class="radio-group">
        <label class="radio-item" :class="{ active: localSettings.proofreadMode === 'redblue' }">
          <input 
            v-model="localSettings.proofreadMode" 
            type="radio" 
            value="redblue"
            @change="emitChange"
          />
          <span class="radio-circle"></span>
          <div class="radio-content">
            <span class="radio-title">红蓝模式</span>
            <span class="radio-desc">使用红色标记删除内容，蓝色标记新增内容</span>
          </div>
        </label>
        <label class="radio-item" :class="{ active: localSettings.proofreadMode === 'revision' }">
          <input 
            v-model="localSettings.proofreadMode" 
            type="radio" 
            value="revision"
            @change="emitChange"
          />
          <span class="radio-circle"></span>
          <div class="radio-content">
            <span class="radio-title">修订模式</span>
            <span class="radio-desc">使用Word修订功能标记修改内容</span>
          </div>
        </label>
      </div>
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
          网络代理
        </h2>
        <p class="section-subtitle">
          配置 HTTP/HTTPS 请求的代理服务器
        </p>
      </div>
    </div>

    <div class="proxy-section">
      <div class="setting-row" style="border-bottom: none; padding-bottom: 8px;">
        <span class="setting-label">启用代理</span>
        <label class="switch">
          <input v-model="localSettings.proxy.enabled" type="checkbox" @change="emitChange" />
          <span class="slider"></span>
        </label>
      </div>
      <div class="proxy-inputs" :class="{ disabled: !localSettings.proxy.enabled }">
        <div class="proxy-row">
          <div class="input-group flex-grow">
            <label class="input-label">代理地址 (IP)</label>
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
            <label class="input-label">端口</label>
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
          提示：HTTP 和 HTTPS 请求将统一使用此代理。仅支持 HTTP 代理协议，不支持 SOCKS。
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue';

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
    const localSettings = ref({
      showPanelOnStart: props.settings.showPanelOnStart ?? true,
      proofreadMode: props.settings.proofreadMode ?? 'redblue',
      proxy: {
        enabled: props.settings.proxy?.enabled ?? false,
        host: props.settings.proxy?.host ?? '',
        port: props.settings.proxy?.port ?? 0
      }
    });

    watch(() => props.settings, (newVal) => {
      localSettings.value.showPanelOnStart = newVal.showPanelOnStart ?? true;
      localSettings.value.proofreadMode = newVal.proofreadMode ?? 'redblue';
      localSettings.value.proxy.enabled = newVal.proxy?.enabled ?? false;
      localSettings.value.proxy.host = newVal.proxy?.host ?? '';
      localSettings.value.proxy.port = newVal.proxy?.port ?? 7897;
    }, { deep: true });

    const emitChange = () => {
      emit('update:settings', {
        showPanelOnStart: localSettings.value.showPanelOnStart,
        proofreadMode: localSettings.value.proofreadMode,
        proxy: { ...localSettings.value.proxy }
      });
    };

    return {
      localSettings,
      emitChange
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
  appearance: none;
  -webkit-appearance: none;
  margin: 0;
}
.text-input[type="number"] {
  appearance: textfield;
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

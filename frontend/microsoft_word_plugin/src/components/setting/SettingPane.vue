<template>
  <div class="setting-container">
    <!-- 左侧导航栏 -->
    <div class="setting-nav">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        class="nav-item"
        :class="{ active: currentTab === tab.id }"
        @click="currentTab = tab.id"
      >
        <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path :d="tab.icon" />
        </svg>
        <span class="nav-text">{{ tab.name }}</span>
      </div>
    </div>

    <!-- 右侧内容区 -->
    <div class="setting-content">
      <!-- 通用设置 -->
      <div v-if="currentTab === 'general'" class="tab-content">
        <div class="tab-header">
          <h2 class="tab-title">通用设置</h2>
          <p class="tab-desc">配置应用的基础行为</p>
        </div>
        <div class="setting-section">
          <GeneralSetting :settings="generalSettings" @update:settings="onGeneralSettingsChange" />
        </div>
      </div>

      <!-- 大模型设置 -->
      <div v-if="currentTab === 'model'" class="tab-content">
        <div class="tab-header">
          <h2 class="tab-title">大模型设置</h2>
          <p class="tab-desc">配置AI模型提供商和模型</p>
        </div>
        <div class="setting-section">
          <ModelSetting :providers="settings.providers" @update:providers="onProvidersChange" />
        </div>
      </div>

      <!-- 个性化设置 -->
      <div v-if="currentTab === 'personalization'" class="tab-content">
        <div class="tab-header">
          <h2 class="tab-title">个性化设置</h2>
          <p class="tab-desc">自定义您的AI助手行为和响应参数</p>
        </div>
        <div class="setting-section">
          <PersonalizationSetting :settings="personalizationSettings" @update:settings="onPersonalizationChange" />
        </div>
      </div>

      <!-- 数据管理 -->
      <div v-if="currentTab === 'data'" class="tab-content full-height">
        <DataManagementSetting />
      </div>

      <!-- 底部保存按钮 -->
      <div v-if="currentTab !== 'data'" class="setting-footer">
        <button class="btn btn-save" :disabled="saving" @click="saveSettings">
          <span v-if="saving" class="loading-spinner"></span>
          {{ saving ? '保存中...' : '保存设置' }}
        </button>
        <transition name="fade">
          <span v-if="saveMessage" :class="['save-msg', saveSuccess ? 'success' : 'error']">
            {{ saveMessage }}
          </span>
        </transition>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed } from 'vue';
import GeneralSetting from './GeneralSetting.vue';
import ModelSetting from './ModelSetting.vue';
import PersonalizationSetting from './PersonalizationSetting.vue';
import DataManagementSetting from './DataManagementSetting.vue';

export default {
  name: 'SettingPane',
  components: {
    GeneralSetting,
    ModelSetting,
    PersonalizationSetting,
    DataManagementSetting
  },
  setup() {
    const currentTab = ref('general');
    const saving = ref(false);
    const saveMessage = ref('');
    const saveSuccess = ref(false);

    const tabs = ref([
      {
        id: 'general',
        name: '通用',
        icon: 'M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z'
      },
      {
        id: 'model',
        name: '大模型',
        icon: 'M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z M3.27 6.96L12 12.01l8.73-5.05 M12 22.08V12'
      },
      {
        id: 'personalization',
        name: '个性化',
        icon: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z'
      },
      {
        id: 'data',
        name: '数据管理',
        icon: 'M12.89 1.45l8 4A2 2 0 0 1 22 7.24v9.53a2 2 0 0 1-1.11 1.79l-8 4a2 2 0 0 1-1.79 0l-8-4a2 2 0 0 1-1.1-1.8V7.24a2 2 0 0 1 1.11-1.79l8-4a2 2 0 0 1 1.78 0z M2.32 6.16L12 11l9.68-4.84 M12 22V11'
      }
    ]);

    const settings = reactive({
      showPanelOnStart: true,
      proofreadMode: 'redblue',
      proxy: { enabled: false, host: '', port: 0 },
      providers: [
        // 模拟数据
        {
          name: 'OpenAI',
          apiKey: '',
          baseUrl: 'https://api.openai.com/v1',
          models: [
            { id: 'gpt-4', name: 'GPT-4', enabled: true },
            { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', enabled: true }
          ],
          expanded: false,
          showKey: false,
          fetchingModels: false,
          availableModels: []
        }
      ],
      customPrompt: '',
      temperature: 0.7
    });

    const generalSettings = computed(() => ({
      showPanelOnStart: settings.showPanelOnStart,
      proofreadMode: settings.proofreadMode,
      proxy: { ...settings.proxy }
    }));

    const personalizationSettings = computed(() => ({
      customPrompt: settings.customPrompt,
      temperature: settings.temperature
    }));

    const onGeneralSettingsChange = (newSettings) => {
      settings.showPanelOnStart = newSettings.showPanelOnStart;
      settings.proofreadMode = newSettings.proofreadMode;
      settings.proxy = { ...newSettings.proxy };
    };

    const onProvidersChange = (newProviders) => {
      settings.providers = newProviders;
    };

    const onPersonalizationChange = (newSettings) => {
      settings.customPrompt = newSettings.customPrompt;
      settings.temperature = newSettings.temperature;
    };

    const saveSettings = () => {
      saving.value = true;
      // TODO: 后端集成后保存设置
      setTimeout(() => {
        saving.value = false;
        saveSuccess.value = true;
        saveMessage.value = '设置已保存';
        setTimeout(() => {
          saveMessage.value = '';
        }, 2000);
      }, 500);
    };

    return {
      currentTab,
      tabs,
      settings,
      generalSettings,
      personalizationSettings,
      saving,
      saveMessage,
      saveSuccess,
      onGeneralSettingsChange,
      onProvidersChange,
      onPersonalizationChange,
      saveSettings
    };
  }
};
</script>

<style scoped>
.setting-container {
  display: flex;
  height: 100vh;
  background: #f7f8fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* 左侧导航 */
.setting-nav {
  width: 80px;
  background: white;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  padding: 12px 0;
  flex-shrink: 0;
}
.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  cursor: pointer;
  transition: all 0.2s;
  border-left: 3px solid transparent;
  color: #666;
}
.nav-item:hover {
  background: #f5f5f5;
  color: #333;
}
.nav-item.active {
  color: #667eea;
  background: #f0f4ff;
  border-left-color: #667eea;
}
.nav-icon {
  width: 20px;
  height: 20px;
}
.nav-text {
  font-size: 11px;
  font-weight: 500;
  text-align: center;
}

/* 右侧内容 */
.setting-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}
.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}
.tab-content.full-height {
  padding: 0;
}
.tab-content::-webkit-scrollbar { width: 6px; }
.tab-content::-webkit-scrollbar-track { background: transparent; }
.tab-content::-webkit-scrollbar-thumb { background: #c5cdd8; border-radius: 2px; }

.tab-header {
  margin-bottom: 20px;
}
.tab-title {
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin: 0 0 4px;
}
.tab-desc {
  font-size: 12px;
  color: #888;
  margin: 0;
}

.setting-section {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* 底部保存 */
.setting-footer {
  padding: 12px 20px;
  background: white;
  border-top: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.btn-save {
  padding: 8px 24px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-save:hover:not(:disabled) {
  background: #5a6fd6;
}
.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.save-msg {
  font-size: 12px;
}
.save-msg.success { color: #27ae60; }
.save-msg.error { color: #e74c3c; }
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>

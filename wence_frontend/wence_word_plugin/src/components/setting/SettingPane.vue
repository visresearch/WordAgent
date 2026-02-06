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
        <svg
          class="nav-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
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
          <h2 class="tab-title">
            通用设置
          </h2>
          <p class="tab-desc">
            配置应用的基础行为
          </p>
        </div>
        <div class="setting-section">
          <GeneralSetting 
            :settings="generalSettings" 
            @update:settings="onGeneralSettingsChange"
          />
        </div>
      </div>

      <!-- 大模型设置 -->
      <div v-if="currentTab === 'model'" class="tab-content">
        <div class="tab-header">
          <h2 class="tab-title">
            大模型设置
          </h2>
          <p class="tab-desc">
            配置AI模型提供商和模型
          </p>
        </div>
        <div class="setting-section">
          <ModelSetting 
            :providers="settings.providers" 
            @update:providers="onProvidersChange"
          />
        </div>
      </div>

      <!-- 个性化设置 -->
      <div v-if="currentTab === 'personalization'" class="tab-content full-height">
        <PersonalizationPane />
      </div>

      <!-- 数据管理 -->
      <div v-if="currentTab === 'data'" class="tab-content full-height">
        <DataManagementPane />
      </div>

      <!-- 底部保存按钮（通用和模型设置需要） -->
      <div v-if="currentTab === 'general' || currentTab === 'model'" class="setting-footer">
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
import { ref, reactive, computed, onMounted } from 'vue';
import api from '../js/api.js';
import GeneralSetting from './GeneralSetting.vue';
import ModelSetting from './ModelSetting.vue';
import PersonalizationPane from './PersonalizationSetting.vue';
import DataManagementPane from './DataManagementSetting.vue';

export default {
  name: 'SettingPane',
  components: {
    GeneralSetting,
    ModelSetting,
    PersonalizationPane,
    DataManagementPane
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
      providers: []
    });

    const generalSettings = computed(() => ({
      showPanelOnStart: settings.showPanelOnStart,
      proofreadMode: settings.proofreadMode
    }));

    const loadSettings = async () => {
      try {
        const data = await api.getSettings();
        if (data) {
          if (data.showPanelOnStart !== undefined) {
            settings.showPanelOnStart = data.showPanelOnStart;
          }
          if (data.proofreadMode !== undefined) {
            settings.proofreadMode = data.proofreadMode;
          }
          if (data.providers) {
            settings.providers = data.providers.map(p => ({
              ...p,
              enabled: p.enabled !== false,
              expanded: false,
              showKey: false,
              fetchingModels: false
            }));
          }
        }
      } catch (error) {
        console.error('加载设置失败:', error);
      }
    };

    const saveSettings = async () => {
      saving.value = true;
      saveMessage.value = '';

      try {
        const settingsToSave = {
          showPanelOnStart: settings.showPanelOnStart,
          proofreadMode: settings.proofreadMode,
          providers: settings.providers.map(p => ({
            name: p.name,
            baseUrl: p.baseUrl,
            apiKey: p.apiKey,
            models: p.models,
            enabled: p.enabled
          }))
        };

        await api.saveSettings(settingsToSave);

        saveMessage.value = '设置已保存！';
        saveSuccess.value = true;

        setTimeout(() => {
          saveMessage.value = '';
        }, 2000);
      } catch (error) {
        console.error('保存设置失败:', error);
        saveMessage.value = '保存失败，请重试';
        saveSuccess.value = false;
      } finally {
        saving.value = false;
      }
    };

    const onGeneralSettingsChange = (newSettings) => {
      settings.showPanelOnStart = newSettings.showPanelOnStart;
      settings.proofreadMode = newSettings.proofreadMode;
    };

    const onProvidersChange = (newProviders) => {
      settings.providers = newProviders.map(p => ({
        ...p,
        enabled: p.enabled !== false,
        expanded: false,
        showKey: false,
        fetchingModels: false
      }));
    };

    onMounted(() => {
      loadSettings();
    });

    return {
      currentTab,
      tabs,
      settings,
      generalSettings,
      saving,
      saveMessage,
      saveSuccess,
      saveSettings,
      onGeneralSettingsChange,
      onProvidersChange
    };
  }
};
</script>

<style scoped>
.setting-container {
  display: flex;
  height: 100vh;
  width: 100%;
  background: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
  overflow: hidden;
}

/* ========== 左侧导航栏 ========== */
.setting-nav {
  width: 140px;
  background: #ffffff;
  border-right: 1px solid #e8e8e8;
  padding: 20px 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin: 0 8px;
  font-size: 14px;
  color: #666666;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 8px;
}

.nav-item:hover {
  color: #333333;
  background: #f5f5f5;
}

.nav-item.active {
  color: #333333;
  background: #f5f5f5;
  font-weight: 500;
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.nav-text {
  font-size: 13px;
  white-space: nowrap;
}

/* ========== 右侧内容区 ========== */
.setting-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.tab-content.full-height {
  padding: 0;
}

.tab-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f0f0;
}

.tab-title {
  font-size: 20px;
  font-weight: 600;
  color: #333333;
  margin: 0 0 8px 0;
}

.tab-desc {
  font-size: 13px;
  color: #888888;
  margin: 0;
}

/* 设置分组卡片 */
.setting-section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* ========== 底部保存按钮 ========== */
.setting-footer {
  padding: 16px 32px;
  background: white;
  border-top: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  gap: 16px;
}

.btn {
  display: flex;
  align-items: center;
  gap: 8px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-save {
  padding: 10px 32px;
  background: #667eea;
  color: white;
}

.btn-save:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.save-msg {
  font-size: 13px;
}

.save-msg.success {
  color: #10b981;
}

.save-msg.error {
  color: #dc2626;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 滚动条样式 */
.tab-content::-webkit-scrollbar {
  width: 6px;
}

.tab-content::-webkit-scrollbar-track {
  background: #f5f5f5;
}

.tab-content::-webkit-scrollbar-thumb {
  background: #bdc3c7;
  border-radius: 3px;
}

.tab-content::-webkit-scrollbar-thumb:hover {
  background: #95a5a6;
}
</style>

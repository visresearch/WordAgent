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
        <img :src="tab.icon" class="nav-icon" alt="" />
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
      <div v-if="currentTab === 'personalization'" class="tab-content">
        <div class="tab-header">
          <h2 class="tab-title">
            个性化设置
          </h2>
          <p class="tab-desc">
            自定义您的AI助手行为和响应参数
          </p>
        </div>
        <div class="setting-section">
          <PersonalizationPane
            :settings="personalizationSettings"
            @update:settings="onPersonalizationChange"
          />
        </div>
      </div>

      <!-- MCP 服务器管理 -->
      <div v-if="currentTab === 'mcp'" class="tab-content">
        <div class="tab-header">
          <h2 class="tab-title">
            MCP 服务器管理
          </h2>
          <p class="tab-desc">
            管理 MCP 服务器名称和 JSON 配置，支持连接测试
          </p>
        </div>
        <div class="setting-section">
          <MCPserverSetting
            :mcp-servers="settings.mcpServers"
            @update:mcp-servers="onMcpServersChange"
          />
        </div>
      </div>

      <!-- 数据管理 -->
      <div v-if="currentTab === 'data'" class="tab-content full-height">
        <DataManagementPane
          :cache-info="cacheInfo"
          @update:cache-info="onCacheUpdate"
        />
      </div>

      <!-- Skill 管理 -->
      <div v-if="currentTab === 'skill'" class="tab-content">
        <div class="tab-header">
          <h2 class="tab-title">
            Skill 管理
          </h2>
          <p class="tab-desc">
            查看和管理本地已下载 Skill，支持上传压缩包、启用开关和删除
          </p>
        </div>
        <div class="setting-section">
          <SkillSetting />
        </div>
      </div>

      <!-- 底部保存按钮（通用、模型和个性化设置需要） -->
      <div class="setting-footer">
        <button
          v-if="currentTab !== 'data' && currentTab !== 'skill'"
          class="btn btn-save"
          :disabled="saving"
          @click="saveSettings"
        >
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
import { settingsState } from '../../settingsState.js';
import GeneralSetting from './GeneralSetting.vue';
import ModelSetting from './ModelSetting.vue';
import MCPserverSetting from './MCPserverSetting.vue';
import PersonalizationPane from './PersonalizationSetting.vue';
import DataManagementPane from './DataManagementSetting.vue';
import SkillSetting from './SkillSetting.vue';
import iconSetting from '../../assets/icons/setting.svg';
import iconModel from '../../assets/icons/model.svg';
import iconUser from '../../assets/icons/user.svg';
import iconMcp from '../../assets/icons/mcp.svg';
import iconData from '../../assets/icons/data.svg';
import iconSkill from '../../assets/icons/skill.svg';

export default {
  name: 'SettingPane',
  components: {
    GeneralSetting,
    ModelSetting,
    MCPserverSetting,
    PersonalizationPane,
    DataManagementPane,
    SkillSetting
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
        icon: iconSetting
      },
      {
        id: 'model',
        name: '大模型',
        icon: iconModel
      },
      {
        id: 'personalization',
        name: '个性化',
        icon: iconUser
      },
      {
        id: 'mcp',
        name: 'MCP',
        icon: iconMcp
      },
      {
        id: 'skill',
        name: 'Skill',
        icon: iconSkill
      },
      {
        id: 'data',
        name: '数据管理',
        icon: iconData
      }
    ]);

    const settings = reactive({
      showPanelOnStart: true,
      proofreadMode: 'revision',
      proxy: {
        enabled: false,
        host: '',
        port: 0
      },
      providers: [],
      mcpServers: [],
      customPrompt: '',
      temperature: 0.7
    });

    // 缓存信息（只加载一次）
    const cacheInfo = reactive({
      dir: '',
      fileCount: -1,
      totalSize: -1
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

    const loadCacheInfo = async () => {
      try {
        const data = await api.scanCache();
        cacheInfo.dir = data.dir || '';
        cacheInfo.fileCount = data.fileCount || 0;
        cacheInfo.totalSize = data.totalSize || 0;
      } catch (error) {
        console.error('加载缓存信息失败:', error);
        cacheInfo.fileCount = 0;
        cacheInfo.totalSize = 0;
      }
    };

    const onCacheUpdate = (newInfo) => {
      if (newInfo.dir !== undefined) {
        cacheInfo.dir = newInfo.dir;
      }
      if (newInfo.fileCount !== undefined) {
        cacheInfo.fileCount = newInfo.fileCount;
      }
      if (newInfo.totalSize !== undefined) {
        cacheInfo.totalSize = newInfo.totalSize;
      }
    };

    const loadSettings = async () => {
      try {
        const data = await api.getSettings();
        if (data) {
          if (data.showPanelOnStart !== undefined) {
            settings.showPanelOnStart = data.showPanelOnStart;
          }
          if (data.proofreadMode !== undefined) {
            settings.proofreadMode = data.proofreadMode;
            settingsState.proofreadMode = data.proofreadMode;
          }
          if (data.providers) {
            settings.providers = data.providers.map(p => ({
              ...p,
              apiType: p.apiType || 'openai',
              enabled: p.enabled !== false,
              expanded: false,
              showKey: false,
              fetchingModels: false
            }));
          }
          if (data.proxy) {
            settings.proxy.enabled = data.proxy.enabled ?? false;
            settings.proxy.host = data.proxy.host ?? '';
            settings.proxy.port = data.proxy.port ?? 0;
          }
          if (data.customPrompt !== undefined) {
            settings.customPrompt = data.customPrompt;
          }
          if (data.temperature !== undefined) {
            settings.temperature = data.temperature;
          }
          if (Array.isArray(data.mcpServers)) {
            settings.mcpServers = data.mcpServers.map(s => {
              const config = (s.config && typeof s.config === 'object') ? s.config : {};
              return {
                name: s.name || '',
                config,
                configSource: typeof s.configSource === 'string' ? s.configSource : JSON.stringify(config, null, 2),
                enabled: s.enabled !== false,
                expanded: false
              };
            });
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
          proxy: { ...settings.proxy },
          providers: settings.providers.map(p => ({
            name: p.name,
            baseUrl: p.baseUrl,
            apiKey: p.apiKey,
            apiType: p.apiType || 'openai',
            models: p.models,
            enabled: p.enabled
          })),
          mcpServers: settings.mcpServers.map(s => {
            const config = (s.config && typeof s.config === 'object') ? s.config : {};
            return {
              name: s.name,
              config,
              configSource: typeof s.configSource === 'string' ? s.configSource : JSON.stringify(config, null, 2),
              enabled: s.enabled !== false
            };
          }),
          customPrompt: settings.customPrompt,
          temperature: settings.temperature
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
      settingsState.proofreadMode = newSettings.proofreadMode;
      if (newSettings.proxy) {
        settings.proxy.enabled = newSettings.proxy.enabled;
        settings.proxy.host = newSettings.proxy.host;
        settings.proxy.port = newSettings.proxy.port;
      }
    };

    const onPersonalizationChange = (newSettings) => {
      settings.customPrompt = newSettings.customPrompt;
      settings.temperature = newSettings.temperature;
    };

    const onProvidersChange = (newProviders) => {
      settings.providers = newProviders.map(p => ({
        ...p,
        apiType: p.apiType || 'openai',
        enabled: p.enabled !== false,
        expanded: p.expanded ?? false,
        showKey: p.showKey ?? false,
        fetchingModels: p.fetchingModels ?? false
      }));
    };

    const onMcpServersChange = (newServers) => {
      settings.mcpServers = newServers.map(s => {
        const config = (s.config && typeof s.config === 'object') ? s.config : {};
        return {
          name: s.name || '',
          config,
          configSource: typeof s.configSource === 'string' ? s.configSource : JSON.stringify(config, null, 2),
          enabled: s.enabled !== false,
          expanded: s.expanded ?? false
        };
      });
    };

    onMounted(() => {
      loadSettings();
      loadCacheInfo();
    });

    return {
      currentTab,
      tabs,
      settings,
      generalSettings,
      personalizationSettings,
      saving,
      saveMessage,
      saveSuccess,
      cacheInfo,
      saveSettings,
      onGeneralSettingsChange,
      onPersonalizationChange,
      onProvidersChange,
      onMcpServersChange,
      onCacheUpdate
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
  object-fit: contain;
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
  flex-shrink: 0;
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

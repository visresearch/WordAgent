<template>
  <div class="setting-container">
    <!-- 左侧导航栏 -->
    <div class="setting-nav">
      <div 
        class="nav-item" 
        :class="{ active: currentTab === 'general' }"
        @click="currentTab = 'general'"
      >
        通用
      </div>
      <div
        class="nav-item"
        :class="{ active: currentTab === 'model' }"
        @click="currentTab = 'model'"
      >
        大模型
      </div>
    </div>

    <!-- 右侧内容区 -->
    <div class="setting-content">
      <!-- 通用设置 -->
      <div v-if="currentTab === 'general'" class="tab-content">
        <!-- 启动时显示AI面板 -->
        <div class="setting-row">
          <span class="setting-label">启动时显示AI面板</span>
          <label class="switch">
            <input v-model="settings.showPanelOnStart" type="checkbox" />
            <span class="slider"></span>
          </label>
        </div>

        <!-- 校对显示模式 -->
        <div class="setting-group">
          <div class="group-title">
            校对显示模式
          </div>
          <div class="radio-group">
            <label class="radio-item" :class="{ active: settings.proofreadMode === 'redblue' }">
              <input 
                v-model="settings.proofreadMode" 
                type="radio" 
                value="redblue"
              />
              <span class="radio-circle"></span>
              <div class="radio-content">
                <span class="radio-title">红蓝模式</span>
                <span class="radio-desc">使用红色标记删除内容，蓝色标记新增内容</span>
              </div>
            </label>
            <label class="radio-item" :class="{ active: settings.proofreadMode === 'revision' }">
              <input 
                v-model="settings.proofreadMode" 
                type="radio" 
                value="revision"
              />
              <span class="radio-circle"></span>
              <div class="radio-content">
                <span class="radio-title">修订模式</span>
                <span class="radio-desc">使用Word修订功能标记修改内容</span>
              </div>
            </label>
          </div>
        </div>
      </div>

      <!-- 大模型设置 -->
      <div v-if="currentTab === 'model'" class="tab-content">
        <!-- 标题栏 -->
        <div class="models-toolbar">
          <div class="toolbar-left">
            <span class="toolbar-title">已配置的提供商</span>
            <span v-if="enabledModelsCount > 0" class="models-count">{{ enabledModelsCount }} 个可用模型</span>
          </div>
          <div class="toolbar-right">
            <button class="btn-add-provider" @click="addNewProvider">
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z" />
              </svg>
              添加提供商
            </button>
          </div>
        </div>

        <!-- 提供商列表 -->
        <div class="providers-list">
          <!-- 提供商卡片 -->
          <div 
            v-for="(provider, pIndex) in settings.providers" 
            :key="pIndex" 
            class="provider-card"
          >
            <!-- 提供商头部 -->
            <div class="provider-header">
              <div class="provider-info" @click="toggleProviderExpand(pIndex)">
                <svg 
                  class="expand-icon" 
                  :class="{ expanded: provider.expanded }"
                  width="12"
                  height="12"
                  viewBox="0 0 16 16"
                  fill="currentColor"
                >
                  <path fill-rule="evenodd" d="M4.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708L10.293 8 4.646 2.354a.5.5 0 0 1 0-.708z" />
                </svg>
                <span class="provider-name">{{ provider.name || '新提供商' }}</span>
                <span v-if="provider.models && provider.models.length" class="provider-meta">
                  {{ provider.models.length }} 个模型
                </span>
              </div>
              <div class="provider-actions">
                <label class="switch" @click.stop>
                  <input v-model="provider.enabled" type="checkbox" />
                  <span class="slider"></span>
                </label>
                <button class="action-btn delete" title="删除" @click.stop="removeProvider(pIndex)">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                  >
                    <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z" />
                    <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- 提供商配置表单（展开时显示） -->
            <div v-if="provider.expanded" class="provider-body">
              <!-- 配置字段 -->
              <div class="provider-form">
                <div class="form-row">
                  <label class="field-label">名称</label>
                  <input
                    v-model="provider.name"
                    type="text"
                    class="field-input"
                    placeholder="例如: openai"
                  />
                </div>
                <div class="form-row">
                  <label class="field-label">API Key</label>
                  <div class="api-key-wrapper">
                    <input 
                      v-model="provider.apiKey" 
                      :type="provider.showKey ? 'text' : 'password'"
                      class="field-input"
                      placeholder="sk-..."
                    />
                    <button class="btn-toggle-visibility" @click="provider.showKey = !provider.showKey">
                      <svg
                        v-if="provider.showKey"
                        width="16"
                        height="16"
                        viewBox="0 0 16 16"
                        fill="currentColor"
                      >
                        <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM1.173 8a13.133 13.133 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.133 13.133 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5c-2.12 0-3.879-1.168-5.168-2.457A13.134 13.134 0 0 1 1.172 8z" />
                        <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zM4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0z" />
                      </svg>
                      <svg
                        v-else
                        width="16"
                        height="16"
                        viewBox="0 0 16 16"
                        fill="currentColor"
                      >
                        <path d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7.028 7.028 0 0 0-2.79.588l.77.771A5.944 5.944 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.134 13.134 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755-.165.165-.337.328-.517.486l.708.709z" />
                        <path d="M11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829l.822.822zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829z" />
                        <path d="M3.35 5.47c-.18.16-.353.322-.518.487A13.134 13.134 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7.029 7.029 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12-.708.708z" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div class="form-row">
                  <label class="field-label">Base URL</label>
                  <input
                    v-model="provider.baseUrl"
                    type="text"
                    class="field-input"
                    placeholder="https://api.openai.com/v1"
                  />
                </div>
              </div>

              <!-- 模型操作按钮 -->
              <div class="model-actions-bar">
                <button class="btn-fetch" :disabled="provider.fetchingModels" @click="fetchModelsForProvider(pIndex)">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                  >
                    <path fill-rule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z" />
                    <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z" />
                  </svg>
                  {{ provider.fetchingModels ? '获取中...' : '获取模型列表' }}
                </button>
                <button class="btn-custom" @click="addCustomModel(pIndex)">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                  >
                    <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z" />
                  </svg>
                  自定义模型
                </button>
                <button 
                  v-if="provider.availableModels && provider.availableModels.length > 0" 
                  class="btn-hide-available" 
                  @click="hideAvailableModels(pIndex)"
                >
                  收起可用列表
                </button>
              </div>

              <!-- 可用模型列表（从API获取的，临时显示） -->
              <div v-if="provider.availableModels && provider.availableModels.length > 0" class="models-list available-models">
                <div class="models-list-header">
                  <span>可用模型 ({{ provider.availableModels.length }})</span>
                  <span class="header-hint">点击 + 添加模型</span>
                </div>
                <div class="models-list-body">
                  <div 
                    v-for="model in provider.availableModels" 
                    :key="model.id" 
                    class="model-item"
                    :class="{ 'is-added': isModelAdded(provider, model.id) }"
                  >
                    <span class="model-name">{{ model.name || model.id }}</span>
                    <button 
                      v-if="!isModelAdded(provider, model.id)"
                      class="btn-add-model"
                      title="添加模型"
                      @click="addModelFromAvailable(pIndex, model)"
                    >
                      <svg
                        width="12"
                        height="12"
                        viewBox="0 0 16 16"
                        fill="currentColor"
                      >
                        <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z" />
                      </svg>
                    </button>
                    <span v-else class="added-badge">已添加</span>
                  </div>
                </div>
              </div>

              <!-- 已添加的模型列表 -->
              <div v-if="provider.models && provider.models.length > 0" class="models-list added-models">
                <div class="models-list-header">
                  <span>已添加的模型 ({{ provider.models.length }})</span>
                </div>
                <div class="models-list-body">
                  <div 
                    v-for="model in provider.models" 
                    :key="model.id" 
                    class="model-item"
                  >
                    <span class="model-name">{{ model.name || model.id }}</span>
                    <div class="model-actions">
                      <label class="switch switch-sm">
                        <input v-model="model.enabled" type="checkbox" @change="saveSettings" />
                        <span class="slider"></span>
                      </label>
                      <button class="btn-remove-model" title="移除" @click="removeModelFromProvider(pIndex, model.id)">
                        <svg
                          width="12"
                          height="12"
                          viewBox="0 0 16 16"
                          fill="currentColor"
                        >
                          <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 无模型提示 -->
              <div v-if="(!provider.models || provider.models.length === 0) && (!provider.availableModels || provider.availableModels.length === 0)" class="no-models-hint">
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 16 16"
                  fill="currentColor"
                  opacity="0.3"
                >
                  <path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5ZM3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.58 26.58 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.933.933 0 0 1-.765.935c-.845.147-2.34.346-4.235.346-1.895 0-3.39-.2-4.235-.346A.933.933 0 0 1 3 9.219V8.062Z" />
                  <path d="M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2V1.866ZM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5Z" />
                </svg>
                <p>暂无模型，请点击"获取模型列表"或"自定义模型"</p>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="settings.providers.length === 0" class="empty-state">
            <svg
              width="64"
              height="64"
              viewBox="0 0 16 16"
              fill="currentColor"
              opacity="0.2"
            >
              <path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5ZM3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.58 26.58 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.933.933 0 0 1-.765.935c-.845.147-2.34.346-4.235.346-1.895 0-3.39-.2-4.235-.346A.933.933 0 0 1 3 9.219V8.062Zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a24.767 24.767 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25.286 25.286 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135Z" />
              <path d="M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2V1.866ZM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5Z" />
            </svg>
            <p class="empty-text">
              暂无配置的提供商，点击上方"添加提供商"开始配置
            </p>
          </div>
        </div>
      </div>

      <!-- 底部保存按钮 -->
      <div class="setting-footer">
        <button class="btn btn-save" @click="saveSettings">
          保存设置
        </button>
        <span v-if="saveMessage" :class="['save-msg', saveSuccess ? 'success' : 'error']">
          {{ saveMessage }}
        </span>
      </div>
    </div>
  </div>
</template>

<script>
import api from './js/api.js';

export default {
  name: 'SettingPane',
  data() {
    return {
      currentTab: 'general',
      settings: {
        showPanelOnStart: true,
        proofreadMode: 'redblue',
        providers: []
      },
      saveMessage: '',
      saveSuccess: false
    };
  },
  computed: {
    enabledModelsCount() {
      let count = 0;
      this.settings.providers.forEach(p => {
        if (p.enabled && p.models) {
          count += p.models.filter(m => m.enabled).length;
        }
      });
      return count;
    }
  },
  mounted() {
    this.loadSettings();
  },
  methods: {
    async loadSettings() {
      try {
        const data = await api.getSettings();
        if (data && data.providers) {
          this.settings = { ...this.settings, ...data };
          this.settings.providers = this.settings.providers.map(p => ({
            ...p,
            enabled: p.enabled !== false,
            expanded: false,
            showKey: false,
            fetchingModels: false
          }));
        }
      } catch (error) {
        console.error('加载设置失败:', error);
      }
    },
    async saveSettings() {
      try {
        const settingsToSave = {
          ...this.settings,
          providers: this.settings.providers.map(p => ({
            name: p.name,
            baseUrl: p.baseUrl,
            apiKey: p.apiKey,
            models: p.models,
            enabled: p.enabled
          }))
        };

        await api.saveSettings(settingsToSave);

        this.saveMessage = '设置已保存！';
        this.saveSuccess = true;

        setTimeout(() => {
          this.saveMessage = '';
        }, 2000);
      } catch (error) {
        console.error('保存设置失败:', error);
        this.saveMessage = '保存失败，请重试';
        this.saveSuccess = false;
      }
    },
    addNewProvider() {
      const newProvider = {
        name: '',
        baseUrl: '',
        apiKey: '',
        models: [],
        enabled: true,
        expanded: true,
        showKey: false,
        fetchingModels: false
      };
      this.settings.providers.push(newProvider);
    },
    removeProvider(index) {
      if (confirm('确定要删除此提供商吗？')) {
        this.settings.providers.splice(index, 1);
        this.saveSettings();
      }
    },
    toggleProviderExpand(index) {
      this.settings.providers[index].expanded = !this.settings.providers[index].expanded;
    },
    async fetchModelsForProvider(index) {
      const provider = this.settings.providers[index];
      
      if (!provider.apiKey || !provider.baseUrl) {
        alert('请先填写 API Key 和 Base URL');
        return;
      }

      provider.fetchingModels = true;

      try {
        const response = await api.fetchAvailableModels({
          baseUrl: provider.baseUrl,
          apiKey: provider.apiKey
        });

        const availableModels = response.models ? response.models.map(m => ({
          id: m.id || m,
          name: m.name || m.id || m
        })) : [];

        // Vue 3 直接赋值即可实现响应式
        provider.availableModels = availableModels;
      } catch (error) {
        console.error('获取模型失败:', error);
        alert('获取模型失败: ' + (error.message || '请检查配置'));
      } finally {
        provider.fetchingModels = false;
      }
    },
    isModelAdded(provider, modelId) {
      return provider.models && provider.models.some(m => m.id === modelId);
    },
    addModelFromAvailable(providerIndex, model) {
      const provider = this.settings.providers[providerIndex];
      if (!provider.models) {
        provider.models = [];
      }
      
      if (!this.isModelAdded(provider, model.id)) {
        provider.models.push({
          id: model.id,
          name: model.name || model.id,
          enabled: false
        });
        this.saveSettings();
      }
    },
    removeModelFromProvider(providerIndex, modelId) {
      const provider = this.settings.providers[providerIndex];
      if (provider.models) {
        const idx = provider.models.findIndex(m => m.id === modelId);
        if (idx !== -1) {
          provider.models.splice(idx, 1);
          this.saveSettings();
        }
      }
    },
    hideAvailableModels(index) {
      const provider = this.settings.providers[index];
      provider.availableModels = [];
    },
    addCustomModel(index) {
      const modelId = prompt('请输入自定义模型 ID:');
      if (!modelId || !modelId.trim()) {
        return;
      }

      const provider = this.settings.providers[index];
      if (!provider.models) {
        provider.models = [];
      }
      
      const exists = provider.models.some(m => m.id === modelId.trim());
      if (!exists) {
        provider.models.push({
          id: modelId.trim(),
          name: modelId.trim(),
          enabled: false
        });
        this.saveSettings();
      } else {
        alert('该模型已存在');
      }
    }
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
  width: 120px;
  background: #fafafa;
  border-right: 1px solid #e8e8e8;
  padding: 20px 0;
  flex-shrink: 0;
}

.nav-item {
  padding: 12px 24px;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  color: #333;
  background: #f0f0f0;
}

.nav-item.active {
  color: #2563eb;
  background: #eff6ff;
  border-left-color: #2563eb;
  font-weight: 500;
}

/* ========== 右侧内容区 ========== */
.setting-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

/* ========== 通用设置 ========== */
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
  background-color: #2563eb;
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
  border-color: #2563eb;
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
  border-color: #2563eb;
}

.radio-item.active .radio-circle::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 8px;
  height: 8px;
  background: #2563eb;
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

/* ========== 大模型设置 ========== */

/* 工具栏 */
.models-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.models-count {
  font-size: 12px;
  color: #2563eb;
  background: #eff6ff;
  padding: 2px 8px;
  border-radius: 10px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-add-provider {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add-provider:hover {
  background: #1d4ed8;
}

/* 提供商列表 */
.providers-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.provider-card {
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  overflow: hidden;
}

.provider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}

.provider-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.expand-icon {
  color: #999;
  transition: transform 0.2s;
  flex-shrink: 0;
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.provider-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.provider-meta {
  font-size: 12px;
  color: #888;
}

.provider-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  color: #666;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f5f5f5;
  color: #333;
}

.action-btn.delete:hover {
  background: #fee2e2;
  color: #dc2626;
  border-color: #fecaca;
}

/* 提供商内容区 */
.provider-body {
  padding: 16px;
}

.provider-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-row .field-label {
  width: 80px;
  flex-shrink: 0;
  font-size: 13px;
  color: #666;
  margin: 0;
}

.form-row .field-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 13px;
}

.form-row .field-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.api-key-wrapper {
  display: flex;
  gap: 8px;
  flex: 1;
}

.api-key-wrapper .field-input {
  flex: 1;
}

.btn-toggle-visibility {
  padding: 8px 10px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  color: #666;
  transition: all 0.2s;
  display: flex;
  align-items: center;
}

.btn-toggle-visibility:hover {
  background: #e8e8e8;
}

/* 模型操作按钮栏 */
.model-actions-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.btn-fetch,
.btn-custom {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: #2563eb;
  transition: all 0.2s;
}

.btn-fetch:hover:not(:disabled),
.btn-custom:hover {
  background: #f8faff;
  border-color: #2563eb;
}

.btn-fetch:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 模型列表（旧样式保留用于兼容） */
.models-list {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
}

.models-list-header {
  padding: 10px 12px;
  background: #f8f8f8;
  border-bottom: 1px solid #e8e8e8;
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.models-list-body {
  max-height: 240px;
  overflow-y: auto;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0;
}

.model-item:last-child {
  border-bottom: none;
}

.model-name {
  font-size: 13px;
  color: #333;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
}

/* 小号开关 */
.switch-sm {
  width: 36px;
  height: 20px;
}

.switch-sm .slider:before {
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
}

.switch-sm input:checked + .slider:before {
  transform: translateX(16px);
}

/* 可用模型区域 */
.models-list.available-models {
  margin-bottom: 16px;
}

.models-list.available-models .models-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.models-list.available-models .model-item.is-added {
  background: #f9f9f9;
}

.btn-hide-available {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-hide-available:hover {
  background: #f0f0f0;
}

.header-hint {
  font-size: 11px;
  color: #999;
  font-weight: normal !important;
}

.added-badge {
  font-size: 11px;
  color: #10b981;
  background: #d1fae5;
  padding: 2px 8px;
  border-radius: 10px;
}

.btn-add-model {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  cursor: pointer;
  color: #2563eb;
  transition: all 0.2s;
}

.btn-add-model:hover {
  color: #1d4ed8;
}

/* 已添加模型区域 */
.models-list.added-models {
  border-color: #e8e8e8;
}

.model-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-remove-model {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #999;
  transition: all 0.2s;
}

.btn-remove-model:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* 无模型提示 */
.no-models-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 16px;
  color: #999;
}

.no-models-hint svg {
  margin-bottom: 12px;
}

.no-models-hint p {
  font-size: 13px;
  margin: 0;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 64px 24px;
  background: white;
  border: 1px dashed #e0e0e0;
  border-radius: 12px;
}

.empty-state svg {
  margin-bottom: 16px;
}

.empty-text {
  color: #999;
  font-size: 14px;
  margin: 0;
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

.btn-save {
  padding: 10px 32px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-save:hover {
  background: #1d4ed8;
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
</style>

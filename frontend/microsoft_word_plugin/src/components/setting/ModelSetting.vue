<template>
  <div class="model-setting-container">
    <!-- 标题区 -->
    <div class="section-header">
      <svg
        class="section-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
        <line
          x1="12"
          y1="22.08"
          x2="12"
          y2="12"
        />
      </svg>
      <div class="section-title-group">
        <h2 class="section-title">
          大模型服务商配置
        </h2>
        <p class="section-subtitle">
          管理AI服务提供商和模型设置
        </p>
      </div>
    </div>

    <!-- 工具栏 -->
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
        v-for="(provider, pIndex) in localProviders" 
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
                @input="emitChange"
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
                  @input="emitChange"
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
                @input="emitChange"
              />
            </div>
            <div class="form-row">
              <label class="field-label">API 类型</label>
              <div class="api-type-segment">
                <button
                  type="button"
                  class="api-type-btn"
                  :class="{ active: provider.apiType === 'openai' }"
                  @click="setProviderApiType(pIndex, 'openai')"
                >
                  OpenAI 兼容
                </button>
                <button
                  type="button"
                  class="api-type-btn"
                  :class="{ active: provider.apiType === 'anthropic' }"
                  @click="setProviderApiType(pIndex, 'anthropic')"
                >
                  Anthropic
                </button>
              </div>
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
                <div class="model-info">
                  <span class="model-name">{{ model.name || model.id }}</span>
                  <span class="model-id">{{ model.id }}</span>
                </div>
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
                <div class="model-info">
                  <span class="model-name">{{ model.name || model.id }}</span>
                  <span class="model-id">{{ model.id }}</span>
                </div>
                <div class="model-actions">
                  <label class="switch switch-sm">
                    <input v-model="model.enabled" type="checkbox" @change="emitChange" />
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
              xmlns="http://www.w3.org/2000/svg"
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M7 11H5V9H7M14 7H11.38L13.29 9H14V9.75L15.87 11.71C15.95 11.5 16 11.25 16 11V9C16 7.9 15.11 7 14 7M4.45 2.62L3 4L5.86 7H5C3.9 7 3 7.9 3 9V17H5V13H7V17H9V10.3L10 11.34V17H12V13.45L19.55 21.38L21 20M20.9 17H21V15H20V9H21V7H17V9H18V13.95Z" />
            </svg>
            <p>暂无模型，请点击"获取模型列表"</p>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="localProviders.length === 0" class="empty-state">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="64"
          height="64"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M7 11H5V9H7M14 7H11.38L13.29 9H14V9.75L15.87 11.71C15.95 11.5 16 11.25 16 11V9C16 7.9 15.11 7 14 7M4.45 2.62L3 4L5.86 7H5C3.9 7 3 7.9 3 9V17H5V13H7V17H9V10.3L10 11.34V17H12V13.45L19.55 21.38L21 20M20.9 17H21V15H20V9H21V7H17V9H18V13.95Z" />
        </svg>
        <p class="empty-text">
          暂无配置的提供商，点击上方"添加提供商"开始配置
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, computed } from 'vue';
import api from '../js/api.js';

export default {
  name: 'ModelSetting',
  props: {
    providers: {
      type: Array,
      required: true
    }
  },
  emits: ['update:providers'],
  setup(props, { emit }) {
    const localProviders = ref(props.providers.map(p => ({
      ...p,
      apiType: p.apiType || 'openai',
      enabled: p.enabled !== false,
      expanded: p.expanded || false,
      showKey: p.showKey || false,
      fetchingModels: p.fetchingModels || false
    })));

    watch(() => props.providers, (newVal) => {
      localProviders.value = newVal.map(p => ({
        ...p,
        apiType: p.apiType || 'openai',
        enabled: p.enabled !== false,
        expanded: p.expanded || false,
        showKey: p.showKey || false,
        fetchingModels: p.fetchingModels || false
      }));
    }, { deep: true });

    const enabledModelsCount = computed(() => {
      let count = 0;
      localProviders.value.forEach(p => {
        if (p.enabled && p.models) {
          count += p.models.filter(m => m.enabled).length;
        }
      });
      return count;
    });

    const emitChange = () => {
      emit('update:providers', localProviders.value.map(p => ({
        name: p.name,
        baseUrl: p.baseUrl,
        apiKey: p.apiKey,
        apiType: p.apiType || 'openai',
        models: p.models,
        enabled: p.enabled,
        expanded: p.expanded,
        showKey: p.showKey,
        fetchingModels: p.fetchingModels
      })));
    };

    const addNewProvider = () => {
      const newProvider = {
        name: '',
        baseUrl: '',
        apiKey: '',
        apiType: 'openai',
        models: [],
        enabled: true,
        expanded: true,
        showKey: false,
        fetchingModels: false
      };
      localProviders.value.push(newProvider);
      emitChange();
    };

    const removeProvider = (index) => {
      if (confirm('确定要删除此提供商吗？')) {
        localProviders.value.splice(index, 1);
        emitChange();
      }
    };

    const toggleProviderExpand = (index) => {
      localProviders.value[index].expanded = !localProviders.value[index].expanded;
    };

    const fetchModelsForProvider = async (index) => {
      const provider = localProviders.value[index];

      if (!provider.apiKey || !provider.baseUrl) {
        alert('请先填写 API Key 和 Base URL');
        return;
      }

      provider.fetchingModels = true;

      try {
        const response = await api.fetchAvailableModels({
          baseUrl: provider.baseUrl,
          apiKey: provider.apiKey,
          apiType: provider.apiType || 'openai'
        });

        const availableModels = response.models ? response.models.map(m => ({
          id: m.id || m,
          name: m.name || m.id || m
        })) : [];

        provider.availableModels = availableModels;
      } catch (error) {
        console.error('获取模型失败:', error);
        alert('获取模型失败: ' + (error.message || '请检查配置'));
      } finally {
        provider.fetchingModels = false;
      }
    };

    const isModelAdded = (provider, modelId) => {
      return provider.models && provider.models.some(m => m.id === modelId);
    };

    const addModelFromAvailable = (providerIndex, model) => {
      const provider = localProviders.value[providerIndex];
      if (!provider.models) {
        provider.models = [];
      }
      
      if (!isModelAdded(provider, model.id)) {
        provider.models.push({
          id: model.id,
          name: model.name || model.id,
          enabled: false
        });
        emitChange();
      }
    };

    const removeModelFromProvider = (providerIndex, modelId) => {
      const provider = localProviders.value[providerIndex];
      if (provider.models) {
        const idx = provider.models.findIndex(m => m.id === modelId);
        if (idx !== -1) {
          provider.models.splice(idx, 1);
          emitChange();
        }
      }
    };

    const hideAvailableModels = (index) => {
      localProviders.value[index].availableModels = [];
    };

    const setProviderApiType = (index, apiType) => {
      const provider = localProviders.value[index];
      if (!provider) {
        return;
      }
      if (provider.apiType !== apiType) {
        provider.apiType = apiType;
        emitChange();
      }
    };

    return {
      localProviders,
      enabledModelsCount,
      emitChange,
      addNewProvider,
      removeProvider,
      toggleProviderExpand,
      fetchModelsForProvider,
      isModelAdded,
      addModelFromAvailable,
      removeModelFromProvider,
      hideAvailableModels,
      setProviderApiType
    };
  }
};
</script>

<style scoped>
.model-setting-container {
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
  color: #667eea;
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
  background: #667eea;
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
  border-color: #667eea;
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

/* Hide browser-native password reveal icons; keep only the custom eye button. */
.api-key-wrapper .field-input[type='password']::-ms-reveal,
.api-key-wrapper .field-input[type='password']::-ms-clear {
  display: none;
}

.api-key-wrapper .field-input[type='password']::-webkit-credentials-auto-fill-button,
.api-key-wrapper .field-input[type='password']::-webkit-contacts-auto-fill-button {
  visibility: hidden;
  display: none !important;
  pointer-events: none;
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

.api-type-segment {
  display: flex;
  flex: 1;
  gap: 8px;
}

.api-type-btn {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fff;
  color: #555;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.api-type-btn:hover {
  border-color: #667eea;
  color: #4f46e5;
  background: #f8faff;
}

.api-type-btn.active {
  border-color: #667eea;
  color: #fff;
  background: #667eea;
}

/* 模型操作按钮栏 */
.model-actions-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.btn-fetch {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: #667eea;
  transition: all 0.2s;
}

.btn-fetch:hover:not(:disabled) {
  background: #f8faff;
  border-color: #667eea;
}

.btn-fetch:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

/* 模型列表 */
.models-list {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 12px;
}

.models-list:last-child {
  margin-bottom: 0;
}

.models-list-header {
  padding: 10px 12px;
  background: #f8f8f8;
  border-bottom: 1px solid #e8e8e8;
  font-size: 12px;
  color: #666;
  font-weight: 500;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-hint {
  font-size: 11px;
  color: #999;
  font-weight: normal;
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

.model-item.is-added {
  background: #f9f9f9;
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.model-name {
  font-size: 13px;
  color: #333;
}

.model-id {
  font-size: 11px;
  color: #888;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
}

.model-actions {
  display: flex;
  align-items: center;
  gap: 8px;
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
  color: #667eea;
  transition: all 0.2s;
}

.btn-add-model:hover {
  color: #1d4ed8;
}

.added-badge {
  font-size: 11px;
  color: #10b981;
  background: #d1fae5;
  padding: 2px 8px;
  border-radius: 10px;
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

/* 无模型提示 */
.no-models-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 16px;
  color: #bbb;
}

.no-models-hint svg {
  margin-bottom: 12px;
  opacity: 0.5;
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
  color: #bbb;
  border: 1px dashed #e0e0e0;
  border-radius: 12px;
}

.empty-state svg {
  opacity: 0.4;
  margin-bottom: 16px;
}

.empty-text {
  color: #999;
  font-size: 14px;
  margin: 0;
}
</style>

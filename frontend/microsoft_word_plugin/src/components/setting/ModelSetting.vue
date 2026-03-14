<template>
  <div class="model-setting-container">
    <div class="section-header">
      <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
        <line x1="12" y1="22.08" x2="12" y2="12" />
      </svg>
      <div class="section-title-group">
        <h2 class="section-title">大模型服务商配置</h2>
        <p class="section-subtitle">管理AI服务提供商和模型设置</p>
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
          <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z" />
          </svg>
          添加提供商
        </button>
      </div>
    </div>

    <!-- 提供商列表 -->
    <div class="providers-list">
      <div v-for="(provider, pIndex) in localProviders" :key="pIndex" class="provider-card">
        <div class="provider-header">
          <div class="provider-info" @click="toggleProviderExpand(pIndex)">
            <svg class="expand-icon" :class="{ expanded: provider.expanded }" width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
              <path fill-rule="evenodd" d="M4.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708L10.293 8 4.646 2.354a.5.5 0 0 1 0-.708z" />
            </svg>
            <span class="provider-name">{{ provider.name || '新提供商' }}</span>
            <span v-if="provider.models && provider.models.length" class="provider-meta">{{ provider.models.length }} 个模型</span>
          </div>
          <div class="provider-actions">
            <button class="action-btn delete" title="删除" @click.stop="removeProvider(pIndex)">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z" />
                <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4L4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 展开内容 -->
        <div v-if="provider.expanded" class="provider-body">
          <div class="provider-form">
            <div class="form-row">
              <label class="field-label">名称</label>
              <input v-model="provider.name" type="text" class="field-input" placeholder="例如: openai" @input="emitChange" />
            </div>
            <div class="form-row">
              <label class="field-label">API Key</label>
              <div class="api-key-wrapper">
                <input v-model="provider.apiKey" :type="provider.showKey ? 'text' : 'password'" class="field-input" placeholder="sk-..." @input="emitChange" />
                <button class="btn-toggle-visibility" @click="provider.showKey = !provider.showKey">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                    <path v-if="provider.showKey" d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM1.173 8a13.133 13.133 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.133 13.133 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5c-2.12 0-3.879-1.168-5.168-2.457A13.134 13.134 0 0 1 1.172 8z" />
                    <path v-else d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7.028 7.028 0 0 0-2.79.588l.77.771A5.944 5.944 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.134 13.134 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755-.165.165-.337.328-.517.486l.708.709z" />
                  </svg>
                </button>
              </div>
            </div>
            <div class="form-row">
              <label class="field-label">Base URL</label>
              <input v-model="provider.baseUrl" type="text" class="field-input" placeholder="https://api.openai.com/v1" @input="emitChange" />
            </div>
          </div>

          <!-- 已添加的模型列表 -->
          <div v-if="provider.models && provider.models.length > 0" class="models-list">
            <div class="models-list-header">
              <span>已配置模型 ({{ provider.models.length }})</span>
            </div>
            <div class="models-list-body">
              <div v-for="(model, mIndex) in provider.models" :key="model.id" class="model-item">
                <span class="model-name">{{ model.name || model.id }}</span>
                <div class="model-controls">
                  <label class="switch-small">
                    <input v-model="model.enabled" type="checkbox" @change="emitChange" />
                    <span class="slider-small"></span>
                  </label>
                  <button class="btn-remove-model" @click="removeModel(pIndex, mIndex)">
                    <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- 添加自定义模型 -->
          <div class="model-actions-bar">
            <button class="btn-custom" @click="addCustomModel(pIndex)">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z" />
              </svg>
              自定义模型
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';

export default {
  name: 'ModelSetting',
  props: {
    providers: { type: Array, required: true }
  },
  emits: ['update:providers'],
  setup(props, { emit }) {
    const localProviders = ref(JSON.parse(JSON.stringify(props.providers)));

    watch(() => props.providers, (newVal) => {
      localProviders.value = JSON.parse(JSON.stringify(newVal));
    }, { deep: true });

    const enabledModelsCount = computed(() => {
      let count = 0;
      localProviders.value.forEach((p) => {
        if (p.models) {
          count += p.models.filter((m) => m.enabled).length;
        }
      });
      return count;
    });

    const emitChange = () => {
      emit('update:providers', JSON.parse(JSON.stringify(localProviders.value)));
    };

    const addNewProvider = () => {
      localProviders.value.push({
        name: '',
        apiKey: '',
        baseUrl: '',
        models: [],
        expanded: true,
        showKey: false,
        fetchingModels: false,
        availableModels: []
      });
      emitChange();
    };

    const removeProvider = (index) => {
      localProviders.value.splice(index, 1);
      emitChange();
    };

    const toggleProviderExpand = (index) => {
      localProviders.value[index].expanded = !localProviders.value[index].expanded;
    };

    const addCustomModel = (pIndex) => {
      const modelId = prompt('请输入模型 ID（例如 gpt-4o）');
      if (modelId && modelId.trim()) {
        const provider = localProviders.value[pIndex];
        if (!provider.models) provider.models = [];
        provider.models.push({ id: modelId.trim(), name: modelId.trim(), enabled: true });
        emitChange();
      }
    };

    const removeModel = (pIndex, mIndex) => {
      localProviders.value[pIndex].models.splice(mIndex, 1);
      emitChange();
    };

    return {
      localProviders,
      enabledModelsCount,
      emitChange,
      addNewProvider,
      removeProvider,
      toggleProviderExpand,
      addCustomModel,
      removeModel
    };
  }
};
</script>

<style scoped>
.model-setting-container { padding: 0; }

.section-header {
  display: flex; align-items: flex-start; gap: 16px;
  margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid #f0f0f0;
}
.section-icon { width: 24px; height: 24px; color: #667eea; flex-shrink: 0; margin-top: 2px; }
.section-title-group { flex: 1; }
.section-title { font-size: 18px; font-weight: 600; margin: 0 0 4px; color: #2c3e50; }
.section-subtitle { font-size: 13px; color: #7f8c8d; margin: 0; }

.models-toolbar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; padding: 8px 0;
}
.toolbar-title { font-size: 13px; color: #555; font-weight: 500; }
.models-count { font-size: 11px; color: #888; margin-left: 8px; }
.btn-add-provider {
  display: flex; align-items: center; gap: 4px; padding: 6px 12px;
  background: #667eea; color: white; border: none; border-radius: 6px;
  font-size: 12px; cursor: pointer; transition: background 0.2s;
}
.btn-add-provider:hover { background: #5a6fd6; }

.providers-list { display: flex; flex-direction: column; gap: 12px; }

.provider-card {
  background: white; border: 1px solid #e8e8e8; border-radius: 8px; overflow: hidden;
}
.provider-header {
  display: flex; justify-content: space-between; align-items: center; padding: 12px 16px;
}
.provider-info {
  display: flex; align-items: center; gap: 8px; cursor: pointer; flex: 1;
}
.expand-icon { transition: transform 0.2s; color: #888; }
.expand-icon.expanded { transform: rotate(90deg); }
.provider-name { font-size: 14px; font-weight: 500; color: #333; }
.provider-meta { font-size: 11px; color: #888; }
.provider-actions { display: flex; gap: 4px; }
.action-btn.delete {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; padding: 0; background: transparent;
  border: none; border-radius: 4px; color: #999; cursor: pointer; transition: all 0.15s;
}
.action-btn.delete:hover { background: #fff0f0; color: #e74c3c; }

.provider-body { padding: 0 16px 16px; border-top: 1px solid #f0f0f0; }
.provider-form { display: flex; flex-direction: column; gap: 12px; padding-top: 12px; }
.form-row { display: flex; flex-direction: column; gap: 4px; }
.field-label { font-size: 12px; color: #555; font-weight: 500; }
.field-input {
  width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px;
  font-size: 13px; color: #333; background: #fafafa; outline: none;
  transition: border-color 0.2s; box-sizing: border-box;
}
.field-input:focus { border-color: #667eea; background: white; }
.api-key-wrapper { position: relative; display: flex; }
.api-key-wrapper .field-input { padding-right: 36px; }
.btn-toggle-visibility {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: #888; cursor: pointer; padding: 2px;
}
.btn-toggle-visibility:hover { color: #333; }

.models-list { margin-top: 16px; }
.models-list-header {
  font-size: 12px; color: #555; font-weight: 500; margin-bottom: 8px;
  display: flex; align-items: center; justify-content: space-between;
}
.models-list-body { display: flex; flex-direction: column; gap: 4px; }
.model-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; background: #f8f9fa; border-radius: 6px;
}
.model-name { font-size: 12px; color: #333; }
.model-controls { display: flex; align-items: center; gap: 8px; }

/* Small switch */
.switch-small { position: relative; display: inline-block; width: 32px; height: 18px; }
.switch-small input { opacity: 0; width: 0; height: 0; }
.slider-small {
  position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
  background-color: #ccc; transition: 0.3s; border-radius: 18px;
}
.slider-small:before {
  position: absolute; content: ""; height: 14px; width: 14px; left: 2px; bottom: 2px;
  background-color: white; transition: 0.3s; border-radius: 50%;
}
.switch-small input:checked + .slider-small { background-color: #667eea; }
.switch-small input:checked + .slider-small:before { transform: translateX(14px); }

.btn-remove-model {
  display: flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; padding: 0; background: transparent;
  border: none; color: #999; cursor: pointer; border-radius: 4px; transition: all 0.15s;
}
.btn-remove-model:hover { background: #fff0f0; color: #e74c3c; }

.model-actions-bar {
  display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #f0f0f0;
}
.btn-custom {
  display: flex; align-items: center; gap: 4px; padding: 6px 12px;
  background: #f0f0f0; color: #333; border: 1px solid #d0d0d0; border-radius: 6px;
  font-size: 12px; cursor: pointer; transition: all 0.2s;
}
.btn-custom:hover { background: #e8e8e8; border-color: #bbb; }
</style>

<template>
  <div class="mcp-setting-container">
    <div class="section-header">
      <img class="section-icon" :src="iconMcp" alt="MCP 图标" />
      <div class="section-title-group">
        <h2 class="section-title">
          MCP 服务器配置
        </h2>
        <p class="section-subtitle">
          点击服务器卡片可展开编辑，不会打开新窗口
        </p>
      </div>
    </div>

    <div class="toolbar">
      <button class="btn-add-server" @click="addServer">
        <svg
          width="14"
          height="14"
          viewBox="0 0 16 16"
          fill="currentColor"
        >
          <path d="M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4z" />
        </svg>
        添加服务器
      </button>
    </div>

    <div v-if="localServers.length === 0" class="empty-state">
      <p>还没有 MCP 服务器，点击上方“添加服务器”开始配置。</p>
    </div>

    <div class="server-list">
      <div
        v-for="(server, index) in localServers"
        :key="index"
        class="server-card"
      >
        <div class="server-header" @click="toggleExpand(index)">
          <div class="server-info">
            <svg
              class="expand-icon"
              :class="{ expanded: server.expanded }"
              width="12"
              height="12"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path fill-rule="evenodd" d="M4.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708L10.293 8 4.646 2.354a.5.5 0 0 1 0-.708z" />
            </svg>
            <span class="server-name">{{ server.name || '未命名服务器' }}</span>
          </div>
          <div class="server-actions" @click.stop>
            <label class="switch switch-sm" title="启用/禁用 MCP 服务器">
              <input v-model="server.enabled" type="checkbox" @change="emitChange" />
              <span class="slider"></span>
            </label>
            <button class="action-btn delete" title="删除" @click.stop="removeServer(index)">
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

        <div v-if="server.expanded" class="server-body">
          <div class="form-row">
            <label class="field-label">服务器名称</label>
            <input
              v-model="server.name"
              type="text"
              class="field-input"
              placeholder="例如：local-filesystem"
              @input="emitChange"
            />
          </div>

          <div class="form-row">
            <label class="field-label">服务器配置 (JSON)</label>
            <div class="json-editor-wrapper">
              <div :ref="(el) => setLineNumberRef(index, el)" class="json-line-numbers">
                <span v-for="line in getLineCount(server.configSource)" :key="line">{{ line }}</span>
              </div>
              <textarea
                :ref="(el) => setTextareaRef(index, el)"
                v-model="server.configSource"
                class="json-editor"
                rows="10"
                spellcheck="false"
                placeholder="请输入 MCP 服务器 JSON 配置"
                @scroll="syncLineNumberScroll(index)"
                @input="onConfigChange(server, index)"
                @blur="onConfigBlur(server)"
              ></textarea>
            </div>
            <p v-if="server.jsonError" class="json-error">
              {{ server.jsonError }}
            </p>
          </div>

          <div class="action-row">
            <button
              class="btn-test"
              :disabled="server.testing"
              @click="testConnection(index)"
            >
              {{ server.testing ? '测试中...' : '测试连接' }}
            </button>
            <span
              v-if="server.testMessage"
              :class="['test-message', server.testSuccess ? 'success' : 'error']"
            >
              {{ server.testMessage }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { nextTick, ref, watch } from 'vue';
import api from '../js/api.js';
import iconMcp from '../../assets/icons/mcp.svg';

function normalizeServer(server = {}) {
  const name = server.name || '';
  const config = (server.config && typeof server.config === 'object') ? server.config : {};
  const configSource = typeof server.configSource === 'string'
    ? server.configSource
    : JSON.stringify(config, null, 2);

  return {
    name,
    config,
    enabled: server.enabled !== false,
    configSource,
    expanded: server.expanded ?? false,
    testing: false,
    testSuccess: false,
    testMessage: '',
    jsonError: ''
  };
}

export default {
  name: 'MCPserverSetting',
  props: {
    mcpServers: {
      type: Array,
      required: true
    }
  },
  emits: ['update:mcp-servers'],
  setup(props, { emit }) {
    const localServers = ref((props.mcpServers || []).map(normalizeServer));
    const isSyncingFromLocal = ref(false);
    const textareaRefs = {};
    const lineNumberRefs = {};

    watch(() => props.mcpServers, (newVal) => {
      if (isSyncingFromLocal.value) {
        return;
      }
      localServers.value = (newVal || []).map(normalizeServer);
    }, { deep: true });

    const emitChange = () => {
      isSyncingFromLocal.value = true;
      emit('update:mcp-servers', localServers.value.map((s) => ({
        name: s.name,
        config: s.config,
        configSource: s.configSource,
        enabled: s.enabled !== false,
        expanded: s.expanded
      })));
      nextTick(() => {
        isSyncingFromLocal.value = false;
      });
    };

    const getLineCount = (source) => {
      return Math.max(1, (source || '').split('\n').length);
    };

    const setTextareaRef = (index, el) => {
      if (el) {
        textareaRefs[index] = el;
      } else {
        delete textareaRefs[index];
      }
    };

    const setLineNumberRef = (index, el) => {
      if (el) {
        lineNumberRefs[index] = el;
      } else {
        delete lineNumberRefs[index];
      }
    };

    const syncLineNumberScroll = (index) => {
      const textarea = textareaRefs[index];
      const linePanel = lineNumberRefs[index];
      if (textarea && linePanel) {
        linePanel.scrollTop = textarea.scrollTop;
      }
    };

    const parseConfig = (server) => {
      try {
        const source = (server.configSource || '').trim();
        if (!source) {
          server.config = {};
          server.jsonError = '';
          return false;
        }

        const parsed = JSON.parse(server.configSource || '{}');
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
          server.jsonError = '配置必须是 JSON 对象（不能是数组或基础类型）';
          return false;
        }

        // 兼容用户直接粘贴 { mcpServers: { name: config } } 的完整配置格式
        if (parsed.mcpServers && typeof parsed.mcpServers === 'object' && !Array.isArray(parsed.mcpServers)) {
          const entries = Object.entries(parsed.mcpServers);
          if (!entries.length) {
            server.jsonError = 'mcpServers 不能为空对象';
            return false;
          }

          const targetName = server.name && parsed.mcpServers[server.name]
            ? server.name
            : entries[0][0];
          const targetConfig = parsed.mcpServers[targetName];

          if (!targetConfig || typeof targetConfig !== 'object' || Array.isArray(targetConfig)) {
            server.jsonError = 'mcpServers 中的服务器配置必须是对象';
            return false;
          }

          server.name = targetName;
          server.config = targetConfig;
          server.jsonError = '';
          return true;
        }

        server.config = parsed;
        server.jsonError = '';
        return true;
      } catch (error) {
        server.jsonError = `JSON 格式错误: ${error.message}`;
        return false;
      }
    };

    const onConfigChange = (server, index) => {
      const isValid = parseConfig(server);
      syncLineNumberScroll(index);
      if (isValid) {
        emitChange();
      }
    };

    const onConfigBlur = (server) => {
      if (parseConfig(server)) {
        emitChange();
      }
    };

    const addServer = () => {
      localServers.value.push({
        name: '',
        config: {},
        enabled: true,
        configSource: '',
        expanded: true,
        testing: false,
        testSuccess: false,
        testMessage: '',
        jsonError: ''
      });
      emitChange();
    };

    const removeServer = (index) => {
      localServers.value.splice(index, 1);
      emitChange();
    };

    const toggleExpand = (index) => {
      localServers.value[index].expanded = !localServers.value[index].expanded;
      emitChange();
    };

    const testConnection = async (index) => {
      const server = localServers.value[index];
      if (!server.name.trim()) {
        server.testSuccess = false;
        server.testMessage = '请先填写服务器名称';
        return;
      }

      if (!(server.configSource || '').trim()) {
        server.testSuccess = false;
        server.testMessage = '请先填写服务器配置';
        return;
      }

      if (!parseConfig(server)) {
        server.testSuccess = false;
        server.testMessage = '请先修复 JSON 配置';
        return;
      }

      server.testing = true;
      server.testMessage = '';

      try {
        const result = await api.testMcpServer({
          name: server.name,
          config: server.config
        });
        server.testSuccess = !!result.success;
        server.testMessage = result.message || (result.success ? '连接成功' : '连接失败');
      } catch (error) {
        server.testSuccess = false;
        server.testMessage = error.message || '连接失败';
      } finally {
        server.testing = false;
      }
    };

    return {
      iconMcp,
      localServers,
      addServer,
      removeServer,
      toggleExpand,
      onConfigChange,
      onConfigBlur,
      getLineCount,
      setTextareaRef,
      setLineNumberRef,
      syncLineNumberScroll,
      testConnection,
      emitChange
    };
  }
};
</script>

<style scoped>
.mcp-setting-container {
  width: 100%;
}

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

.toolbar {
  margin-bottom: 16px;
}

.btn-add-server {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  border-radius: 8px;
  background: #10b981;
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 12px;
  cursor: pointer;
}

.btn-add-server:hover {
  background: #059669;
}

.empty-state {
  border: 1px dashed #d1d5db;
  border-radius: 10px;
  padding: 20px;
  color: #6b7280;
  font-size: 13px;
  text-align: center;
}

.server-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.server-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  background: #ffffff;
}

.server-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #f9fafb;
  cursor: pointer;
}

.server-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.expand-icon {
  color: #6b7280;
  transition: transform 0.2s ease;
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.server-name {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
}

.server-actions {
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

.server-body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.field-input {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  color: #111827;
  outline: none;
}

.field-input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.15);
}

.json-editor {
  width: 100%;
  border: none;
  border-left: 1px solid #1f2937;
  border-radius: 0;
  padding: 12px;
  box-sizing: border-box;
  background: transparent;
  color: #e5e7eb;
  font-size: 12px;
  line-height: 1.5;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  outline: none;
  resize: vertical;
  min-height: 220px;
}

.json-editor-wrapper {
  display: flex;
  border: 1px solid #111827;
  border-radius: 8px;
  background: #0b0f17;
  overflow: hidden;
}

.json-editor-wrapper:focus-within {
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.json-line-numbers {
  width: 42px;
  padding: 12px 8px;
  box-sizing: border-box;
  background: #0f1520;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
  text-align: right;
  user-select: none;
  overflow: hidden;
}

.json-line-numbers span {
  display: block;
}

.json-error {
  margin: 0;
  color: #dc2626;
  font-size: 12px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.btn-test {
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  background: #4f46e5;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
}

.btn-test:hover:not(:disabled) {
  background: #4338ca;
}

.btn-test:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.test-message {
  font-size: 12px;
}

.test-message.success {
  color: #059669;
}

.test-message.error {
  color: #dc2626;
}

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
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.switch input:checked + .slider {
  background-color: #667eea;
}

.switch input:checked + .slider:before {
  transform: translateX(20px);
}

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
</style>

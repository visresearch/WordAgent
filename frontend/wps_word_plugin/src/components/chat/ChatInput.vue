<template>
  <div>
    <!-- 已添加文件预览列表 -->
    <div v-for="(file, index) in uploadedFiles" :key="`${file.name}-${file.size}-${file.lastModified}-${index}`" class="current-selection-bar">
      <div class="selection-bar-content">
        <div class="selection-bar-icon">
          <img :src="fileIcon" alt="附件" class="selection-bar-icon-img" />
        </div>
        <div class="selection-bar-info">
          <span class="selection-bar-preview">{{ file.name }} ({{ formatFileSize(file.size) }})</span>
        </div>
        <button class="selection-bar-clear" title="移除文件" @click="$emit('remove-file', index)">
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

    <!-- 多选区预览列表 -->
    <div v-for="(sel, index) in selections" :key="index" class="current-selection-bar">
      <div class="selection-bar-content">
        <div class="selection-bar-icon">
          <svg
            width="14"
            height="14"
            viewBox="0 0 16 16"
            fill="currentColor"
          >
            <path
              d="M14 1H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z"
            />
            <path d="M3 4h10v1H3V4zm0 3h10v1H3V7zm0 3h6v1H3v-1z" />
          </svg>
        </div>
        <div class="selection-bar-info">
          <span class="selection-bar-preview">{{ sel.startText }} → {{ sel.endText }} (段落 {{ sel.startParaIndex }} - {{ sel.endParaIndex }})</span>
        </div>
        <button class="selection-bar-clear" title="清除选区" @click="$emit('remove-selection', index)">
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

    <!-- 统一的 AI 操作确认条（删除+生成合并显示） -->
    <div v-if="pendingDeletes.length > 0 || pendingDocument" class="current-selection-bar pending-document-bar" :class="{ 'pending-delete-bar': pendingDeletes.length > 0 && !pendingDocument }">
      <div class="selection-bar-content">
        <div class="selection-bar-icon pending-icon" :class="{ 'pending-delete-icon': pendingDeletes.length > 0 && !pendingDocument }">
          <svg
            width="14"
            height="14"
            viewBox="0 0 16 16"
            fill="currentColor"
          >
            <path
              d="M14 1H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z"
            />
            <path d="M3 4h10v1H3V4zm0 3h10v1H3V7zm0 3h6v1H3v-1z" />
          </svg>
        </div>
        <div class="selection-bar-info">
          <span class="selection-bar-preview">{{ pendingSummary }}</span>
        </div>
        <div class="pending-actions">
          <button class="pending-btn confirm-btn" :class="{ 'delete-confirm-btn': pendingDeletes.length > 0 && !pendingDocument }" @click="$emit('confirm-pending')">
            确定
          </button>
          <button class="pending-btn cancel-btn" @click="$emit('cancel-pending')">
            取消
          </button>
        </div>
      </div>
    </div>

    <div class="chat-input-area">
      <div class="input-container">
        <textarea
          ref="chatInput"
          v-model="inputText"
          :placeholder="inputPlaceholder"
          class="chat-input"
          rows="1"
          @keydown.enter.exact.prevent="sendMessage"
          @input="autoResize"
        ></textarea>
        <div class="input-toolbar">
          <div class="toolbar-left">
            <!-- 模式选择 -->
            <div class="custom-select" :class="{ open: modeDropdownOpen }">
              <div class="select-trigger" @click="toggleModeDropdown">
                <span class="mode-option-content">
                  <span class="mode-option-icon" :style="modeIconStyle(currentModeIcon)" aria-hidden="true"></span>
                  <span>{{ currentModeLabel }}</span>
                </span>
                <svg
                  class="select-arrow"
                  width="8"
                  height="8"
                  viewBox="0 0 12 12"
                >
                  <path
                    d="M3 4.5L6 7.5L9 4.5"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    fill="none"
                  />
                </svg>
              </div>
              <div class="select-dropdown">
                <div
                  class="select-option"
                  :class="{ active: mode === 'agent' }"
                  @click="selectMode('agent')"
                >
                  <span class="mode-option-icon" :style="modeIconStyle(agentIcon)" aria-hidden="true"></span>
                  <span>Agent</span>
                </div>
                <div
                  class="select-option"
                  :class="{ active: mode === 'ask' }"
                  @click="selectMode('ask')"
                >
                  <span class="mode-option-icon" :style="modeIconStyle(askIcon)" aria-hidden="true"></span>
                  <span>Ask</span>
                </div>
                <div
                  class="select-option"
                  :class="{ active: mode === 'plan' }"
                  @click="selectMode('plan')"
                >
                  <span class="mode-option-icon" :style="modeIconStyle(planIcon)" aria-hidden="true"></span>
                  <span>Plan</span>
                </div>
              </div>
            </div>

            <!-- 模型选择 -->
            <div
              class="custom-select"
              :class="{ open: modelDropdownOpen, disabled: modelsLoading }"
            >
              <div class="select-trigger" @click="toggleModelDropdown">
                <span v-if="modelsLoading">加载中...</span>
                <span v-else>{{ selectedModelName }}</span>
                <svg
                  class="select-arrow"
                  width="8"
                  height="8"
                  viewBox="0 0 12 12"
                >
                  <path
                    d="M3 4.5L6 7.5L9 4.5"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    fill="none"
                  />
                </svg>
              </div>
              <div class="select-dropdown model-dropdown">
                <div
                  v-for="model in availableModels"
                  :key="model.id"
                  class="select-option"
                  :class="{ active: selectedModel === model.id }"
                  @click="selectModel(model.id)"
                >
                  {{ model.name }}
                </div>
              </div>
            </div>
          </div>
          <div class="toolbar-right">
            <div class="btn-wrapper token-ring-wrapper">
              <div class="token-ring">
                <svg viewBox="0 0 12 12" class="token-ring-svg">
                  <circle
                    cx="6"
                    cy="6"
                    r="4"
                    fill="none"
                    stroke="#e0e0e0"
                    stroke-width="2"
                  />
                  <circle
                    cx="6"
                    cy="6"
                    r="4"
                    fill="none"
                    :stroke="tokenRingColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-dasharray="25.13"
                    :stroke-dashoffset="tokenRingOffset"
                    transform="rotate(-90 6 6)"
                  />
                </svg>
              </div>
              <div class="token-ring-tooltip">
                {{ tokenRingTitle }}
              </div>
            </div>
            <div class="btn-wrapper">
              <button class="add-selection-btn" title="添加文件" @click="triggerFilePicker">
                <img :src="fileIcon" alt="添加文件" class="toolbar-icon" />
              </button>
              <span class="tooltip">添加文件</span>
            </div>
            <input
              ref="fileInput"
              type="file"
              class="file-input-hidden"
              accept=".png,.jpg,.jpeg,.pdf,.docx,.txt,.md"
              multiple
              @change="handleFileChange"
            />
            <div class="btn-wrapper">
              <button class="add-selection-btn" title="添加选区" @click="$emit('add-selection')">
                <img :src="addIcon" alt="添加选区" class="toolbar-icon" />
              </button>
              <span class="tooltip">添加选区</span>
            </div>
            <div class="btn-wrapper">
              <button
                v-if="!isLoading"
                class="send-btn"
                :disabled="!inputText.trim()"
                @click="sendMessage"
              >
                <img :src="sendIcon" alt="发送" class="toolbar-icon" />
              </button>
              <button v-else class="stop-btn" @click="$emit('stop')">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 16 16"
                  fill="none"
                >
                  <circle
                    cx="8"
                    cy="8"
                    r="7"
                    stroke="currentColor"
                    stroke-width="1.5"
                    fill="none"
                  />
                  <rect
                    x="5"
                    y="5"
                    width="6"
                    height="6"
                    rx="0.5"
                    fill="currentColor"
                  />
                </svg>
              </button>
              <span class="tooltip">{{ isLoading ? '终止' : '发送' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import addIcon from '@/assets/icons/add.svg';
import agentIcon from '@/assets/icons/agent.svg?url';
import askIcon from '@/assets/icons/ask.svg?url';
import fileIcon from '@/assets/icons/file.svg';
import planIcon from '@/assets/icons/plan.svg?url';
import sendIcon from '@/assets/icons/send.svg';

export default {
  name: 'ChatInput',
  props: {
    mode: {
      type: String,
      default: 'agent'
    },
    selectedModel: {
      type: String,
      default: ''
    },
    availableModels: {
      type: Array,
      default: () => []
    },
    modelsLoading: {
      type: Boolean,
      default: false
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    selections: {
      type: Array,
      default: () => []
    },
    uploadedFiles: {
      type: Array,
      default: () => []
    },
    pendingDocument: {
      type: Object,
      default: null
    },
    pendingDeletes: {
      type: Array,
      default: () => []
    },
    tokenStats: {
      type: Object,
      default: () => ({ current: 0, max: 200000 })
    }
  },
  emits: ['send', 'stop', 'add-selection', 'remove-selection', 'add-files', 'remove-file', 'update:mode', 'update:selectedModel', 'refresh-models', 'confirm-pending', 'cancel-pending'],
  data() {
    return {
      inputText: '',
      modeDropdownOpen: false,
      modelDropdownOpen: false,
      addIcon,
      agentIcon,
      askIcon,
      fileIcon,
      planIcon,
      sendIcon
    };
  },
  computed: {
    inputPlaceholder() {
      if (this.mode === 'plan') {
        return '概述需要研究的目标或问题';
      }
      if (this.mode === 'ask') {
        return '输入要咨询的问题';
      }
      return '描述下一步要构建的内容';
    },
    currentModeLabel() {
      if (this.mode === 'plan') {
        return 'Plan';
      }
      if (this.mode === 'ask') {
        return 'Ask';
      }
      return 'Agent';
    },
    currentModeIcon() {
      if (this.mode === 'plan') {
        return this.planIcon;
      }
      if (this.mode === 'ask') {
        return this.askIcon;
      }
      return this.agentIcon;
    },
    selectedModelName() {
      const model = this.availableModels.find((m) => m.id === this.selectedModel);
      return model ? model.name : '选择模型';
    },
    pendingSummary() {
      const parts = [];
      if (this.pendingDeletes.length > 0) {
        const totalDeleteParas = this.pendingDeletes.reduce((sum, d) => {
          const start = d.origStartParaIndex ?? d.startParaIndex ?? 0;
          const end = d.origEndParaIndex ?? d.endParaIndex ?? start;
          return sum + (end - start + 1);
        }, 0);
        parts.push(`删除 ${totalDeleteParas} 个段落`);
      }
      if (this.pendingDocument) {
        parts.push(this.pendingDocument.preview);
      }
      return 'AI 操作：' + parts.join('，');
    },
    tokenRingOffset() {
      const max = this.tokenStats.max || 200000;
      const percentage = max > 0 ? Math.min(100, (this.tokenStats.current || 0) / max * 100) : 0;
      const circumference = 25.13; // 2 * PI * 4
      return circumference * (1 - percentage / 100);
    },
    tokenRingColor() {
      const max = this.tokenStats.max || 200000;
      const percentage = max > 0 ? Math.min(100, (this.tokenStats.current || 0) / max * 100) : 0;
      if (percentage >= 90) {
        return '#e74c3c';
      }
      if (percentage >= 70) {
        return '#f39c12';
      }
      return '#667eea';
    },
    tokenRingTitle() {
      const current = this.tokenStats.current || 0;
      const max = this.tokenStats.max || 200000;
      const currentK = (current / 1000).toFixed(1);
      const maxK = (max / 1000).toFixed(0);
      const percentage = max > 0 ? Math.min(100, Math.round(current / max * 100)) : 0;
      return `上下文：${currentK}k / ${maxK}k tokens（${percentage}%）`;
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.autoResize();
    });
    document.addEventListener('click', this.closeDropdowns);
  },
  beforeUnmount() {
    document.removeEventListener('click', this.closeDropdowns);
  },
  methods: {
    autoResize() {
      const textarea = this.$refs.chatInput;
      if (textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
      }
    },

    triggerFilePicker() {
      const fileInput = this.$refs.fileInput;
      if (fileInput) {
        fileInput.click();
      }
    },

    handleFileChange(event) {
      const fileList = event?.target?.files;
      if (!fileList || fileList.length === 0) {
        return;
      }

      const allowedExtensions = new Set(['png', 'jpg', 'jpeg', 'pdf', 'docx', 'txt', 'md']);
      const validFiles = [];
      const invalidFiles = [];

      for (const file of Array.from(fileList)) {
        const fileName = file.name || '';
        const ext = fileName.includes('.') ? fileName.split('.').pop().toLowerCase() : '';
        if (allowedExtensions.has(ext)) {
          validFiles.push(file);
        } else {
          invalidFiles.push(fileName || '未命名文件');
        }
      }

      if (validFiles.length > 0) {
        this.$emit('add-files', validFiles);
      }

      if (invalidFiles.length > 0) {
        alert(`以下文件格式不支持：${invalidFiles.join('，')}。仅支持 png、jpg、pdf、docx、txt、md。`);
      }

      event.target.value = '';
    },

    formatFileSize(size) {
      if (!size || size <= 0) {
        return '0 B';
      }
      const units = ['B', 'KB', 'MB', 'GB'];
      let index = 0;
      let value = size;
      while (value >= 1024 && index < units.length - 1) {
        value /= 1024;
        index++;
      }
      return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
    },

    sendMessage() {
      if (!this.inputText.trim() || this.isLoading) {
        return;
      }
      const text = this.inputText.trim();
      this.$emit('send', text);
      this.inputText = '';
      this.$nextTick(() => {
        this.autoResize();
      });
    },

    toggleModeDropdown(e) {
      e.stopPropagation();
      this.modelDropdownOpen = false;
      this.modeDropdownOpen = !this.modeDropdownOpen;
    },

    toggleModelDropdown(e) {
      if (this.modelsLoading) {
        return;
      }
      e.stopPropagation();
      this.modeDropdownOpen = false;
      if (!this.modelDropdownOpen) {
        this.$emit('refresh-models');
      }
      this.modelDropdownOpen = !this.modelDropdownOpen;
    },

    selectMode(value) {
      this.$emit('update:mode', value);
      this.modeDropdownOpen = false;
    },

    selectModel(id) {
      this.$emit('update:selectedModel', id);
      this.modelDropdownOpen = false;
    },

    modeIconStyle(icon) {
      return {
        '--mode-icon-url': `url(${icon})`
      };
    },

    closeDropdowns() {
      this.modeDropdownOpen = false;
      this.modelDropdownOpen = false;
    }
  }
};
</script>

<style scoped>
/* 当前选区预览条 */
.current-selection-bar {
  background: #f0f0f0;
  border-top: 1px solid #d8d8d8;
  border-bottom: 1px solid #d8d8d8;
  padding: 6px 10px;
}

.selection-bar-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selection-bar-icon {
  flex-shrink: 0;
  color: #667eea;
  display: flex;
  align-items: center;
}

.selection-bar-icon-img {
  width: 14px;
  height: 14px;
  display: block;
  user-select: none;
}

.selection-bar-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.selection-bar-preview {
  font-size: 11px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.selection-bar-range {
  font-size: 9px;
  color: #888;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.selection-bar-clear {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  color: #333;
  border: none;
  border-radius: 0;
  cursor: pointer;
  transition: all 0.2s;
}

.selection-bar-clear:hover {
  background: #f5f5f5;
  color: #000;
  border-color: #ccc;
}

/* 修改预览条 */
.pending-document-bar {
  border-top: 1px solid #d8d8d8;
  border-bottom: 1px solid #d8d8d8;
  background: #f0f0f0;
}

/* 删除预览条 */
.pending-delete-bar {
  background: #fff5f5;
  border-top-color: #ffcccc;
  border-bottom-color: #ffcccc;
}

.pending-icon {
  color: #e74c3c !important;
}

.pending-delete-icon {
  color: #dc3545 !important;
}

.pending-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.pending-btn {
  padding: 2px 10px;
  font-size: 11px;
  border-radius: 4px;
  border: 1px solid #ddd;
  cursor: pointer;
  transition: all 0.2s;
  line-height: 1.4;
}

.confirm-btn {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.confirm-btn:hover {
  background: #5a6fd6;
  border-color: #5a6fd6;
}

.delete-confirm-btn {
  background: #dc3545;
  border-color: #dc3545;
}

.delete-confirm-btn:hover {
  background: #c82333;
  border-color: #c82333;
}

.cancel-btn {
  background: white;
  color: #666;
  border-color: #ddd;
}

.cancel-btn:hover {
  background: #f5f5f5;
  color: #333;
  border-color: #ccc;
}

/* 输入区域 */
.chat-input-area {
  padding: 12px 12px;
  background: #f7f8fa;
  flex-shrink: 0;
}

.input-container {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.chat-input {
  width: 100%;
  padding: 6px 10px;
  padding-bottom: 0;
  border: none;
  resize: none;
  font-size: 12px;
  font-family: inherit;
  outline: none;
  background: transparent;
  color: #333;
  box-sizing: border-box;
  overflow: hidden;
  min-height: 20px;
  max-height: 150px;
  line-height: 1.4;
  user-select: none;
}

.chat-input::placeholder {
  color: #999;
}

.input-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 6px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 4px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-wrapper {
  position: relative;
  display: inline-flex;
}

.btn-wrapper .tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  padding: 3px 6px;
  background: white;
  color: #333;
  font-size: 10px;
  border-radius: 4px;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition:
    opacity 0.2s,
    visibility 0.2s;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border: 1px solid #e0e0e0;
  margin-bottom: 4px;
}

.btn-wrapper:hover .tooltip {
  opacity: 1;
  visibility: visible;
}

/* 自定义下拉组件 */
.custom-select {
  position: relative;
  display: inline-flex;
  font-size: 8px;
}

.custom-select.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.select-trigger {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
  color: #666;
  cursor: pointer;
  border-radius: 3px;
  transition: color 0.2s;
  user-select: none;
}

.select-trigger:hover {
  color: #667eea;
}

.custom-select.open .select-trigger {
  color: #667eea;
}

.select-arrow {
  transition: transform 0.2s;
}

.custom-select.open .select-arrow {
  transform: rotate(180deg);
}

.select-dropdown {
  position: absolute;
  bottom: 100%;
  left: 0;
  min-width: 100%;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 2px 0;
  margin-bottom: 4px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(4px);
  transition:
    opacity 0.15s,
    visibility 0.15s,
    transform 0.15s;
  z-index: 100;
}

.custom-select.open .select-dropdown {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.model-dropdown {
  min-width: 100px;
}

.mode-option-content {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.mode-option-icon {
  width: 11px;
  height: 11px;
  display: block;
  flex-shrink: 0;
  background-color: currentColor;
  -webkit-mask-image: var(--mode-icon-url);
  mask-image: var(--mode-icon-url);
  -webkit-mask-repeat: no-repeat;
  mask-repeat: no-repeat;
  -webkit-mask-position: center;
  mask-position: center;
  -webkit-mask-size: contain;
  mask-size: contain;
}

.select-option {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px;
  color: #333;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}

.select-option:hover {
  background: #f5f5f5;
}

.select-option.active {
  color: #667eea;
  background: #f0f4ff;
}

.add-selection-btn {
  width: 18px;
  height: 18px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #888;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
}

.add-selection-btn:hover {
  background: #f0f0f0;
  color: #667eea;
}

.toolbar-icon {
  width: 12px;
  height: 12px;
  display: block;
  user-select: none;
}

.file-input-hidden {
  display: none;
}

.send-btn {
  width: 18px;
  height: 18px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #888;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: #f0f0f0;
  color: #667eea;
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.stop-btn {
  width: 18px;
  height: 18px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #e74c3c;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
}

.stop-btn:hover {
  background: #fef0ef;
  color: #c0392b;
}

/* Token 环样式 */
.token-ring-wrapper {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: default;
  width: 12px;
  height: 12px;
}

.token-ring {
  width: 12px;
  height: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.token-ring-svg {
  width: 100%;
  height: 100%;
}

.token-ring-wrapper:hover .token-ring-tooltip {
  opacity: 1;
  visibility: visible;
}

.token-ring-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  padding: 3px 6px;
  background: white;
  color: #333;
  font-size: 10px;
  border-radius: 4px;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition:
    opacity 0.2s,
    visibility 0.2s;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border: 1px solid #e0e0e0;
  margin-bottom: 4px;
}
</style>

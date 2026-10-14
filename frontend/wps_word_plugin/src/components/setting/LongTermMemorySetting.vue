<template>
  <div class="setting-section">
    <div class="section-header">
      <svg
        class="section-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z" />
        <path d="M12 6v6l4 2" />
      </svg>
      <div class="section-title-group">
        <h2 class="section-title">
          {{ $t('data.memory') }}
        </h2>
        <p class="section-subtitle">
          {{ $t('data.memoryDesc') }}
        </p>
      </div>
    </div>

    <div class="setting-row">
      <span class="setting-label">{{ $t('data.enableMemory') }}</span>
      <label class="switch">
        <input
          :checked="enabled"
          type="checkbox"
          :disabled="typeof enabled !== 'boolean'"
          @change="$emit('update:enabled', $event.target.checked)"
        />
        <span class="slider"></span>
      </label>
    </div>

    <div class="memory-editor-box">
      <div class="json-editor-wrapper">
        <div :ref="setMemoryLineNumberRef" class="json-line-numbers">
          <span v-for="line in memoryLineCount" :key="line">{{ line }}</span>
        </div>
        <textarea
          ref="memoryTextareaRef"
          v-model="memoryContent"
          class="json-editor memory-json-editor"
          spellcheck="false"
          :placeholder="$t('data.memoryPlaceholder')"
          :disabled="memoryLoading"
          @input="onMemoryInput"
          @scroll="syncMemoryLineNumberScroll"
        ></textarea>
      </div>
    </div>

    <div class="memory-hint">
      <span class="hint-icon">💡</span>
      <span>{{ $t('data.memoryHint') }}</span>
    </div>

    <div class="action-area">
      <button class="btn btn-secondary" :disabled="memoryLoading" @click="loadMemory">
        {{ memoryLoading ? $t('common.loading') : $t('common.refresh') }}
      </button>
      <button
        class="btn btn-primary"
        :disabled="!memoryHasChanged || memorySaving"
        @click="saveMemory"
      >
        <svg
          v-if="memorySaving"
          class="loading-spinner"
          width="16"
          height="16"
          viewBox="0 0 24 24"
        >
          <circle
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
            fill="none"
            stroke-dasharray="31.4"
            stroke-dashoffset="10"
          />
        </svg>
        {{ memorySaving ? $t('common.saving') : $t('data.saveMemory') }}
      </button>
    </div>
    <p v-if="resultMessage" class="memory-result" :class="{ error: !resultSuccess }">
      {{ resultMessage }}
    </p>
  </div>
</template>

<script>
import { computed, nextTick, onMounted, ref } from 'vue';
import api from '../js/api.js';
import { t } from '../../i18n/index.js';

export default {
  name: 'LongTermMemorySetting',
  props: { enabled: { type: Boolean, default: undefined } },
  emits: ['update:enabled'],
  setup() {
    const resultMessage = ref('');
    const resultSuccess = ref(false);
    // 长期记忆相关
    const memoryContent = ref('');
    const memoryLoading = ref(false);
    const memorySaving = ref(false);
    const memoryHasChanged = ref(false);
    const memoryTextareaRef = ref(null);
    const memoryLineNumberRef = ref(null);

    const memoryLineCount = computed(() =>
      Math.max(1, (memoryContent.value || '').split('\n').length)
    );

    const syncMemoryLineNumberScroll = () => {
      if (memoryTextareaRef.value && memoryLineNumberRef.value) {
        memoryLineNumberRef.value.scrollTop = memoryTextareaRef.value.scrollTop;
      }
    };

    const setMemoryLineNumberRef = (el) => {
      memoryLineNumberRef.value = el;
    };

    const onMemoryInput = () => {
      memoryHasChanged.value = true;
      nextTick(syncMemoryLineNumberScroll);
    };

    const loadMemory = async () => {
      memoryLoading.value = true;
      try {
        const content = await api.getMemory();
        memoryContent.value = content;
        memoryHasChanged.value = false;
        nextTick(syncMemoryLineNumberScroll);
      } catch (error) {
        console.error('加载长期记忆失败:', error);
        resultMessage.value = t('data.memoryLoadFailed', {
          error: error.message || t('common.unknownError')
        });
        resultSuccess.value = false;
        setTimeout(() => {
          resultMessage.value = '';
        }, 5000);
      } finally {
        memoryLoading.value = false;
      }
    };

    const saveMemory = async () => {
      memorySaving.value = true;
      try {
        await api.saveMemory(memoryContent.value);
        memoryHasChanged.value = false;
        resultMessage.value = t('data.memorySaved');
        resultSuccess.value = true;
        setTimeout(() => {
          resultMessage.value = '';
        }, 3000);
      } catch (error) {
        console.error('保存长期记忆失败:', error);
        resultMessage.value = t('data.memorySaveFailed', {
          error: error.message || t('common.unknownError')
        });
        resultSuccess.value = false;
        setTimeout(() => {
          resultMessage.value = '';
        }, 5000);
      } finally {
        memorySaving.value = false;
      }
    };

    onMounted(loadMemory);
    return {
      resultMessage,
      resultSuccess,
      memoryContent,
      memoryLoading,
      memorySaving,
      memoryHasChanged,
      memoryLineCount,
      memoryTextareaRef,
      loadMemory,
      saveMemory,
      setMemoryLineNumberRef,
      syncMemoryLineNumberScroll,
      onMemoryInput
    };
  }
};
</script>

<style scoped src="./setting.css"></style>
<style scoped>
.memory-editor-box {
  margin-bottom: 12px;
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

.memory-json-editor {
  flex: 1;
  padding: 12px;
  border: none;
  border-radius: 0;
  background: transparent;
  color: #e5e7eb;
  font-size: 13px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  line-height: 1.5;
  resize: none;
  outline: none;
  white-space: pre;
  overflow: auto;
}

.memory-json-editor::placeholder {
  color: #6b7280;
}

.memory-json-editor:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.memory-hint {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 16px;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 2px;
  margin-bottom: 10px;
}

.setting-label {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
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
  inset: 0;
  background-color: #cbd5e1;
  transition: 0.2s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: '';
  height: 18px;
  width: 18px;
  left: 3px;
  top: 3px;
  background-color: white;
  transition: 0.2s;
  border-radius: 50%;
}

.switch input:checked + .slider {
  background-color: #667eea;
}

.switch input:checked + .slider:before {
  transform: translateX(20px);
}

.hint-icon {
  flex-shrink: 0;
}

.memory-json-editor {
  min-height: 200px;
}
.switch input:disabled + .slider {
  opacity: 0.5;
  cursor: not-allowed;
}
.memory-result {
  color: #059669;
  font-size: 13px;
}
.memory-result.error {
  color: #dc2626;
}
.action-area {
  display: flex;
  gap: 12px;
}
.btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}
.btn-primary {
  color: white;
  background: #667eea;
}
.btn-secondary {
  color: #374151;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.loading-spinner {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>

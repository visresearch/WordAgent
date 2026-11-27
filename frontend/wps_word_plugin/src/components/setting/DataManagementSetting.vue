<template>
  <div class="data-management-container">
    <!-- 清除缓存 -->
    <section class="setting-section">
      <div class="section-header">
        <svg
          class="section-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M21 4H8l-7 8 7 8h13a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z" />
          <line
            x1="18"
            y1="9"
            x2="12"
            y2="15"
          />
          <line
            x1="12"
            y1="9"
            x2="18"
            y2="15"
          />
        </svg>
        <div class="section-title-group">
          <h2 class="section-title">
            {{ $t('data.clearCache') }}
          </h2>
          <p class="section-subtitle">
            {{ $t('data.clearCacheDesc') }}
          </p>
        </div>
      </div>

      <dl class="cache-details">
        <div class="cache-row">
          <dt>{{ $t('data.cacheLocation') }}</dt>
          <dd>{{ cacheDir || 'wence_data/project/temp；wence_data/project/uploads' }}</dd>
        </div>
        <div class="cache-row">
          <dt>{{ $t('data.cacheSize') }}</dt>
          <dd>{{ cacheSizeText }}</dd>
        </div>
      </dl>

      <div class="action-area">
        <button
          class="btn btn-secondary"
          :disabled="scanningCache"
          @click="scanCache"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <circle cx="11" cy="11" r="8" />
            <line
              x1="21"
              y1="21"
              x2="16.65"
              y2="16.65"
            />
          </svg>
          {{ scanningCache ? $t('data.scanning') : $t('data.scan') }}
        </button>
        <button
          class="btn btn-primary"
          :disabled="clearingCache || cacheFileCount === 0"
          @click="clearCache"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
          {{ clearingCache ? $t('data.clearing') : $t('data.clearCache') }}
        </button>
      </div>
    </section>

    <!-- 数据清理 -->
    <section class="setting-section">
      <div class="section-header">
        <svg
          class="section-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          <line
            x1="10"
            y1="11"
            x2="10"
            y2="17"
          />
          <line
            x1="14"
            y1="11"
            x2="14"
            y2="17"
          />
        </svg>
        <div class="section-title-group">
          <h2 class="section-title">
            {{ $t('data.deleteAll') }}
          </h2>
          <p class="section-subtitle">
            {{ $t('data.deleteAllDesc') }}
          </p>
        </div>
      </div>

      <div class="warning-box">
        <span
          class="warning-icon section-icon-mask"
          :style="{ '--section-icon-url': 'url(' + warningIcon + ')' }"
          aria-hidden="true"
        ></span>
        <div class="warning-content">
          <p class="warning-title">
            {{ $t('data.warning') }}
          </p>
          <p>
            {{ $t('data.deleteIncludes') }}
          </p>
          <ul class="warning-list">
            <li>{{ $t('data.chats') }}</li>
            <li>{{ $t('data.cachedDocs') }}</li>
            <li>{{ $t('data.sessionState') }}</li>
          </ul>
        </div>
      </div>

      <div class="action-area">
        <button
          class="btn btn-danger"
          :disabled="deleting"
          @click="showDeleteConfirm = true"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="currentColor"
          >
            <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z" />
            <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z" />
          </svg>
          {{ $t('data.deleteAll') }}
        </button>
      </div>

      <!-- 删除确认对话框 -->
      <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
        <div class="modal-dialog">
          <div class="modal-header">
            <svg
              class="modal-icon"
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line
                x1="15"
                y1="9"
                x2="9"
                y2="15"
              />
              <line
                x1="9"
                y1="9"
                x2="15"
                y2="15"
              />
            </svg>
            <h3 class="modal-title">
              {{ $t('data.confirmTitle') }}
            </h3>
          </div>

          <div class="modal-body">
            <p>{{ $t('data.confirmBody') }}</p>
            <div class="confirm-input-group">
              <label for="data-delete-confirm">{{ $t('data.typeDelete') }}</label>
              <input
                id="data-delete-confirm"
                v-model="confirmText"
                type="text"
                class="confirm-input"
                :placeholder="$t('data.deletePlaceholder')"
                @keyup.enter="confirmDelete"
              />
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" @click="cancelDelete">
              {{ $t('common.cancel') }}
            </button>
            <button
              class="btn btn-danger"
              :disabled="confirmText !== 'DELETE' || deleting"
              @click="confirmDelete"
            >
              <span v-if="deleting" class="loading-spinner"></span>
              {{ deleting ? $t('data.deleting') : $t('data.confirmDelete') }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <!-- 操作结果提示 -->
    <transition name="fade">
      <div v-if="resultMessage" class="result-message" :class="{ success: resultSuccess, error: !resultSuccess }">
        <svg
          v-if="resultSuccess"
          width="20"
          height="20"
          viewBox="0 0 16 16"
          fill="currentColor"
        >
          <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z" />
        </svg>
        <svg
          v-else
          width="20"
          height="20"
          viewBox="0 0 16 16"
          fill="currentColor"
        >
          <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zM5.354 4.646a.5.5 0 1 0-.708.708L7.293 8l-2.647 2.646a.5.5 0 0 0 .708.708L8 8.707l2.646 2.647a.5.5 0 0 0 .708-.708L8.707 8l2.647-2.646a.5.5 0 0 0-.708-.708L8 7.293 5.354 4.646z" />
        </svg>
        <span>{{ resultMessage }}</span>
      </div>
    </transition>
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';
import api from '../js/api.js';
import { t } from '../../i18n/index.js';
import warningIcon from '../../../../shared/assets/icons/warning.svg';

export default {
  name: 'DataManagementPane',
  props: {
    cacheInfo: {
      type: Object,
      required: true
    }
  },
  emits: ['update:cache-info'],
  setup(props, { emit }) {
    const showDeleteConfirm = ref(false);
    const confirmText = ref('');
    const deleting = ref(false);
    const resultMessage = ref('');
    const resultSuccess = ref(false);

    // 缓存相关（从 props 同步）
    const cacheDir = ref(props.cacheInfo.dir || '');
    const cacheFileCount = ref(props.cacheInfo.fileCount ?? -1);
    const cacheSizeBytes = ref(props.cacheInfo.totalSize ?? -1);
    const scanningCache = ref(false);
    const clearingCache = ref(false);

    watch(() => props.cacheInfo, (newVal) => {
      cacheDir.value = newVal.dir || '';
      cacheFileCount.value = newVal.fileCount ?? -1;
      cacheSizeBytes.value = newVal.totalSize ?? -1;
    }, { deep: true });

    /**
     * 格式化文件大小
     */
    const formatSize = (bytes) => {
      if (bytes < 1024) {
        return bytes + ' B';
      }
      if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(1) + ' KB';
      }
      if (bytes < 1024 * 1024 * 1024) {
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
      }
      return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
    };

    const cacheSizeText = computed(() => {
      if (cacheSizeBytes.value < 0) {
        return t('data.calculating');
      }
      if (cacheSizeBytes.value === 0) {
        return t('data.noCache');
      }
      return t('data.cacheSummary', { size: formatSize(cacheSizeBytes.value), count: cacheFileCount.value });
    });

    /**
     * 扫描缓存文件大小
     */
    const scanCache = async () => {
      scanningCache.value = true;
      try {
        const data = await api.scanCache();
        cacheDir.value = data.dir || '';
        cacheFileCount.value = data.fileCount || 0;
        cacheSizeBytes.value = data.totalSize || 0;
        emit('update:cache-info', { dir: cacheDir.value, fileCount: cacheFileCount.value, totalSize: cacheSizeBytes.value });
      } catch (error) {
        console.error('扫描缓存失败:', error);
        cacheSizeBytes.value = 0;
        cacheFileCount.value = 0;
        emit('update:cache-info', { dir: '', fileCount: 0, totalSize: 0 });
      } finally {
        scanningCache.value = false;
      }
    };

    /**
     * 清除缓存图片文件
     */
    const clearCacheFiles = async () => {
      if (cacheFileCount.value === 0) {
        return;
      }
      if (!confirm(t('data.clearConfirm'))) {
        return;
      }

      clearingCache.value = true;
      try {
        const data = await api.clearCache();
        cacheFileCount.value = 0;
        cacheSizeBytes.value = 0;
        emit('update:cache-info', { fileCount: 0, totalSize: 0 });
        resultMessage.value = t('data.cleared', { count: data.deleted });
        resultSuccess.value = true;
        setTimeout(() => {
          resultMessage.value = ''; 
        }, 3000);
      } catch (error) {
        console.error('清除缓存失败:', error);
        resultMessage.value = t('data.clearFailed', { error: error.message || t('common.unknownError') });
        resultSuccess.value = false;
        setTimeout(() => {
          resultMessage.value = ''; 
        }, 5000);
      } finally {
        clearingCache.value = false;
      }
    };

    const cancelDelete = () => {
      showDeleteConfirm.value = false;
      confirmText.value = '';
    };

    const confirmDelete = async () => {
      if (confirmText.value !== 'DELETE') {
        return;
      }
      
      deleting.value = true;
      resultMessage.value = '';

      try {
        // 调用清除所有聊天记录的 API
        await api.clearAllSessions();
        
        resultMessage.value = t('data.deleted');
        resultSuccess.value = true;
        showDeleteConfirm.value = false;
        confirmText.value = '';

        setTimeout(() => {
          resultMessage.value = '';
        }, 5000);
      } catch (error) {
        console.error('删除数据失败:', error);
        resultMessage.value = t('data.deleteFailed', { error: error.message || t('common.pleaseRetry') });
        resultSuccess.value = false;

        setTimeout(() => {
          resultMessage.value = '';
        }, 5000);
      } finally {
        deleting.value = false;
      }
    };

    return {
      warningIcon,
      showDeleteConfirm,
      confirmText,
      deleting,
      resultMessage,
      resultSuccess,
      cancelDelete,
      confirmDelete,
      cacheDir,
      cacheFileCount,
      cacheSizeText,
      scanningCache,
      clearingCache,
      scanCache,
      clearCache: clearCacheFiles
    };
  }
};
</script>

<style scoped src="../../../../shared/assets/setting.css"></style>

<style scoped>
.data-management-container > .setting-section:last-child {
  margin-bottom: 0;
}

.cache-details {
  margin: 0 0 16px;
}

.cache-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 14px;
  color: #333;
  overflow-wrap: anywhere;
}

.cache-row dd {
  margin: 0;
  color: #666;
  text-align: right;
}

.warning-box {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: 6px;
  background: #fef3f2;
  color: #991b1b;
  font-size: 13px;
}

.warning-icon {
  width: 18px;
  height: 18px;
  margin-top: 2px;
  flex-shrink: 0;
}

.warning-content {
  min-width: 0;
  overflow-wrap: anywhere;
}

.warning-title {
  margin-bottom: 4px;
  font-weight: 600;
}

.warning-list {
  margin: 4px 0 0;
  padding-inline-start: 18px;
}

.action-area,
.modal-footer {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  padding: 8px 16px;
  border: 1px solid transparent;
  border-radius: 6px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
  text-align: left;
  overflow-wrap: anywhere;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
}

.btn svg {
  flex-shrink: 0;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn:focus-visible {
  outline: 2px solid #667eea;
  outline-offset: 2px;
}

.btn-secondary {
  border-color: #e0e0e0;
  background: #fff;
  color: #666;
}

.btn-secondary:hover:not(:disabled) {
  background: #f5f5f5;
}

.btn-primary {
  background: #667eea;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #596bda;
}

.btn-danger {
  background: #dc2626;
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: #b91c1c;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.4);
}

.modal-dialog {
  display: flex;
  flex-direction: column;
  width: 440px;
  max-width: 100%;
  max-height: 100%;
  overflow: hidden;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  background: #fff;
  color: #333;
  box-shadow: 0 20px 60px rgba(24, 30, 48, 0.2);
}

.modal-header {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 10px;
  padding: 16px 24px;
  border-bottom: 1px solid #eee;
}

.modal-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  color: #dc2626;
}

.modal-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
}

.modal-body {
  min-height: 0;
  padding: 16px 24px;
  overflow-y: auto;
  color: #666;
  font-size: 13px;
}

.modal-body p {
  margin: 0 0 16px;
}

.confirm-input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.confirm-input-group label {
  color: #333;
}

.confirm-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  color: #333;
  font: inherit;
}

.confirm-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.12);
}

.modal-footer {
  justify-content: flex-end;
  flex-shrink: 0;
  padding: 14px 24px;
  border-top: 1px solid #eee;
}

.loading-spinner {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.result-message {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  overflow-wrap: anywhere;
}

.result-message svg {
  width: 16px;
  height: 16px;
  margin-top: 2px;
  flex-shrink: 0;
}

.result-message.success {
  color: #059669;
}

.result-message.error {
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
</style>

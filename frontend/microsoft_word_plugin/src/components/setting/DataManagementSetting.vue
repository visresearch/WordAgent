<template>
  <div class="data-management-container">
    <div class="page-header">
      <h1 class="page-title">
        数据管理
      </h1>
      <p class="page-desc">
        管理应用数据和存储
      </p>
    </div>

    <div class="settings-content">
      <!-- 清除缓存 -->
      <div class="setting-section">
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
              清除缓存
            </h2>
            <p class="section-subtitle">
              清除解析文档时生成的临时图片文件，释放磁盘空间
            </p>
          </div>
        </div>

        <div class="cache-info-box">
          <div class="cache-info-item">
            <span class="cache-label">缓存位置</span>
            <span class="cache-value">{{ cacheDir || '插件临时文件目录' }}</span>
          </div>
          <div class="cache-info-item">
            <span class="cache-label">缓存大小</span>
            <span class="cache-value">{{ cacheSizeText }}</span>
          </div>
        </div>

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
            {{ scanningCache ? '扫描中...' : '扫描缓存' }}
          </button>
          <button
            class="btn btn-warning"
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
            {{ clearingCache ? '清除中...' : '清除缓存' }}
          </button>
        </div>
      </div>

      <!-- 数据清理 -->
      <div class="setting-section danger-section">
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
              删除所有数据
            </h2>
            <p class="section-subtitle">
              清除应用中的所有聊天记录和缓存数据
            </p>
          </div>
        </div>

        <div class="warning-box">
          <svg
            class="warning-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line
              x1="12"
              y1="9"
              x2="12"
              y2="13"
            />
            <line
              x1="12"
              y1="17"
              x2="12.01"
              y2="17"
            />
          </svg>
          <div class="warning-content">
            <p class="warning-title">
              警告：此操作不可撤销
            </p>
            <p class="warning-text">
              删除所有数据将会清除：
            </p>
            <ul class="warning-list">
              <li>所有聊天历史记录</li>
              <li>缓存的文档数据</li>
              <li>会话状态信息</li>
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
            删除所有数据
          </button>
        </div>

        <!-- 删除确认对话框 -->
        <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
          <div class="modal-dialog">
            <div class="modal-header">
              <svg
                class="modal-icon danger"
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
                确认删除所有数据？
              </h3>
            </div>
            
            <div class="modal-body">
              <p>此操作将永久删除所有数据，包括聊天记录、缓存和设置。此操作无法撤销。</p>
              <div class="confirm-input-group">
                <label>请输入 <strong>DELETE</strong> 以确认：</label>
                <input 
                  v-model="confirmText" 
                  type="text" 
                  class="confirm-input"
                  placeholder="输入 DELETE"
                  @keyup.enter="confirmDelete"
                />
              </div>
            </div>
            
            <div class="modal-footer">
              <button class="btn btn-cancel" @click="cancelDelete">
                取消
              </button>
              <button 
                class="btn btn-confirm-danger" 
                :disabled="confirmText !== 'DELETE' || deleting"
                @click="confirmDelete"
              >
                <span v-if="deleting" class="loading-spinner"></span>
                {{ deleting ? '删除中...' : '确认删除' }}
              </button>
            </div>
          </div>
        </div>
      </div>

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
  </div>
</template>

<script>
import { ref, computed, watch } from 'vue';
import api from '../js/api.js';

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
        return '计算中...';
      }
      if (cacheSizeBytes.value === 0) {
        return '无缓存';
      }
      return `${formatSize(cacheSizeBytes.value)}（${cacheFileCount.value} 个文件）`;
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
      if (!confirm('确定要清除所有缓存的临时图片文件吗？')) {
        return;
      }

      clearingCache.value = true;
      try {
        const data = await api.clearCache();
        cacheFileCount.value = 0;
        cacheSizeBytes.value = 0;
        emit('update:cache-info', { fileCount: 0, totalSize: 0 });
        resultMessage.value = `已成功清除 ${data.deleted} 个缓存文件`;
        resultSuccess.value = true;
        setTimeout(() => {
          resultMessage.value = ''; 
        }, 3000);
      } catch (error) {
        console.error('清除缓存失败:', error);
        resultMessage.value = '清除缓存失败：' + (error.message || '未知错误');
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
        
        resultMessage.value = '所有数据已成功删除！';
        resultSuccess.value = true;
        showDeleteConfirm.value = false;
        confirmText.value = '';

        setTimeout(() => {
          resultMessage.value = '';
        }, 5000);
      } catch (error) {
        console.error('删除数据失败:', error);
        resultMessage.value = '删除失败：' + (error.message || '请稍后重试');
        resultSuccess.value = false;

        setTimeout(() => {
          resultMessage.value = '';
        }, 5000);
      } finally {
        deleting.value = false;
      }
    };

    return {
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

<style scoped>
.data-management-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
}

.page-header {
  padding: 24px 32px 16px 32px;
  border-bottom: 2px solid #f0f0f0;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: #333333;
}

.page-desc {
  font-size: 13px;
  margin: 0;
  color: #888888;
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
}

.setting-section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.danger-section {
  border: 2px solid #fee2e2;
}

.section-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f0f0;
}

.danger-section .section-header {
  border-bottom-color: #fee2e2;
}

.section-icon {
  width: 24px;
  height: 24px;
  color: #d97706;
  flex-shrink: 0;
  margin-top: 2px;
}

.danger-section .section-icon {
  color: #e74c3c;
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

.danger-section .section-title {
  color: #c0392b;
}

.section-subtitle {
  font-size: 13px;
  color: #7f8c8d;
  margin: 0;
}

/* 缓存信息 */
.cache-info-box {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cache-info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.cache-label {
  font-size: 13px;
  color: #6b7280;
}

.cache-value {
  font-size: 13px;
  color: #374151;
  font-weight: 500;
  word-break: break-all;
  text-align: right;
  max-width: 60%;
}

.warning-box {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: #fef3f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  margin-bottom: 24px;
}

.warning-icon {
  width: 24px;
  height: 24px;
  color: #dc2626;
  flex-shrink: 0;
}

.warning-content {
  flex: 1;
}

.warning-title {
  font-size: 14px;
  font-weight: 600;
  color: #991b1b;
  margin: 0 0 8px 0;
}

.warning-text {
  font-size: 13px;
  color: #7f1d1d;
  margin: 0 0 8px 0;
}

.warning-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #7f1d1d;
}

.warning-list li {
  margin-bottom: 4px;
}

.action-area {
  display: flex;
  justify-content: flex-start;
  gap: 12px;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-warning {
  background: #f59e0b;
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #d97706;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
}

.btn-warning:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  transition: all 0.2s ease;
}

.btn-danger {
  background: #dc2626;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #b91c1c;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4);
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-dialog {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 440px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.modal-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 24px 16px;
  text-align: center;
}

.modal-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 16px;
}

.modal-icon.danger {
  color: #dc2626;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.modal-body {
  padding: 0 24px 24px;
}

.modal-body p {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 20px 0;
  text-align: center;
}

.confirm-input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.confirm-input-group label {
  font-size: 13px;
  color: #374151;
}

.confirm-input-group strong {
  color: #dc2626;
}

.confirm-input {
  padding: 10px 12px;
  border: 2px solid #e5e7eb;
  border-radius: 6px;
  font-size: 14px;
  transition: all 0.2s ease;
}

.confirm-input:focus {
  outline: none;
  border-color: #dc2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}

.modal-footer {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  background: #f9fafb;
  justify-content: flex-end;
}

.btn-cancel {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
}

.btn-cancel:hover {
  background: #e5e7eb;
}

.btn-confirm-danger {
  background: #dc2626;
  color: white;
}

.btn-confirm-danger:hover:not(:disabled) {
  background: #b91c1c;
}

.btn-confirm-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-spinner {
  width: 16px;
  height: 16px;
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

/* 结果提示 */
.result-message {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
}

.result-message.success {
  background: #d1fae5;
  color: #065f46;
}

.result-message.error {
  background: #fee2e2;
  color: #991b1b;
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
.settings-content::-webkit-scrollbar {
  width: 8px;
}

.settings-content::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.settings-content::-webkit-scrollbar-thumb {
  background: #bdc3c7;
  border-radius: 4px;
}

.settings-content::-webkit-scrollbar-thumb:hover {
  background: #95a5a6;
}
</style>

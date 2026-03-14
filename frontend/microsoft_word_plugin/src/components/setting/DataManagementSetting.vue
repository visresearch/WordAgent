<template>
  <div class="data-management-container">
    <div class="tab-header">
      <h2 class="tab-title">数据管理</h2>
      <p class="tab-desc">管理缓存数据和应用存储</p>
    </div>

    <div class="data-content">
      <!-- 缓存管理 -->
      <div class="data-section">
        <div class="section-header">
          <svg class="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
          </svg>
          <div class="section-title-group">
            <h3 class="section-title">缓存管理</h3>
            <p class="section-subtitle">清除应用缓存以释放空间</p>
          </div>
        </div>

        <div class="cache-info">
          <div class="cache-stat">
            <span class="stat-label">缓存大小</span>
            <span class="stat-value">{{ formatSize(cacheSize) }}</span>
          </div>
          <div class="cache-stat">
            <span class="stat-label">缓存文件数</span>
            <span class="stat-value">{{ cacheFileCount }}</span>
          </div>
        </div>

        <div class="action-row">
          <button class="btn-scan" @click="scanCache">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
              <path fill-rule="evenodd" d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z" />
              <path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466z" />
            </svg>
            扫描缓存
          </button>
          <button class="btn-clear" :disabled="cacheFileCount === 0" @click="clearCache">
            清除缓存
          </button>
        </div>

        <transition name="fade">
          <div v-if="cacheMessage" :class="['result-msg', cacheSuccess ? 'success' : 'error']">
            {{ cacheMessage }}
          </div>
        </transition>
      </div>

      <!-- 危险操作 -->
      <div class="data-section danger-section">
        <div class="section-header">
          <svg class="section-icon danger-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <div class="section-title-group">
            <h3 class="section-title danger-title">危险操作</h3>
            <p class="section-subtitle">此操作不可撤销，请谨慎执行</p>
          </div>
        </div>

        <div class="danger-box">
          <div class="danger-info">
            <strong>删除所有数据</strong>
            <p>这将删除所有聊天记录、会话、设置和缓存数据。此操作不可撤销。</p>
          </div>
          <button class="btn-danger" @click="showDeleteConfirm = true">删除所有数据</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteConfirm" class="dialog-overlay" @click.self="showDeleteConfirm = false">
      <div class="delete-dialog">
        <div class="dialog-header">确认删除所有数据</div>
        <div class="dialog-content">
          <p>此操作将永久删除：</p>
          <ul>
            <li>所有聊天记录和会话</li>
            <li>所有设置和配置</li>
            <li>所有缓存文件</li>
          </ul>
          <p class="warning-text">请输入 <strong>DELETE</strong> 确认操作：</p>
          <input v-model="deleteConfirmText" type="text" class="confirm-input" placeholder="输入 DELETE" />
        </div>
        <div class="dialog-actions">
          <button class="dialog-btn cancel-btn" @click="showDeleteConfirm = false; deleteConfirmText = ''">取消</button>
          <button class="dialog-btn delete-confirm-btn" :disabled="deleteConfirmText !== 'DELETE'" @click="deleteAllData">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';

export default {
  name: 'DataManagementSetting',
  setup() {
    const cacheSize = ref(0);
    const cacheFileCount = ref(0);
    const cacheMessage = ref('');
    const cacheSuccess = ref(false);
    const showDeleteConfirm = ref(false);
    const deleteConfirmText = ref('');

    const formatSize = (bytes) => {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const scanCache = () => {
      // TODO: 后端集成后替换
      cacheSize.value = 2048576;
      cacheFileCount.value = 15;
      cacheMessage.value = '缓存扫描完成';
      cacheSuccess.value = true;
      setTimeout(() => { cacheMessage.value = ''; }, 2000);
    };

    const clearCache = () => {
      // TODO: 后端集成后替换
      cacheSize.value = 0;
      cacheFileCount.value = 0;
      cacheMessage.value = '缓存已清除';
      cacheSuccess.value = true;
      setTimeout(() => { cacheMessage.value = ''; }, 2000);
    };

    const deleteAllData = () => {
      if (deleteConfirmText.value !== 'DELETE') return;
      // TODO: 后端集成后替换
      showDeleteConfirm.value = false;
      deleteConfirmText.value = '';
      cacheSize.value = 0;
      cacheFileCount.value = 0;
    };

    return {
      cacheSize, cacheFileCount, cacheMessage, cacheSuccess,
      showDeleteConfirm, deleteConfirmText,
      formatSize, scanCache, clearCache, deleteAllData
    };
  }
};
</script>

<style scoped>
.data-management-container {
  display: flex; flex-direction: column; height: 100%;
}
.tab-header { padding: 20px 20px 0; }
.tab-title { font-size: 16px; font-weight: 600; color: #333; margin: 0 0 4px; }
.tab-desc { font-size: 12px; color: #888; margin: 0; }

.data-content { flex: 1; overflow-y: auto; padding: 20px; }

.data-section {
  background: white; border-radius: 12px; padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 20px;
}
.section-header {
  display: flex; align-items: flex-start; gap: 16px;
  margin-bottom: 20px; padding-bottom: 16px; border-bottom: 2px solid #f0f0f0;
}
.section-icon { width: 24px; height: 24px; color: #667eea; flex-shrink: 0; margin-top: 2px; }
.danger-icon { color: #e74c3c !important; }
.section-title-group { flex: 1; }
.section-title { font-size: 16px; font-weight: 600; margin: 0 0 4px; color: #2c3e50; }
.danger-title { color: #e74c3c !important; }
.section-subtitle { font-size: 12px; color: #7f8c8d; margin: 0; }

.cache-info { display: flex; gap: 24px; margin-bottom: 16px; }
.cache-stat { display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: 12px; color: #888; }
.stat-value { font-size: 16px; font-weight: 600; color: #333; }

.action-row { display: flex; gap: 8px; }
.btn-scan {
  display: flex; align-items: center; gap: 4px; padding: 8px 16px;
  background: #f0f0f0; color: #333; border: 1px solid #d0d0d0; border-radius: 6px;
  font-size: 12px; cursor: pointer; transition: all 0.2s;
}
.btn-scan:hover { background: #e8e8e8; }
.btn-clear {
  padding: 8px 16px; background: #667eea; color: white; border: none;
  border-radius: 6px; font-size: 12px; cursor: pointer; transition: all 0.2s;
}
.btn-clear:hover:not(:disabled) { background: #5a6fd6; }
.btn-clear:disabled { opacity: 0.5; cursor: not-allowed; }

.result-msg { margin-top: 12px; font-size: 12px; padding: 8px 12px; border-radius: 6px; }
.result-msg.success { background: #f0fff4; color: #27ae60; }
.result-msg.error { background: #fff5f5; color: #e74c3c; }

.danger-box {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px; background: #fff8f8; border: 1px solid #fde2e2; border-radius: 8px;
}
.danger-info strong { font-size: 14px; color: #333; display: block; margin-bottom: 4px; }
.danger-info p { font-size: 12px; color: #888; margin: 0; }
.btn-danger {
  padding: 8px 16px; background: #e74c3c; color: white; border: none;
  border-radius: 6px; font-size: 12px; cursor: pointer; transition: all 0.2s; flex-shrink: 0;
}
.btn-danger:hover { background: #c0392b; }

/* Dialog */
.dialog-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4); display: flex; align-items: center;
  justify-content: center; z-index: 1000;
}
.delete-dialog {
  background: white; border-radius: 12px; padding: 20px; width: 300px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}
.dialog-header { font-size: 14px; font-weight: 600; color: #e74c3c; margin-bottom: 16px; }
.dialog-content { font-size: 12px; color: #666; line-height: 1.5; }
.dialog-content ul { margin: 8px 0; padding-left: 20px; }
.dialog-content li { margin: 4px 0; }
.warning-text { color: #e74c3c; font-weight: 500; margin-top: 12px; }
.confirm-input {
  width: 100%; padding: 8px 12px; border: 1px solid #fde2e2; border-radius: 6px;
  font-size: 13px; outline: none; margin-top: 8px; box-sizing: border-box;
}
.confirm-input:focus { border-color: #e74c3c; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
.dialog-btn { padding: 8px 16px; border: none; border-radius: 6px; font-size: 12px; cursor: pointer; }
.cancel-btn { background: #f0f0f0; color: #666; }
.cancel-btn:hover { background: #e0e0e0; }
.delete-confirm-btn { background: #e74c3c; color: white; }
.delete-confirm-btn:hover:not(:disabled) { background: #c0392b; }
.delete-confirm-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

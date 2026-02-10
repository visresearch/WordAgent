<template>
  <div class="session-container">
    <!-- 新聊天按钮 -->
    <div class="new-chat-section">
      <button class="new-chat-btn" @click="createNewSession">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M12 5v14M5 12h14" />
        </svg>
        <span>新聊天</span>
      </button>
    </div>

    <!-- 会话列表 -->
    <div class="session-list">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-state">
        <div class="loading-spinner"></div>
        <span>加载中...</span>
      </div>

      <!-- 空状态 -->
      <div v-else-if="sessions.length === 0" class="empty-state">
        <svg
          class="empty-icon"
          viewBox="0 0 1024 1024"
          xmlns="http://www.w3.org/2000/svg"
          width="48"
          height="48"
        >
          <path d="M881.777778 1024H142.222222a56.888889 56.888889 0 0 1-56.888889-56.888889V56.888889a56.888889 56.888889 0 0 1 56.888889-56.888889h739.555556a56.888889 56.888889 0 0 1 56.888889 56.888889v910.222222a56.888889 56.888889 0 0 1-56.888889 56.888889z m0-938.666667a28.444444 28.444444 0 0 0-28.444445-28.444444H170.666667a28.444444 28.444444 0 0 0-28.444445 28.444444v853.333334a28.444444 28.444444 0 0 0 28.444445 28.444444h682.666666a28.444444 28.444444 0 0 0 28.444445-28.444444V85.333333z" fill="currentColor" />
          <path d="M227.555556 512h284.444444v56.888889H227.555556zM227.555556 711.111111h483.555555v56.888889H227.555556z" fill="currentColor" />
        </svg>
        <span>暂无历史会话</span>
      </div>

      <!-- 会话项列表 -->
      <div v-else class="sessions-wrapper">
        <div 
          v-for="session in sortedSessions" 
          :key="session.id"
          :class="['session-item', { active: session.id === currentSessionId }]"
          @click="selectSession(session)"
        >
          <div class="session-content">
            <div class="session-title">
              {{ session.title || '新对话' }}
            </div>
            <div class="session-preview">
              {{ session.preview || '暂无消息' }}
            </div>
          </div>
          <div class="session-actions">
            <button class="action-btn" title="重命名" @click.stop="renameSession(session)">
              <svg
                width="12"
                height="12"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10zM11.207 2.5L13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5zm-9.761 5.175l-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325z" />
              </svg>
            </button>
            <button class="action-btn delete-btn" title="删除" @click.stop="deleteSession(session)">
              <svg
                width="12"
                height="12"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z" />
                <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4L4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 重命名对话框 -->
    <div v-if="showRenameDialog" class="dialog-overlay" @click.self="closeRenameDialog">
      <div class="rename-dialog">
        <div class="dialog-header">
          重命名会话
        </div>
        <input 
          ref="renameInput" 
          v-model="renameValue" 
          type="text" 
          class="rename-input"
          placeholder="输入新名称"
          @keyup.enter="confirmRename"
        />
        <div class="dialog-actions">
          <button class="dialog-btn cancel-btn" @click="closeRenameDialog">
            取消
          </button>
          <button class="dialog-btn confirm-btn" @click="confirmRename">
            确定
          </button>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="showDeleteDialog" class="dialog-overlay" @click.self="closeDeleteDialog">
      <div class="delete-dialog">
        <div class="dialog-header">
          确认删除
        </div>
        <div class="dialog-content">
          确定要删除这个会话吗？此操作无法撤销。
        </div>
        <div class="dialog-actions">
          <button class="dialog-btn cancel-btn" @click="closeDeleteDialog">
            取消
          </button>
          <button class="dialog-btn delete-confirm-btn" @click="confirmDelete">
            删除
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, nextTick } from 'vue';
import api from '../js/api.js';

export default {
  name: 'SessionPane',
  setup() {
    const isLoading = ref(false);
    const currentSessionId = ref(null);
    const sessions = ref([]);
    
    // 重命名对话框
    const showRenameDialog = ref(false);
    const renameValue = ref('');
    const renameTarget = ref(null);
    const renameInput = ref(null);
    
    // 删除对话框
    const showDeleteDialog = ref(false);
    const deleteTarget = ref(null);

    // 按修改时间排序的会话列表（后端已排序，这里做兜底）
    const sortedSessions = computed(() => {
      return [...sessions.value].sort((a, b) => 
        new Date(b.updatedAt) - new Date(a.updatedAt)
      );
    });

    // 获取当前文档信息
    const getDocumentInfo = () => {
      try {
        const doc = window.Application?.ActiveDocument;
        if (!doc) {
          return null;
        }
        const fullPath = doc.FullName || '';
        const docName = doc.Name || 'Untitled';
        let docId;
        if (fullPath && fullPath !== docName) {
          let hash = 0;
          for (let i = 0; i < fullPath.length; i++) {
            const char = fullPath.charCodeAt(i);
            hash = (hash << 5) - hash + char;
            hash = hash & hash;
          }
          docId = 'doc_' + Math.abs(hash).toString(36);
        } else {
          const storedId = window.Application.PluginStorage.getItem(`unsaved_doc_${docName}`);
          if (storedId) {
            docId = storedId;
          } else {
            docId = `unsaved_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            window.Application.PluginStorage.setItem(`unsaved_doc_${docName}`, docId);
          }
        }
        return { docId, docName };
      } catch (e) {
        console.warn('获取文档信息失败:', e);
        return null;
      }
    };

    // 加载会话列表
    const loadSessions = async () => {
      isLoading.value = true;
      try {
        const result = await api.getSessions({ limit: 100 });
        if (result.success && result.data?.sessions) {
          sessions.value = result.data.sessions;
        } else {
          console.warn('加载会话列表失败:', result.error);
          sessions.value = [];
        }
      } catch (error) {
        console.error('加载会话列表失败:', error);
        sessions.value = [];
      } finally {
        isLoading.value = false;
      }
    };

    // 创建新会话
    const createNewSession = async () => {
      try {
        const docInfo = getDocumentInfo();
        const result = await api.createSession({
          docId: docInfo?.docId || null,
          docName: docInfo?.docName || null,
          title: '新对话'
        });

        if (result.success && result.data?.session) {
          const newSession = result.data.session;
          sessions.value.unshift(newSession);
          currentSessionId.value = newSession.id;
          notifySessionChange(newSession.id, newSession.title);
        } else {
          console.error('创建会话失败:', result.error);
        }
      } catch (error) {
        console.error('创建会话失败:', error);
      }
    };

    // 选择会话
    const selectSession = (session) => {
      currentSessionId.value = session.id;
      notifySessionChange(session.id, session.title);
    };

    // 通知会话变更
    const notifySessionChange = (sessionId, title = null) => {
      if (window.Application && window.Application.PluginStorage) {
        window.Application.PluginStorage.setItem('current_session_id', String(sessionId));
      }
      window.dispatchEvent(new CustomEvent('session-changed', { 
        detail: { sessionId, title } 
      }));
    };

    // 重命名会话
    const renameSession = (session) => {
      renameTarget.value = session;
      renameValue.value = session.title || '';
      showRenameDialog.value = true;
      nextTick(() => {
        renameInput.value?.focus();
        renameInput.value?.select();
      });
    };

    const closeRenameDialog = () => {
      showRenameDialog.value = false;
      renameTarget.value = null;
      renameValue.value = '';
    };

    const confirmRename = async () => {
      if (!renameTarget.value || !renameValue.value.trim()) {
        return;
      }
      
      try {
        const result = await api.renameSessionApi(renameTarget.value.id, renameValue.value.trim());
        if (result.success && result.data?.session) {
          // 更新本地列表中的标题
          const target = sessions.value.find(s => s.id === renameTarget.value.id);
          if (target) {
            target.title = result.data.session.title;
          }
        } else {
          console.error('重命名失败:', result.error);
        }
        closeRenameDialog();
      } catch (error) {
        console.error('重命名失败:', error);
      }
    };

    // 删除会话
    const deleteSession = (session) => {
      deleteTarget.value = session;
      showDeleteDialog.value = true;
    };

    const closeDeleteDialog = () => {
      showDeleteDialog.value = false;
      deleteTarget.value = null;
    };

    const confirmDelete = async () => {
      if (!deleteTarget.value) {
        return;
      }
      
      try {
        const result = await api.deleteSessionApi(deleteTarget.value.id);
        if (result.success) {
          const index = sessions.value.findIndex(s => s.id === deleteTarget.value.id);
          if (index > -1) {
            sessions.value.splice(index, 1);
          }
          
          // 如果删除的是当前会话，切换到最新会话或清空
          if (currentSessionId.value === deleteTarget.value.id) {
            if (sessions.value.length > 0) {
              const latest = sortedSessions.value[0];
              currentSessionId.value = latest.id;
              notifySessionChange(latest.id, latest.title);
            } else {
              currentSessionId.value = null;
              notifySessionChange(null);
            }
          }
        } else {
          console.error('删除失败:', result.error);
        }
        closeDeleteDialog();
      } catch (error) {
        console.error('删除失败:', error);
      }
    };

    // 监听外部会话创建事件（AIChatPane 自动创建会话时通知刷新列表）
    const onSessionCreated = () => {
      loadSessions();
    };

    onMounted(() => {
      loadSessions();

      // 获取当前会话ID
      if (window.Application && window.Application.PluginStorage) {
        const savedSessionId = window.Application.PluginStorage.getItem('current_session_id');
        if (savedSessionId) {
          currentSessionId.value = Number(savedSessionId) || savedSessionId;
        }
      }

      // 监听会话创建/更新事件
      window.addEventListener('session-created', onSessionCreated);
      window.addEventListener('session-updated', onSessionCreated);
    });

    return {
      isLoading,
      currentSessionId,
      sessions,
      sortedSessions,
      showRenameDialog,
      renameValue,
      renameInput,
      showDeleteDialog,
      createNewSession,
      selectSession,
      renameSession,
      closeRenameDialog,
      confirmRename,
      deleteSession,
      closeDeleteDialog,
      confirmDelete
    };
  }
};
</script>

<style scoped>
.session-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f7f8fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* 新聊天按钮区域 */
.new-chat-section {
  padding: 12px 16px;
  background: #f7f8fa;
  flex-shrink: 0;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 10px 16px;
  background: white;
  color: #333;
  border: 1px solid #d0d0d0;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.new-chat-btn:hover {
  background: #f8f8f8;
  border-color: #999;
}

/* 会话列表 */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 16px 16px;
}

.session-list::-webkit-scrollbar {
  width: 6px;
}

.session-list::-webkit-scrollbar-track {
  background: transparent;
}

.session-list::-webkit-scrollbar-thumb {
  background: #c5cdd8;
  border-radius: 2px;
}

.sessions-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 会话项 */
.session-item {
  display: flex;
  align-items: flex-start;
  padding: 12px;
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.session-item:hover {
  border-color: #d0d0d0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.session-item.active {
  border-color: #999;
  background: #f8f8f8;
}

.session-content {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-preview {
  font-size: 11px;
  color: #888;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #888;
  cursor: pointer;
  transition: all 0.15s;
}

.action-btn:hover {
  background: #f0f0f0;
  color: #333;
}

.action-btn.delete-btn:hover {
  background: #fff0f0;
  color: #e74c3c;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #888;
  font-size: 12px;
  gap: 12px;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #e0e0e0;
  border-top-color: #666;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #888;
  text-align: center;
}

.empty-icon {
  color: #ddd;
  margin-bottom: 16px;
}

.empty-state span {
  font-size: 13px;
}

/* 对话框通用样式 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.rename-dialog,
.delete-dialog {
  background: white;
  border-radius: 12px;
  padding: 20px;
  width: 280px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.dialog-header {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 16px;
}

.dialog-content {
  font-size: 12px;
  color: #666;
  margin-bottom: 20px;
  line-height: 1.5;
}

.rename-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
  margin-bottom: 16px;
  transition: border-color 0.2s;
}

.rename-input:focus {
  border-color: #666;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.dialog-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.cancel-btn {
  background: #f0f0f0;
  color: #666;
}

.cancel-btn:hover {
  background: #e0e0e0;
}

.confirm-btn {
  background: #667eea;
  color: white;
}

.confirm-btn:hover {
  background: #5a6fd6;
}

.delete-confirm-btn {
  background: #e74c3c;
  color: white;
}

.delete-confirm-btn:hover {
  background: #c0392b;
}
</style>

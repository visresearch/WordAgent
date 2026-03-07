<template>
  <div class="ai-chat-container">
    <div v-if="currentSessionTitle" class="session-header">
      <span class="session-title">{{ currentSessionTitle }}</span>
    </div>
    <ChatMessages
      ref="chatMessages"
      :messages="messages"
      :is-loading="isLoading"
      :has-history="hasHistory"
      :history-loaded="historyLoaded"
      @load-history="loadAndShowHistory"
      @insert-to-word="insertToWord"
      @copy="copyToClipboard"
      @retry="retryMessage"
      @revert="revertToMessage"
      @toggle-thinking="toggleThinking"
    />
    <ChatInput
      :mode="mode"
      :selected-model="selectedModel"
      :available-models="availableModels"
      :models-loading="modelsLoading"
      :is-loading="isLoading"
      :selections="selections"
      :pending-document="pendingDocument"
      @update:mode="mode = $event"
      @update:selected-model="selectedModel = $event"
      @send="handleSend"
      @stop="stopGeneration"
      @add-selection="addSelectionManually"
      @remove-selection="removeSelection"
      @refresh-models="loadModels"
      @confirm-document="confirmDocument"
      @cancel-document="cancelDocument"
    />
  </div>
</template>

<script>
import { generateDocxFromJSON } from '../js/docxJsonConverter.js';
import api from '../js/api.js';
import ChatMessages from './ChatMessages.vue';
import ChatInput from './ChatInput.vue';

export default {
  name: 'AIChatPane',
  components: {
    ChatMessages,
    ChatInput
  },
  data() {
    return {
      mode: 'agent',
      selectedModel: '',
      availableModels: [],
      modelsLoading: false,
      messages: [],
      isLoading: false,
      lastReadJSON: null,
      selections: [],  // 多选区数组 [{preview, startText, endText, startPos, endPos, charCount, hasMore}]
      currentStreamCtrl: null,
      currentDocId: null,
      currentDocName: null,
      currentSessionId: null,
      currentSessionTitle: null,
      pendingDocument: null,
      pendingDocumentMsg: null,
      historyLoading: false,
      hasHistory: false,
      historyLoaded: false
    };
  },
  mounted() {
    this.loadModels();
    this.initSessionAndLoadHistory();

    // 监听同窗口 SessionPane 切换会话的事件
    window.addEventListener('session-changed', this.onSessionChanged);
    // 监听跨 TaskPane 的 localStorage storage 事件（WPS 中各 TaskPane 是独立窗口）
    window.addEventListener('storage', this.onStorageChanged);
  },
  beforeUnmount() {
    window.removeEventListener('session-changed', this.onSessionChanged);
    window.removeEventListener('storage', this.onStorageChanged);
  },
  methods: {
    /**
     * 切换 thinking 展开/收起
     */
    toggleThinking(index) {
      if (this.messages[index]) {
        this.messages[index].thinkingExpanded = !this.messages[index].thinkingExpanded;
      }
    },

    /**
     * 滚动到底部（委托给 ChatMessages）
     */
    scrollToBottom() {
      this.$refs.chatMessages?.scrollToBottom();
    },

    /**
     * 复制到剪切板
     */
    async copyToClipboard(content) {
      try {
        await navigator.clipboard.writeText(content);
        console.log('已复制到剪切板');
      } catch (error) {
        console.error('复制失败:', error);
        const textarea = document.createElement('textarea');
        textarea.value = content;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try {
          document.execCommand('copy');
          console.log('已复制到剪切板（降级方案）');
        } catch (e) {
          console.error('降级复制也失败:', e);
        }
        document.body.removeChild(textarea);
      }
    },

    /**
     * 还原到某条消息 - 删除该消息之后的所有消息
     */
    async revertToMessage(messageIndex) {
      console.log(`撤销消息索引 ${messageIndex} 对应的文档内容`);

      if (this.isLoading) {
        return;
      }

      try {
        if (!window.Application) {
          alert('WPS API 不可用');
          return;
        }

        const doc = window.Application.ActiveDocument;
        if (!doc) {
          alert('请先打开一个Word文档');
          return;
        }

        const msg = this.messages[messageIndex];
        if (!msg) {
          alert('消息不存在');
          return;
        }

        if (!msg.insertStartPos && msg.insertStartPos !== 0) {
          console.log('该消息没有可撤销的文档内容（可能还未输出到文档）');
          return;
        }

        const startPos = msg.insertStartPos;
        const endPos = msg.insertEndPos;
        console.log(`准备删除插入范围: ${startPos} - ${endPos}`);

        try {
          try {
            const insertedRange = doc.Range(startPos, endPos);
            while (insertedRange.Comments.Count > 0) {
              insertedRange.Comments.Item(1).Delete();
            }
            console.log('删除批注完成');
          } catch (commentErr) {
            console.log('删除批注:', commentErr.message);
          }

          const range = doc.Range(startPos, endPos);
          range.Delete();

          console.log('✅ 成功删除插入内容');

          msg.documentReverted = true;
          delete msg.insertStartPos;
          delete msg.insertEndPos;
          delete msg.docLengthBefore;
          delete msg.commentIndex;
        } catch (e) {
          console.error('删除失败:', e.message);
          alert('撤销失败: ' + e.message);
        }
      } catch (error) {
        console.error('撤销失败:', error);
        alert('撤销失败: ' + error.message);
      }
    },

    /**
     * 终止生成
     */
    stopGeneration() {
      if (this.currentStreamCtrl) {
        this.currentStreamCtrl.abort();
        this.currentStreamCtrl = null;
      }
      this.isLoading = false;
    },

    /**
     * 初始化会话并加载历史记录
     * 优先使用 PluginStorage 中保存的 session_id，否则查找当前文档的最新会话
     */
    async initSessionAndLoadHistory() {
      try {
        console.log('[初始化] 开始获取文档信息和会话');
        const docInfo = this.getDocumentInfo();
        if (docInfo) {
          this.currentDocId = docInfo.docId;
          this.currentDocName = docInfo.docName;
        }

        // 尝试从 PluginStorage 或 localStorage 恢复上次的 session_id
        let savedSessionId = null;
        if (window.Application && window.Application.PluginStorage) {
          savedSessionId = window.Application.PluginStorage.getItem('current_session_id');
        }
        if (!savedSessionId) {
          try {
            const stored = localStorage.getItem('wence_session_change');
            if (stored) {
              const data = JSON.parse(stored);
              savedSessionId = data?.sessionId ? String(data.sessionId) : null;
            }
          } catch (e) {
            // ignore
          }
        }

        if (savedSessionId) {
          // 有保存的 session_id，直接加载该会话
          console.log('[初始化] 恢复上次会话:', savedSessionId);
          this.currentSessionId = Number(savedSessionId) || savedSessionId;
          await this.loadSessionMessages();
        } else {
          // 没有保存的 session_id，查找当前文档的最新会话
          console.log('[初始化] 查找最新会话, docId:', this.currentDocId);
          const result = await api.getLatestSession(this.currentDocId);
          if (result.success && result.data?.session) {
            this.currentSessionId = result.data.session.id;
            this.currentSessionTitle = result.data.session.title || null;
            console.log('[初始化] 找到最新会话:', this.currentSessionId);

            // 保存到 PluginStorage
            if (window.Application && window.Application.PluginStorage) {
              window.Application.PluginStorage.setItem('current_session_id', String(this.currentSessionId));
            }

            // 如果有消息，标记有历史
            this.hasHistory = result.data.messages && result.data.messages.length > 0;
          } else {
            console.log('[初始化] 当前文档没有历史会话');
            this.hasHistory = false;
          }
        }
      } catch (e) {
        console.error('[初始化] 失败:', e);
      }
    },

    /**
     * 跨 TaskPane 通信：监听 localStorage 的 storage 事件
     * 当 SessionPane（另一个 TaskPane 窗口）写入 localStorage 时触发
     */
    onStorageChanged(event) {
      if (event.key !== 'wence_session_change') {
        return;
      }
      try {
        const data = JSON.parse(event.newValue);
        if (data) {
          console.log('[跨窗口会话切换] storage 事件, data:', data);
          this.onSessionChanged({ detail: data });
        }
      } catch (e) {
        console.error('[跨窗口会话切换] 解析失败:', e);
      }
    },

    /**
     * 监听 SessionPane 切换会话的事件
     */
    async onSessionChanged(event) {
      const { sessionId, title } = event.detail || {};
      console.log('[会话切换] 收到事件, sessionId:', sessionId, 'title:', title);

      if (!sessionId) {
        // 会话被清空（如删除了当前会话）
        this.currentSessionId = null;
        this.currentSessionTitle = null;
        this.messages = [];
        this.hasHistory = false;
        this.historyLoaded = false;
        return;
      }

      // 如果已经是当前会话，不重复加载
      if (this.currentSessionId === sessionId && this.historyLoaded) {
        console.log('[会话切换] 已是当前会话，跳过');
        return;
      }

      // 先清空旧消息，再加载新会话
      this.messages = [];
      this.hasHistory = false;
      this.historyLoaded = false;
      this.currentSessionId = sessionId;
      this.currentSessionTitle = title || null;

      // 同步到 PluginStorage
      if (window.Application && window.Application.PluginStorage) {
        window.Application.PluginStorage.setItem('current_session_id', String(sessionId));
      }

      // 加载该会话的消息
      await this.loadSessionMessages();
    },

    /**
     * 点击显示历史记录
     */
    async loadAndShowHistory() {
      console.log('[显示历史] 点击按钮，当前 sessionId:', this.currentSessionId);
      await this.loadSessionMessages();
      this.historyLoaded = true;
    },

    /**
     * 获取当前 Word 文档的唯一标识信息
     */
    getDocumentInfo() {
      try {
        const doc = window.Application?.ActiveDocument;
        if (!doc) {
          return null;
        }

        const fullPath = doc.FullName || '';
        const docName = doc.Name || 'Untitled';

        let docId;
        if (fullPath && fullPath !== docName) {
          docId = this.hashString(fullPath);
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
    },

    /**
     * 简单的字符串 hash 函数
     */
    hashString(str) {
      let hash = 0;
      for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = (hash << 5) - hash + char;
        hash = hash & hash;
      }
      return 'doc_' + Math.abs(hash).toString(36);
    },

    /**
     * 加载当前会话的聊天历史
     */
    async loadSessionMessages() {
      if (!this.currentSessionId) {
        console.warn('[加载历史] 缺少 sessionId');
        return;
      }

      console.log('[加载历史] 开始加载, sessionId:', this.currentSessionId);

      this.historyLoading = true;
      try {
        const result = await api.getSession(this.currentSessionId);
        console.log('[加载历史] API 返回:', result);

        if (result.success && result.data?.messages) {
          console.log('[加载历史] 消息数量:', result.data.messages.length);
          this.messages = result.data.messages.map((msg) => ({
            role: msg.role,
            content: msg.content,
            contentParts: msg.contentParts || [],
            documentJson: msg.documentJson || null,
            selectionContext: msg.selectionContext || null
          }));

          if (result.data.lastUsedModel) {
            this.selectedModel = result.data.lastUsedModel;
          }
          if (result.data.lastUsedMode) {
            this.mode = result.data.lastUsedMode;
          }

          // 更新文档信息（来自会话关联的文档）
          if (result.data.session) {
            this.currentDocId = result.data.session.docId || this.currentDocId;
            this.currentDocName = result.data.session.docName || this.currentDocName;
            this.currentSessionTitle = result.data.session.title || null;
          }

          this.hasHistory = this.messages.length > 0;
          this.historyLoaded = true;
          this.scrollToBottom();
        } else {
          console.warn('[加载历史] 返回数据格式不正确:', result);
        }
      } catch (e) {
        console.error('[加载历史] 失败:', e);
      }
      this.historyLoading = false;
    },

    /**
     * 确保当前有一个活跃的会话，如果没有则自动创建
     * @returns {number|null} sessionId
     */
    async ensureSession() {
      if (this.currentSessionId) {
        return this.currentSessionId;
      }

      console.log('[自动创建会话] docId:', this.currentDocId);
      try {
        const result = await api.createSession({
          docId: this.currentDocId || null,
          docName: this.currentDocName || null,
          title: '新对话'
        });

        if (result.success && result.data?.session) {
          this.currentSessionId = result.data.session.id;
          console.log('[自动创建会话] 新会话ID:', this.currentSessionId);

          // 保存到 PluginStorage
          if (window.Application && window.Application.PluginStorage) {
            window.Application.PluginStorage.setItem('current_session_id', String(this.currentSessionId));
          }

          // 通知 SessionPane 刷新列表
          window.dispatchEvent(new CustomEvent('session-created'));

          return this.currentSessionId;
        }
      } catch (e) {
        console.error('[自动创建会话] 失败:', e);
      }
      return null;
    },

    /**
     * 保存消息到后端（基于会话）
     */
    async saveMessageToHistory(role, content, documentJson = null, selectionContext = null, contentParts = null) {
      // 确保有会话
      const sessionId = await this.ensureSession();
      if (!sessionId) {
        console.warn('[保存消息] 无法获取会话ID，消息未保存');
        return;
      }

      console.log('[保存消息]', {
        sessionId,
        role,
        contentLength: content.length
      });

      try {
        await api.addSessionMessage(sessionId, {
          role,
          content,
          documentJson,
          selectionContext,
          contentParts,
          model: this.selectedModel || 'auto',
          mode: this.mode
        });
        console.log('[保存消息] 成功');

        // 第一条用户消息会自动设置会话标题，更新本地标题
        if (role === 'user' && (!this.currentSessionTitle || this.currentSessionTitle === '新对话')) {
          const newTitle = content.length > 30 ? content.substring(0, 30) + '...' : content;
          this.currentSessionTitle = newTitle;

          // 通过 localStorage 通知 SessionPane 更新标题和预览（跨 TaskPane 窗口通信）
          try {
            localStorage.setItem('wence_session_title_update', JSON.stringify({
              sessionId: this.currentSessionId,
              title: newTitle,
              preview: content.length > 50 ? content.substring(0, 50) + '...' : content,
              timestamp: Date.now()
            }));
          } catch (e) {
            console.warn('localStorage 写入标题更新失败:', e);
          }
        } else {
          // 非首条消息也同步预览
          try {
            localStorage.setItem('wence_session_title_update', JSON.stringify({
              sessionId: this.currentSessionId,
              preview: content.length > 50 ? content.substring(0, 50) + '...' : content,
              timestamp: Date.now()
            }));
          } catch (e) {
            console.warn('localStorage 写入预览更新失败:', e);
          }
        }

        // 通知 SessionPane 更新列表（预览和标题可能变了）
        window.dispatchEvent(new CustomEvent('session-updated'));
      } catch (e) {
        console.warn('保存消息失败:', e);
      }
    },

    /**
     * 清空当前会话的聊天历史
     */
    async clearChatHistory() {
      if (!this.currentSessionId) {
        this.messages = [];
        return;
      }

      try {
        const result = await api.deleteSessionApi(this.currentSessionId);
        if (result.success) {
          this.messages = [];
          this.currentSessionId = null;
          this.hasHistory = false;
          this.historyLoaded = false;

          // 清除 PluginStorage
          if (window.Application && window.Application.PluginStorage) {
            window.Application.PluginStorage.removeItem('current_session_id');
          }

          // 通知 SessionPane 刷新
          window.dispatchEvent(new CustomEvent('session-updated'));
        }
      } catch (e) {
        console.warn('清空历史记录失败:', e);
        this.messages = [];
      }
    },

    /**
     * 加载可用模型列表
     */
    async loadModels() {
      console.log('loadModels 被调用');
      this.modelsLoading = true;
      try {
        console.log('开始请求模型列表...');
        const result = await api.getModels();
        console.log('模型列表响应:', result);
        if (result.success && result.data?.models && result.data.models.length > 0) {
          this.availableModels = result.data.models;
          const modelExists = this.availableModels.some(m => m.id === this.selectedModel);
          if (!modelExists) {
            this.selectedModel = 'auto';
          }
        } else {
          console.warn('获取模型列表失败:', result.error);
          this.availableModels = [{ id: 'auto', name: 'Auto' }];
          this.selectedModel = 'auto';
        }
      } catch (error) {
        console.error('加载模型列表失败:', error);
        this.availableModels = [{ id: 'auto', name: 'Auto' }];
        this.selectedModel = 'auto';
      }
      this.modelsLoading = false;
    },

    /**
     * 手动添加选区（点击按钮触发）
     */
    addSelectionManually() {
      console.log('[AIChatPane] 手动触发添加选区');

      try {
        const selection = window.Application?.Selection;
        if (!selection) {
          console.warn('[Selection] 无法获取选区');
          alert('无法获取选区，请确保在 WPS Word 中选中了文本');
          return;
        }

        const range = selection.Range;
        if (!range) {
          console.warn('[Selection] 无法获取范围');
          alert('无法获取选区范围');
          return;
        }

        const text = range.Text || '';
        const cleanedText = text.replace(/[\r\n\u0007\f]/g, ' ').trim();

        if (!cleanedText || cleanedText.length < 2) {
          console.warn('[Selection] 没有选中有效内容');
          alert('请先在文档中选中文本内容');
          return;
        }

        console.log('[Selection] 选中内容长度:', cleanedText.length);

        const maxPreviewLen = 50;
        let preview = cleanedText;
        let hasMore = false;

        if (preview.length > maxPreviewLen) {
          preview = preview.substring(0, maxPreviewLen);
          hasMore = true;
        }

        const startText = cleanedText.substring(0, Math.min(10, cleanedText.length));
        const endText =
          cleanedText.length > 10 ? cleanedText.substring(cleanedText.length - 10) : cleanedText;

        const selectionInfo = {
          preview: preview + (hasMore ? '...' : ''),
          startText: startText + (cleanedText.length > 10 ? '...' : ''),
          endText: (cleanedText.length > 20 ? '...' : '') + endText,
          charCount: cleanedText.length,
          hasMore,
          range: { startPos: range.Start, endPos: range.End }
        };

        console.log('[Selection] 选区信息已生成:', {
          preview: selectionInfo.preview,
          charCount: selectionInfo.charCount
        });

        this.handleSelectionAdd(selectionInfo);
      } catch (error) {
        console.error('[Selection] 处理选区失败:', error);
        alert('处理选中内容时出错: ' + error.message);
      }
    },

    /**
     * 处理添加的选区（追加到列表）
     */
    handleSelectionAdd(selectionInfo) {
      console.log('[AIChatPane] 收到选区信息:', selectionInfo);

      // 检查是否已存在相同范围的选区，避免重复
      const exists = this.selections.some(
        s => s.startPos === selectionInfo.range.startPos && s.endPos === selectionInfo.range.endPos
      );
      if (exists) {
        console.log('[AIChatPane] 该选区已存在，跳过');
        return;
      }

      this.selections.push({
        preview: selectionInfo.preview,
        startText: selectionInfo.startText,
        endText: selectionInfo.endText,
        startPos: selectionInfo.range.startPos,
        endPos: selectionInfo.range.endPos,
        charCount: selectionInfo.charCount,
        hasMore: selectionInfo.hasMore
      });

      console.log('[AIChatPane] 选区已添加，当前共', this.selections.length, '个选区');
    },

    /**
     * 移除指定索引的选区
     */
    removeSelection(index) {
      if (index >= 0 && index < this.selections.length) {
        this.selections.splice(index, 1);
        console.log('[AIChatPane] 移除选区，剩余', this.selections.length, '个');
      }
    },

    /**
     * 清除所有选区
     */
    clearAllSelections() {
      this.selections = [];
      try {
        const selection = window.Application?.Selection;
        if (selection) {
          selection.Collapse(1);
        }
      } catch (e) {
        console.warn('取消选区失败:', e);
      }
    },

    /**
     * 重试生成 - 重新发送上一条用户消息
     */
    async retryMessage(aiMessageIndex) {
      if (this.isLoading) {
        return;
      }

      let userMessageIndex = aiMessageIndex - 1;
      while (userMessageIndex >= 0 && this.messages[userMessageIndex].role !== 'user') {
        userMessageIndex--;
      }

      if (userMessageIndex < 0) {
        console.warn('找不到对应的用户消息');
        return;
      }

      const userMsg = this.messages[userMessageIndex];
      const userMessage = userMsg.content;

      this.messages.splice(aiMessageIndex, 1);

      const retryRanges = this.selections.length > 0
        ? this.selections.map(s => ({ startPos: s.startPos, endPos: s.endPos }))
        : null;
      this._sendStreamRequest(userMessage, retryRanges);
    },

    /**
     * 处理用户发送消息（由 ChatInput 触发）
     */
    handleSend(userMessage) {
      const userMsgObj = {
        role: 'user',
        content: userMessage
      };

      let selectionContext = null;
      let documentRange = null;

      if (this.selections.length > 0) {
        selectionContext = this.selections.map(s => ({
          preview: s.preview,
          startText: s.startText,
          endText: s.endText,
          startPos: s.startPos,
          endPos: s.endPos,
          charCount: s.charCount
        }));
        documentRange = this.selections.map(s => ({ startPos: s.startPos, endPos: s.endPos }));
        userMsgObj.selectionContext = selectionContext;
      }

      this.messages.push(userMsgObj);
      this.historyLoaded = true;

      this.clearAllSelections();

      this.saveMessageToHistory('user', userMessage, null, selectionContext);

      this._sendStreamRequest(userMessage, documentRange);
    },

    /**
     * 发送流式请求的公共方法
     */
    _sendStreamRequest(userMessage, documentRange) {
      this.isLoading = true;
      this.scrollToBottom();

      const aiMessageIndex = this.messages.length;
      this.messages.push({
        role: 'assistant',
        content: '',
        contentParts: [],
        documentJson: null,
        thinking: '',
        thinkingExpanded: true,
        thinkingStartTime: null,
        thinkingDuration: '',
        statusText: ''
      });

      const streamCtrl = api.chatStream(userMessage, {
        mode: this.mode,
        model: this.selectedModel || 'auto',
        documentRange: documentRange,
        history: this.messages.slice(0, -1).slice(-10),

        onMessage: (data) => {
          this._handleStreamMessage(data, aiMessageIndex);
        },

        onError: (error) => {
          console.error('请求失败:', error);
          this.messages[aiMessageIndex].content = `网络错误：${error.message}。请确保后端服务运行在 localhost:3880`;
        },

        onComplete: () => {
          this.isLoading = false;

          const msg = this.messages[aiMessageIndex];
          if (msg.thinking && msg.thinkingExpanded) {
            msg.thinkingExpanded = false;
          }

          this.scrollToBottom();

          if (msg.content) {
            this.saveMessageToHistory('assistant', msg.content, msg.documentJson, null, msg.contentParts);
          }
        }
      });

      this.currentStreamCtrl = streamCtrl;
    },

    /**
     * 处理流式消息
     */
    _handleStreamMessage(data, aiMessageIndex) {
      const msg = this.messages[aiMessageIndex];

      // 后端请求读取文档：委托 api.js 解析文档并回传
      if (data.type === 'read_document') {
        console.log('[AIChatPane] 后端请求读取文档, startPos:', data.startPos, 'endPos:', data.endPos);
        msg.contentParts.push({
          type: 'status',
          content: data.content || `📑 正在读取文档(${data.startPos} - ${data.endPos})`,
          loading: true
        });
        this.scrollToBottom();
        api.wsManager._handleDocumentRequest(data.startPos, data.endPos);
        return;
      }

      // 后端请求查询文档：委托 api.js 解析文档并执行 Style Query DSL
      if (data.type === 'query_document') {
        console.log('[AIChatPane] 后端请求查询文档, query:', data.query);
        msg.contentParts.push({
          type: 'status',
          content: data.content || '🔍 正在搜索文档...',
          loading: true
        });
        this.scrollToBottom();
        api.wsManager._handleQueryRequest(data.query);
        return;
      }

      // 查询完成：替换 loading 状态
      if (data.type === 'query_complete') {
        console.log('[AIChatPane] 文档查询完成');
        const parts = msg.contentParts;
        let found = false;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === 'status' && parts[i].loading) {
            parts.splice(i, 1, {
              type: 'status',
              content: data.content || '✅ 搜索完成',
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          parts.push({
            type: 'status',
            content: data.content || '✅ 搜索完成',
            loading: false
          });
        }
        this.scrollToBottom();
        return;
      }

      if (data.type === 'read_complete') {
        console.log('[AIChatPane] 文档读取完成');
        this.lastReadJSON = data.documentJson || null;
        // 反向查找最后一个 loading 状态的 status，用 splice 替换以确保 Vue 响应式更新
        const parts = msg.contentParts;
        let found = false;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === 'status' && parts[i].loading) {
            console.log('[AIChatPane] 找到 loading 状态，索引:', i, '内容:', parts[i].content);
            parts.splice(i, 1, {
              type: 'status',
              content: data.content || '✅ 文档读取完成',
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          console.warn('[AIChatPane] 未找到 loading 状态的 read_document，直接追加');
          parts.push({
            type: 'status',
            content: data.content || '✅ 文档读取完成',
            loading: false
          });
        }
        this.scrollToBottom();
        return;
      }

      if (data.type === 'generate_document') {
        console.log('[AIChatPane] 生成文档中...');
        msg.contentParts.push({
          type: 'status',
          content: data.content || '📝 正在生成文档',
          loading: true
        });
        this.scrollToBottom();
        return;
      }

      if (data.type === 'generate_complete') {
        console.log('[AIChatPane] 文档生成完成');
        const parts = msg.contentParts;
        let found = false;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === 'status' && parts[i].loading) {
            console.log('[AIChatPane] 找到 loading 状态，索引:', i, '内容:', parts[i].content);
            parts.splice(i, 1, {
              type: 'status',
              content: data.content || '✅ 文档已生成',
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          console.warn('[AIChatPane] 未找到 loading 状态的 generate_document，直接追加');
          parts.push({
            type: 'status',
            content: data.content || '✅ 文档已生成',
            loading: false
          });
        }
        this.scrollToBottom();
        return;
      }
      // 其他消息类型：text, json, status 等
      if (data.type === 'status' && data.content) {
        msg.contentParts.push({
          type: 'status',
          content: data.content,
          loading: !!data.loading
        });
        this.scrollToBottom();
        return;
      } else if (data.type === 'text' && data.content) {
        if (msg.thinkingStartTime && msg.thinkingExpanded) {
          const duration = Math.round((Date.now() - msg.thinkingStartTime) / 1000);
          msg.thinkingDuration = `${duration}秒`;
          msg.thinkingExpanded = false;
        }

        const content = data.content;
        msg.content += content;

        const parts = msg.contentParts;
        if (parts.length > 0 && parts[parts.length - 1].type === 'text') {
          parts[parts.length - 1].content += content;
        } else {
          parts.push({ type: 'text', content });
        }

        this.scrollToBottom();
      } else if (data.type === 'json' && data.content) {
        msg.documentJson = data.content;

        console.log('收到完整JSON，自动输出到文档');
        this.$nextTick(() => {
          this.insertToWord(msg, false);

          // 插入后显示预览条，等待用户确认或取消
          const paragraphs = data.content.paragraphs || [];
          // const previewText = paragraphs.map(p => p.content || '').join(' ').slice(0, 60);
          const paraCount = paragraphs.length;
          const tableCount = (data.content.tables || []).length;
          let summary = `${paraCount} 个段落`;
          if (tableCount > 0) {
            summary += `，${tableCount} 个表格`;
          }

          this.pendingDocument = {
            preview: `AI 已生成（${summary}）`
          };
          this.pendingDocumentMsg = msg;
        });

        this.scrollToBottom();
      } else if (data.error) {
        msg.content += `\n\n错误: ${data.error}`;
      }
    },

    /**
     * 确认文档修改 —— 去掉文策AI批注
     */
    confirmDocument() {
      if (this.pendingDocumentMsg) {
        try {
          const doc = window.Application.ActiveDocument;
          const msg = this.pendingDocumentMsg;
          if (doc && msg.insertStartPos !== undefined && msg.insertEndPos !== undefined) {
            // 遍历批注，删除文策AI的批注
            const comments = doc.Comments;
            for (let i = comments.Count; i >= 1; i--) {
              const comment = comments.Item(i);
              if (comment.Author === '文策AI') {
                const commentRange = comment.Scope;
                // 只删除当前插入范围内的批注
                if (commentRange.Start >= msg.insertStartPos && commentRange.End <= msg.insertEndPos) {
                  comment.Delete();
                  console.log('已删除文策AI批注');
                }
              }
            }
          }
        } catch (e) {
          console.error('删除批注失败:', e);
        }
      }
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
    },

    /**
     * 取消文档修改 —— 撤销插入
     */
    cancelDocument() {
      if (this.pendingDocumentMsg) {
        const msgIndex = this.messages.indexOf(this.pendingDocumentMsg);
        if (msgIndex !== -1) {
          this.revertToMessage(msgIndex);
        }
      }
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
      console.log('用户取消了文档插入，已撤销');
    },

    /**
     * 插入内容到 Word 文档
     */
    insertToWord(msg, insertAtCursor = true) {
      try {
        const doc = window.Application.ActiveDocument;
        if (!doc) {
          alert('请先打开一个Word文档');
          return;
        }

        let jsonData = msg.documentJson || null;
        const content = msg.content || '';

        if (!jsonData) {
          if (content.includes('```json')) {
            const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/);
            if (jsonMatch) {
              try {
                jsonData = JSON.parse(jsonMatch[1]);
              } catch (e) {
                console.log('JSON 代码块解析失败，使用纯文本模式');
              }
            }
          } else if (content.trim().startsWith('{') && content.trim().endsWith('}')) {
            try {
              jsonData = JSON.parse(content);
            } catch (e) {
              console.log('不是有效 JSON，使用纯文本模式');
            }
          }
        }

        if (jsonData && (jsonData.paragraphs || jsonData.tables)) {
          console.log('检测到文档 JSON，使用格式化输出');

          const selection = window.Application.Selection;
          let insertPos;

          if (insertAtCursor) {
            insertPos = selection.Range.Start;
            console.log('插入到光标位置:', insertPos);
          } else {
            insertPos = selection.Range.End;
            console.log('插入到选区末尾:', insertPos, 'Start:', selection.Range.Start);
          }

          msg.docLengthBefore = doc.Content.End;
          console.log('记录插入前文档长度:', msg.docLengthBefore);

          const result = generateDocxFromJSON(jsonData, doc, insertPos);

          if (result.success) {
            console.log('带格式的文档内容已成功插入');
            console.log(`实际插入范围: ${result.startPos} - ${result.endPos}`);

            msg.insertStartPos = result.startPos;
            msg.insertEndPos = result.endPos;
            console.log('记录插入范围用于撤销:', msg.insertStartPos, '-', msg.insertEndPos);

            try {
              const insertedRange = doc.Range(result.startPos, result.endPos);
              const comment = doc.Comments.Add(insertedRange, '');
              comment.Author = '文策AI';
              console.log('批注添加成功');
            } catch (e) {
              console.error('添加批注失败:', e);
            }
          } else {
            console.error('生成文档失败:', result.error);
            this.insertPlainText(content);
          }
        } else {
          this.insertPlainText(content, msg);
        }
      } catch (error) {
        console.error('插入文本失败:', error);
        alert('插入失败，请确保已打开Word文档');
      }
    },

    /**
     * 插入纯文本（作为后备方案）
     */
    insertPlainText(content, msg = null) {
      try {
        const doc = window.Application.ActiveDocument;
        const selection = window.Application.Selection;

        if (msg) {
          msg.docLengthBefore = doc.Content.End;
          console.log('记录插入前文档长度:', msg.docLengthBefore);
        }

        let cleanContent = content;
        if (content.includes('```json')) {
          cleanContent = content.replace(/```json\s*/g, '').replace(/```/g, '');
        }

        selection.TypeText(cleanContent);
        selection.TypeParagraph();

        console.log('纯文本已成功插入到Word文档');
      } catch (error) {
        console.error('插入纯文本失败:', error);
      }
    },

    hidePane() {
      let tsId = window.Application.PluginStorage.getItem('ai_taskpane_id');
      if (tsId) {
        let tskpane = window.Application.GetTaskPane(tsId);
        if (tskpane) {
          tskpane.Visible = false;
        }
      }
    }
  }
};
</script>

<style scoped>
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 100vh;
  width: 100%;
  background: #f7f8fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
}

.session-header {
  flex-shrink: 0;
  padding: 8px 14px;
  background: #f7f8fa;
  border-bottom: 1px solid #e8e8e8;
}

.session-title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}
</style>

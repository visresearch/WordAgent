<template>
  <div ref="chatRoot" class="chat-root">
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
        :uploaded-files="uploadedFiles"
        :pending-document="pendingDocument"
        :pending-deletes="pendingDeletes"
        @update:mode="mode = $event"
        @update:selected-model="selectedModel = $event"
        @send="handleSend"
        @stop="stopGeneration"
        @add-selection="addSelectionFromWord"
        @remove-selection="removeSelection"
        @add-files="addFiles"
        @remove-file="removeFile"
        @refresh-models="loadModels"
        @confirm-pending="confirmPending"
        @cancel-pending="cancelPending"
      />
    </div>
    <transition name="slide-session">
      <div v-if="sessionVisible" class="session-panel">
        <SessionPane
          :current-session-id="currentSessionId"
          @select-session="onSelectSession"
          @create-session="onCreateSession"
        />
      </div>
    </transition>
  </div>
</template>

<script>
/* global Word */
import { generateDocxFromJSON, deleteDocxPara, addCommentToParas } from '../js/docxJsonConverter.js';
import api from '../js/api.js';
import ChatMessages from './ChatMessages.vue';
import ChatInput from './ChatInput.vue';
import SessionPane from './SessionPane.vue';
import { sessionState } from '../../sessionState.js';

export default {
  name: 'AIChatPane',
  components: {
    ChatMessages,
    ChatInput,
    SessionPane
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
      selections: [],
      uploadedFiles: [],
      currentStreamCtrl: null,
      currentSessionId: null,
      currentSessionTitle: null,
      pendingDocument: null,
      pendingDocumentMsg: null,
      pendingDeletes: [],  // [{startParaIndex, endParaIndex, preview, msg}] 待确认删除列表
      hasHistory: false,
      historyLoaded: false,
      historyLoading: false,
      _streamingSessionId: null,
      _streamingCache: {},
      isWide: false
    };
  },
  computed: {
    sessionVisible() {
      if (sessionState.manualValue !== null) {
        return sessionState.manualValue;
      }
      return this.isWide;
    }
  },
  watch: {
    sessionVisible(val) {
      sessionState.visible = val;
    },
    isWide() {
      sessionState.manualValue = null;
    }
  },
  mounted() {
    this.loadModels();
    this.initSessionAndLoadHistory();

    this._onResize = () => {
      this.isWide = window.innerWidth >= 600;
    };
    this._onResize();
    window.addEventListener('resize', this._onResize);
    sessionState.visible = this.sessionVisible;
  },
  beforeUnmount() {
    if (this._onResize) {
      window.removeEventListener('resize', this._onResize);
    }
  },
  methods: {
    toggleThinking(index) {
      if (this.messages[index]) {
        this.messages[index].thinkingExpanded = !this.messages[index].thinkingExpanded;
      }
    },

    scrollToBottom() {
      this.$refs.chatMessages?.scrollToBottom();
    },

    async copyToClipboard(content) {
      try {
        await navigator.clipboard.writeText(content);
      } catch (error) {
        const textarea = document.createElement('textarea');
        textarea.value = content;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        try { document.execCommand('copy'); } catch (e) { /* ignore */ }
        document.body.removeChild(textarea);
      }
    },

    stopGeneration() {
      if (this.currentStreamCtrl) {
        this.currentStreamCtrl.abort();
        this.currentStreamCtrl = null;
      }
      this.isLoading = false;
    },

    // ============== 会话管理 ==============

    async initSessionAndLoadHistory() {
      try {
        let savedSessionId = null;
        try {
          savedSessionId = localStorage.getItem('wence_current_session_id');
        } catch (e) { /* ignore */ }

        if (savedSessionId) {
          this.currentSessionId = Number(savedSessionId) || savedSessionId;
          await this.loadSessionMessages();
        } else {
          const result = await api.getLatestSession();
          if (result.success && result.data?.session) {
            this.currentSessionId = result.data.session.id;
            this.currentSessionTitle = result.data.session.title || null;
            try {
              localStorage.setItem('wence_current_session_id', String(this.currentSessionId));
            } catch (e) { /* ignore */ }
            this.hasHistory = result.data.messages && result.data.messages.length > 0;
          } else {
            this.hasHistory = false;
          }
        }
      } catch (e) {
        console.error('[初始化] 失败:', e);
      }
    },

    async onSelectSession(session) {
      const sessionId = session.id;
      const title = session.title;

      if (!sessionId) {
        this.currentSessionId = null;
        this.currentSessionTitle = null;
        this.messages = [];
        this.hasHistory = false;
        this.historyLoaded = false;
        return;
      }

      if (this.currentSessionId === sessionId && this.historyLoaded) {
        return;
      }

      // 缓存正在流式生成的会话消息
      if (this.isLoading && this._streamingSessionId === this.currentSessionId) {
        this._streamingCache[this.currentSessionId] = this.messages;
      }

      // 从缓存恢复
      if (this._streamingCache[sessionId]) {
        this.messages = this._streamingCache[sessionId];
        this.currentSessionId = sessionId;
        this.currentSessionTitle = title || null;
        this.hasHistory = this.messages.length > 0;
        this.historyLoaded = true;
        try {
          localStorage.setItem('wence_current_session_id', String(sessionId));
        } catch (e) { /* ignore */ }
        this.$nextTick(() => this.scrollToBottom());
        return;
      }

      this.messages = [];
      this.hasHistory = false;
      this.historyLoaded = false;
      this.currentSessionId = sessionId;
      this.currentSessionTitle = title || null;

      try {
        localStorage.setItem('wence_current_session_id', String(sessionId));
      } catch (e) { /* ignore */ }

      await this.loadSessionMessages();
    },

    onCreateSession(session) {
      this.currentSessionId = session.id;
      this.currentSessionTitle = session.title;
      this.messages = [];
      this.historyLoaded = false;
      this.hasHistory = false;
      try {
        localStorage.setItem('wence_current_session_id', String(session.id));
      } catch (e) { /* ignore */ }
    },

    async loadAndShowHistory() {
      await this.loadSessionMessages();
      this.historyLoaded = true;
    },

    async loadSessionMessages() {
      if (!this.currentSessionId) return;

      this.historyLoading = true;
      try {
        const result = await api.getSession(this.currentSessionId);
        if (result.success && result.data?.messages) {
          this.messages = result.data.messages.map((msg) => ({
            role: msg.role,
            content: msg.content,
            contentParts: (msg.contentParts && msg.contentParts.length > 0)
              ? msg.contentParts
              : (msg.content ? [{ type: 'text', content: msg.content }] : []),
            documentJson: msg.documentJson || null,
            selectionContext: msg.selectionContext || null,
            thinking: msg.thinking || '',
            thinkingExpanded: false,
            thinkingDone: true
          }));

          if (result.data.lastUsedModel) {
            this.selectedModel = result.data.lastUsedModel;
          }
          if (result.data.lastUsedMode) {
            this.mode = result.data.lastUsedMode;
          }
          if (result.data.session) {
            this.currentSessionTitle = result.data.session.title || null;
          }

          this.hasHistory = this.messages.length > 0;
          this.historyLoaded = true;
          this.scrollToBottom();
        } else if (result && result.success === false) {
          this.currentSessionId = null;
          this.currentSessionTitle = null;
          this.messages = [];
          this.hasHistory = false;
          this.historyLoaded = false;
          try { localStorage.removeItem('wence_current_session_id'); } catch (e) { /* ignore */ }
        }
      } catch (e) {
        console.error('[加载历史] 失败:', e);
      }
      this.historyLoading = false;
    },

    async ensureSession() {
      if (this.currentSessionId) {
        try {
          const existsResult = await api.getSession(this.currentSessionId);
          if (existsResult.success && existsResult.data?.session) {
            return this.currentSessionId;
          }
        } catch (e) { /* ignore */ }

        this.currentSessionId = null;
        this.currentSessionTitle = null;
        try { localStorage.removeItem('wence_current_session_id'); } catch (e) { /* ignore */ }
      }

      try {
        const result = await api.createSession({ title: '新对话' });
        if (result.success && result.data?.session) {
          this.currentSessionId = result.data.session.id;
          try {
            localStorage.setItem('wence_current_session_id', String(this.currentSessionId));
          } catch (e) { /* ignore */ }
          window.dispatchEvent(new CustomEvent('session-created'));
          return this.currentSessionId;
        }
      } catch (e) {
        console.error('[自动创建会话] 失败:', e);
      }
      return null;
    },

    async saveMessageToHistory(role, content, documentJson = null, selectionContext = null, contentParts = null, thinking = null) {
      let sessionId = await this.ensureSession();
      if (!sessionId) return;

      try {
        let saveResult = await api.addSessionMessage(sessionId, {
          role,
          content,
          documentJson,
          selectionContext,
          contentParts,
          thinking,
          model: this.selectedModel || 'auto',
          mode: this.mode
        });

        if (!saveResult?.success) {
          this.currentSessionId = null;
          this.currentSessionTitle = null;
          try { localStorage.removeItem('wence_current_session_id'); } catch (e) { /* ignore */ }

          sessionId = await this.ensureSession();
          if (!sessionId) return;

          saveResult = await api.addSessionMessage(sessionId, {
            role,
            content,
            documentJson,
            selectionContext,
            contentParts,
            thinking,
            model: this.selectedModel || 'auto',
            mode: this.mode
          });
        }

        if (role === 'user' && (!this.currentSessionTitle || this.currentSessionTitle === '新对话')) {
          this.currentSessionTitle = content.length > 30 ? content.substring(0, 30) + '...' : content;
        }

        window.dispatchEvent(new CustomEvent('session-updated'));
      } catch (e) {
        console.warn('保存消息失败:', e);
      }
    },

    // ============== 模型加载 ==============

    async loadModels() {
      this.modelsLoading = true;
      try {
        const result = await api.getModels();
        if (result.success && result.data?.models && result.data.models.length > 0) {
          this.availableModels = result.data.models;
          const modelExists = this.availableModels.some(m => m.id === this.selectedModel);
          if (!modelExists) {
            this.selectedModel = 'auto';
          }
        } else {
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

    // ============== 选区管理 ==============

    async addSelectionFromWord() {
      try {
        await Word.run(async (context) => {
          const selection = context.document.getSelection();
          selection.load('text');
          await context.sync();

          const text = (selection.text || '').trim();
          if (!text || text.length < 2) return;

          const maxPreviewLen = 50;
          let preview = text;
          let hasMore = false;
          if (preview.length > maxPreviewLen) {
            preview = preview.substring(0, maxPreviewLen);
            hasMore = true;
          }

          const startText = text.substring(0, Math.min(10, text.length));
          const endText = text.length > 10 ? text.substring(text.length - 10) : text;

          this.selections.push({
            preview: preview + (hasMore ? '...' : ''),
            startText: startText + (text.length > 10 ? '...' : ''),
            endText: (text.length > 20 ? '...' : '') + endText,
            charCount: text.length,
            hasMore,
            fullText: text
          });
        });
      } catch (error) {
        console.error('获取选区失败:', error);
      }
    },

    removeSelection(index) {
      if (index >= 0 && index < this.selections.length) {
        this.selections.splice(index, 1);
      }
    },

    addFiles(files) {
      if (!Array.isArray(files) || files.length === 0) {
        return;
      }

      for (const file of files) {
        const exists = this.uploadedFiles.some(
          f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified
        );
        if (!exists) {
          this.uploadedFiles.push(file);
        }
      }
    },

    removeFile(index) {
      if (index >= 0 && index < this.uploadedFiles.length) {
        this.uploadedFiles.splice(index, 1);
      }
    },

    clearAllFiles() {
      this.uploadedFiles = [];
    },

    // ============== 消息发送与流式处理 ==============

    retryMessage(aiMessageIndex) {
      if (this.isLoading) return;

      let userMessageIndex = aiMessageIndex - 1;
      while (userMessageIndex >= 0 && this.messages[userMessageIndex].role !== 'user') {
        userMessageIndex--;
      }
      if (userMessageIndex < 0) return;

      const userMessage = this.messages[userMessageIndex].content;
      this.messages.splice(aiMessageIndex, 1);
      this._sendStreamRequest(userMessage, null);
    },

    async handleSend(userMessage) {
      const userMsgObj = {
        role: 'user',
        content: userMessage
      };

      let selectionContext = null;

      if (this.selections.length > 0) {
        selectionContext = this.selections.map((s) => ({
          preview: s.preview,
          startText: s.startText,
          endText: s.endText,
          charCount: s.charCount
        }));
        userMsgObj.selectionContext = selectionContext;
      }

      let uploadedFilesMeta = [];

      if (this.uploadedFiles.length > 0) {
        try {
          const uploadResult = await api.uploadFiles(this.uploadedFiles);
          if (uploadResult.success && uploadResult.files) {
            uploadedFilesMeta = uploadResult.files;
            console.log('[AIChatPane] 附件上传成功:', uploadedFilesMeta.length, '个文件');
          } else {
            console.warn('[AIChatPane] 附件上传失败:', uploadResult.error);
          }
        } catch (err) {
          console.warn('[AIChatPane] 附件上传异常:', err);
        }
      }

      this.messages.push(userMsgObj);
      this.historyLoaded = true;
      this.selections = [];
      this.clearAllFiles();

      this.saveMessageToHistory('user', userMessage, null, selectionContext);
      this._sendStreamRequest(userMessage, null, uploadedFilesMeta);
    },

    _sendStreamRequest(userMessage, documentRange, files = []) {
      this.isLoading = true;
      const streamSessionId = this.currentSessionId;
      this._streamingSessionId = streamSessionId;
      this.scrollToBottom();

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
      const aiMsg = this.messages[this.messages.length - 1];

      const streamCtrl = api.chatStream(userMessage, {
        mode: this.mode,
        model: this.selectedModel || 'auto',
        documentRange: documentRange,
        history: this.messages.slice(0, -1).slice(-10),
        files: files,

        onMessage: (data) => {
          this._handleStreamMessage(data, aiMsg);
        },

        onError: (error) => {
          console.error('请求失败:', error);
          aiMsg.content = `网络错误：${error.message}。请确保后端服务运行在 localhost:3880`;
          this.isLoading = false;
        },

        onComplete: () => {
          this.isLoading = false;
          this._streamingSessionId = null;

          if (aiMsg.thinking && aiMsg.thinkingExpanded) {
            aiMsg.thinkingExpanded = false;
          }

          if (this.currentSessionId === streamSessionId) {
            this.scrollToBottom();
            if (aiMsg.content) {
              this.saveMessageToHistory('assistant', aiMsg.content, aiMsg.documentJson, null, aiMsg.contentParts, aiMsg.thinking || null);
            }
          } else {
            if (aiMsg.content) {
              api.addSessionMessage(streamSessionId, {
                role: 'assistant',
                content: aiMsg.content,
                documentJson: aiMsg.documentJson,
                contentParts: aiMsg.contentParts,
                thinking: aiMsg.thinking || null,
                model: this.selectedModel || 'auto',
                mode: this.mode
              });
            }
          }

          delete this._streamingCache[streamSessionId];
        }
      });

      this.currentStreamCtrl = streamCtrl;
    },

    _handleStreamMessage(data, aiMsg) {
      const msg = aiMsg;

      // 后端请求读取文档
      if (data.type === 'read_document') {
        msg.contentParts.push({
          type: 'status',
          content: data.content || `📑 正在读取文档(段落 ${data.startParaIndex} - ${data.endParaIndex})`,
          loading: true
        });
        this.scrollToBottom();
        api.wsManager._handleDocumentRequest(data.startParaIndex, data.endParaIndex);
        return;
      }

      // 后端请求查询文档
      if (data.type === 'search_documnet') {
        msg.contentParts.push({
          type: 'status',
          content: data.content || '🔍 正在搜索文档...',
          loading: true
        });
        this.scrollToBottom();
        api.wsManager._handleQueryRequest(data.query);
        return;
      }

      // 查询完成
      if (data.type === 'query_complete') {
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
          parts.push({ type: 'status', content: data.content || '✅ 搜索完成', loading: false });
        }
        this.scrollToBottom();
        return;
      }

      // 读取完成
      if (data.type === 'read_complete') {
        this.lastReadJSON = data.documentJson || null;
        const parts = msg.contentParts;
        let found = false;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === 'status' && parts[i].loading) {
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
          parts.push({ type: 'status', content: data.content || '✅ 文档读取完成', loading: false });
        }
        this.scrollToBottom();
        return;
      }

      // 后端请求删除文档段落：用批注标记，加入待删除列表（非阻塞）
      if (data.type === 'delete_document') {
        console.log('[AIChatPane] 后端请求删除文档段落, startParaIndex:', data.startParaIndex, 'endParaIndex:', data.endParaIndex);
        msg.contentParts.push({
          type: 'status',
          content: data.content || `🗑️ 准备删除段落(${data.startParaIndex} - ${data.endParaIndex})`,
          loading: false
        });
        this.scrollToBottom();

        // 在文档中用批注标记要删除的段落
        (async () => {
          try {
            await Word.run(async (context) => {
              const allParas = context.document.body.paragraphs;
              allParas.load('items');
              await context.sync();

              let startIdx = data.startParaIndex;
              let endIdx = data.endParaIndex;
              const totalParas = allParas.items.length;
              if (endIdx === -1) endIdx = totalParas - 1;

              const startPara = allParas.items[startIdx];
              const endPara = allParas.items[endIdx];
              const startRange = startPara.getRange('Start');
              const endRange = endPara.getRange('End');
              const fullRange = startRange.expandTo(endRange);
              fullRange.insertComment('[文策AI-删除] 待删除内容');
              await context.sync();

              const deleteCount = endIdx - startIdx + 1;
              this.pendingDeletes.push({
                startParaIndex: startIdx,
                endParaIndex: endIdx,
                preview: `AI 准备删除 ${deleteCount} 个段落（段落 ${startIdx} - ${endIdx}）`,
                msg: msg
              });
              console.log('[AIChatPane] 已添加删除标记批注');
            });
          } catch (e) {
            console.error('[AIChatPane] 标记删除段落失败:', e);
          }
        })();
        return;
      }

      // 删除完成
      if (data.type === 'delete_complete') {
        const parts = msg.contentParts;
        let found = false;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === 'status' && parts[i].loading) {
            parts.splice(i, 1, {
              type: 'status',
              content: data.content || '✅ 删除完成',
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          parts.push({ type: 'status', content: data.content || '✅ 删除完成', loading: false });
        }
        this.scrollToBottom();
        return;
      }

      // 生成文档中
      if (data.type === 'generate_document') {
        msg.contentParts.push({
          type: 'status',
          content: data.content || '📝 正在生成文档',
          loading: true
        });
        this.scrollToBottom();
        return;
      }

      // 生成完成
      if (data.type === 'generate_complete') {
        const parts = msg.contentParts;
        let found = false;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === 'status' && parts[i].loading) {
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
          parts.push({ type: 'status', content: data.content || '✅ 文档已生成', loading: false });
        }
        this.scrollToBottom();
        return;
      }

      // 其他状态消息
      if (data.type === 'thinking' && data.content) {
        if (!msg.thinkingStartTime) {
          msg.thinkingStartTime = Date.now();
        }
        msg.thinking += data.content;
        this.scrollToBottom();
        return;
      }

      if (data.type === 'status' && data.content) {
        msg.contentParts.push({ type: 'status', content: data.content, loading: !!data.loading });
        this.scrollToBottom();
        return;
      }

      if (data.type === 'text' && data.content) {
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
          this.insertToWord(msg);

          // 插入后显示预览条，等待用户确认或取消
          const paragraphs = data.content.paragraphs || [];
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

    // ============== 待处理操作确认/取消 ==============

    /**
     * 一键确认所有待处理操作（删除 + 生成）
     */
    async confirmPending() {
      try {
        await Word.run(async (context) => {
          // 1. 通过"[文策AI-删除]"批注定位并删除段落
          if (this.pendingDeletes.length > 0) {
            const comments = context.document.body.getComments();
            comments.load('items');
            await context.sync();

            for (const comment of comments.items) {
              comment.load('content');
            }
            await context.sync();

            // 收集所有删除批注及其范围
            const deleteItems = [];
            for (const comment of comments.items) {
              if (comment.content && comment.content.startsWith('[文策AI-删除]')) {
                deleteItems.push(comment);
              }
            }

            // 从后往前删除（避免前面的删除影响后面的位置）
            for (let i = deleteItems.length - 1; i >= 0; i--) {
              const range = deleteItems[i].getRange();
              deleteItems[i].delete();
              range.delete();
            }
            await context.sync();
          }

          // 2. 确认生成文档（去掉"[文策AI]"批注）
          if (this.pendingDocumentMsg) {
            const comments = context.document.body.getComments();
            comments.load('items');
            await context.sync();

            for (const comment of comments.items) {
              comment.load('content');
            }
            await context.sync();

            for (const comment of comments.items) {
              if (comment.content && comment.content.startsWith('[文策AI]') && !comment.content.startsWith('[文策AI-删除]')) {
                comment.delete();
              }
            }
            await context.sync();
          }
        });
      } catch (e) {
        console.error('确认操作失败:', e);
      }
      this.pendingDeletes = [];
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
    },

    /**
     * 一键取消所有待处理操作（移除删除标记 + 撤销生成）
     */
    async cancelPending() {
      // 1. 移除所有"[文策AI-删除]"批注
      if (this.pendingDeletes.length > 0) {
        try {
          await Word.run(async (context) => {
            const comments = context.document.body.getComments();
            comments.load('items');
            await context.sync();

            for (const comment of comments.items) {
              comment.load('content');
            }
            await context.sync();

            for (const comment of comments.items) {
              if (comment.content && comment.content.startsWith('[文策AI-删除]')) {
                comment.delete();
              }
            }
            await context.sync();
          });
        } catch (e) {
          console.error('移除删除标记批注失败:', e);
        }
        this.pendingDeletes = [];
      }

      // 2. 撤销生成文档（通过批注定位并删除内容）
      if (this.pendingDocumentMsg) {
        try {
          await Word.run(async (context) => {
            const comments = context.document.body.getComments();
            comments.load('items');
            await context.sync();

            for (const comment of comments.items) {
              comment.load('content');
            }
            await context.sync();

            for (const comment of comments.items) {
              if (comment.content && comment.content.startsWith('[文策AI]') && !comment.content.startsWith('[文策AI-删除]')) {
                const range = comment.getRange();
                comment.delete();
                range.delete();
              }
            }
            await context.sync();
          });
        } catch (e) {
          console.error('撤销生成文档失败:', e);
        }
        this.pendingDocumentMsg.documentReverted = true;
      }
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
      console.log('用户取消了所有待处理操作');
    },

    /**
     * 还原到某条消息 - 通过批注定位删除插入的内容
     */
    async revertToMessage(messageIndex) {
      if (this.isLoading) return;
      const msg = this.messages[messageIndex];
      if (!msg) return;

      try {
        await Word.run(async (context) => {
          const comments = context.document.body.getComments();
          comments.load('items');
          await context.sync();

          for (const comment of comments.items) {
            comment.load('content');
          }
          await context.sync();

          for (const comment of comments.items) {
            if (comment.content && comment.content.startsWith('[文策AI]') && !comment.content.startsWith('[文策AI-删除]')) {
              const range = comment.getRange();
              comment.delete();
              range.delete();
            }
          }
          await context.sync();
        });
        msg.documentReverted = true;
      } catch (e) {
        console.error('撤销失败:', e);
      }
    },

    // ============== 文档操作 ==============

    async insertToWord(msg) {
      try {
        let jsonData = msg.documentJson || null;
        const content = msg.content || '';

        if (!jsonData) {
          if (content.includes('```json')) {
            const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/);
            if (jsonMatch) {
              try { jsonData = JSON.parse(jsonMatch[1]); } catch (e) { /* ignore */ }
            }
          } else if (content.trim().startsWith('{') && content.trim().endsWith('}')) {
            try { jsonData = JSON.parse(content); } catch (e) { /* ignore */ }
          }
        }

        if (jsonData && (jsonData.paragraphs || jsonData.tables)) {
          // 统一使用 JSON 中 AI 指定的 insertParaIndex 作为插入位置
          let insertLocation = 'end';
          if (jsonData.insertParaIndex !== null && jsonData.insertParaIndex !== undefined) {
            if (jsonData.insertParaIndex === -1) {
              insertLocation = 'end';
            } else {
              insertLocation = 'before';
              jsonData.paraIndex = jsonData.insertParaIndex;
            }
          }

          const result = await generateDocxFromJSON(jsonData, insertLocation);
          if (result?.error) {
            console.error('生成文档失败:', result.error);
            await this._insertPlainText(content);
          } else {
            // 添加"[文策AI]"批注标记新生成的内容
            try {
              await Word.run(async (context) => {
                const paras = context.document.body.paragraphs;
                paras.load('items');
                await context.sync();

                // 简单方式：对最后插入的段落范围添加批注
                // 由于无法精确获取插入范围，通过 insertParaIndex 推算
                const totalParas = paras.items.length;
                const newParaCount = jsonData.paragraphs?.length || 0;
                if (newParaCount > 0 && totalParas > 0) {
                  let startIdx, endIdx;
                  if (insertLocation === 'end') {
                    endIdx = totalParas - 1;
                    startIdx = totalParas - newParaCount;
                  } else {
                    startIdx = jsonData.insertParaIndex;
                    endIdx = startIdx + newParaCount - 1;
                  }
                  if (startIdx >= 0 && endIdx < totalParas) {
                    const startPara = paras.items[startIdx];
                    const endPara = paras.items[endIdx];
                    const startRange = startPara.getRange('Start');
                    const endRange = endPara.getRange('End');
                    const fullRange = startRange.expandTo(endRange);
                    fullRange.insertComment('[文策AI] 待添加内容');
                    await context.sync();
                  }
                }
              });
            } catch (e) {
              console.error('添加批注失败:', e);
            }
          }
        } else {
          await this._insertPlainText(content);
        }
      } catch (error) {
        console.error('插入文档失败:', error);
      }
    },

    async _insertPlainText(content) {
      try {
        await Word.run(async (context) => {
          const body = context.document.body;
          let cleanContent = content;
          if (content.includes('```json')) {
            cleanContent = content.replace(/```json\s*/g, '').replace(/```/g, '');
          }
          body.insertText(cleanContent, Word.InsertLocation.end);
          await context.sync();
        });
      } catch (error) {
        console.error('插入纯文本失败:', error);
      }
    }
  }
};
</script>

<style scoped>
.chat-root {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.ai-chat-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  height: 100%;
  background: #f7f8fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.session-panel {
  width: 300px;
  flex-shrink: 0;
  border-left: 1px solid #e8e8e8;
  height: 100%;
  overflow: hidden;
}

.session-header {
  padding: 10px 14px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
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

/* Session slide transition */
.slide-session-enter-active,
.slide-session-leave-active {
  transition: width 0.25s ease, opacity 0.25s ease;
  overflow: hidden;
}
.slide-session-enter-from,
.slide-session-leave-to {
  width: 0;
  opacity: 0;
}
</style>

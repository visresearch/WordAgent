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
        :selected-model-provider="selectedModelProvider"
        :available-models="availableModels"
        :models-loading="modelsLoading"
        :is-loading="isLoading"
        :selections="selections"
        :uploaded-files="uploadedFiles"
        :pending-document="pendingDocument"
        :pending-deletes="pendingDeletes"
        @update:mode="mode = $event"
        @update:selected-model="selectedModel = $event"
        @update:selected-model-provider="selectedModelProvider = $event"
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
import { settingsState } from '../../settingsState.js';

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
      selectedModelProvider: '',
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
      _streamInsertions: [], // [{insertParaIndex, count}] 当前流式中已执行的插入操作
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
    this._loadProofreadMode();
    this._loadWenceTempDir();

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
    _formatMcpText(value) {
      if (value === null || value === undefined) {
        return "";
      }

      let raw = "";
      if (typeof value === "string") {
        raw = value;
      } else {
        try {
          raw = JSON.stringify(value, null, 2);
        } catch (e) {
          raw = String(value);
        }
      }

      return raw;
    },

    _upsertMcpCallPart(msg, toolName, argsPayload = null) {
      if (!msg.contentParts) {
        msg.contentParts = [];
      }

      const safeToolName = toolName || "unknown_tool";
      const argsText = this._formatMcpText(argsPayload);

      const lastPart = msg.contentParts.length > 0 ? msg.contentParts[msg.contentParts.length - 1] : null;
      if (
        lastPart &&
        lastPart.type === "mcp" &&
        lastPart.toolName === safeToolName &&
        !lastPart.completed
      ) {
        if (!lastPart.argsText && argsText) {
          lastPart.argsText = argsText;
        }
        return;
      }

      msg.contentParts.push({
        type: "mcp",
        toolName: safeToolName,
        preview: `🔧 调用 MCP 工具: ${safeToolName}`,
        argsText: argsText || "无参数",
        outputText: "等待工具输出...",
        completed: false,
        isError: false,
      });
    },

    _attachMcpResultPart(msg, toolName, outputPreview, isError = false) {
      if (!msg.contentParts) {
        msg.contentParts = [];
      }

      const safeToolName = toolName || "unknown_tool";
      const outputText = this._formatMcpText(outputPreview);

      for (let i = msg.contentParts.length - 1; i >= 0; i--) {
        const part = msg.contentParts[i];
        if (part.type === "mcp" && part.toolName === safeToolName && !part.completed) {
          part.outputText = outputText || "（无输出）";
          part.completed = true;
          part.isError = !!isError;
          return;
        }
      }

      msg.contentParts.push({
        type: "mcp",
        toolName: safeToolName,
        preview: `🔧 调用 MCP 工具: ${safeToolName}`,
        argsText: "参数未知",
        outputText: outputText || "（无输出）",
        completed: true,
        isError: !!isError,
      });
    },

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
            thinkingDone: true,
            attachedFiles: msg.attachedFiles || null
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

    async saveMessageToHistory(role, content, documentJson = null, selectionContext = null, contentParts = null, thinking = null, attachedFiles = null) {
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
          mode: this.mode,
          attachedFiles
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
            mode: this.mode,
            attachedFiles
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
          selection.load("text");

          const selParagraphs = selection.paragraphs;
          selParagraphs.load("items");

          let selectionTables = null;
          let selectionInlinePictures = null;
          try {
            selectionTables = selection.tables;
            selectionTables.load("items");
          } catch (e) {
            selectionTables = null;
          }
          try {
            selectionInlinePictures = selection.inlinePictures;
            selectionInlinePictures.load("items");
          } catch (e) {
            selectionInlinePictures = null;
          }

          const allParagraphs = context.document.body.paragraphs;
          allParagraphs.load("items");
          await context.sync();

          const text = selection.text || "";
          const cleanedText = text.replace(/[\r\n\u0007\f]/g, " ").trim();
          const hasTable = !!(selectionTables && selectionTables.items && selectionTables.items.length > 0);
          const hasInlineImage = !!(
            selectionInlinePictures &&
            selectionInlinePictures.items &&
            selectionInlinePictures.items.length > 0
          );
          const hasNonTextContent = hasTable || hasInlineImage;

          if (!cleanedText && !hasNonTextContent) {
            return;
          }

          // 计算选区对应的段落索引
          let startParaIndex = 0;
          let endParaIndex = 0;

          if (selParagraphs.items.length > 0) {
            const firstSelParaRange = selParagraphs.items[0].getRange('Whole');
            const lastSelParaRange = selParagraphs.items[selParagraphs.items.length - 1].getRange('Whole');

            const startComparisons = allParagraphs.items.map(p =>
              p.getRange('Whole').compareLocationWith(firstSelParaRange)
            );
            const endComparisons = allParagraphs.items.map(p =>
              p.getRange('Whole').compareLocationWith(lastSelParaRange)
            );
            await context.sync();

            for (let i = 0; i < startComparisons.length; i++) {
              if (startComparisons[i].value === 'Equal') {
                startParaIndex = i;
                break;
              }
            }
            for (let i = 0; i < endComparisons.length; i++) {
              if (endComparisons[i].value === 'Equal') {
                endParaIndex = i;
              }
            }
          }

          const maxPreviewLen = 50;
          let displayText = cleanedText;
          if (!displayText) {
            if (hasInlineImage && hasTable) {
              displayText = "[图片+表格选区]";
            } else if (hasInlineImage) {
              displayText = "[图片选区]";
            } else if (hasTable) {
              displayText = "[表格选区]";
            }
          }

          let preview = displayText;
          let hasMore = false;
          if (preview.length > maxPreviewLen) {
            preview = preview.substring(0, maxPreviewLen);
            hasMore = true;
          }

          const startText = displayText.substring(0, Math.min(10, displayText.length));
          const endText =
            displayText.length > 10 ? displayText.substring(displayText.length - 10) : displayText;

          this.selections.push({
            preview: preview + (hasMore ? "..." : ""),
            startText: startText + (displayText.length > 10 ? "..." : ""),
            endText: (displayText.length > 20 ? "..." : "") + endText,
            charCount: cleanedText.length || (hasNonTextContent ? 1 : 0),
            hasMore,
            startParaIndex,
            endParaIndex,
            fullText: cleanedText
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
      let documentRange = null;

      if (this.selections.length > 0) {
        selectionContext = this.selections.map((s) => ({
          preview: s.preview,
          startText: s.startText,
          endText: s.endText,
          startParaIndex: s.startParaIndex,
          endParaIndex: s.endParaIndex,
          charCount: s.charCount
        }));
        documentRange = this.selections.map(s => ({
          startParaIndex: s.startParaIndex,
          endParaIndex: s.endParaIndex
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

      // 添加附件到用户消息对象
      if (uploadedFilesMeta.length > 0) {
        userMsgObj.attachedFiles = uploadedFilesMeta;
      }

      this.messages.push(userMsgObj);
      this.historyLoaded = true;
      this.selections = [];
      this.clearAllFiles();

      this.saveMessageToHistory('user', userMessage, null, selectionContext, null, null, uploadedFilesMeta.length > 0 ? uploadedFilesMeta : null);
      this._sendStreamRequest(userMessage, documentRange, uploadedFilesMeta);
    },

    _sendStreamRequest(userMessage, documentRange, files = []) {
      this.isLoading = true;
      const streamSessionId = this.currentSessionId;
      this._streamingSessionId = streamSessionId;
      this._streamInsertions = [];
      this.scrollToBottom();

      this.messages.push({
        role: 'assistant',
        content: '',
        contentParts: [],
        documentJson: null,
        thinking: '',
        thinkingExpanded: true,
        thinkingStartTime: null,
        thinkingDone: false,
        statusText: ''
      });
      const aiMsg = this.messages[this.messages.length - 1];

      const streamCtrl = api.chatStream(userMessage, {
        mode: this.mode,
        model: this.selectedModel,
        provider: this.selectedModelProvider,
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
          // _streamInsertions 不在此处重置，留给 confirmPending/cancelPending 使用

          if (aiMsg.thinking) {
            aiMsg.thinkingDone = true;
            if (aiMsg.thinkingExpanded) {
              aiMsg.thinkingExpanded = false;
            }
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

          // 如果只有删除没有插入（无 json 事件），在流结束后补充添加删除批注
          if (this.pendingDeletes.length > 0 && !this.pendingDocumentMsg) {
            this._addDeleteComments();
          }

          delete this._streamingCache[streamSessionId];
        }
      });

      this.currentStreamCtrl = streamCtrl;
    },

    _handleStreamMessage(data, aiMsg) {
      const msg = aiMsg;

      // 收到非 thinking 事件时，标记思考已结束
      if (data.type !== 'thinking' && msg.thinkingStartTime && !msg.thinkingDone) {
        msg.thinkingDone = true;
        if (msg.thinkingExpanded) {
          msg.thinkingExpanded = false;
        }
      }

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
              content: data.content || '📑 文档读取完成',
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          parts.push({ type: 'status', content: data.content || '📑 文档读取完成', loading: false });
        }
        this.scrollToBottom();
        return;
      }

      // 后端请求删除文档段落：记录待删除列表，批注将在所有文档操作完成后统一添加
      if (data.type === 'delete_document') {
        console.log('[AIChatPane] 后端请求删除文档段落, startParaIndex:', data.startParaIndex, 'endParaIndex:', data.endParaIndex);
        msg.contentParts.push({
          type: 'status',
          content: data.content || `🗑️ 准备删除段落(${data.startParaIndex} - ${data.endParaIndex})`,
          loading: false
        });
        this.scrollToBottom();

        // 存储原始索引，确认时再根据实际插入情况计算偏移
        this.pendingDeletes.push({
          origStartParaIndex: data.startParaIndex,
          origEndParaIndex: data.endParaIndex,
          preview: `AI 准备删除段落（段落 ${data.startParaIndex} - ${data.endParaIndex}）`,
          msg: msg,
          _commentAdded: false
        });
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
              content: data.content || '📝 文档已生成',
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          parts.push({ type: 'status', content: data.content || '📝 文档已生成', loading: false });
        }
        this.scrollToBottom();
        return;
      }

      if (data.type === "mcp_tool_call") {
        this._upsertMcpCallPart(msg, data.toolName, data.args);
        this.scrollToBottom();
        return;
      }

      if (data.type === "mcp_tool_result") {
        this._attachMcpResultPart(msg, data.toolName, data.outputPreview, data.isError);
        this.scrollToBottom();
        return;
      }

      // 其他状态消息
      if (data.type === 'thinking' && data.content) {
        if (!msg.thinkingStartTime) {
          msg.thinkingStartTime = Date.now();
          msg.thinkingDone = false;
        }
        msg.thinking += data.content;
        this.scrollToBottom();
        return;
      }

      if (data.type === 'status' && data.content) {
        const mcpCallPattern = /^🔧\s*调用\s*MCP\s*工具:\s*([A-Za-z0-9._:-]+)(?:\((.*)\))?\s*$/s;
        const mcpMatch = String(data.content).match(mcpCallPattern);
        if (mcpMatch) {
          const toolName = mcpMatch[1];
          const argsRaw = (mcpMatch[2] || "").trim();
          let argsPayload = argsRaw;
          if (argsRaw) {
            try {
              argsPayload = JSON.parse(argsRaw);
            } catch (e) {
              // 保留原始字符串
            }
          }
          this._upsertMcpCallPart(msg, toolName, argsPayload || null);
          this.scrollToBottom();
          return;
        }

        msg.contentParts.push({ type: 'status', content: data.content, loading: !!data.loading });
        this.scrollToBottom();
        return;
      }

      // 处理 tool 输出压缩信息
      if (data.type === 'tool_compress') {
        msg.contentParts.push({
          type: 'tool_compress',
          content: data.content,
          detail: data.detail || {},
        });
        this.scrollToBottom();
        return;
      }

      if (data.type === 'text' && data.content) {
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

        // 计算原始插入位置和段落数
        const _insParaCount = (data.content.paragraphs || []).length;
        const _insTableCount = (data.content.tables || []).length;
        const _insShiftCount = _insParaCount + _insTableCount;
        const _insParaIndex = data.content.insertParaIndex ?? -1;

        // 根据同一流中之前的插入操作调整当前插入位置
        // （第二次及以后的插入需要偏移，因为前面的插入已改变文档结构）
        if (_insParaIndex !== -1 && _insParaIndex !== null && _insParaIndex !== undefined && this._streamInsertions.length > 0) {
          let adjustedInsPos = _insParaIndex;
          for (const ins of this._streamInsertions) {
            const insAt = ins.insertParaIndex;
            if (insAt === -1 || insAt === null || insAt === undefined) continue;
            if (insAt <= adjustedInsPos) {
              adjustedInsPos += ins.count;
            }
          }
          data.content.insertParaIndex = adjustedInsPos;
        }

        // 用原始索引记录插入意图（供后续 delete_document 偏移计算）
        if (_insShiftCount > 0) {
          this._streamInsertions.push({ insertParaIndex: _insParaIndex, count: _insShiftCount });
        }

        console.log('收到完整JSON，自动输出到文档');
        this.$nextTick(async () => {
          // 先设置 pendingDocument 更新 UI（同步，立即生效）
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

          // 执行文档插入（await 确保完成后再添加批注，避免并发 Word.run）
          await this.insertToWord(msg);

          // 插入完成后，统一添加所有待处理批注（生成 + 删除）
          await this._addAllPendingComments(msg);
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
      // 1. 删除段落
      if (this.pendingDeletes.length > 0) {
        let deleted = false;
        const useComments = this.pendingDeletes.some(pd => pd._markingMode === 'comment');

        if (useComments) {
          // 批注模式：通过批注定位删除
          try {
            await Word.run(async (context) => {
              const comments = context.document.body.getComments();
              comments.load('items');
              await context.sync();

              for (const comment of comments.items) {
                comment.load('content');
              }
              await context.sync();

              const deleteItems = [];
              for (const comment of comments.items) {
                if (comment.content && comment.content.startsWith('[文策AI-删除]')) {
                  deleteItems.push(comment);
                }
              }

              if (deleteItems.length > 0) {
                for (let i = deleteItems.length - 1; i >= 0; i--) {
                  const range = deleteItems[i].getRange();
                  deleteItems[i].delete();
                  range.delete();
                }
                await context.sync();
                deleted = true;
                console.log('[AIChatPane] 通过批注成功删除', deleteItems.length, '处内容');
              }
            });
          } catch (e) {
            console.warn('[AIChatPane] 通过批注删除失败，降级到索引删除:', e);
          }
        }

        // 高亮模式 或 批注模式降级：按索引删除，先清除高亮再删除
        if (!deleted) {
          const deletes = this.pendingDeletes.map(pd => {
            let adjStart = pd._adjStartParaIndex ?? pd.origStartParaIndex;
            let adjEnd = pd._adjEndParaIndex ?? pd.origEndParaIndex;
            if (pd._adjStartParaIndex === undefined) {
              // 未记录调整后索引，重新计算
              adjStart = pd.origStartParaIndex;
              adjEnd = pd.origEndParaIndex;
              for (const ins of this._streamInsertions) {
                const insAt = ins.insertParaIndex;
                if (insAt === -1 || insAt === null || insAt === undefined) continue;
                if (insAt <= adjStart) {
                  adjStart += ins.count;
                  if (adjEnd !== -1) adjEnd += ins.count;
                }
              }
            }
            return { startParaIndex: adjStart, endParaIndex: adjEnd, isHighlight: pd._markingMode === 'highlight' };
          });
          const sortedDeletes = deletes.sort((a, b) => b.startParaIndex - a.startParaIndex);
          for (const d of sortedDeletes) {
            try {
              // 先清除高亮标记
              if (d.isHighlight) {
                await this._clearHighlightOnRange(d.startParaIndex, d.endParaIndex);
              }
              const result = await deleteDocxPara(d.startParaIndex, d.endParaIndex);
              console.log('[AIChatPane] 按索引删除:', result.message);
            } catch (e) {
              console.error('[AIChatPane] 删除段落失败:', e);
            }
          }
        }
      }

      // 2. 确认生成文档：移除标注（保留内容）
      if (this.pendingDocumentMsg) {
        const insertMsg = this.pendingDocumentMsg;
        if (insertMsg._markingMode === 'highlight') {
          // 高亮模式：清除高亮
          if (insertMsg.insertStartParaIndex !== undefined && insertMsg.insertEndParaIndex !== undefined) {
            await this._clearHighlightOnRange(insertMsg.insertStartParaIndex, insertMsg.insertEndParaIndex);
          }
        } else {
          // 批注模式：删除批注
          await this._removeCommentsByPrefix('[文策AI]', true);
        }
      }

      this.pendingDeletes = [];
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
      this._streamInsertions = [];
    },

    /**
     * 一键取消所有待处理操作（移除删除标记 + 撤销生成）
     */
    async cancelPending() {
      // 1. 移除所有删除标注（不删除内容）
      if (this.pendingDeletes.length > 0) {
        const hasComments = this.pendingDeletes.some(pd => pd._markingMode === 'comment');
        const hasHighlights = this.pendingDeletes.some(pd => pd._markingMode === 'highlight');
        if (hasComments) {
          await this._removeCommentsByPrefix('[文策AI-删除]');
        }
        if (hasHighlights) {
          for (const pd of this.pendingDeletes) {
            if (pd._markingMode === 'highlight' && pd._adjStartParaIndex !== undefined) {
              await this._clearHighlightOnRange(pd._adjStartParaIndex, pd._adjEndParaIndex);
            }
          }
        }
        this.pendingDeletes = [];
      }

      // 2. 撤销生成文档
      if (this.pendingDocumentMsg) {
        let reverted = false;
        const insertMsg = this.pendingDocumentMsg;

        if (insertMsg._markingMode === 'highlight') {
          // 高亮模式：清除高亮后按索引删除插入的内容
          if (insertMsg.insertStartParaIndex !== undefined && insertMsg.insertEndParaIndex !== undefined) {
            await this._clearHighlightOnRange(insertMsg.insertStartParaIndex, insertMsg.insertEndParaIndex);
            try {
              const result = await deleteDocxPara(insertMsg.insertStartParaIndex, insertMsg.insertEndParaIndex);
              reverted = result?.success ?? false;
            } catch (e) {
              console.warn('按索引撤销失败:', e);
            }
          }
        } else {
          // 批注模式：通过批注定位删除内容
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
              reverted = true;
            });
          } catch (e) {
            console.warn('通过批注撤销生成文档失败:', e);
          }
        }
        this.pendingDocumentMsg.documentReverted = reverted;
      }
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
      this._streamInsertions = [];
      console.log('用户取消了所有待处理操作');
    },

    /**
     * 统一添加所有待处理批注（在 insertToWord 完成后调用）
     */
    async _addAllPendingComments(insertMsg) {
      const mode = settingsState.proofreadMode || 'revision';
      // 为生成的内容添加标注
      if (insertMsg) {
        const si = insertMsg.insertStartParaIndex;
        const ei = insertMsg.insertEndParaIndex;
        if (si !== undefined && ei !== undefined) {
          try {
            const res = await addCommentToParas(si, ei, '[文策AI] 待添加内容', mode);
            if (res && res.success) {
              insertMsg._markingMode = res.mode; // 'comment' or 'highlight'
              console.log('[AIChatPane] 已为生成内容添加标注, 模式:', res.mode, '范围:', si, '-', ei);
            } else {
              console.warn('[AIChatPane] 添加生成标注返回失败:', res);
            }
          } catch (e) {
            console.warn('添加生成标注异常:', e);
          }
        } else {
          console.warn('[AIChatPane] 插入范围未设置, insertStartParaIndex:', si, 'insertEndParaIndex:', ei);
        }
      }
      // 为待删除内容添加标注
      await this._addDeleteComments();
    },

    /**
     * 为待删除内容添加批注（使用调整后的索引）
     */
    async _addDeleteComments() {
      const mode = settingsState.proofreadMode || 'revision';
      for (const pd of this.pendingDeletes) {
        if (pd._commentAdded) continue;
        let adjStart = pd.origStartParaIndex;
        let adjEnd = pd.origEndParaIndex;
        for (const ins of this._streamInsertions) {
          const insAt = ins.insertParaIndex;
          if (insAt === -1 || insAt === null || insAt === undefined) continue;
          if (insAt <= adjStart) {
            adjStart += ins.count;
            if (adjEnd !== -1) adjEnd += ins.count;
          }
        }
        try {
          const res = await addCommentToParas(adjStart, adjEnd, '[文策AI-删除] 待删除内容', mode);
          if (res && res.success) {
            pd._commentAdded = true;
            pd._adjStartParaIndex = adjStart;
            pd._adjEndParaIndex = adjEnd;
            pd._markingMode = res.mode; // 'comment' or 'highlight'
            console.log('[AIChatPane] 已添加删除标注(模式:', res.mode, '索引:', adjStart, '-', adjEnd, ')');
          } else {
            console.warn('[AIChatPane] 删除标注添加失败:', res, '索引:', adjStart, '-', adjEnd);
          }
        } catch (e) {
          console.warn('[AIChatPane] 标记删除段落异常:', e);
        }
      }
    },

    /**
     * 移除指定前缀的批注（best-effort，不抛错）
     * @param {string} prefix - 批注内容前缀
     * @param {boolean} excludeDelete - 是否排除 '[文策AI-删除]' 前缀的批注
     */
    async _removeCommentsByPrefix(prefix, excludeDelete = false) {
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
            if (comment.content && comment.content.startsWith(prefix)) {
              if (excludeDelete && comment.content.startsWith('[文策AI-删除]')) continue;
              comment.delete();
            }
          }
          await context.sync();
        });
      } catch (e) {
        console.warn('清理批注失败(不影响功能):', e);
      }
    },

    /**
     * 清除指定段落范围的高亮（用于批注 API 不可用时的降级标记清理）
     */
    async _clearHighlightOnRange(startParaIndex, endParaIndex) {
      try {
        await Word.run(async (context) => {
          const allParas = context.document.body.paragraphs;
          allParas.load('items');
          await context.sync();
          const total = allParas.items.length;
          let end = endParaIndex === -1 ? total - 1 : endParaIndex;
          if (startParaIndex >= 0 && end < total) {
            const startRange = allParas.items[startParaIndex].getRange('Start');
            const endRange = allParas.items[end].getRange('End');
            const fullRange = startRange.expandTo(endRange);
            fullRange.font.highlightColor = null;
            await context.sync();
          }
        });
      } catch (e) {
        // best-effort
      }
    },

    /**
     * 还原到某条消息 - 通过批注定位删除插入的内容
     */
    async revertToMessage(messageIndex) {
      if (this.isLoading) return;
      const msg = this.messages[messageIndex];
      if (!msg) return;

      let reverted = false;
      // 优先通过批注定位删除
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
          reverted = true;
        });
      } catch (e) {
        console.warn('通过批注撤销失败，尝试按索引撤销:', e);
      }

      // 降级方案：通过记录的段落索引删除
      if (!reverted && msg.insertStartParaIndex !== undefined && msg.insertEndParaIndex !== undefined) {
        try {
          const result = await deleteDocxPara(msg.insertStartParaIndex, msg.insertEndParaIndex);
          if (result.success) {
            reverted = true;
            console.log('[AIChatPane] 按索引撤销成功:', result.message);
          }
        } catch (e) {
          console.error('按索引撤销也失败:', e);
        }
      }

      msg.documentReverted = reverted;
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

        if (jsonData && (jsonData.paragraphs || jsonData.tables || jsonData.images)) {
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
            // 计算插入范围并记录到 msg（用于撤销）
            const newParaCount = jsonData.paragraphs?.length || 0;
            if (newParaCount > 0) {
              try {
                await Word.run(async (context) => {
                  const paras = context.document.body.paragraphs;
                  paras.load('items');
                  await context.sync();

                  const totalParas = paras.items.length;
                  let startIdx, endIdx;
                  if (insertLocation === 'end') {
                    endIdx = totalParas - 1;
                    startIdx = totalParas - newParaCount;
                  } else {
                    startIdx = jsonData.insertParaIndex;
                    endIdx = startIdx + newParaCount - 1;
                  }
                  if (startIdx >= 0 && endIdx < totalParas) {
                    msg.insertStartParaIndex = startIdx;
                    msg.insertEndParaIndex = endIdx;
                  }
                });
              } catch (e) { /* ignore */ }

              // 批注将在 _addAllPendingComments 中统一添加
            }
          }
        } else {
          await this._insertPlainText(content);
        }
      } catch (error) {
        console.error('插入文档失败:', error);
      }
    },

    async _loadProofreadMode() {
      try {
        const data = await api.getSettings();
        if (data && data.proofreadMode) {
          settingsState.proofreadMode = data.proofreadMode;
        }
      } catch (e) {
        console.warn('加载 proofreadMode 失败，使用默认值:', e);
      }
    },

    async _loadWenceTempDir() {
      try {
        const data = await api.getWenceTempDir();
        const dir = data && data.dir ? String(data.dir) : "";
        if (!dir) {
          return;
        }
        window.__WENCE_TEMP_DIR__ = dir;
        try {
          localStorage.setItem("wence_temp_dir", dir);
        } catch (e) {}
      } catch (e) {
        console.warn("加载图片临时目录失败:", e);
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

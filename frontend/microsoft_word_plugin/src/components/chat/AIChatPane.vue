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
        :enable-thinking="enableThinking"
        @update:mode="mode = $event"
        @update:selected-model="selectedModel = $event"
        @update:selected-model-provider="selectedModelProvider = $event"
        @update:enable-thinking="enableThinking = $event"
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
import { generateDocxFromJSON, deleteDocxPara, addCommentToParas, resolveParagraphParaIDs } from '../js/docxJsonConverter.js';
import api from '../js/api.js';
import ChatMessages from './ChatMessages.vue';
import ChatInput from './ChatInput.vue';
import SessionPane from './SessionPane.vue';
import { sessionState } from '../../sessionState.js';
import { settingsState } from '../../settingsState.js';
import { chatState } from '../../chatState.js';

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
      pendingDeletes: [],  // [{paraIDs, docId, preview, msg}] 待确认删除列表
      pendingInsertions: [], // [{documentJson, docId, insertParaID, msg}] 待确认的文档插入列表
      _streamInsertions: [], // [{insertParaID, count, docId}] 当前流式中已执行的插入操作
      hasHistory: false,
      historyLoaded: false,
      historyLoading: false,
      _streamingSessionId: null,
      _streamingCache: {},
      isWide: false,
      enableThinking: true,  // 是否启用深度思考
      _insertQueue: Promise.resolve(),
      _initializing: false   // 是否正在初始化，防止 ensureSession 创建重复会话
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
    },
    isLoading(val) {
      chatState.aiBusy = !!val;
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
    chatState.aiBusy = false;
    if (this._onResize) {
      window.removeEventListener('resize', this._onResize);
    }
  },
  methods: {
    _sanitizeContentParts(parts) {
      if (!Array.isArray(parts)) {
        return [];
      }
      return parts.map((part) => {
        const { loading, ...rest } = part || {};
        return rest;
      });
    },

    _extractDocumentJsonFromToolJson(toolJson) {
      const calls = Array.isArray(toolJson?.calls) ? toolJson.calls : [];
      for (let i = calls.length - 1; i >= 0; i--) {
        const call = calls[i];
        if (call?.tool !== 'generate_document') {
          continue;
        }
        const output = call.output;
        if (output && typeof output === 'object' && (output.paragraphs || output.tables || output.images)) {
          return output;
        }
        if (typeof output === 'string') {
          try {
            const parsed = JSON.parse(output);
            if (parsed && (parsed.paragraphs || parsed.tables || parsed.images)) {
              return parsed;
            }
          } catch (e) {}
        }
      }
      return null;
    },

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
      // 防止初始化过程中 ensureSession 创建新会话
      this._initializing = true;
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

            // 直接使用返回的消息数据
            const messages = result.data.messages || [];
            this.messages = messages.map((msg) => {
              const toolJson = msg.toolJson || null;
              const parts = this._sanitizeContentParts(msg.contentParts);
              return {
                role: msg.role,
                content: msg.content,
                contentParts: parts.length > 0 ? parts : (msg.content ? [{ type: 'text', content: msg.content }] : []),
                documentJson: this._extractDocumentJsonFromToolJson(toolJson),
                toolJson,
                selectionContext: msg.selectionContext || null,
                thinking: msg.thinking || '',
                thinkingExpanded: !!msg.thinking,
                thinkingDone: true,
                attachedFiles: msg.attachedFiles || null
              };
            });

            if (result.data.lastUsedModel) {
              this.selectedModel = result.data.lastUsedModel;
            }
            if (result.data.lastUsedMode) {
              this.mode = result.data.lastUsedMode;
            }

            this.hasHistory = this.messages.length > 0;
            this.historyLoaded = true;
            this.$nextTick(() => this.scrollToBottom());
          } else {
            this.hasHistory = false;
            this.historyLoaded = false;
          }
        }
      } catch (e) {
        console.error('[初始化] 失败:', e);
      } finally {
        this._initializing = false;
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

      await this.loadSessionMessages(sessionId);
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

    async loadSessionMessages(sessionId) {
      const targetSessionId = sessionId || this.currentSessionId;
      if (!targetSessionId) return;

      this.historyLoading = true;
      try {
        const result = await api.getSession(targetSessionId);
        // 检查当前会话是否已切换，避免竞态条件
        if (this.currentSessionId !== targetSessionId) {
          console.log('[加载历史] 会话已切换，忽略过时响应');
          return;
        }
        if (result.success && result.data?.messages) {
          this.messages = result.data.messages.map((msg) => {
            const toolJson = msg.toolJson || null;
            const parts = this._sanitizeContentParts(msg.contentParts);
            return {
              role: msg.role,
              content: msg.content,
              contentParts: parts.length > 0 ? parts : (msg.content ? [{ type: 'text', content: msg.content }] : []),
              documentJson: this._extractDocumentJsonFromToolJson(toolJson),
              toolJson,
              selectionContext: msg.selectionContext || null,
              thinking: msg.thinking || '',
              thinkingExpanded: !!msg.thinking,
              thinkingDone: true,
              attachedFiles: msg.attachedFiles || null
            };
          });

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
      // 初始化期间如果有会话 ID 就直接返回，避免创建重复会话
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

      // 初始化期间不创建新会话，等待初始化完成
      if (this._initializing) {
        return null;
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

          const doc = context.document;
          // Microsoft Word 只会有一个活动文档，固定使用 0 作为当前文档ID
          const docId = 0;
          const docName = '';

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
            // 用户未选中任何内容，提示用户
            console.warn('[Selection] 未选中任何内容');
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
            fullText: cleanedText,
            docId
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
      // 确保有会话
      const sessionId = await this.ensureSession();
      if (!sessionId) {
        console.error('[发送] 无法获取会话，取消发送');
        return;
      }

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
          charCount: s.charCount,
          docId: Number.isInteger(s.docId) ? s.docId : 0,
          docName: s.docName || ''
        }));
        documentRange = this.selections.map(s => ({
          startParaIndex: s.startParaIndex,
          endParaIndex: s.endParaIndex,
          docId: Number.isInteger(s.docId) ? s.docId : 0,
          docName: s.docName || ''
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
      if (!this.currentSessionTitle || this.currentSessionTitle === '新对话') {
        this.currentSessionTitle = userMessage.length > 30 ? userMessage.substring(0, 30) + '...' : userMessage;
      }
      this.historyLoaded = true;
      this.selections = [];
      this.clearAllFiles();

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
        history: this.messages.slice(0, -2).slice(-10),
        files: files,
        enableThinking: this.enableThinking,
        sessionId: streamSessionId,

        onMessage: (data) => {
          this._handleStreamMessage(data, aiMsg);
        },

        onError: (error) => {
          console.error('请求失败:', error);
          const errMsg = String(error?.message || '');
          if (errMsg.includes('⛔ 网络超时连接，自动断开')) {
            aiMsg.content = '⛔ 网络超时连接，自动断开';
          } else {
            aiMsg.content = `网络错误：${errMsg}。请确保后端服务运行在 localhost:3880`;
          }
          this.isLoading = false;
        },

        onComplete: () => {
          this.isLoading = false;
          this._streamingSessionId = null;

          if (aiMsg.thinking) {
            aiMsg.thinkingDone = true;
          }

          this.scrollToBottom();
          window.dispatchEvent(new CustomEvent('session-created'));

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

      // 后端 keepalive ping 仅用于保活，不影响任何 UI 状态
      if (data.type === 'ping') {
        return;
      }

      // 收到非 thinking 事件时，标记思考已结束
      if (data.type !== 'thinking' && msg.thinkingStartTime && !msg.thinkingDone) {
        msg.thinkingDone = true;
      }

      // 后端请求读取文档
      if (data.type === 'read_document') {
        const hasParaIDMode =
          this._toParaIdOrNull(data.startParaID) !== null || this._toParaIdOrNull(data.endParaID) !== null;
        msg.contentParts.push({
          type: 'status',
          content: data.content || (
            hasParaIDMode
              ? `📑 正在读取文档(段落ID ${data.startParaID ?? ''} - ${data.endParaID ?? data.startParaID ?? ''})`
              : `📑 正在读取文档(段落 ${data.startParaIndex} - ${data.endParaIndex})`
          ),
          loading: true
        });
        this.scrollToBottom();
        api.wsManager._handleDocumentRequest({
          startParaIndex: this._toIntOrNull(data.startParaIndex),
          endParaIndex: this._toIntOrNull(data.endParaIndex),
          startParaID: this._toParaIdOrNull(data.startParaID),
          endParaID: this._toParaIdOrNull(data.endParaID),
          docId: this._toIntOrDefault(data.docId, 0)
        });
        return;
      }

      // 后端请求查询文档
      if (data.type === 'search_document') {
        msg.contentParts.push({
          type: 'status',
          content: data.content || '🔍 正在搜索文档...',
          loading: true
        });
        this.scrollToBottom();
        api.wsManager._handleQueryRequest(data.query, this._toIntOrDefault(data.docId, 0));
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

      // 后端请求删除文档段落：立即标记删除范围（真正删除在用户确认时执行）
      if (data.type === 'delete_document') {
        const paraIDs = this._normalizeParaIdList(data.paraIDs);
        console.log('[AIChatPane] 后端请求删除文档段落, paraIDs:', paraIDs, 'docId:', data.docId);
        msg.contentParts.push({
          type: 'status',
          content: data.content || `🗑️ 准备删除段落ID(${paraIDs.join(', ')})`,
          loading: false
        });
        this.scrollToBottom();
        this._applyImmediateDelete({
          paraIDs,
          docId: this._toIntOrDefault(data.docId, 0)
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
        msg._docId = this._toIntOrDefault(data.docId, 0);
        msg._insertParaID = this._toParaIdOrNull(data.insertParaID);
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
        }
        // 同一轮对话可能在“已结束”后继续返回思考片段，收到新 thinking 时恢复进行中状态
        msg.thinkingDone = false;
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
        const insItem = {
          documentJson: data.content,
          docId: this._toIntOrDefault(data.docId, this._toIntOrDefault(data.content.docId, 0)),
          insertParaID: this._toParaIdOrNull(data.content.insertParaID),
          msg: msg
        };
        this._insertQueue = this._insertQueue
          .then(() => this._applyImmediateInsertion(insItem))
          .then((inserted) => {
            if (!inserted) {
              msg.contentParts.push({
                type: 'status',
                content: '⚠️ 文档插入失败，请检查目标文档是否可写',
                loading: false
              });
              this.scrollToBottom();
            }
          })
          .catch((e) => {
            console.error('[AIChatPane] 插入队列执行失败:', e);
          });
        this.scrollToBottom();
      } else if (data.error) {
        msg.content += `\n\n错误: ${data.error}`;
      }
    },

    // ============== 待处理操作确认/取消（与 WPS 行为对齐） ==============

    _toIntOrNull(value) {
      if (value === null || value === undefined || value === '') {
        return null;
      }
      const n = Number.parseInt(String(value), 10);
      return Number.isFinite(n) ? n : null;
    },

    _toParaIdOrNull(value) {
      if (value === null || value === undefined) {
        return null;
      }
      if (typeof value === 'string') {
        const trimmed = value.trim();
        return trimmed ? trimmed : null;
      }
      if (typeof value === 'number' && Number.isFinite(value)) {
        return String(value);
      }
      return null;
    },

    _normalizeParaIdList(values) {
      if (!Array.isArray(values)) {
        return [];
      }
      const normalized = values
        .map(v => this._toParaIdOrNull(v))
        .filter(v => v !== null);
      return [...new Set(normalized)];
    },

    async _resolveParaIDsToIndices(paraIDs = []) {
      const normalized = this._normalizeParaIdList(paraIDs);
      if (!normalized.length) {
        return [];
      }

      return await Word.run(async (context) => {
        const allParas = context.document.body.paragraphs;
        allParas.load('items');
        await context.sync();
        const allParaIDs = await resolveParagraphParaIDs(context, allParas.items);

        const idSet = new Set(normalized);
        const indices = [];
        for (let idx = 0; idx < allParas.items.length; idx++) {
          const paraID = allParaIDs[idx];
          if (paraID && idSet.has(paraID)) {
            indices.push(idx);
          }
        }
        return indices;
      });
    },

    async _resolveParaIDIndexMap(paraIDs = []) {
      const normalized = this._normalizeParaIdList(paraIDs);
      if (!normalized.length) {
        return new Map();
      }

      return await Word.run(async (context) => {
        const allParas = context.document.body.paragraphs;
        allParas.load('items');
        await context.sync();
        const allParaIDs = await resolveParagraphParaIDs(context, allParas.items);

        const wanted = new Set(normalized);
        const indexMap = new Map();
        for (let idx = 0; idx < allParas.items.length; idx++) {
          const paraID = allParaIDs[idx];
          if (paraID && wanted.has(paraID) && !indexMap.has(paraID)) {
            indexMap.set(paraID, idx);
          }
        }
        return indexMap;
      });
    },

    async _deleteByParaIDsOneByOne(paraIDs = []) {
      const normalized = this._normalizeParaIdList(paraIDs);
      if (!normalized.length) {
        return;
      }
      for (const paraID of normalized) {
        try {
          await deleteDocxPara([paraID]);
        } catch (e) {
          console.warn('[AIChatPane] 按 paraID 单段删除失败:', paraID, e);
        }
      }
    },

    _toIntOrDefault(value, defaultValue) {
      const n = this._toIntOrNull(value);
      return n === null ? defaultValue : n;
    },

    _refreshPendingDocumentSummary() {
      if (this.pendingInsertions.length === 0) {
        this.pendingDocument = null;
        this.pendingDocumentMsg = null;
        return;
      }

      const totalParaCount = this.pendingInsertions.reduce(
        (sum, item) => sum + ((item.documentJson?.paragraphs || []).length),
        0
      );
      const totalTableCount = this.pendingInsertions.reduce(
        (sum, item) => sum + ((item.documentJson?.tables || []).length),
        0
      );

      let summary = `${totalParaCount} 个段落`;
      if (totalTableCount > 0) {
        summary += `，${totalTableCount} 个表格`;
      }
      this.pendingDocument = { preview: `AI 已生成（${summary}，待确认）` };
      this.pendingDocumentMsg = this.pendingInsertions[this.pendingInsertions.length - 1]?.msg || null;
    },

    _applyImmediateDelete(payload) {
      const docId = this._toIntOrDefault(payload?.docId, 0);
      const paraIDs = this._normalizeParaIdList(payload?.paraIDs);
      if (!paraIDs.length) {
        return;
      }

      this.pendingDeletes.push({
        paraIDs,
        docId,
        preview: `AI 准备删除段落（paraID: ${paraIDs.join(', ')}）`,
        _commentAdded: false,
        _markingMode: 'highlight'
      });
      // Microsoft Office 统一使用高亮标记，不使用批注。
      this._addDeleteComments(docId);
    },

    async _applyImmediateInsertion(insItem) {
      const normalizedDocId = this._toIntOrDefault(insItem.docId, 0);
      const requestedInsertParaID = this._toParaIdOrNull(insItem.insertParaID);
      const docPayload = { ...(insItem.documentJson || {}) };
      const result = await generateDocxFromJSON(docPayload, "selection", requestedInsertParaID);
      if (!result || !result.success) {
        console.error('[AIChatPane] 即时插入失败:', result?.error || '(unknown)');
        return false;
      }
      if (result.warning && insItem.msg && Array.isArray(insItem.msg.contentParts)) {
        insItem.msg.contentParts.push({
          type: 'status',
          content: `⚠️ ${result.warning}`,
          loading: false
        });
      }

      const paraCount = (docPayload.paragraphs || []).length;
      const tableCount = (docPayload.tables || []).length;
      const shiftCount = paraCount + tableCount;

      if (shiftCount > 0) {
        this._streamInsertions.push({
          insertParaID: requestedInsertParaID,
          count: shiftCount,
          docId: normalizedDocId
        });
      }

      let insertStartParaIndex = null;
      let insertEndParaIndex = null;
      if (shiftCount > 0) {
        if (requestedInsertParaID === null) {
          const totalParas = await Word.run(async (context) => {
            const paras = context.document.body.paragraphs;
            paras.load('items');
            await context.sync();
            return paras.items.length;
          });
          insertEndParaIndex = totalParas - 1;
          insertStartParaIndex = Math.max(0, totalParas - shiftCount);
        } else {
          const indices = await this._resolveParaIDsToIndices([requestedInsertParaID]);
          if (indices.length > 0) {
            insertStartParaIndex = indices[0] + 1;
            insertEndParaIndex = insertStartParaIndex + shiftCount - 1;
          }
        }
      }

      const pendingItem = {
        ...insItem,
        docId: normalizedDocId,
        insertParaID: requestedInsertParaID,
        insertStartParaIndex,
        insertEndParaIndex,
        _alreadyInserted: true,
        _markingMode: 'highlight'
      };

      if (pendingItem.msg) {
        pendingItem.msg._docId = normalizedDocId;
        pendingItem.msg._insertParaID = requestedInsertParaID;
        pendingItem.msg.documentJson = docPayload;
        pendingItem.msg.insertStartParaIndex = insertStartParaIndex;
        pendingItem.msg.insertEndParaIndex = insertEndParaIndex;
      }

      this.pendingInsertions.push(pendingItem);
      this._refreshPendingDocumentSummary();
      await this._markInsertHighlight(pendingItem);

      console.log(
        '[AIChatPane] 文档已即时插入:',
        `docId=${normalizedDocId}`,
        `insertParaID=${requestedInsertParaID}`,
        `range=${insertStartParaIndex}-${insertEndParaIndex}`
      );
      return true;
    },

    async _markInsertHighlight(insItem) {
      if (
        insItem.insertStartParaIndex === null ||
        insItem.insertStartParaIndex === undefined ||
        insItem.insertEndParaIndex === null ||
        insItem.insertEndParaIndex === undefined
      ) {
        return;
      }
      try {
        // Microsoft Office 统一用高亮标记新增内容（浅红）
        await addCommentToParas(
          insItem.insertStartParaIndex,
          insItem.insertEndParaIndex,
          '[文策AI] 待添加内容',
          'redblue'
        );
        insItem._markingMode = 'highlight';
      } catch (e) {
        console.warn('[AIChatPane] 标记新增内容失败:', e);
      }
    },

    async _addDeleteComments(docId = null) {
      const normalizedDocId = this._toIntOrDefault(docId, 0);
      for (const pd of this.pendingDeletes) {
        if (pd._commentAdded) {
          continue;
        }
        const pdDocId = this._toIntOrDefault(pd.docId, 0);
        if (normalizedDocId !== pdDocId) {
          continue;
        }
        const paraIDs = this._normalizeParaIdList(pd.paraIDs || []);
        if (!paraIDs.length) {
          continue;
        }
        const indexMap = await this._resolveParaIDIndexMap(paraIDs);
        let markedCount = 0;

        for (const paraID of paraIDs) {
          const paraIndex = indexMap.get(paraID);
          if (!Number.isInteger(paraIndex)) {
            continue;
          }
          try {
            // 删除标记严格按 paraID 对应段落逐段高亮，避免区间误标记
            const res = await addCommentToParas(
              paraIndex,
              paraIndex,
              '[文策AI-删除] 待删除内容',
              'redblue'
            );
            if (res && res.success) {
              markedCount++;
            }
          } catch (e) {
            console.warn('[AIChatPane] 标记删除段落失败:', paraID, e);
          }
        }
        if (markedCount > 0) {
          pd._commentAdded = true;
          pd._markingMode = 'highlight';
        }
      }
    },

    /**
     * 一键确认所有待处理操作（删除 + 生成）
     */
    async confirmPending() {
      // 1) 删除正文：按 paraID 删除，不依赖索引偏移
      const deletes = [...this.pendingDeletes];
      for (const d of deletes) {
        await this._clearHighlightOnParaIDs(d.paraIDs || [], d.docId);
        await this._deleteByParaIDsOneByOne(d.paraIDs || []);
      }

      // 2) 确认新增：仅移除新增高亮，保留内容
      for (const ins of this.pendingInsertions) {
        if (
          ins.insertStartParaIndex !== null &&
          ins.insertStartParaIndex !== undefined &&
          ins.insertEndParaIndex !== null &&
          ins.insertEndParaIndex !== undefined
        ) {
          await this._clearHighlightOnRange(ins.insertStartParaIndex, ins.insertEndParaIndex);
        }
      }

      this.pendingDeletes = [];
      this.pendingInsertions = [];
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
      this._streamInsertions = [];
    },

    /**
     * 一键取消所有待处理操作（移除删除标记 + 回滚新增）
     */
    async cancelPending() {
      // 1) 取消删除：只清除删除高亮，不删除正文
      for (const pd of this.pendingDeletes) {
        await this._clearHighlightOnParaIDs(pd.paraIDs || [], pd.docId);
      }

      // 2) 取消新增：按倒序删除新增内容，避免位置串扰
      const inserts = [...this.pendingInsertions].sort(
        (a, b) => (b.insertStartParaIndex ?? -1) - (a.insertStartParaIndex ?? -1)
      );
      for (const ins of inserts) {
        if (
          ins.insertStartParaIndex === null ||
          ins.insertStartParaIndex === undefined ||
          ins.insertEndParaIndex === null ||
          ins.insertEndParaIndex === undefined
        ) {
          continue;
        }
        await this._clearHighlightOnRange(ins.insertStartParaIndex, ins.insertEndParaIndex);
        try {
          const paraIDs = [];
          for (let i = ins.insertStartParaIndex; i <= ins.insertEndParaIndex; i++) {
            paraIDs.push(i);
          }
          await deleteDocxPara(paraIDs);
        } catch (e) {
          console.warn('[AIChatPane] cancelPending 回滚新增失败:', e);
        }
      }

      this.pendingDeletes = [];
      this.pendingInsertions = [];
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
      this._streamInsertions = [];
    },

    /**
     * 清除指定段落范围的高亮（best-effort）
     */
    async _clearHighlightOnRange(startParaIndex, endParaIndex) {
      try {
        await Word.run(async (context) => {
          const allParas = context.document.body.paragraphs;
          allParas.load('items');
          await context.sync();
          const total = allParas.items.length;
          if (total <= 0) {
            return;
          }
          let start = Number.isFinite(Number(startParaIndex)) ? Number(startParaIndex) : 0;
          let end = endParaIndex === -1 ? total - 1 : Number(endParaIndex);
          start = Math.max(0, Math.min(start, total - 1));
          end = Number.isFinite(end) ? end : start;
          end = Math.max(start, Math.min(end, total - 1));
          if (start >= 0 && end < total) {
            const startRange = allParas.items[start].getRange('Start');
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

    async _clearHighlightOnParaIDs(paraIDs = [], docId = 0) {
      const normalized = this._normalizeParaIdList(paraIDs);
      if (!normalized.length) {
        return;
      }
      const indexMap = await this._resolveParaIDIndexMap(normalized);
      for (const paraID of normalized) {
        const paraIndex = indexMap.get(paraID);
        if (!Number.isInteger(paraIndex)) {
          continue;
        }
        await this._clearHighlightOnRange(paraIndex, paraIndex);
      }
      void docId;
    },

    /**
     * 还原到某条消息（Microsoft Office 统一走高亮/索引回滚）
     */
    async revertToMessage(messageIndex) {
      if (this.isLoading) return;
      const msg = this.messages[messageIndex];
      if (!msg) return;

      if (
        msg.insertStartParaIndex === null ||
        msg.insertStartParaIndex === undefined ||
        msg.insertEndParaIndex === null ||
        msg.insertEndParaIndex === undefined
      ) {
        msg.documentReverted = false;
        return;
      }

      try {
        await this._clearHighlightOnRange(msg.insertStartParaIndex, msg.insertEndParaIndex);
        const paraIDs = [];
        for (let i = msg.insertStartParaIndex; i <= msg.insertEndParaIndex; i++) {
          paraIDs.push(i);
        }
        const result = await deleteDocxPara(paraIDs);
        msg.documentReverted = !!result?.success;
      } catch (e) {
        console.warn('[AIChatPane] revertToMessage 回滚失败:', e);
        msg.documentReverted = false;
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
          const insertParaID = this._toParaIdOrNull(jsonData.insertParaID);
          const result = await generateDocxFromJSON(jsonData, 'selection', insertParaID);
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
                  if (insertParaID === null) {
                    endIdx = totalParas - 1;
                    startIdx = totalParas - newParaCount;
                  } else {
                    const indices = await this._resolveParaIDsToIndices([insertParaID]);
                    if (indices.length > 0) {
                      startIdx = indices[0] + 1;
                      endIdx = startIdx + newParaCount - 1;
                    }
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

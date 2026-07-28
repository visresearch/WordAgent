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
        :delete-revisions="deleteRevisions"
        :token-stats="tokenStats"
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
import {
  generateDocxFromJSON,
  deleteDocxPara,
  insertBreakAfterParagraph,
  resolveParagraphParaIDs
} from '../js/docxJsonConverter.js';
import {
  abortTrackedEdit,
  beginTrackedEdit,
  finishTrackedEdit,
  hasRevisionBatch,
  settleRevisionBatch,
  undoLastDocumentAction
} from '../js/revisionPreview.mjs';
import api from '../js/api.js';
import ChatMessages from './ChatMessages.vue';
import ChatInput from './ChatInput.vue';
import SessionPane from './SessionPane.vue';
import { sessionState } from '../../sessionState.js';
import { settingsState } from '../../settingsState.js';
import { chatState } from '../../chatState.js';
import { t } from '../../i18n/index.js';

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
      deleteRevisions: [],  // 已立即执行、等待统一接受/拒绝的原生删除修订
      pendingInsertions: [], // [{documentJson, docId, insertParaID, msg}] 待确认的文档插入列表
      _streamInsertions: [], // [{insertParaID, count, docId}] 当前流式中已执行的插入操作
      hasHistory: false,
      historyLoaded: false,
      historyLoading: false,
      _streamingSessionId: null,
      _streamingCache: {},
      isWide: false,
      tokenStats: { current: 0, max: 200000, percentage: 0 },
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

    _normalizeSelectionContext(selectionContext) {
      if (!selectionContext) {
        return null;
      }
      if (Array.isArray(selectionContext)) {
        return selectionContext.filter(Boolean);
      }
      if (typeof selectionContext === 'object') {
        return [selectionContext];
      }
      return null;
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
        preview: t('chat.callMcp', { name: safeToolName }),
        argsText: argsText || t('chat.noArguments'),
        outputText: t('chat.mcpWaiting'),
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
          part.outputText = outputText || t('chat.noOutput');
          part.completed = true;
          part.isError = !!isError;
          return;
        }
      }

      msg.contentParts.push({
        type: "mcp",
        toolName: safeToolName,
        preview: t('chat.callMcp', { name: safeToolName }),
        argsText: t('chat.unknownArguments'),
        outputText: outputText || t('chat.noOutput'),
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
      this._streamingSessionId = null;
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
                selectionContext: this._normalizeSelectionContext(msg.selectionContext),
                thinking: msg.thinking || '',
                thinkingExpanded: !!msg.thinking,
                thinkingDone: true,
                attachedFiles: msg.attachedFiles || null
              };
            });

            if (result.data.lastUsedModel) {
              this.selectedModel = result.data.lastUsedModel;
            }
            if (result.data.lastUsedProvider) {
              this.selectedModelProvider = result.data.lastUsedProvider;
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
              selectionContext: this._normalizeSelectionContext(msg.selectionContext),
              thinking: msg.thinking || '',
              thinkingExpanded: !!msg.thinking,
              thinkingDone: true,
              attachedFiles: msg.attachedFiles || null
            };
          });

          if (result.data.lastUsedModel) {
            this.selectedModel = result.data.lastUsedModel;
          }
          if (result.data.lastUsedProvider) {
            this.selectedModelProvider = result.data.lastUsedProvider;
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
        const result = await api.createSession({ title: t('session.newConversation') });
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
          if (!this.selectedModel) {
            this.selectedModel = result.data.models[0].id;
            this.selectedModelProvider = result.data.models[0].provider || '';
          } else if (!this.selectedModelProvider) {
            const matched = this.availableModels.find((m) => m.id === this.selectedModel);
            if (matched) {
              this.selectedModelProvider = matched.provider || '';
            }
          } else {
            const modelExists = this.availableModels.some(
              (m) => m.id === this.selectedModel && m.provider === this.selectedModelProvider
            );
            if (!modelExists) {
              const matched = this.availableModels.find((m) => m.id === this.selectedModel);
              if (matched) {
                this.selectedModelProvider = matched.provider || '';
              }
            }
          }
        } else {
          this.availableModels = [{ id: 'auto', name: 'Auto' }];
          this.selectedModel = 'auto';
          this.selectedModelProvider = '';
        }
      } catch (error) {
        console.error('加载模型列表失败:', error);
        this.availableModels = [{ id: 'auto', name: 'Auto' }];
        this.selectedModel = 'auto';
        this.selectedModelProvider = '';
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
          let startParaID = null;
          let endParaID = null;

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

            try {
              const allParaIDs = await resolveParagraphParaIDs(context, allParagraphs.items);
              startParaID = allParaIDs[startParaIndex] || null;
              endParaID = allParaIDs[endParaIndex] || startParaID;
            } catch (e) {
              console.warn('[Selection] 获取选区 paraID 失败:', e);
            }
          }

          const maxPreviewLen = 50;
          let displayText = cleanedText;
          if (!displayText) {
            if (hasInlineImage && hasTable) {
              displayText = t('chat.imageTableSelection');
            } else if (hasInlineImage) {
              displayText = t('chat.imageSelection');
            } else if (hasTable) {
              displayText = t('chat.tableSelection');
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
            startParaID,
            endParaID,
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
          startParaID: s.startParaID,
          endParaID: s.endParaID,
          charCount: s.charCount,
          docId: Number.isInteger(s.docId) ? s.docId : 0,
          docName: s.docName || ''
        }));
        documentRange = this.selections.map(s => ({
          startParaIndex: s.startParaIndex,
          endParaIndex: s.endParaIndex,
          startParaID: s.startParaID,
          endParaID: s.endParaID,
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
      if (!this.currentSessionTitle || ['新对话', 'New conversation'].includes(this.currentSessionTitle)) {
        this.currentSessionTitle = userMessage.length > 30 ? userMessage.substring(0, 30) + '...' : userMessage;
      }
      this.historyLoaded = true;
      this.selections = [];
      this.clearAllFiles();

      this._sendStreamRequest(userMessage, documentRange, uploadedFilesMeta, selectionContext);
    },

    _sendStreamRequest(userMessage, documentRange, files = [], selectionContext = null) {
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
        selectionContext: selectionContext,
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
            aiMsg.content = t('chat.networkTimeout');
          } else {
            aiMsg.content = t('chat.networkError', { error: errMsg });
          }
          this.isLoading = false;
          this._streamingSessionId = null;
          this.currentStreamCtrl = null;
          if (aiMsg.thinking) {
            aiMsg.thinkingDone = true;
          }
          delete this._streamingCache[streamSessionId];
          this.scrollToBottom();
        },

        onComplete: () => {
          this.isLoading = false;
          this._streamingSessionId = null;

          if (aiMsg.thinking) {
            aiMsg.thinkingDone = true;
          }

          this.scrollToBottom();
          window.dispatchEvent(new CustomEvent('session-created'));

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

      if (data.type === 'token_stats') {
        this.tokenStats = {
          current: data.current_tokens || 0,
          max: data.max_tokens || 200000,
          percentage: data.percentage || 0
        };
        return;
      }

      // 后端请求读取文档
      if (data.type === 'read_document') {
        const hasParaIDMode =
          this._toParaIdOrNull(data.startParaID) !== null || this._toParaIdOrNull(data.endParaID) !== null;
        msg.contentParts.push({
          type: 'status',
          content: data.content || (
            hasParaIDMode
              ? t('chat.readingDocumentById', { start: data.startParaID ?? '', end: data.endParaID ?? data.startParaID ?? '' })
              : t('chat.readingDocument', { start: data.startParaIndex, end: data.endParaIndex })
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
          content: data.content || t('chat.searchingDocument'),
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
              content: data.content || t('chat.searchComplete'),
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          parts.push({ type: 'status', content: data.content || t('chat.searchComplete'), loading: false });
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
              content: data.content || t('chat.documentReadComplete'),
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          parts.push({ type: 'status', content: data.content || t('chat.documentReadComplete'), loading: false });
        }
        this.scrollToBottom();
        return;
      }

      // 后端请求删除文档段落：立即在原生修订模式下执行，并回传真实结果。
      if (data.type === 'delete_document') {
        const paraIDs = this._normalizeParaIdList(data.paraIDs);
        console.log('[AIChatPane] 后端请求删除文档段落, paraIDs:', paraIDs, 'docId:', data.docId);
        msg.contentParts.push({
          type: 'status',
          content: data.content || t('chat.prepareDelete', { ids: paraIDs.join(', ') }),
          loading: true
        });
        this.scrollToBottom();
        this._insertQueue = this._insertQueue
          .then(() => this._applyImmediateDelete({
            paraIDs,
            docId: this._toIntOrDefault(data.docId, 0),
            requestId: data.requestId || null
          }))
          .catch((e) => {
            console.warn("[AIChatPane] apply immediate delete failed:", e);
            if (data.requestId) {
              api.wsManager.send({
                type: 'delete_response',
                requestId: data.requestId,
                success: false,
                deletedCount: 0,
                error: e?.message || String(e)
              }).catch((sendError) => console.warn('[AIChatPane] 回传删除异常失败:', sendError));
            }
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
              content: data.content || t('chat.deleteComplete'),
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          parts.push({ type: 'status', content: data.content || t('chat.deleteComplete'), loading: false });
        }
        this.scrollToBottom();
        return;
      }

      if (data.type === 'insert_break') {
        const requestId = data.requestId || null;
        const paraID = this._toParaIdOrNull(data.paraID);
        const breakType = data.breakType;
        this._insertQueue = this._insertQueue
          .then(async () => {
            const result = await insertBreakAfterParagraph(paraID, breakType);
            if (requestId) {
              await api.wsManager.send({
                type: 'insert_break_response',
                requestId,
                success: Boolean(result?.success),
                breakType,
                paragraphAfterBreak: result?.paragraphAfterBreak || null,
                error: result?.success ? undefined : (result?.error || '插入断行失败')
              });
            }
            msg.contentParts.push({
              type: 'status',
              content: result?.success
                ? (data.content || t('chat.insertBreakSuccess'))
                : t('chat.insertBreakFailed', { error: result?.error || t('common.unknownError') }),
              loading: false
            });
            this.scrollToBottom();
            return result;
          })
          .catch(async (error) => {
            if (requestId) {
              try {
                await api.wsManager.send({
                  type: 'insert_break_response',
                  requestId,
                  success: false,
                  breakType,
                  error: error?.message || String(error)
                });
              } catch (sendError) {
                console.warn('[AIChatPane] 回传 Word 插入断行错误失败:', sendError);
              }
            }
          });
        return;
      }

      // 后端请求创建并打开新的空白 DOCX 文档
      if (data.type === 'create_document') {
        const pendingPart = {
          type: 'status',
          content: t('chat.createDocumentPending'),
          loading: true
        };
        msg.contentParts.push(pendingPart);
        api.createDocument()
          .then((result) => {
            if (!result?.success) {
              throw new Error(result?.error || 'Word 未返回新文档对象');
            }
            pendingPart.content = t('chat.createDocumentSuccess');
            pendingPart.loading = false;
            msg._docId = this._toIntOrDefault(result.documentId, 0);
            api.wsManager.send({
              type: 'create_document_response',
              success: true,
              documentId: msg._docId
            }).catch((sendError) => console.warn('[AIChatPane] 回传新文档创建结果失败:', sendError));
          })
          .catch((error) => {
            pendingPart.content = t('chat.createDocumentFailed', { error: error?.message || error });
            pendingPart.loading = false;
            console.error('[AIChatPane] 创建 Word 空白 DOCX 失败:', error);
            api.wsManager.send({
              type: 'create_document_response',
              success: false,
              error: error?.message || String(error)
            }).catch((sendError) => console.warn('[AIChatPane] 回传新文档创建错误失败:', sendError));
          })
          .finally(() => this.scrollToBottom());
        this.scrollToBottom();
        return;
      }

      // 生成文档中
      if (data.type === 'generate_document') {
        msg.contentParts.push({
          type: 'status',
          content: data.content || t('chat.generatingDocument'),
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
              content: data.content || t('chat.documentGenerated'),
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          parts.push({ type: 'status', content: data.content || t('chat.documentGenerated'), loading: false });
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
          msg: msg,
          requestId: data.requestId || null
        };
        this._insertQueue = this._insertQueue
          .then(() => this._applyImmediateInsertion(insItem))
          .then((inserted) => {
            if (!inserted) {
              msg.contentParts.push({
                type: 'status',
                content: t('chat.documentInsertFailed'),
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
        msg.content += `\n\n${t('chat.errorLabel', { error: data.error })}`;
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
      const normalize = (raw) => {
        const trimmed = String(raw).trim();
        return /^[+-]?(0|[1-9]\d*)$/.test(trimmed) ? String(Number(trimmed)) : null;
      };
      if (typeof value === 'string') {
        return normalize(value);
      }
      if (typeof value === 'number' && Number.isFinite(value)) {
        return normalize(value);
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
      try {
        await deleteDocxPara(normalized);
      } catch (e) {
        console.warn("[AIChatPane] delete by paraIDs failed:", normalized, e);
      }
    },

    _shiftParaIndexIDsForInsertions(paraIDs = [], docId = 0) {
      const normalizedDocId = this._toIntOrDefault(docId, 0);
      const insertionRanges = this.pendingInsertions
        .filter((ins) => this._toIntOrDefault(ins.docId, 0) === normalizedDocId)
        .map((ins) => {
          const start = Number(ins.insertStartParaIndex);
          const end = Number(ins.insertEndParaIndex);
          if (Number.isInteger(start) && Number.isInteger(end) && end >= start) {
            return { start, count: end - start + 1 };
          }
          const insertedCount = this._normalizeParaIdList(ins.insertedParaIDs || []).length;
          return Number.isInteger(start) && insertedCount > 0
            ? { start, count: insertedCount }
            : null;
        })
        .filter(Boolean)
        .sort((a, b) => a.start - b.start);

      return [...new Set(
        this._normalizeParaIdList(paraIDs)
          .map((paraID) => Number(paraID))
          .filter((idx) => Number.isInteger(idx) && idx >= 0)
          .map((originalIndex) => {
            let shiftedIndex = originalIndex;
            for (const range of insertionRanges) {
              if (range.start <= shiftedIndex) {
                shiftedIndex += range.count;
              }
            }
            return String(shiftedIndex);
          })
      )];
    },

    _toIntOrDefault(value, defaultValue) {
      const n = this._toIntOrNull(value);
      return n === null ? defaultValue : n;
    },

    _buildGeneratedDocumentPreview(paragraphCount, tableCount) {
      const summaryParts = [];
      if (paragraphCount > 0) {
        summaryParts.push(t('chat.paragraphCount', { count: paragraphCount }));
      }
      if (tableCount > 0) {
        summaryParts.push(t('chat.tableCount', { count: tableCount }));
      }
      return summaryParts.length > 0
        ? t('chat.generatedPending', { summary: summaryParts.join(t('chat.summarySeparator')) })
        : t('chat.documentGenerated');
    },

    _countDocumentContent(documentJson) {
      const blocks = Array.isArray(documentJson?.paragraphs) ? documentJson.paragraphs : [];
      return blocks.reduce(
        (counts, block) => {
          if (Array.isArray(block?.tables)) {
            counts.tableCount += block.tables.length;
          } else {
            counts.paragraphCount += 1;
          }
          return counts;
        },
        { paragraphCount: 0, tableCount: 0 }
      );
    },

    _refreshPendingDocumentSummary() {
      if (this.pendingInsertions.length === 0) {
        this.pendingDocument = null;
        this.pendingDocumentMsg = null;
        return;
      }

      const totalParaCount = this.pendingInsertions.reduce(
        (sum, item) => sum + this._countDocumentContent(item.documentJson).paragraphCount,
        0
      );
      const totalTableCount = this.pendingInsertions.reduce(
        (sum, item) => sum + this._countDocumentContent(item.documentJson).tableCount,
        0
      );

      this.pendingDocument = {
        preview: this._buildGeneratedDocumentPreview(totalParaCount, totalTableCount)
      };
      this.pendingDocumentMsg = this.pendingInsertions[this.pendingInsertions.length - 1]?.msg || null;
    },

    async _applyImmediateDelete(payload) {
      const sendResult = async (result) => {
        if (!payload?.requestId) {
          return;
        }
        try {
          await api.wsManager.send({
            type: 'delete_response',
            requestId: payload.requestId,
            ...result
          });
        } catch (error) {
          console.warn('[AIChatPane] 回传 Word 删除结果失败:', error);
        }
      };
      const docId = this._toIntOrDefault(payload?.docId, 0);
      const paraIDs = this._normalizeParaIdList(payload?.paraIDs);
      if (!paraIDs.length) {
        await sendResult({ success: false, deletedCount: 0, error: 'delete_document 缺少有效 paraIDs' });
        return false;
      }

      let trackedEdit = null;
      let deleteResult = null;
      try {
        trackedEdit = await beginTrackedEdit();
        deleteResult = await deleteDocxPara(paraIDs);
        if (!deleteResult?.success) {
          await abortTrackedEdit(trackedEdit);
          const error = deleteResult?.message || '删除段落失败';
          await sendResult({
            success: false,
            deletedCount: Number(deleteResult?.deletedCount) || 0,
            missingParaIDs: deleteResult?.missingParaIDs || paraIDs,
            replacementInsertParaID: deleteResult?.replacementInsertParaID ?? null,
            error
          });
          return false;
        }

        const revisionBatch = await finishTrackedEdit(trackedEdit, 'delete');
        if (!revisionBatch.batchId) {
          await undoLastDocumentAction();
          const error = 'Microsoft Word 未创建原生删除修订，已撤销本次删除';
          await sendResult({
            success: false,
            deletedCount: 0,
            missingParaIDs: [],
            replacementInsertParaID: deleteResult?.replacementInsertParaID ?? null,
            error
          });
          return false;
        }

        this.deleteRevisions.push({
          paraIDs: deleteResult.deletedParaIDs || paraIDs,
          docId,
          replacementInsertParaID: deleteResult.replacementInsertParaID ?? '0',
          preview: t('chat.deletePreview', { ids: paraIDs.join(', ') }),
          _revisionCreated: true,
          _revisionBatchId: revisionBatch.batchId,
          _markingMode: 'revision'
        });
        api.wsManager.clearDocumentCache();

        const missingParaIDs = deleteResult.missingParaIDs || [];
        const fullyDeleted = missingParaIDs.length === 0;
        await sendResult({
          success: fullyDeleted,
          deletedCount: Number(deleteResult.deletedCount) || 0,
          missingParaIDs,
          replacementInsertParaID: deleteResult.replacementInsertParaID ?? '0',
          revisionCount: revisionBatch.revisionCount,
          ...(fullyDeleted ? {} : { error: '部分 paraID 未找到；请重新读取文档后仅处理仍存在的段落' })
        });
        return fullyDeleted;
      } catch (error) {
        await abortTrackedEdit(trackedEdit);
        if (deleteResult?.success) {
          try {
            await undoLastDocumentAction();
          } catch (undoError) {
            console.error('[AIChatPane] Word 删除异常后撤销失败:', undoError);
          }
        }
        const message = error?.message || String(error);
        console.warn('[AIChatPane] 创建 Microsoft Word 原生删除修订失败:', message);
        await sendResult({ success: false, deletedCount: 0, missingParaIDs: [], error: message });
        return false;
      }
    },

    async _applyImmediateInsertion(insItem) {
      const sendResult = async (payload) => {
        if (!insItem?.requestId) {
          return;
        }
        try {
          await api.wsManager.send({
            type: 'generate_document_response',
            requestId: insItem.requestId,
            ...payload
          });
        } catch (error) {
          console.warn('[AIChatPane] 回传 Word 文档生成结果失败:', error);
        }
      };
      const normalizedDocId = this._toIntOrDefault(insItem.docId, 0);
      const requestedInsertParaID = this._toParaIdOrNull(insItem.insertParaID);
      if (requestedInsertParaID === null) {
        console.error('[AIChatPane] generate_document 缺少必填 insertParaID:', insItem);
        await sendResult({ success: false, error: 'generate_document 缺少必填 insertParaID' });
        return false;
      }
      const conflictingDelete = this.deleteRevisions.find(
        (item) => this._toIntOrDefault(item.docId, 0) === normalizedDocId
          && Array.isArray(item.paraIDs)
          && item.paraIDs.some((paraID) => this._toParaIdOrNull(paraID) === requestedInsertParaID)
      );
      if (conflictingDelete) {
        const safeAnchor = this._toParaIdOrNull(conflictingDelete.replacementInsertParaID) || '0';
        const error = `insertParaID ${requestedInsertParaID} 正处于待接受的删除修订中；请改用 delete_document 返回的 replacementInsertParaID=${safeAnchor}`;
        console.warn('[AIChatPane] 拒绝在 Word 待删除段落内插入:', error);
        await sendResult({ success: false, error, replacementInsertParaID: safeAnchor });
        return false;
      }
      const docPayload = { ...(insItem.documentJson || {}) };
      let trackedEdit = null;
      let result = null;
      try {
        trackedEdit = await beginTrackedEdit();
        result = await generateDocxFromJSON(docPayload, "selection", requestedInsertParaID);
        if (!result || !result.success) {
          await abortTrackedEdit(trackedEdit);
          console.error('[AIChatPane] 即时插入失败:', result?.error || '(unknown)');
          await sendResult({ success: false, error: result?.error || '文档插入失败' });
          return false;
        }
      } catch (error) {
        await abortTrackedEdit(trackedEdit);
        console.error('[AIChatPane] 创建 Microsoft Word 原生新增修订失败:', error);
        await sendResult({ success: false, error: error?.message || String(error) });
        return false;
      }
      if (result.warning && insItem.msg && Array.isArray(insItem.msg.contentParts)) {
        insItem.msg.contentParts.push({
          type: 'status',
          content: `⚠️ ${result.warning}`,
          loading: false
        });
      }

      const { paragraphCount: paraCount, tableCount } = this._countDocumentContent(docPayload);
      const shiftCount = paraCount + tableCount;
      const insertedParaIDs = this._normalizeParaIdList(result.insertedParaIDs || []);

      let insertStartParaIndex = null;
      let insertEndParaIndex = null;
      if (shiftCount > 0) {
        if (requestedInsertParaID === '0') {
          insertStartParaIndex = 0;
          insertEndParaIndex = shiftCount - 1;
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
        insertedParaIDs,
        _alreadyInserted: true,
        _markingMode: null
      };

      try {
        const revisionBatch = await finishTrackedEdit(trackedEdit, 'insert');
        pendingItem._revisionBatchId = revisionBatch.batchId;
        pendingItem._markingMode = revisionBatch.batchId ? 'revision' : 'revision-unavailable';
        if (!revisionBatch.batchId) {
          console.warn('[AIChatPane] Word 未返回本次插入产生的原生修订，正在撤销插入');
          await undoLastDocumentAction();
          await sendResult({ success: false, error: 'Word 未返回本次插入产生的原生修订' });
          return false;
        }
      } catch (error) {
        await abortTrackedEdit(trackedEdit);
        console.error('[AIChatPane] 读取本次新增修订失败，正在撤销插入:', error);
        try {
          await undoLastDocumentAction();
        } catch (undoError) {
          console.error('[AIChatPane] 撤销无修订插入失败:', undoError);
        }
        await sendResult({ success: false, error: error?.message || String(error) });
        return false;
      }

      if (shiftCount > 0) {
        this._streamInsertions.push({
          insertParaID: requestedInsertParaID,
          count: shiftCount,
          docId: normalizedDocId
        });
      }

      if (pendingItem.msg) {
        pendingItem.msg._docId = normalizedDocId;
        pendingItem.msg._insertParaID = requestedInsertParaID;
        pendingItem.msg.documentJson = docPayload;
        pendingItem.msg.insertStartParaIndex = insertStartParaIndex;
        pendingItem.msg.insertEndParaIndex = insertEndParaIndex;
        pendingItem.msg.insertedParaIDs = insertedParaIDs;
        pendingItem.msg._revisionBatchId = pendingItem._revisionBatchId;
      }

      this.pendingInsertions.push(pendingItem);
      this._refreshPendingDocumentSummary();

      let lastParagraph = null;
      const lastParaID = insertedParaIDs.length > 0
        ? insertedParaIDs[insertedParaIDs.length - 1]
        : null;
      if (lastParaID !== null) {
        const lastIndices = await this._resolveParaIDsToIndices([lastParaID]);
        if (lastIndices.length > 0) {
          lastParagraph = {
            paraID: Number(lastParaID),
            paraIndex: lastIndices[0],
            pageStart: null,
            pageEnd: null
          };
        }
      }

      console.log(
        '[AIChatPane] 文档已即时插入:',
        `docId=${normalizedDocId}`,
        `insertParaID=${requestedInsertParaID}`,
        `range=${insertStartParaIndex}-${insertEndParaIndex}`
      );
      await sendResult({
        success: true,
        docId: normalizedDocId,
        lastParagraph
      });
      return true;
    },

    /**
     * 接受本轮已经执行的原生增删修订。
     */
    async confirmPending() {
      try {
        await this._insertQueue;
      } catch (e) {
        console.warn("[AIChatPane] pending operation queue failed before confirm:", e);
      }
      for (const ins of this.pendingInsertions) {
        if (ins._markingMode === 'revision' && hasRevisionBatch(ins._revisionBatchId)) {
          const settled = await settleRevisionBatch(ins._revisionBatchId, 'accept');
          console.log('[AIChatPane] 已接受新增内容修订:', settled);
          if (settled.success) {
            ins._revisionBatchId = null;
            if (ins.msg) {
              ins.msg._revisionBatchId = null;
            }
          }
        }
      }

      for (const pd of this.deleteRevisions) {
        if (pd._markingMode === 'revision' && hasRevisionBatch(pd._revisionBatchId)) {
          const settled = await settleRevisionBatch(pd._revisionBatchId, 'accept');
          console.log('[AIChatPane] 已接受删除内容修订:', settled);
          if (settled.success) {
            pd._revisionBatchId = null;
          }
        }
      }

      this.deleteRevisions = [];
      this.pendingInsertions = [];
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
      this._streamInsertions = [];
    },

    /**
     * 拒绝本轮已经执行的原生增删修订。
     */
    async cancelPending() {
      try {
        await this._insertQueue;
      } catch (e) {
        console.warn("[AIChatPane] pending operation queue failed before cancel:", e);
      }

      for (const pd of this.deleteRevisions) {
        if (pd._markingMode === 'revision' && hasRevisionBatch(pd._revisionBatchId)) {
          const settled = await settleRevisionBatch(pd._revisionBatchId, 'reject');
          console.log('[AIChatPane] 已拒绝删除内容修订:', settled);
          if (settled.success) {
            pd._revisionBatchId = null;
          }
        }
      }

      const inserts = [...this.pendingInsertions].reverse();
      for (const ins of inserts) {
        if (ins._markingMode === 'revision' && hasRevisionBatch(ins._revisionBatchId)) {
          const settled = await settleRevisionBatch(ins._revisionBatchId, 'reject');
          console.log('[AIChatPane] 已拒绝新增内容修订:', settled);
          if (settled.success) {
            ins._revisionBatchId = null;
            if (ins.msg) {
              ins.msg._revisionBatchId = null;
            }
          }
        }
      }

      this.deleteRevisions = [];
      this.pendingInsertions = [];
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
      this._streamInsertions = [];
    },

    /**
     * 还原到某条消息（优先按隐藏书签 paraID 回滚）
     */
    async revertToMessage(messageIndex) {
      if (this.isLoading) return;
      const msg = this.messages[messageIndex];
      if (!msg) return;

      if (hasRevisionBatch(msg._revisionBatchId)) {
        const settled = await settleRevisionBatch(msg._revisionBatchId, 'reject');
        msg.documentReverted = settled.success;
        if (settled.success) {
          msg._revisionBatchId = null;
        }
        return;
      }

      const insertedParaIDs = this._normalizeParaIdList(msg.insertedParaIDs || []);
      if (insertedParaIDs.length > 0) {
        try {
          const result = await deleteDocxPara(insertedParaIDs);
          msg.documentReverted = !!result?.success;
        } catch (e) {
          console.warn('[AIChatPane] revertToMessage 按 paraID 回滚失败:', e);
          msg.documentReverted = false;
        }
        return;
      }

      if (
        msg.insertStartParaIndex === null ||
        msg.insertStartParaIndex === undefined ||
        msg.insertEndParaIndex === null ||
        msg.insertEndParaIndex === undefined
      ) {
        msg.documentReverted = false;
        return;
      }

      msg.documentReverted = false;
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
          if (insertParaID === null) {
            console.error('生成文档失败: 缺少必填 insertParaID');
            await this._insertPlainText(content);
            return;
          }
          const result = await generateDocxFromJSON(jsonData, 'selection', insertParaID);
          msg.insertedParaIDs = this._normalizeParaIdList(result?.insertedParaIDs || []);
          if (result?.error) {
            console.error('生成文档失败:', result.error);
            await this._insertPlainText(content);
          } else {
            // 计算插入范围并记录到 msg（用于撤销）
            const newParaCount = this._countDocumentContent(jsonData).paragraphCount;
            if (newParaCount > 0) {
              try {
                await Word.run(async (context) => {
                  const paras = context.document.body.paragraphs;
                  paras.load('items');
                  await context.sync();

                  const totalParas = paras.items.length;
                  let startIdx, endIdx;
                  if (insertParaID === '0') {
                    startIdx = 0;
                    endIdx = newParaCount - 1;
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

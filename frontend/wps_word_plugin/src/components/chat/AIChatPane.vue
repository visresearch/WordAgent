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
        :pending-edits="pendingEdits"
        :delete-revisions="deleteRevisions"
        :token-stats="tokenStats"
        :enable-thinking="enableThinking"
        @update:mode="mode = $event"
        @update:selected-model="selectedModel = $event"
        @update:selected-model-provider="selectedModelProvider = $event"
        @update:enable-thinking="enableThinking = $event"
        @send="handleSend"
        @stop="stopGeneration"
        @add-selection="addSelectionManually"
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
import { generateDocxFromJSON, editDocxParagraph, deleteDocxPara, insertBreakAfterParagraph, getParagraphParaID } from '../js/docxJsonConverter.js';
import {
  abortTrackedEdit,
  beginTrackedEdit,
  finishTrackedEdit,
  hasRevisionBatch,
  settleRevisionBatch,
  settleAllDocumentRevisions
} from '../js/revisionPreview.js';
import api, { getDocumentById } from '../js/api.js';
import ChatMessages from './ChatMessages.vue';
import ChatInput from './ChatInput.vue';
import SessionPane from './SessionPane.vue';
import { sessionState } from '../../sessionState.js';
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
      selections: [],  // 多选区数组 [{preview, startText, endText, startParaIndex, endParaIndex, charCount, hasMore}]
      uploadedFiles: [], // 已添加文件列表（File 对象）
      currentStreamCtrl: null,
      currentSessionId: null,
      currentSessionTitle: null,
      pendingDocument: null,
      pendingDocumentMsg: null,
      deleteRevisions: [],  // 已立即执行、等待统一接受/拒绝的原生删除修订
      pendingEdits: [],  // 已立即执行、等待统一接受/拒绝的原生段落编辑修订
      pendingInsertions: [],  // [{documentJson, docId, insertParaID, msg}] 待确认的文档插入列表
      _streamInsertions: [], // [{insertParaID, count, docId}] 当前流式中已执行的插入操作
      historyLoading: false,
      hasHistory: false,
      historyLoaded: false,
      _streamingSessionId: null,   // 正在流式生成的 session ID
      _streamingCache: {},         // {sessionId: messages[]} 流式生成期间切走时缓存消息
      isWide: false,
      tokenStats: { current: 0, max: 258000, percentage: 0 },
      enableThinking: true,  // 是否启用深度思考
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
    }
  },
  mounted() {
    this.loadModels();
    this.initSessionAndLoadHistory();
    this._loadWenceTempDir();

    // 监听窗口宽度变化（600px 阈值）
    this._onResize = () => {
      this.isWide = window.innerWidth >= 600;
    };
    this._onResize();
    window.addEventListener('resize', this._onResize);
    sessionState.visible = this.sessionVisible;

    // 监听 Ribbon 按钮通过 localStorage 发送的 session 切换信号
    // storage 事件可能不在同一窗口触发，用轮询兜底
    this._lastToggleVal = '';
    try {
      this._lastToggleVal = localStorage.getItem('wence_session_toggle') || ''; 
    } catch (e) {}
    this._togglePoll = setInterval(() => {
      try {
        const val = localStorage.getItem('wence_session_toggle') || '';
        if (val !== this._lastToggleVal) {
          this._lastToggleVal = val;
          sessionState.manualValue = !sessionState.visible;
        }
      } catch (e) {}
    }, 200);
  },
  beforeUnmount() {
    if (this._onResize) {
      window.removeEventListener('resize', this._onResize);
    }
    if (this._togglePoll) {
      clearInterval(this._togglePoll);
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
      const normalizeToolOutput = (output) => {
        if (!output || typeof output !== 'object') {
          return null;
        }
        if (output.paragraphs || output.tables || output.images) {
          return output;
        }
        if (
          output.document &&
          typeof output.document === 'object' &&
          (output.document.paragraphs || output.document.tables || output.document.images)
        ) {
          return output.document;
        }
        return null;
      };

      const calls = Array.isArray(toolJson?.calls) ? toolJson.calls : [];
      for (let i = calls.length - 1; i >= 0; i--) {
        const call = calls[i];
        if (call?.tool !== 'generate_document') {
          continue;
        }
        const output = call.output;
        const normalizedOutput = normalizeToolOutput(output);
        if (normalizedOutput) {
          return normalizedOutput;
        }
        if (typeof output === 'string') {
          try {
            const parsed = JSON.parse(output);
            const normalizedParsed = normalizeToolOutput(parsed);
            if (normalizedParsed) {
              return normalizedParsed;
            }
          } catch (e) {}
        }
      }
      return null;
    },

    _toIntOrNull(value) {
      if (typeof value === 'number' && Number.isInteger(value)) {
        return value;
      }
      if (typeof value === 'string') {
        const text = value.trim();
        if (/^[+-]?\d+$/.test(text)) {
          const parsed = Number.parseInt(text, 10);
          return Number.isNaN(parsed) ? null : parsed;
        }
      }
      return null;
    },

    _toIntOrDefault(value, fallback = 0) {
      const parsed = this._toIntOrNull(value);
      return Number.isInteger(parsed) ? parsed : fallback;
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

    _syncPendingDocumentPreview() {
      if (this.pendingInsertions.length === 0) {
        this.pendingDocument = null;
        this.pendingDocumentMsg = null;
        return;
      }
      const paragraphCount = this.pendingInsertions.reduce(
        (sum, item) => sum + this._countDocumentContent(item.documentJson).paragraphCount,
        0
      );
      const tableCount = this.pendingInsertions.reduce(
        (sum, item) => sum + this._countDocumentContent(item.documentJson).tableCount,
        0
      );
      this.pendingDocument = {
        preview: this._buildGeneratedDocumentPreview(paragraphCount, tableCount)
      };
      this.pendingDocumentMsg = this.pendingInsertions[this.pendingInsertions.length - 1]?.msg || null;
    },

    _formatMcpText(value) {
      if (value === null || value === undefined) {
        return '';
      }

      let raw = '';
      if (typeof value === 'string') {
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

      const safeToolName = toolName || 'unknown_tool';
      const argsText = this._formatMcpText(argsPayload);

      const lastPart = msg.contentParts.length > 0 ? msg.contentParts[msg.contentParts.length - 1] : null;
      if (
        lastPart &&
        lastPart.type === 'mcp' &&
        lastPart.toolName === safeToolName &&
        !lastPart.completed
      ) {
        if (!lastPart.argsText && argsText) {
          lastPart.argsText = argsText;
        }
        return;
      }

      msg.contentParts.push({
        type: 'mcp',
        toolName: safeToolName,
        preview: t('chat.callMcp', { name: safeToolName }),
        argsText: argsText || t('chat.noArguments'),
        outputText: t('chat.mcpWaiting'),
        completed: false,
        isError: false
      });
    },

    _attachMcpResultPart(msg, toolName, outputPreview, isError = false) {
      if (!msg.contentParts) {
        msg.contentParts = [];
      }

      const safeToolName = toolName || 'unknown_tool';
      const outputText = this._formatMcpText(outputPreview);

      for (let i = msg.contentParts.length - 1; i >= 0; i--) {
        const part = msg.contentParts[i];
        if (part.type === 'mcp' && part.toolName === safeToolName && !part.completed) {
          part.outputText = outputText || t('chat.noOutput');
          part.completed = true;
          part.isError = !!isError;
          return;
        }
      }

      msg.contentParts.push({
        type: 'mcp',
        toolName: safeToolName,
        preview: t('chat.callMcp', { name: safeToolName }),
        argsText: t('chat.unknownArguments'),
        outputText: outputText || t('chat.noOutput'),
        completed: true,
        isError: !!isError
      });
    },

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
          alert(t('chat.wpsUnavailable'));
          return;
        }

        const doc = window.Application.ActiveDocument;
        if (!doc) {
          alert(t('chat.openDocumentFirst'));
          return;
        }

        const msg = this.messages[messageIndex];
        if (!msg) {
          alert(t('chat.messageMissing'));
          return;
        }

        const pendingRevisionInsertions = this.pendingInsertions
          .filter((item) => item.msg === msg && hasRevisionBatch(item._revisionBatchId))
          .sort((a, b) => (b.insertStartPos ?? -1) - (a.insertStartPos ?? -1));
        if (pendingRevisionInsertions.length > 0) {
          for (const item of pendingRevisionInsertions) {
            settleRevisionBatch(item._revisionBatchId, 'reject');
            item._revisionBatchId = null;
          }
          this.pendingInsertions = this.pendingInsertions.filter((item) => item.msg !== msg);
          msg._revisionBatchId = null;
          msg.documentReverted = true;
          if (this.pendingInsertions.length === 0) {
            this.pendingDocument = null;
            this.pendingDocumentMsg = null;
          }
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
          alert(t('chat.undoFailed', { error: e.message }));
        }
      } catch (error) {
        console.error('撤销失败:', error);
        alert(t('chat.undoFailed', { error: error.message }));
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
     * 优先使用 PluginStorage 中保存的 session_id，否则查找全局最新会话
     */
    async initSessionAndLoadHistory() {
      // 防止初始化过程中 ensureSession 创建新会话
      this._initializing = true;
      try {
        console.log('[初始化] 开始获取会话');

        // 尝试从 PluginStorage 恢复上次的 session_id
        let savedSessionId = null;
        if (window.Application && window.Application.PluginStorage) {
          savedSessionId = window.Application.PluginStorage.getItem('current_session_id');
        }

        if (savedSessionId) {
          // 有保存的 session_id，直接加载该会话
          console.log('[初始化] 恢复上次会话:', savedSessionId);
          this.currentSessionId = Number(savedSessionId) || savedSessionId;
          await this.loadSessionMessages();
        } else {
          // 没有保存的 session_id，查找全局最新会话
          console.log('[初始化] 查找全局最新会话');
          const result = await api.getLatestSession();
          if (result.success && result.data?.session) {
            this.currentSessionId = result.data.session.id;
            this.currentSessionTitle = result.data.session.title || null;
            console.log('[初始化] 找到最新会话:', this.currentSessionId);

            // 保存到 PluginStorage
            if (window.Application && window.Application.PluginStorage) {
              window.Application.PluginStorage.setItem('current_session_id', String(this.currentSessionId));
            }

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
            console.log('[初始化] 当前没有历史会话');
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

    /**
     * SessionPane 选择会话事件
     */
    async onSelectSession(session) {
      const sessionId = session.id;
      const title = session.title;
      console.log('[会话切换] sessionId:', sessionId, 'title:', title);

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
        if (window.Application && window.Application.PluginStorage) {
          window.Application.PluginStorage.setItem('current_session_id', String(sessionId));
        }
        this.$nextTick(() => this.scrollToBottom());
        return;
      }

      this.messages = [];
      this.hasHistory = false;
      this.historyLoaded = false;
      this.currentSessionId = sessionId;
      this.currentSessionTitle = title || null;

      if (window.Application && window.Application.PluginStorage) {
        window.Application.PluginStorage.setItem('current_session_id', String(sessionId));
      }

      await this.loadSessionMessages(sessionId);
    },

    /**
     * SessionPane 创建会话事件
     */
    onCreateSession(session) {
      this.currentSessionId = session.id;
      this.currentSessionTitle = session.title;
      this.messages = [];
      this.historyLoaded = false;
      this.hasHistory = false;
      if (window.Application && window.Application.PluginStorage) {
        window.Application.PluginStorage.setItem('current_session_id', String(session.id));
      }
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
     * 加载当前会话的聊天历史
     */
    async loadSessionMessages(sessionId) {
      const targetSessionId = sessionId || this.currentSessionId;
      if (!targetSessionId) {
        console.warn('[加载历史] 缺少 sessionId');
        return;
      }

      console.log('[加载历史] 开始加载, sessionId:', targetSessionId);

      this.historyLoading = true;
      try {
        const result = await api.getSession(targetSessionId);
        console.log('[加载历史] API 返回:', result);

        // 检查当前会话是否已切换，避免竞态条件
        if (this.currentSessionId !== targetSessionId) {
          console.log('[加载历史] 会话已切换，忽略过时响应');
          return;
        }

        if (result.success && result.data?.messages) {
          console.log('[加载历史] 消息数量:', result.data.messages.length);
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
          if (result.data.lastUsedProvider) {
            this.selectedModelProvider = result.data.lastUsedProvider;
          }
          if (result.data.lastUsedMode) {
            this.mode = result.data.lastUsedMode;
          }

          // 更新会话标题
          if (result.data.session) {
            this.currentSessionTitle = result.data.session.title || null;
          }

          this.hasHistory = this.messages.length > 0;
          this.historyLoaded = true;
          this.scrollToBottom();
        } else {
          console.warn('[加载历史] 返回数据格式不正确:', result);
          if (result && result.success === false) {
            // 会话不存在或已失效，清理本地状态，避免后续继续写入无效 session_id
            this.currentSessionId = null;
            this.currentSessionTitle = null;
            this.messages = [];
            this.hasHistory = false;
            this.historyLoaded = false;
            if (window.Application && window.Application.PluginStorage) {
              window.Application.PluginStorage.removeItem('current_session_id');
            }
          }
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
        try {
          const existsResult = await api.getSession(this.currentSessionId);
          if (existsResult.success && existsResult.data?.session) {
            return this.currentSessionId;
          }
          console.warn('[自动创建会话] 当前 session 已失效，准备重建:', this.currentSessionId);
        } catch (e) {
          console.warn('[自动创建会话] 校验 session 失败，准备重建:', e);
        }

        this.currentSessionId = null;
        this.currentSessionTitle = null;
        if (window.Application && window.Application.PluginStorage) {
          window.Application.PluginStorage.removeItem('current_session_id');
        }
      }

      // 初始化期间不创建新会话，等待初始化完成
      if (this._initializing) {
        return null;
      }

      console.log('[自动创建会话] 开始创建');
      try {
        const result = await api.createSession({ title: t('session.newConversation') });

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
          // 如果当前没有选中模型（空字符串），默认选择第一个可用模型
          if (!this.selectedModel) {
            this.selectedModel = result.data.models[0].id;
            this.selectedModelProvider = result.data.models[0].provider || '';
          } else if (!this.selectedModelProvider) {
            const matched = result.data.models.find((m) => m.id === this.selectedModel);
            if (matched) {
              this.selectedModelProvider = matched.provider || '';
            }
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
          alert(t('chat.selectionUnavailable'));
          return;
        }

        const range = selection.Range;
        if (!range) {
          console.warn('[Selection] 无法获取范围');
          alert(t('chat.selectionRangeUnavailable'));
          return;
        }

        const text = range.Text || '';
        const cleanedText = text.replace(/[\r\n\u0007\f]/g, ' ').trim();

        let hasTable = false;
        let hasInlineImage = false;
        let hasFloatingImage = false;
        try {
          hasTable = !!(range.Tables && range.Tables.Count > 0);
        } catch {}
        try {
          hasInlineImage = !!(range.InlineShapes && range.InlineShapes.Count > 0);
        } catch {}
        try {
          hasFloatingImage = !!(range.ShapeRange && range.ShapeRange.Count > 0);
        } catch {}

        const hasNonTextContent = hasTable || hasInlineImage || hasFloatingImage;

        if (!cleanedText && !hasNonTextContent) {
          console.warn('[Selection] 没有选中有效内容');
          alert(t('chat.selectContentFirst'));
          return;
        }

        console.log('[Selection] 选中内容长度:', cleanedText.length, 'hasTable:', hasTable, 'hasImage:', hasInlineImage || hasFloatingImage);

        // 计算选区对应的段落索引
        const doc = window.Application.ActiveDocument;
        // Prefer native document ID; fallback to 0 (active doc) when unavailable.
        let docId = 0;
        try {
          const rawDocId = doc?.DocID;
          const parsedDocId = Number.parseInt(String(rawDocId), 10);
          docId = Number.isNaN(parsedDocId) ? 0 : parsedDocId;
        } catch (e) {
          void e;
          docId = 0;
        }
        const docName = doc?.BuiltInDocumentProperties?.Item('Title')?.Value || doc?.Name || t('chat.unnamedDocument');
        const totalParas = doc.Paragraphs.Count;
        let startParaIndex = 0;
        let endParaIndex = 0;

        for (let i = 1; i <= totalParas; i++) {
          const paraRange = doc.Paragraphs.Item(i).Range;
          if (range.Start >= paraRange.Start && range.Start < paraRange.End) {
            startParaIndex = i - 1;
          }
          if (range.End >= paraRange.Start && range.End <= paraRange.End) {
            endParaIndex = i - 1;
            break;
          }
        }

        const maxPreviewLen = 50;
        let displayText = cleanedText;
        if (!displayText) {
          if ((hasInlineImage || hasFloatingImage) && hasTable) {
            displayText = t('chat.imageTableSelection');
          } else if (hasInlineImage || hasFloatingImage) {
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

        const selectionInfo = {
          preview: preview + (hasMore ? '...' : ''),
          startText: startText + (displayText.length > 10 ? '...' : ''),
          endText: (displayText.length > 20 ? '...' : '') + endText,
          charCount: cleanedText.length || (hasNonTextContent ? 1 : 0),
          hasMore,
          range: { startParaIndex, endParaIndex },
          docId,
          docName
        };

        console.log('[Selection] 选区信息已生成:', {
          preview: selectionInfo.preview,
          charCount: selectionInfo.charCount
        });

        this.handleSelectionAdd(selectionInfo);
      } catch (error) {
        console.error('[Selection] 处理选区失败:', error);
        alert(t('chat.selectionFailed', { error: error.message }));
      }
    },

    /**
     * 处理添加的选区（追加到列表）
     */
    handleSelectionAdd(selectionInfo) {
      console.log('[AIChatPane] 收到选区信息:', selectionInfo);

      // 检查是否已存在相同范围的选区，避免重复
      const exists = this.selections.some(
        s => s.startParaIndex === selectionInfo.range.startParaIndex && s.endParaIndex === selectionInfo.range.endParaIndex
      );
      if (exists) {
        console.log('[AIChatPane] 该选区已存在，跳过');
        return;
      }

      this.selections.push({
        preview: selectionInfo.preview,
        startText: selectionInfo.startText,
        endText: selectionInfo.endText,
        startParaIndex: selectionInfo.range.startParaIndex,
        endParaIndex: selectionInfo.range.endParaIndex,
        charCount: selectionInfo.charCount,
        hasMore: selectionInfo.hasMore,
        docId: selectionInfo.docId,
        docName: selectionInfo.docName
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
     * 添加文件（来自 ChatInput 上传）
     */
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

    /**
     * 移除指定索引的文件
     */
    removeFile(index) {
      if (index >= 0 && index < this.uploadedFiles.length) {
        this.uploadedFiles.splice(index, 1);
      }
    },

    /**
     * 清空已添加文件
     */
    clearAllFiles() {
      this.uploadedFiles = [];
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
        ? this.selections.map(s => ({ startParaIndex: s.startParaIndex, endParaIndex: s.endParaIndex }))
        : null;
      this._sendStreamRequest(userMessage, retryRanges);
    },

    /**
     * 处理用户发送消息（由 ChatInput 触发）
     */
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
        selectionContext = this.selections.map(s => ({
          preview: s.preview,
          startText: s.startText,
          endText: s.endText,
          startParaIndex: s.startParaIndex,
          endParaIndex: s.endParaIndex,
          charCount: s.charCount,
          docId: s.docId,
          docName: s.docName
        }));
        documentRange = this.selections.map(s => ({
          startParaIndex: s.startParaIndex,
          endParaIndex: s.endParaIndex,
          docId: Number.isInteger(s.docId) ? s.docId : 0,
          docName: s.docName
        }));
        userMsgObj.selectionContext = selectionContext;
      }

      // 上传附件（在清空前捕获）
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

      this.clearAllSelections();
      this.clearAllFiles();

      this._sendStreamRequest(userMessage, documentRange, uploadedFilesMeta, selectionContext);
    },

    /**
     * 发送流式请求的公共方法
     */
    _sendStreamRequest(userMessage, documentRange, files = [], selectionContext = null) {
      this.tokenStats = {
        current: 0,
        max: this.tokenStats?.max || 258000
      };
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
      // 必须从响应式数组中取引用（Vue 3 push 后内部对象会被包装为 Proxy）
      const aiMsg = this.messages[this.messages.length - 1];

      const streamCtrl = api.chatStream(userMessage, {
        mode: this.mode,
        model: this.selectedModel,
        provider: this.selectedModelProvider,
        documentRange: documentRange,
        selectionContext: selectionContext,
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
          } else if (error?.reconnecting) {
            aiMsg.content = t('chat.networkInterruptedReconnecting');
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

          // 清理缓存
          delete this._streamingCache[streamSessionId];
        }
      });

      this.currentStreamCtrl = streamCtrl;
    },

    /**
     * 处理流式消息
     */
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

      // 处理 token 统计信息
      if (data.type === 'token_stats') {
        this.tokenStats = {
          current: data.current_tokens || 0,
          max: data.max_tokens || 258000
        };
        return;
      }

      if (data.type === 'context_compaction') {
        const parts = msg.contentParts;
        const status = String(data.status || '').toLowerCase();
        const isStarted = status === 'started';
        const content = isStarted
          ? t('chat.contextCompactionStarted')
          : status === 'completed'
            ? t('chat.contextCompactionCompleted')
            : (data.content || t('chat.contextCompactionCompleted'));
        const nextPart = {
          type: 'status',
          content,
          loading: isStarted,
          contextCompaction: true
        };
        let existingIndex = -1;
        for (let index = parts.length - 1; index >= 0; index--) {
          if (parts[index].contextCompaction) {
            existingIndex = index;
            break;
          }
        }
        if (existingIndex >= 0) {
          parts.splice(existingIndex, 1, nextPart);
        } else {
          parts.push(nextPart);
        }
        this.scrollToBottom();
        return;
      }

      // 后端请求读取文档：委托 api.js 解析文档并回传
      if (data.type === 'read_document') {
        console.log(
          '[AIChatPane] 后端请求读取文档,',
          'startParaIndex:', data.startParaIndex,
          'endParaIndex:', data.endParaIndex,
          'startParaID:', data.startParaID,
          'endParaID:', data.endParaID,
          'docId:', data.docId,
          'mode:', data.mode
        );
        const hasParaIDMode = Number.isInteger(data.startParaID) || Number.isInteger(data.endParaID);
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
          startParaID: this._toIntOrNull(data.startParaID),
          endParaID: this._toIntOrNull(data.endParaID),
          docId: this._toIntOrDefault(data.docId, 0),
          mode: data.mode === 'lightweight' ? 'lightweight' : 'full'
        });
        return;
      }

      // 后端请求查询文档：委托 api.js 解析文档并执行 Style Query DSL
      if (data.type === 'search_document') {
        console.log('[AIChatPane] 后端请求查询文档, query:', data.query, 'docId:', data.docId);
        msg.contentParts.push({
          type: 'status',
          content: data.content || t('chat.searchingDocument'),
          loading: true
        });
        this.scrollToBottom();
        api.wsManager._handleQueryRequest(data.query, this._toIntOrDefault(data.docId, 0));
        return;
      }

      // 查询完成：替换 loading 状态
      if (data.type === 'query_complete') {
        console.log('[AIChatPane] 文档查询完成');
        const parts = msg.contentParts;
        let found = false;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === 'status' && parts[i].loading && !parts[i].contextCompaction) {
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
          parts.push({
            type: 'status',
            content: data.content || t('chat.searchComplete'),
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
          if (parts[i].type === 'status' && parts[i].loading && !parts[i].contextCompaction) {
            console.log('[AIChatPane] 找到 loading 状态，索引:', i, '内容:', parts[i].content);
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
          console.warn('[AIChatPane] 未找到 loading 状态的 read_document，直接追加');
          parts.push({
            type: 'status',
            content: data.content || t('chat.documentReadComplete'),
            loading: false
          });
        }
        this.scrollToBottom();
        return;
      }

      // 后端请求删除文档段落：立即在原生修订模式下执行，并回传真实结果。
      if (data.type === 'delete_document') {
        const paraIDs = Array.isArray(data.paraIDs)
          ? data.paraIDs.map(v => Number(v)).filter(v => Number.isInteger(v))
          : [];
        console.log('[AIChatPane] 后端请求删除文档段落, paraIDs:', paraIDs, 'docId:', data.docId);
        msg.contentParts.push({
          type: 'status',
          content: data.content || t('chat.prepareDelete', { ids: paraIDs.join(', ') }),
          loading: true
        });
        this.scrollToBottom();
        this._applyImmediateDelete({
          paraIDs,
          docId: this._toIntOrDefault(data.docId, 0),
          requestId: data.requestId || null
        });
        return;
      }

      // 删除完成：替换 loading 状态
      if (data.type === 'delete_complete') {
        console.log('[AIChatPane] 文档删除完成');
        const parts = msg.contentParts;
        let found = false;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === 'status' && parts[i].loading && !parts[i].contextCompaction) {
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
          parts.push({
            type: 'status',
            content: data.content || t('chat.deleteComplete'),
            loading: false
          });
        }
        this.scrollToBottom();
        return;
      }

      // 后端请求替换单个段落的文本内容；保留原段落标记和 pStyle。
      if (data.type === 'edit_document') {
        const paraID = this._toIntOrNull(data.paraID);
        const runs = Array.isArray(data.runs) ? data.runs : [];
        console.log('[AIChatPane] 后端请求编辑段落:', { paraID, docId: data.docId, runCount: runs.length });
        msg.contentParts.push({
          type: 'status',
          content: data.content || `✏️ 正在更新段落 ${paraID ?? ''}`,
          loading: true
        });
        this.scrollToBottom();
        this._applyImmediateEdit({
          paraID,
          runs,
          docId: this._toIntOrDefault(data.docId, 0),
          requestId: data.requestId || null,
          msg
        });
        return;
      }

      if (data.type === 'edit_complete') {
        const parts = msg.contentParts;
        let found = false;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === 'status' && parts[i].loading && !parts[i].contextCompaction) {
            parts.splice(i, 1, {
              type: 'status',
              content: data.content || `✏️ 段落 ${data.paraID ?? ''} 已更新`,
              loading: false
            });
            found = true;
            break;
          }
        }
        if (!found) {
          parts.push({
            type: 'status',
            content: data.content || `✏️ 段落 ${data.paraID ?? ''} 已更新`,
            loading: false
          });
        }
        this.scrollToBottom();
        return;
      }

      // 后端请求在活动文档中插入原生换行/分页/下一页分节符
      if (data.type === 'insert_break') {
        const paraID = this._toIntOrNull(data.paraID);
        const breakType = data.breakType;
        const requestId = data.requestId || null;
        console.log('[AIChatPane] 后端请求插入断行:', { paraID, breakType });
        const result = insertBreakAfterParagraph(paraID, breakType);
        if (result.success) {
          // 后续 search/read 必须重新读取，不能命中插入前的文档缓存。
          api.wsManager.clearDocumentCache();
          msg.contentParts.push({
            type: 'status',
            content: data.content || t('chat.insertBreakSuccess'),
            loading: false
          });
          if (requestId) {
            api.wsManager.send({
              type: 'insert_break_response',
              requestId,
              success: true,
              breakType,
              paragraphAfterBreak: result.paragraphAfterBreak || null
            }).catch((error) => console.warn('[AIChatPane] 回传插入断行结果失败:', error));
          }
        } else {
          msg.contentParts.push({
            type: 'status',
            content: t('chat.insertBreakFailed', { error: result.error || t('common.unknownError') }),
            loading: false
          });
          console.warn('[AIChatPane] 插入断行失败:', result.error);
          if (requestId) {
            api.wsManager.send({
              type: 'insert_break_response',
              requestId,
              success: false,
              breakType,
              error: result.error || '插入断行失败'
            }).catch((error) => console.warn('[AIChatPane] 回传插入断行错误失败:', error));
          }
        }
        this.scrollToBottom();
        return;
      }

      // 后端请求创建并打开新的空白 DOCX 文档
      if (data.type === 'create_document') {
        const parts = msg.contentParts;
        const pendingPart = {
          type: 'status',
          content: t('chat.createDocumentPending'),
          loading: true
        };
        parts.push(pendingPart);
        try {
          const result = api.createDocument();
          if (!result?.success) {
            throw new Error(result?.error || 'WPS 未返回新文档对象');
          }
          pendingPart.content = t('chat.createDocumentSuccess');
          pendingPart.loading = false;
          msg._docId = this._toIntOrDefault(result.documentId, 0);
          api.wsManager.send({
            type: 'create_document_response',
            success: true,
            documentId: msg._docId
          }).catch((error) => console.warn('[AIChatPane] 回传新文档创建结果失败:', error));
        } catch (error) {
          pendingPart.content = t('chat.createDocumentFailed', { error: error?.message || error });
          pendingPart.loading = false;
          console.error('[AIChatPane] 创建 WPS 空白 DOCX 失败:', error);
          api.wsManager.send({
            type: 'create_document_response',
            success: false,
            error: error?.message || String(error)
          }).catch((sendError) => console.warn('[AIChatPane] 回传新文档创建错误失败:', sendError));
        }
        this.scrollToBottom();
        return;
      }

      if (data.type === 'generate_document') {
        console.log('[AIChatPane] 生成文档中...');
        msg.contentParts.push({
          type: 'status',
          content: data.content || t('chat.generatingDocument'),
          loading: true
        });
        this.scrollToBottom();
        return;
      }

      if (data.type === 'generate_complete') {
        console.log('[AIChatPane] 文档生成完成, docId:', data.docId, 'insertParaID:', data.insertParaID);
        const parts = msg.contentParts;
        let found = false;
        for (let i = parts.length - 1; i >= 0; i--) {
          if (parts[i].type === 'status' && parts[i].loading && !parts[i].contextCompaction) {
            console.log('[AIChatPane] 找到 loading 状态，索引:', i, '内容:', parts[i].content);
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
          console.warn('[AIChatPane] 未找到 loading 状态的 generate_document，直接追加');
          parts.push({
            type: 'status',
            content: data.content || t('chat.documentGenerated'),
            loading: false
          });
        }

        msg._docId = this._toIntOrDefault(data.docId, 0);
        msg._insertParaID = this._toIntOrNull(data.insertParaID);

        this.scrollToBottom();
        return;
      }

      if (data.type === 'mcp_tool_call') {
        this._upsertMcpCallPart(msg, data.toolName, data.args);
        this.scrollToBottom();
        return;
      }

      if (data.type === 'mcp_tool_result') {
        this._attachMcpResultPart(
          msg,
          data.toolName,
          data.outputPreview,
          data.isError
        );
        this.scrollToBottom();
        return;
      }
      // 其他消息类型：text, json, status, thinking 等
      if (data.type === 'thinking' && data.content) {
        if (!msg.thinkingStartTime) {
          msg.thinkingStartTime = Date.now();
        }
        // 同一轮对话中可能出现多段 thinking，收到新 thinking 时恢复“进行中”状态
        msg.thinkingDone = false;
        msg.thinking += data.content;
        this.scrollToBottom();
        return;
      }

      if (data.type === 'status' && data.content) {
        // 兼容旧版本：将文本 status 中的 MCP 调用日志转为结构化卡片
        const mcpCallPattern = /^🔧\s*调用\s*MCP\s*工具:\s*([A-Za-z0-9._:-]+)(?:\((.*)\))?\s*$/s;
        const mcpMatch = String(data.content).match(mcpCallPattern);
        if (mcpMatch) {
          const toolName = mcpMatch[1];
          const argsRaw = (mcpMatch[2] || '').trim();
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

        msg.contentParts.push({
          type: 'status',
          content: data.content,
          loading: !!data.loading
        });
        this.scrollToBottom();
        return;
      }

      // 处理 tool 输出压缩信息
      if (data.type === 'tool_compress') {
        msg.contentParts.push({
          type: 'tool_compress',
          content: data.content,
          detail: data.detail || {}
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
        const documentJson =
          data.content.document &&
          typeof data.content.document === 'object' &&
          (data.content.document.paragraphs || data.content.document.tables || data.content.document.images)
            ? data.content.document
            : data.content;
        const insItem = {
          documentJson,
          docId: this._toIntOrDefault(data.docId, this._toIntOrDefault(data.content.docId ?? documentJson.docId, 0)),
          insertParaID: this._toIntOrNull(data.content.insertParaID ?? documentJson.insertParaID),
          msg: msg,
          insertStartPos: null,
          insertEndPos: null,
          requestId: data.requestId || null
        };
        const inserted = this._applyImmediateInsertion(insItem);
        if (!inserted) {
          msg.contentParts.push({
            type: 'status',
            content: t('chat.documentInsertFailed'),
            loading: false
          });
        }

        this.scrollToBottom();
      } else if (data.error) {
        msg.content += `\n\n${t('chat.errorLabel', { error: data.error })}`;
      }
    },

    _resolveTargetDoc(docId = 0) {
      return getDocumentById(this._toIntOrDefault(docId, 0)) || window.Application.ActiveDocument;
    },

    _applyImmediateDelete(payload) {
      const sendResult = (result) => {
        if (!payload?.requestId) {
          return;
        }
        api.wsManager.send({
          type: 'delete_response',
          requestId: payload.requestId,
          ...result
        }).catch((error) => console.warn('[AIChatPane] 回传删除结果失败:', error));
      };
      const docId = this._toIntOrDefault(payload?.docId, 0);
      const paraIDs = Array.isArray(payload?.paraIDs)
        ? payload.paraIDs.map(v => Number(v)).filter(v => Number.isInteger(v))
        : [];
      const doc = this._resolveTargetDoc(docId);
      if (!doc) {
        console.warn('[AIChatPane] _applyImmediateDelete: 无法获取文档对象 docId=', docId);
        sendResult({ success: false, deletedCount: 0, error: `无法获取文档 docId=${docId}` });
        return false;
      }
      if (!paraIDs.length) {
        console.warn('[AIChatPane] _applyImmediateDelete: paraIDs 为空');
        sendResult({ success: false, deletedCount: 0, error: 'delete_document 缺少有效 paraIDs' });
        return false;
      }

      const targetIds = new Set(paraIDs);
      const matchedParas = [];
      const matchedIds = new Set();
      let firstMatchedIndex = null;
      for (let pi = 1; pi <= doc.Paragraphs.Count; pi++) {
        const para = doc.Paragraphs.Item(pi);
        const pid = Number(getParagraphParaID(para));
        if (Number.isInteger(pid) && targetIds.has(pid)) {
          matchedParas.push(para);
          matchedIds.add(pid);
          if (firstMatchedIndex === null) {
            firstMatchedIndex = pi;
          }
        }
      }
      const missingParaIDs = paraIDs.filter((pid) => !matchedIds.has(pid));
      if (matchedParas.length === 0) {
        const error = '未找到匹配 paraIDs 的段落；这些 ID 可能已经被删除或已经失效';
        sendResult({ success: false, deletedCount: 0, missingParaIDs, error });
        return false;
      }

      // A paragraph carrying a pending deletion Revision still exists in the
      // WPS object model. It must never be reused as the replacement anchor:
      // text inserted there can become part of the deletion and disappear on
      // Accept(). Return the nearest surviving paragraph before the range.
      let replacementInsertParaID = 0;
      for (let pi = Number(firstMatchedIndex) - 1; pi >= 1; pi--) {
        const previousID = Number(getParagraphParaID(doc.Paragraphs.Item(pi)));
        if (Number.isInteger(previousID) && !targetIds.has(previousID)) {
          replacementInsertParaID = previousID;
          break;
        }
      }

      const targetRange = matchedParas.reduce(
        (bounds, para) => {
          const range = this._rangeForDeleteMarking(para);
          return {
            start: Math.min(bounds.start, Number(range.Start)),
            end: Math.max(bounds.end, Number(range.End))
          };
        },
        { start: Number.POSITIVE_INFINITY, end: Number.NEGATIVE_INFINITY }
      );

      let trackedEdit = null;
      let deleteResult = null;
      try {
        trackedEdit = beginTrackedEdit(doc);
        deleteResult = deleteDocxPara([...matchedIds], doc);
        if (!deleteResult || Number(deleteResult.deletedCount) === 0) {
          abortTrackedEdit(trackedEdit);
          const error = deleteResult?.message || '删除段落失败';
          sendResult({
            success: false,
            deletedCount: 0,
            missingParaIDs,
            failedParaIDs: deleteResult?.failedParaIDs || [],
            replacementInsertParaID,
            error
          });
          return false;
        }

        const revisionBatch = finishTrackedEdit(trackedEdit, targetRange, 'delete');
        if (!revisionBatch.batchId) {
          try {
            window.Application.Undo(Number(deleteResult.deletedCount) || 1);
          } catch (undoError) {
            console.error('[AIChatPane] 未检测到删除修订且撤销失败:', undoError);
          }
          const error = 'WPS 未创建原生删除修订，已撤销本次删除';
          sendResult({ success: false, deletedCount: 0, missingParaIDs, replacementInsertParaID, error });
          return false;
        }

        this.deleteRevisions.push({
          paraIDs: [...matchedIds],
          docId,
          replacementInsertParaID,
          preview: t('chat.deletePreview', { ids: [...matchedIds].join(', ') }),
          _revisionCreated: true,
          _revisionBatchId: revisionBatch.batchId,
          _markingMode: 'revision'
        });
        api.wsManager.clearDocumentCache();

        const failedParaIDs = Array.isArray(deleteResult.failedParaIDs)
          ? deleteResult.failedParaIDs
          : [];
        const fullyDeleted = missingParaIDs.length === 0
          && failedParaIDs.length === 0
          && Number(deleteResult.deletedCount) === matchedIds.size;
        sendResult({
          success: fullyDeleted,
          deletedCount: Number(deleteResult.deletedCount) || 0,
          missingParaIDs,
          failedParaIDs,
          replacementInsertParaID,
          revisionCount: revisionBatch.revisionCount,
          ...(fullyDeleted ? {} : { error: '部分段落未删除；请重新读取文档后仅重试仍存在的 paraID' })
        });
        return fullyDeleted;
      } catch (error) {
        abortTrackedEdit(trackedEdit);
        if (deleteResult?.success) {
          try {
            window.Application.Undo(Number(deleteResult.deletedCount) || 1);
          } catch (undoError) {
            console.error('[AIChatPane] 删除异常后撤销失败:', undoError);
          }
        }
        const message = error?.message || String(error);
        console.warn('[AIChatPane] 创建 WPS 原生删除修订失败:', message);
        sendResult({
          success: false,
          deletedCount: 0,
          missingParaIDs,
          replacementInsertParaID,
          error: message
        });
        return false;
      }
    },

    _applyImmediateEdit(payload) {
      const sendResult = (result) => {
        if (!payload?.requestId) {
          return;
        }
        api.wsManager.send({
          type: 'edit_document_response',
          requestId: payload.requestId,
          ...result
        }).catch((error) => console.warn('[AIChatPane] 回传段落编辑结果失败:', error));
      };

      const paraID = this._toIntOrNull(payload?.paraID);
      const docId = this._toIntOrDefault(payload?.docId, 0);
      const runs = Array.isArray(payload?.runs) ? payload.runs : [];
      const doc = this._resolveTargetDoc(docId);
      if (!doc) {
        sendResult({ success: false, paraID, docId, error: `无法获取文档 docId=${docId}` });
        return false;
      }
      if (paraID === null) {
        sendResult({ success: false, paraID: null, docId, error: 'edit_document 缺少有效 paraID' });
        return false;
      }
      const conflictingDelete = this.deleteRevisions.find(
        (item) => this._toIntOrDefault(item.docId, 0) === docId
          && Array.isArray(item.paraIDs)
          && item.paraIDs.some((id) => Number(id) === paraID)
      );
      if (conflictingDelete) {
        const error = `paraID ${paraID} 正处于待删除修订中，请先重新读取文档并使用仍然存在的段落 ID`;
        sendResult({ success: false, paraID, docId, error });
        return false;
      }

      let trackedEdit = null;
      let result = null;
      try {
        trackedEdit = beginTrackedEdit(doc);
        result = editDocxParagraph(paraID, runs, doc);
        if (!result || !result.success) {
          abortTrackedEdit(trackedEdit);
          sendResult({ success: false, paraID, docId, error: result?.error || '段落编辑失败' });
          return false;
        }

        const revisionBatch = finishTrackedEdit(
          trackedEdit,
          { start: result.startPos, end: result.endPos },
          'edit'
        );
        const editItem = {
          docId,
          paraID,
          startPos: result.startPos,
          endPos: result.endPos,
          replacedTextLength: result.replacedTextLength || 0,
          originalText: result.originalText || '',
          _revisionBatchId: revisionBatch.batchId,
          _markingMode: revisionBatch.batchId ? 'revision' : 'revision-unavailable',
          msg: payload.msg || null
        };
        this.pendingEdits.push(editItem);
        if (payload.msg) {
          payload.msg._docId = docId;
          payload.msg._editedParaID = paraID;
          payload.msg._revisionBatchId = revisionBatch.batchId || null;
        }
        api.wsManager.clearDocumentCache();
        sendResult({
          success: true,
          docId,
          paraID,
          revisionCount: revisionBatch.revisionCount,
          paragraph: result.paragraph || null
        });
        return true;
      } catch (error) {
        abortTrackedEdit(trackedEdit);
        sendResult({ success: false, paraID, docId, error: error?.message || String(error) });
        return false;
      }
    },

    _applyImmediateInsertion(insItem) {
      const sendResult = (payload) => {
        if (!insItem?.requestId) {
          return;
        }
        api.wsManager.send({
          type: 'generate_document_response',
          requestId: insItem.requestId,
          ...payload
        }).catch((error) => console.warn('[AIChatPane] 回传文档生成结果失败:', error));
      };
      insItem.docId = this._toIntOrDefault(insItem.docId, 0);
      insItem.insertParaID = this._toIntOrNull(insItem.insertParaID);
      const doc = this._resolveTargetDoc(insItem.docId);
      if (!doc) {
        console.warn('[AIChatPane] _applyImmediateInsertion: 无法获取文档对象 docId=', insItem.docId);
        sendResult({ success: false, error: `无法获取文档 docId=${insItem.docId}` });
        return false;
      }

      const conflictingDelete = this.deleteRevisions.find(
        (item) => this._toIntOrDefault(item.docId, 0) === insItem.docId
          && Array.isArray(item.paraIDs)
          && item.paraIDs.some((paraID) => Number(paraID) === insItem.insertParaID)
      );
      if (conflictingDelete) {
        const safeAnchor = this._toIntOrDefault(conflictingDelete.replacementInsertParaID, 0);
        const error = `insertParaID ${insItem.insertParaID} 正处于待接受的删除修订中；请改用 delete_document 返回的 replacementInsertParaID=${safeAnchor}`;
        console.warn('[AIChatPane] 拒绝在待删除段落内插入:', error);
        sendResult({ success: false, error, replacementInsertParaID: safeAnchor });
        return false;
      }

      let trackedEdit = null;
      try {
        trackedEdit = beginTrackedEdit(doc);
        const result = generateDocxFromJSON(insItem.documentJson, doc, insItem.insertParaID);
        if (!result || !result.success) {
          abortTrackedEdit(trackedEdit);
          console.error('[AIChatPane] 即时插入失败:', result?.error || '(unknown)');
          sendResult({ success: false, error: result?.error || '文档插入失败' });
          return false;
        }
        if (result.warning) {
          if (insItem.msg && Array.isArray(insItem.msg.contentParts)) {
            insItem.msg.contentParts.push({
              type: 'status',
              content: `⚠️ ${result.warning}`,
              loading: false
            });
          }
          console.warn('[AIChatPane] 即时插入警告:', result.warning);
        }

        insItem.insertStartPos = result.startPos;
        insItem.insertEndPos = result.endPos;
        insItem._alreadyInserted = true;
        const revisionBatch = finishTrackedEdit(
          trackedEdit,
          { start: result.startPos, end: result.endPos },
          'insert'
        );
        insItem._revisionBatchId = revisionBatch.batchId;
        insItem._markingMode = revisionBatch.batchId ? 'revision' : 'revision-unavailable';
        if (!revisionBatch.batchId) {
          console.warn('[AIChatPane] WPS 未返回本次插入产生的 Revision，取消时将按插入范围回滚');
        }

        // 记录本次流中已执行的插入，供后续 delete_document 做索引偏移
        const { paragraphCount: paraCount, tableCount } = this._countDocumentContent(insItem.documentJson);
        const shiftCount = paraCount + tableCount;
        if (shiftCount > 0) {
          this._streamInsertions.push({
            insertParaID: insItem.insertParaID,
            count: shiftCount,
            docId: this._toIntOrDefault(insItem.docId, 0)
          });
        }

        if (insItem.msg) {
          insItem.msg.insertStartPos = result.startPos;
          insItem.msg.insertEndPos = result.endPos;
          insItem.msg._docId = this._toIntOrDefault(insItem.docId, 0);
          insItem.msg._insertParaID = insItem.insertParaID;
          insItem.msg.documentJson = insItem.documentJson;
          insItem.msg._revisionBatchId = insItem._revisionBatchId || null;
        }
        this.pendingInsertions.push(insItem);
        this.pendingDocumentMsg = insItem.msg || null;
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
        console.log(
          '[AIChatPane] 文档已即时插入:',
          `docId=${this._toIntOrDefault(insItem.docId, 0)}`,
          `insertParaID=${insItem.insertParaID}`,
          `range=${result.startPos}-${result.endPos}`
        );
        sendResult({
          success: true,
          docId: insItem.docId,
          lastParagraph: result.lastParagraph || null
        });
        return true;
      } catch (e) {
        abortTrackedEdit(trackedEdit);
        console.error('[AIChatPane] 即时插入异常:', e);
        sendResult({ success: false, error: e?.message || String(e) });
        return false;
      }
    },

    /**
     * 接受本轮已经执行的原生增删修订。
     */
    confirmPending() {
      // 与 WPS“审阅 → 接受对文档的所有修订”使用同一集合级接口。
      // 不再逐条处理缓存的 Revision 对象，因为每次 Accept() 都可能使
      // WPS 重排/合并集合，导致后续对象引用错位并误删新增内容。
      const documentResults = new Map();
      const pendingItems = [...this.pendingInsertions, ...this.pendingEdits, ...this.deleteRevisions];
      for (const item of pendingItems) {
        const documentKey = this._toIntOrDefault(item.docId, 0);
        const doc = this._resolveTargetDoc(item.docId);
        if (!doc || documentResults.has(documentKey)) {
          continue;
        }
        const settled = settleAllDocumentRevisions(doc, 'accept');
        documentResults.set(documentKey, settled);
        console.log('[AIChatPane] WPS 原生接受文档全部修订:', settled);
      }

      const operationSettled = (item) => {
        const documentKey = this._toIntOrDefault(item.docId, 0);
        return Boolean(documentResults.get(documentKey)?.success);
      };
      for (const ins of this.pendingInsertions) {
        if (operationSettled(ins) && ins.msg) {
          ins.msg._revisionBatchId = null;
        }
      }
      for (const edit of this.pendingEdits) {
        if (operationSettled(edit) && edit.msg) {
          edit.msg._revisionBatchId = null;
        }
      }
      this.pendingInsertions = this.pendingInsertions.filter((item) => !operationSettled(item));
      this.pendingEdits = this.pendingEdits.filter((item) => !operationSettled(item));
      this.deleteRevisions = this.deleteRevisions.filter((item) => !operationSettled(item));
      this._syncPendingDocumentPreview();
      this._streamInsertions = [];
    },

    /**
     * 拒绝本轮已经执行的原生增删修订。
     */
    cancelPending() {
      // 先拒绝删除修订以恢复原文。
      for (const pd of this.deleteRevisions) {
        const doc = this._resolveTargetDoc(pd.docId);
        if (!doc) {
          continue;
        }
        try {
          if (pd._markingMode === 'revision' && hasRevisionBatch(pd._revisionBatchId)) {
            const settled = settleRevisionBatch(pd._revisionBatchId, 'reject');
            console.log('[AIChatPane] 已拒绝删除内容修订:', settled);
            pd._revisionBatchId = null;
          }
        } catch (e) {
          console.warn('[AIChatPane] cancelPending 清理删除标记失败:', e);
        }
      }

      // 再拒绝段落编辑修订，恢复被替换的原文。
      for (const edit of this.pendingEdits) {
        const doc = this._resolveTargetDoc(edit.docId);
        if (!doc) {
          continue;
        }
        try {
          if (edit._markingMode === 'revision' && hasRevisionBatch(edit._revisionBatchId)) {
            const settled = settleRevisionBatch(edit._revisionBatchId, 'reject');
            console.log('[AIChatPane] 已拒绝段落编辑修订:', settled);
            edit._revisionBatchId = null;
            if (edit.msg) {
              edit.msg._revisionBatchId = null;
            }
          } else if (edit._markingMode === 'revision-unavailable') {
            // 极少数 WPS 版本不产生 Revision 时，用当前替换范围写回原文。
            // 段落标记仍未被触碰，因此 pStyle 和段落边界保持不变。
            doc.Range(edit.startPos, edit.endPos).Text = edit.originalText || '';
          }
        } catch (e) {
          console.warn('[AIChatPane] cancelPending 清理段落编辑失败:', e);
        }
      }

      // 再倒序拒绝新增修订，避免位置变化影响后续批次。
      const inserts = [...this.pendingInsertions].sort(
        (a, b) => (b.insertStartPos ?? -1) - (a.insertStartPos ?? -1)
      );
      for (const ins of inserts) {
        const doc = this._resolveTargetDoc(ins.docId);
        if (!doc) {
          continue;
        }
        try {
          if (ins._markingMode === 'revision' && hasRevisionBatch(ins._revisionBatchId)) {
            const settled = settleRevisionBatch(ins._revisionBatchId, 'reject');
            console.log('[AIChatPane] 已拒绝新增内容修订:', settled);
            if (ins.msg) {
              ins.msg._revisionBatchId = null;
            }
            ins._revisionBatchId = null;
          } else if (ins._markingMode === 'revision-unavailable') {
            if (ins.insertStartPos !== undefined && ins.insertEndPos !== undefined) {
              doc.Range(ins.insertStartPos, ins.insertEndPos).Delete();
            }
          }
        } catch (e) {
          console.warn('[AIChatPane] cancelPending 回滚新增失败:', e);
        }
      }

      this.deleteRevisions = [];
      this.pendingEdits = [];
      this.pendingInsertions = [];
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
      this._streamInsertions = [];
      console.log('用户取消了所有待确认标记与操作');
    },

    /**
     * 处理所有待处理的文档插入操作
     */
    async _processAllPendingInsertions() {
      console.log('[AIChatPane] 开始处理所有待插入文档, 数量:', this.pendingInsertions.length);
      for (let i = 0; i < this.pendingInsertions.length; i++) {
        const ins = this.pendingInsertions[i];
        console.log('[AIChatPane] 处理插入 ', i + 1, '/', this.pendingInsertions.length, ', docId:', ins.docId);

        // 获取正确的文档对象
        const doc = Number.isInteger(ins.docId) ? getDocumentById(ins.docId) : window.Application.ActiveDocument;
        if (!doc) {
          console.warn('[AIChatPane] 无法获取文档对象, docId:', ins.docId);
          continue;
        }

        // 执行文档插入
        let trackedEdit = null;
        trackedEdit = beginTrackedEdit(doc);
        const result = generateDocxFromJSON(ins.documentJson, doc, ins.insertParaID);
        if (result.success) {
          console.log('[AIChatPane] 文档已插入, docId:', ins.docId, ', 范围:', result.startPos, '-', result.endPos);
          ins.insertStartPos = result.startPos;
          ins.insertEndPos = result.endPos;

          const revisionBatch = finishTrackedEdit(
            trackedEdit,
            { start: result.startPos, end: result.endPos },
            'insert'
          );
          ins._revisionBatchId = revisionBatch.batchId;
          ins._markingMode = revisionBatch.batchId ? 'revision' : 'revision-unavailable';
        } else {
          abortTrackedEdit(trackedEdit);
          console.error('[AIChatPane] 文档插入失败:', result.error);
        }
      }

      // 清理待处理列表
      this.pendingInsertions = [];
    },

    /**
     * 取用于删除标记的段落 Range：优先 Duplicate + Expand(wdParagraph)，避免用数值重建 Range 时末尾少字。
     * @param {*} para - WPS Paragraph
     */
    _rangeForDeleteMarking(para) {
      let rng;
      try {
        rng = para.Range.Duplicate;
      } catch (e) {
        void e;
        rng = para.Range;
      }
      try {
        rng.Expand(4); // wdParagraph
      } catch (e2) {
        void e2;
      }
      return rng;
    },

    /**
     * 加载后端返回的图片临时目录（wence_data/temp）
     */
    async _loadWenceTempDir() {
      try {
        const data = await api.getWenceTempDir();
        const dir = (data && data.dir) ? String(data.dir) : '';
        if (!dir) {
          return;
        }
        window.__WENCE_TEMP_DIR__ = dir;
        try {
          localStorage.setItem('wence_temp_dir', dir);
        } catch {}
      } catch (e) {
        console.warn('加载图片临时目录失败:', e);
      }
    },

    /**
     * 插入内容到 Word 文档
     * @param {Object} msg - 消息对象
     * @param {string|null} docId - 文档 ID，null 表示活动文档
     */
    insertToWord(msg, docId = null) {
      try {
        // 仅在存在“尚未执行”的插入队列时，才走队列处理
        if (this.pendingInsertions.some(ins => ins.msg === msg && !ins._alreadyInserted)) {
          console.log('[AIChatPane] 使用 pendingInsertions 处理文档插入');
          this._processAllPendingInsertions();
          return;
        }

        const doc = Number.isInteger(docId) ? getDocumentById(docId) : window.Application.ActiveDocument;
        if (!doc) {
          alert(t('chat.openDocumentFirst'));
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

        if (jsonData && (jsonData.paragraphs || jsonData.tables || jsonData.images)) {
          console.log('检测到文档 JSON，使用格式化输出');

          // 使用 msg._insertParaID（从 generate_complete 事件中保存）
          const insertParaID = Number.isInteger(msg._insertParaID) ? msg._insertParaID : null;
          if (insertParaID === null) {
            console.log('insertParaID 未指定，使用当前光标位置插入');
          } else {
            console.log('插入到段落ID之后:', insertParaID);
          }

          msg.docLengthBefore = doc.Content.End;
          console.log('记录插入前文档长度:', msg.docLengthBefore);

          let trackedEdit = null;
          let result;
          try {
            trackedEdit = beginTrackedEdit(doc);
            result = generateDocxFromJSON(jsonData, doc, insertParaID);
          } catch (revisionError) {
            abortTrackedEdit(trackedEdit);
            throw revisionError;
          }

          if (result.success) {
            console.log('带格式的文档内容已成功插入');
            console.log(`实际插入范围: ${result.startPos} - ${result.endPos}`);

            msg.insertStartPos = result.startPos;
            msg.insertEndPos = result.endPos;
            console.log('记录插入范围用于撤销:', msg.insertStartPos, '-', msg.insertEndPos);

            const revisionBatch = finishTrackedEdit(
              trackedEdit,
              { start: result.startPos, end: result.endPos },
              'insert'
            );
            const pendingItem = {
              documentJson: jsonData,
              docId: this._toIntOrDefault(docId, 0),
              insertParaID,
              msg,
              insertStartPos: result.startPos,
              insertEndPos: result.endPos,
              _alreadyInserted: true,
              _revisionBatchId: revisionBatch.batchId,
              _markingMode: revisionBatch.batchId ? 'revision' : 'revision-unavailable'
            };
            msg._revisionBatchId = revisionBatch.batchId;
            this.pendingInsertions.push(pendingItem);
            this.pendingDocumentMsg = msg;
            const paragraphCount = this._countDocumentContent(jsonData).paragraphCount;
            const tableCount = this._countDocumentContent(jsonData).tableCount;
            this.pendingDocument = {
              preview: this._buildGeneratedDocumentPreview(paragraphCount, tableCount)
            };
          } else {
            abortTrackedEdit(trackedEdit);
            console.error('生成文档失败:', result.error);
            this.insertPlainText(content);
          }
        } else {
          this.insertPlainText(content, msg);
        }
      } catch (error) {
        console.error('插入文本失败:', error);
        alert(t('chat.insertFailed'));
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
.chat-root {
  display: flex;
  height: 100%;
  min-height: 100vh;
  min-width: 100%;
}

.ai-chat-container {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
  height: 100%;
  min-height: 100vh;
  background: #f7f8fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
}

.session-panel {
  width: 300px;
  flex-shrink: 0;
  border-left: 1px solid #e8e8e8;
  height: 100%;
  min-height: 100vh;
  overflow: hidden;
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

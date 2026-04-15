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
import { generateDocxFromJSON, deleteDocxPara } from '../js/docxJsonConverter.js';
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
      pendingDeletes: [],  // [{startParaIndex, endParaIndex, commentStartPos, commentEndPos, preview, msg}] 待确认删除列表
      _streamInsertions: [], // [{insertParaIndex, count}] 当前流式中已执行的插入操作
      historyLoading: false,
      hasHistory: false,
      historyLoaded: false,
      _streamingSessionId: null,   // 正在流式生成的 session ID
      _streamingCache: {},         // {sessionId: messages[]} 流式生成期间切走时缓存消息
      isWide: false,
      _proofreadModeInitialized: false,
      _proofreadModeLoadPromise: null
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
     * 优先使用 PluginStorage 中保存的 session_id，否则查找全局最新会话
     */
    async initSessionAndLoadHistory() {
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

            // 如果有消息，标记有历史
            this.hasHistory = result.data.messages && result.data.messages.length > 0;
          } else {
            console.log('[初始化] 当前没有历史会话');
            this.hasHistory = false;
          }
        }
      } catch (e) {
        console.error('[初始化] 失败:', e);
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

      await this.loadSessionMessages();
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

      console.log('[自动创建会话] 开始创建');
      try {
        const result = await api.createSession({ title: '新对话' });

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
    async saveMessageToHistory(role, content, documentJson = null, selectionContext = null, contentParts = null, thinking = null) {
      // 确保有会话
      let sessionId = await this.ensureSession();
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

        // 兼容旧缓存导致的无效 session_id：自动重建并重试一次
        if (!saveResult?.success) {
          console.warn('[保存消息] 会话失效，尝试重建后重试:', saveResult?.error);
          this.currentSessionId = null;
          this.currentSessionTitle = null;
          if (window.Application && window.Application.PluginStorage) {
            window.Application.PluginStorage.removeItem('current_session_id');
          }

          sessionId = await this.ensureSession();
          if (!sessionId) {
            console.warn('[保存消息] 重建会话失败，消息未保存');
            return;
          }

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

        if (!saveResult?.success) {
          console.warn('[保存消息] 最终保存失败:', saveResult?.error);
          return;
        }

        console.log('[保存消息] 成功');

        // 第一条用户消息会自动设置会话标题，更新本地标题
        if (role === 'user' && (!this.currentSessionTitle || this.currentSessionTitle === '新对话')) {
          const newTitle = content.length > 30 ? content.substring(0, 30) + '...' : content;
          this.currentSessionTitle = newTitle;
        }

        // 通知同页面的 SessionPane 更新列表
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

        // 计算选区对应的段落索引
        const doc = window.Application.ActiveDocument;
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
          range: { startParaIndex, endParaIndex }
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
          charCount: s.charCount
        }));
        documentRange = this.selections.map(s => ({ startParaIndex: s.startParaIndex, endParaIndex: s.endParaIndex }));
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

      this.messages.push(userMsgObj);
      this.historyLoaded = true;

      this.clearAllSelections();
      this.clearAllFiles();

      this.saveMessageToHistory('user', userMessage, null, selectionContext);

      this._sendStreamRequest(userMessage, documentRange, uploadedFilesMeta);
    },

    /**
     * 发送流式请求的公共方法
     */
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
      // 必须从响应式数组中取引用（Vue 3 push 后内部对象会被包装为 Proxy）
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

          // 流完成时用户可能已切到其他 session
          if (this.currentSessionId === streamSessionId) {
            // 仍在原 session，正常保存
            this.scrollToBottom();
            if (aiMsg.content) {
              this.saveMessageToHistory('assistant', aiMsg.content, aiMsg.documentJson, null, aiMsg.contentParts, aiMsg.thinking || null);
            }
          } else {
            // 用户已切走，直接调用 API 保存到原 session
            console.log('[流完成] 用户已切走，保存到原 session:', streamSessionId);
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

      // 收到非 thinking 事件时，标记思考已结束
      if (data.type !== 'thinking' && msg.thinkingStartTime && !msg.thinkingDone) {
        msg.thinkingDone = true;
        if (msg.thinkingExpanded) {
          msg.thinkingExpanded = false;
        }
      }

      // 后端请求读取文档：委托 api.js 解析文档并回传
      if (data.type === 'read_document') {
        console.log('[AIChatPane] 后端请求读取文档, startParaIndex:', data.startParaIndex, 'endParaIndex:', data.endParaIndex);
        msg.contentParts.push({
          type: 'status',
          content: data.content || `📑 正在读取文档(段落 ${data.startParaIndex} - ${data.endParaIndex})`,
          loading: true
        });
        this.scrollToBottom();
        api.wsManager._handleDocumentRequest(data.startParaIndex, data.endParaIndex);
        return;
      }

      // 后端请求查询文档：委托 api.js 解析文档并执行 Style Query DSL
      if (data.type === 'search_documnet') {
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

      // 删除完成：替换 loading 状态
      if (data.type === 'delete_complete') {
        console.log('[AIChatPane] 文档删除完成');
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
          parts.push({
            type: 'status',
            content: data.content || '✅ 删除完成',
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
      // 其他消息类型：text, json, status, thinking 等
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
        msg.contentParts.push({
          type: 'status',
          content: data.content,
          loading: !!data.loading
        });
        this.scrollToBottom();
        return;
      } else if (data.type === 'text' && data.content) {
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
        const _insParaIndex = data.content.insertParaIndex ?? -1;

        // 根据同一流中之前的插入操作调整当前插入位置
        if (_insParaIndex !== -1 && _insParaIndex !== null && _insParaIndex !== undefined && this._streamInsertions.length > 0) {
          let adjustedInsPos = _insParaIndex;
          for (const ins of this._streamInsertions) {
            const insAt = ins.insertParaIndex;
            if (insAt === -1 || insAt === null || insAt === undefined) {
              continue;
            }
            if (insAt <= adjustedInsPos) {
              adjustedInsPos += ins.count;
            }
          }
          data.content.insertParaIndex = adjustedInsPos;
        }

        // 用原始索引记录插入意图（供后续 delete_document 偏移计算）
        if (_insParaCount > 0) {
          this._streamInsertions.push({ insertParaIndex: _insParaIndex, count: _insParaCount });
        }

        console.log('收到完整JSON，自动输出到文档');
        this.$nextTick(async () => {
          // 先设置 pendingDocument 更新 UI
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

          // 执行文档插入
          this.insertToWord(msg);

          // 插入完成后，统一添加所有待处理批注（生成 + 删除）
          await this._addAllPendingComments(msg);
        });

        this.scrollToBottom();
      } else if (data.error) {
        msg.content += `\n\n错误: ${data.error}`;
      }
    },

    /**
     * 一键确认所有待处理操作（删除 + 生成）
     */
    confirmPending() {
      const doc = window.Application.ActiveDocument;

      // 1. 处理待删除内容
      if (this.pendingDeletes.length > 0 && doc) {
        const hasComments = this.pendingDeletes.some(pd => pd._markingMode === 'comment');
        let deleted = false;

        // 批注模式：通过"文策AI-删除"批注定位并删除段落
        if (hasComments) {
          try {
            const deleteRanges = [];
            const comments = doc.Comments;
            for (let i = comments.Count; i >= 1; i--) {
              const comment = comments.Item(i);
              if (comment.Author === '文策AI-删除') {
                const scope = comment.Scope;
                deleteRanges.push({ start: scope.Start, end: scope.End, commentIndex: i });
              }
            }

            if (deleteRanges.length > 0) {
              // 先删除批注（从后往前）
              for (const dr of deleteRanges) {
                try {
                  comments.Item(dr.commentIndex).Delete(); 
                } catch (e) {}
              }
              // 再按 start 从大到小排序删除段落范围
              deleteRanges.sort((a, b) => b.start - a.start);
              const docEnd = doc.Content.End;
              for (const dr of deleteRanges) {
                try {
                  let delStart = dr.start;
                  let delEnd = dr.end;
                  if (delEnd >= docEnd && delStart > 0) {
                    delStart -= 1;
                  }
                  const range = doc.Range(delStart, delEnd);
                  range.Delete();
                  console.log('[AIChatPane] 已删除范围:', delStart, '-', delEnd);
                } catch (e) {
                  console.error('删除段落范围失败:', e);
                }
              }
              deleted = true;
            }
          } catch (e) {
            console.error('批注删除失败:', e);
          }
        }

        // 高亮模式 或 批注模式降级：按索引删除，先清高亮再删
        if (!deleted) {
          const deletes = this.pendingDeletes.map(pd => {
            let adjStart = pd._adjStartParaIndex ?? pd.origStartParaIndex;
            let adjEnd = pd._adjEndParaIndex ?? pd.origEndParaIndex;
            if (pd._adjStartParaIndex === undefined) {
              adjStart = pd.origStartParaIndex;
              adjEnd = pd.origEndParaIndex;
              for (const ins of this._streamInsertions) {
                const insAt = ins.insertParaIndex;
                if (insAt === -1 || insAt === null || insAt === undefined) {
                  continue;
                }
                if (insAt <= adjStart) {
                  adjStart += ins.count;
                  if (adjEnd !== -1) {
                    adjEnd += ins.count;
                  }
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
                this._clearHighlightOnRange(d.startParaIndex, d.endParaIndex);
              }
              const result = deleteDocxPara(d.startParaIndex, d.endParaIndex);
              console.log('[AIChatPane] 按索引删除:', result.message);
            } catch (e) {
              console.error('[AIChatPane] 删除段落失败:', e);
            }
          }
        }
        this.pendingDeletes = [];
      }

      // 2. 确认生成文档：移除标注（保留内容）
      if (this.pendingDocumentMsg && doc) {
        const insertMsg = this.pendingDocumentMsg;
        if (insertMsg._markingMode === 'highlight') {
          // 高亮模式：清除高亮
          if (insertMsg.insertStartPos !== undefined && insertMsg.insertEndPos !== undefined) {
            try {
              const range = doc.Range(insertMsg.insertStartPos, insertMsg.insertEndPos);
              range.Font.HighlightColorIndex = 0; // wdNoHighlight
            } catch (e) {
              console.warn('清除生成高亮失败:', e);
            }
          }
        } else {
          // 批注模式：删除批注
          try {
            const comments = doc.Comments;
            for (let i = comments.Count; i >= 1; i--) {
              const comment = comments.Item(i);
              if (comment.Author === '文策AI-添加') {
                comment.Delete();
              }
            }
          } catch (e) {
            console.error('删除批注失败:', e);
          }
        }
      }
      this.pendingDocument = null;
      this.pendingDocumentMsg = null;
      this._streamInsertions = [];
    },

    /**
     * 一键取消所有待处理操作（移除删除标记 + 撤销生成）
     */
    cancelPending() {
      const doc = window.Application.ActiveDocument;

      // 1. 移除所有删除标注（不删除内容）
      if (this.pendingDeletes.length > 0 && doc) {
        const hasComments = this.pendingDeletes.some(pd => pd._markingMode === 'comment');
        const hasHighlights = this.pendingDeletes.some(pd => pd._markingMode === 'highlight');
        if (hasComments) {
          try {
            const comments = doc.Comments;
            for (let i = comments.Count; i >= 1; i--) {
              const comment = comments.Item(i);
              if (comment.Author === '文策AI-删除') {
                comment.Delete();
              }
            }
          } catch (e) {
            console.error('移除删除标记批注失败:', e);
          }
        }
        if (hasHighlights) {
          for (const pd of this.pendingDeletes) {
            if (pd._markingMode === 'highlight' && pd._adjStartParaIndex !== undefined) {
              this._clearHighlightOnRange(pd._adjStartParaIndex, pd._adjEndParaIndex);
            }
          }
        }
        this.pendingDeletes = [];
      }

      // 2. 撤销生成文档
      if (this.pendingDocumentMsg && doc) {
        let reverted = false;
        const insertMsg = this.pendingDocumentMsg;

        if (insertMsg._markingMode === 'highlight') {
          // 高亮模式：清除高亮后按范围删除插入的内容
          if (insertMsg.insertStartPos !== undefined && insertMsg.insertEndPos !== undefined) {
            try {
              const range = doc.Range(insertMsg.insertStartPos, insertMsg.insertEndPos);
              range.Font.HighlightColorIndex = 0; // wdNoHighlight
              range.Delete();
              reverted = true;
            } catch (e) {
              console.warn('高亮模式撤销失败:', e);
            }
          }
        } else {
          // 批注模式：通过批注定位删除内容
          try {
            const comments = doc.Comments;
            const addRanges = [];
            for (let i = comments.Count; i >= 1; i--) {
              const comment = comments.Item(i);
              if (comment.Author === '文策AI-添加') {
                const scope = comment.Scope;
                addRanges.push({ start: scope.Start, end: scope.End, commentIndex: i });
              }
            }
            if (addRanges.length > 0) {
              for (const ar of addRanges) {
                try {
                  comments.Item(ar.commentIndex).Delete(); 
                } catch (e) {}
              }
              addRanges.sort((a, b) => b.start - a.start);
              for (const ar of addRanges) {
                try {
                  const range = doc.Range(ar.start, ar.end);
                  range.Delete();
                } catch (e) {
                  console.warn('通过批注撤销范围失败:', e);
                }
              }
              reverted = true;
            }
          } catch (e) {
            console.warn('通过批注撤销生成文档失败:', e);
          }
        }

        // 降级：通过 revertToMessage
        if (!reverted) {
          const msgIndex = this.messages.indexOf(this.pendingDocumentMsg);
          if (msgIndex !== -1) {
            this.revertToMessage(msgIndex);
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
      const mode = await this._getProofreadMode();
      // 为生成的内容添加标注（使用 insertToWord 记录的范围）
      if (insertMsg && insertMsg.insertStartPos !== undefined && insertMsg.insertEndPos !== undefined) {
        try {
          const doc = window.Application.ActiveDocument;
          if (doc) {
            const insertedRange = doc.Range(insertMsg.insertStartPos, insertMsg.insertEndPos);
            if (mode === 'redblue') {
              // 红蓝高亮模式：红色 = 添加
              insertedRange.Font.HighlightColorIndex = 5; // wdPink (浅红)
              insertMsg._markingMode = 'highlight';
              console.log('[AIChatPane] 已为生成内容添加浅红色高亮');
            } else {
              // 修订模式：使用批注
              try {
                const comment = doc.Comments.Add(insertedRange, '待添加内容');
                comment.Author = '文策AI-添加';
                insertMsg._markingMode = 'comment';
                console.log('[AIChatPane] 已为生成内容添加批注');
              } catch (commentErr) {
                // 批注失败，降级到高亮
                insertedRange.Font.HighlightColorIndex = 5; // wdPink (浅红)
                insertMsg._markingMode = 'highlight';
                console.warn('[AIChatPane] 批注失败，降级到浅红色高亮:', commentErr);
              }
            }
          }
        } catch (e) {
          console.warn('添加生成标注失败:', e);
        }
      }
      // 为待删除内容添加标注
      await this._addDeleteComments();
    },

    /**
     * 为待删除内容添加标注（使用调整后的索引）
     */
    async _addDeleteComments() {
      const mode = await this._getProofreadMode();
      const doc = window.Application.ActiveDocument;
      if (!doc) {
        return;
      }

      for (const pd of this.pendingDeletes) {
        if (pd._commentAdded) {
          continue;
        }
        let adjStart = pd.origStartParaIndex;
        let adjEnd = pd.origEndParaIndex;
        for (const ins of this._streamInsertions) {
          const insAt = ins.insertParaIndex;
          if (insAt === -1 || insAt === null || insAt === undefined) {
            continue;
          }
          if (insAt <= adjStart) {
            adjStart += ins.count;
            if (adjEnd !== -1) {
              adjEnd += ins.count;
            }
          }
        }
        try {
          const totalParas = doc.Paragraphs.Count;
          let startIdx = adjStart;
          let endIdx = adjEnd;
          if (endIdx === -1) {
            endIdx = totalParas - 1;
          }
          const startPara = doc.Paragraphs.Item(startIdx + 1); // WPS 1-based
          const endPara = doc.Paragraphs.Item(endIdx + 1);
          const rangeStart = startPara.Range.Start;
          const rangeEnd = endPara.Range.End;
          const deleteRange = doc.Range(rangeStart, rangeEnd);

          if (mode === 'redblue') {
            // 红蓝高亮模式：蓝色 = 删除
            deleteRange.Font.HighlightColorIndex = 3; // wdTurquoise (浅蓝)
            pd._commentAdded = true;
            pd._markingMode = 'highlight';
            pd._adjStartParaIndex = adjStart;
            pd._adjEndParaIndex = adjEnd;
            console.log('[AIChatPane] 已添加删除浅蓝色高亮(索引:', adjStart, '-', adjEnd, ')');
          } else {
            // 修订模式：使用批注
            try {
              const comment = doc.Comments.Add(deleteRange, '待删除内容');
              comment.Author = '文策AI-删除';
              pd._commentAdded = true;
              pd._markingMode = 'comment';
              pd._adjStartParaIndex = adjStart;
              pd._adjEndParaIndex = adjEnd;
              console.log('[AIChatPane] 已添加删除标记批注(索引:', adjStart, '-', adjEnd, ')');
            } catch (commentErr) {
              // 批注失败，降级到高亮
              deleteRange.Font.HighlightColorIndex = 3; // wdTurquoise (浅蓝)
              pd._commentAdded = true;
              pd._markingMode = 'highlight';
              pd._adjStartParaIndex = adjStart;
              pd._adjEndParaIndex = adjEnd;
              console.warn('[AIChatPane] 批注失败，降级到浅蓝色高亮:', commentErr);
            }
          }
        } catch (e) {
          console.warn('[AIChatPane] 标记删除段落失败:', e);
        }
      }
    },

    /**
     * 加载校对模式设置
     */
    async _loadProofreadMode() {
      if (this._proofreadModeLoadPromise) {
        return this._proofreadModeLoadPromise;
      }

      this._proofreadModeLoadPromise = (async () => {
        try {
          const data = await api.getSettings();
          if (data && data.proofreadMode) {
            settingsState.proofreadMode = data.proofreadMode;
            this._proofreadModeInitialized = true;
          }
        } catch (e) {
          console.warn('加载校对模式设置失败:', e);
        } finally {
          this._proofreadModeLoadPromise = null;
        }
      })();

      return this._proofreadModeLoadPromise;
    },

    /**
     * 获取当前校对模式（确保已加载）
     * @returns {Promise<'revision'|'redblue'>}
     */
    async _getProofreadMode() {
      if (!this._proofreadModeInitialized) {
        await this._loadProofreadMode();
      }
      return settingsState.proofreadMode === 'redblue' ? 'redblue' : 'revision';
    },

    /**
     * 清除指定段落范围的高亮
     * @param {number} startParaIndex - 起始段落索引 (0-based)
     * @param {number} endParaIndex - 结束段落索引 (0-based, 含)
     */
    _clearHighlightOnRange(startParaIndex, endParaIndex) {
      try {
        const doc = window.Application.ActiveDocument;
        if (!doc) {
          return;
        }
        const totalParas = doc.Paragraphs.Count;
        let endIdx = endParaIndex;
        if (endIdx === -1) {
          endIdx = totalParas - 1;
        }
        if (startParaIndex < 0 || startParaIndex >= totalParas || endIdx >= totalParas) {
          return;
        }
        const startPara = doc.Paragraphs.Item(startParaIndex + 1);
        const endPara = doc.Paragraphs.Item(endIdx + 1);
        const range = doc.Range(startPara.Range.Start, endPara.Range.End);
        range.Font.HighlightColorIndex = 0; // wdNoHighlight
      } catch (e) {
        console.warn('[AIChatPane] 清除高亮失败:', e);
      }
    },

    /**
     * 插入内容到 Word 文档
     */
    insertToWord(msg) {
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

          // 统一使用 JSON 中 AI 指定的 insertParaIndex 作为插入位置
          let insertParaIndex = null;
          if (jsonData.insertParaIndex !== null && jsonData.insertParaIndex !== undefined) {
            insertParaIndex = jsonData.insertParaIndex;
            if (insertParaIndex === -1) {
              console.log('插入到文档末尾');
            } else {
              console.log('插入到 AI 指定段落索引:', insertParaIndex);
            }
          } else {
            // 兼容旧数据：没有 insertParaIndex 时用光标位置
            console.log('无 insertParaIndex，回退到光标位置');
          }

          msg.docLengthBefore = doc.Content.End;
          console.log('记录插入前文档长度:', msg.docLengthBefore);

          const result = generateDocxFromJSON(jsonData, doc, insertParaIndex);

          if (result.success) {
            console.log('带格式的文档内容已成功插入');
            console.log(`实际插入范围: ${result.startPos} - ${result.endPos}`);

            msg.insertStartPos = result.startPos;
            msg.insertEndPos = result.endPos;
            console.log('记录插入范围用于撤销:', msg.insertStartPos, '-', msg.insertEndPos);

            // 批注将在 _addAllPendingComments 中统一添加
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

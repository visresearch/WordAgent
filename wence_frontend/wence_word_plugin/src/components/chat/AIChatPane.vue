<template>
  <div class="ai-chat-container">
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
      :current-selection="currentSelection"
      @update:mode="mode = $event"
      @update:selected-model="selectedModel = $event"
      @send="handleSend"
      @stop="stopGeneration"
      @add-selection="addSelectionManually"
      @clear-selection="clearSelection"
      @refresh-models="loadModels"
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
      currentSelection: null,
      currentSelectionRange: null,
      currentStreamCtrl: null,
      currentDocId: null,
      currentDocName: null,
      historyLoading: false,
      hasHistory: false,
      historyLoaded: false
    };
  },
  mounted() {
    this.loadModels();
    this.initDocumentAndLoadHistory();
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
     * 初始化文档标识并检查是否有历史记录
     */
    async initDocumentAndLoadHistory() {
      try {
        console.log('[初始化] 开始获取文档信息');
        const docInfo = this.getDocumentInfo();
        console.log('[初始化] 文档信息:', docInfo);
        if (docInfo) {
          this.currentDocId = docInfo.docId;
          this.currentDocName = docInfo.docName;
          console.log('[初始化] 已设置 currentDocId:', this.currentDocId);
          await this.checkHasHistory();
        } else {
          console.warn('[初始化] 未获取到文档信息');
        }
      } catch (e) {
        console.error('[初始化] 失败:', e);
      }
    },

    /**
     * 检查当前文档是否有历史聊天记录
     */
    async checkHasHistory() {
      if (!this.currentDocId) {
        this.hasHistory = false;
        return;
      }

      console.log('[检查历史] docId:', this.currentDocId);

      try {
        const result = await api.getChatHistory(this.currentDocId, { limit: 1 });
        console.log('[检查历史] 返回:', result);
        this.hasHistory = result.success && result.data?.messages && result.data.messages.length > 0;
        console.log('[检查历史] hasHistory:', this.hasHistory);
      } catch (e) {
        console.warn('检查历史记录失败:', e);
        this.hasHistory = false;
      }
    },

    /**
     * 点击显示历史记录
     */
    async loadAndShowHistory() {
      console.log('[显示历史] 点击按钮，当前 docId:', this.currentDocId);
      const docInfo = this.getDocumentInfo();
      if (docInfo) {
        this.currentDocId = docInfo.docId;
        this.currentDocName = docInfo.docName;
        console.log('[显示历史] 更新后的 docId:', this.currentDocId);
      }
      await this.loadChatHistory();
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
     * 加载当前文档的聊天历史
     */
    async loadChatHistory() {
      if (!this.currentDocId) {
        console.warn('[加载历史] 缺少 docId');
        return;
      }

      console.log('[加载历史] 开始加载', { docId: this.currentDocId, docName: this.currentDocName });

      this.historyLoading = true;
      try {
        const result = await api.getChatHistory(this.currentDocId, { limit: 200 });
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
     * 保存消息到后端
     */
    async saveMessageToHistory(role, content, documentJson = null, selectionContext = null, contentParts = null) {
      if (!this.currentDocId) {
        console.warn('[保存消息] 缺少 docId，无法保存');
        return;
      }

      console.log('[保存消息]', {
        docId: this.currentDocId,
        docName: this.currentDocName,
        role,
        contentLength: content.length
      });

      try {
        await api.saveMessage({
          docId: this.currentDocId,
          docName: this.currentDocName,
          role,
          content,
          documentJson,
          selectionContext,
          contentParts,
          model: this.selectedModel || 'auto',
          mode: this.mode
        });
        console.log('[保存消息] 成功');
      } catch (e) {
        console.warn('保存消息失败:', e);
      }
    },

    /**
     * 清空当前文档的聊天历史
     */
    async clearChatHistory() {
      if (!this.currentDocId) {
        this.messages = [];
        return;
      }

      try {
        const result = await api.clearChatHistory(this.currentDocId);
        if (result.success) {
          this.messages = [];
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
     * 处理添加的选区
     */
    handleSelectionAdd(selectionInfo) {
      console.log('[AIChatPane] 收到选区信息:', selectionInfo);

      this.currentSelection = {
        preview: selectionInfo.preview,
        startText: selectionInfo.startText,
        endText: selectionInfo.endText,
        charCount: selectionInfo.charCount,
        hasMore: selectionInfo.hasMore
      };

      this.currentSelectionRange = selectionInfo.range;

      console.log('[AIChatPane] 选区已设置，字符数:', selectionInfo.charCount, '范围:', selectionInfo.range);
    },

    /**
     * 清除当前选区
     */
    clearSelection() {
      this.currentSelection = null;
      this.currentSelectionRange = null;
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

      const retryRanges = this.currentSelectionRange ? [this.currentSelectionRange] : null;
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

      if (this.currentSelection && this.currentSelectionRange) {
        selectionContext = { ...this.currentSelection };
        documentRange = [this.currentSelectionRange];
        userMsgObj.selectionContext = selectionContext;
      }

      this.messages.push(userMsgObj);
      this.historyLoaded = true;

      this.clearSelection();

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

      if (data.type === 'status' && data.content) {
        msg.contentParts.push({
          type: 'status',
          content: data.content,
          loading: !!data.loading
        });
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
          this.insertToWord(msg, false);
        });

        this.scrollToBottom();
      } else if (data.error) {
        msg.content += `\n\n错误: ${data.error}`;
      }
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
</style>

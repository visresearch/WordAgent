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
      @toggle-thinking="toggleThinking"
    />
    <ChatInput
      :mode="mode"
      :selected-model="selectedModel"
      :available-models="availableModels"
      :models-loading="modelsLoading"
      :is-loading="isLoading"
      :selections="selections"
      @update:mode="mode = $event"
      @update:selected-model="selectedModel = $event"
      @send="handleSend"
      @stop="stopGeneration"
      @add-selection="addSelectionFromWord"
      @remove-selection="removeSelection"
    />
  </div>
</template>

<script>
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
      selectedModel: 'auto',
      availableModels: [
        { id: 'auto', name: 'Auto' },
        { id: 'gpt-4', name: 'GPT-4' },
        { id: 'gpt-3.5-turbo', name: 'GPT-3.5' }
      ],
      modelsLoading: false,
      messages: [],
      isLoading: false,
      selections: [],
      currentSessionId: null,
      currentSessionTitle: null,
      hasHistory: false,
      historyLoaded: false
    };
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
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
    },

    stopGeneration() {
      this.isLoading = false;
    },

    loadAndShowHistory() {
      // TODO: 后端集成后加载历史记录
      this.historyLoaded = true;
    },

    /**
     * 通过 Office.js Word API 获取用户当前选区文本
     */
    async addSelectionFromWord() {
      try {
        await Word.run(async (context) => {
          const selection = context.document.getSelection();
          selection.load('text');
          await context.sync();

          const text = (selection.text || '').trim();
          if (!text || text.length < 2) {
            return;
          }

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

    retryMessage(aiMessageIndex) {
      if (this.isLoading) return;

      let userMessageIndex = aiMessageIndex - 1;
      while (userMessageIndex >= 0 && this.messages[userMessageIndex].role !== 'user') {
        userMessageIndex--;
      }
      if (userMessageIndex < 0) return;

      const userMessage = this.messages[userMessageIndex].content;
      this.messages.splice(aiMessageIndex, 1);
      this.simulateAIResponse(userMessage);
    },

    handleSend(userMessage) {
      const userMsgObj = {
        role: 'user',
        content: userMessage
      };

      if (this.selections.length > 0) {
        userMsgObj.selectionContext = this.selections.map((s) => ({
          preview: s.preview,
          startText: s.startText,
          endText: s.endText,
          charCount: s.charCount
        }));
      }

      this.messages.push(userMsgObj);
      this.historyLoaded = true;
      this.selections = [];

      this.simulateAIResponse(userMessage);
    },

    /**
     * 模拟 AI 回复（仅 UI 展示用，未接入后端）
     */
    simulateAIResponse(userMessage) {
      this.isLoading = true;
      this.scrollToBottom();

      this.messages.push({
        role: 'assistant',
        content: '',
        contentParts: [],
        thinking: '',
        thinkingExpanded: true,
        thinkingStartTime: null,
        thinkingDuration: '',
        statusText: ''
      });

      const aiMsg = this.messages[this.messages.length - 1];

      // 模拟思考过程
      setTimeout(() => {
        aiMsg.thinking = '正在分析您的请求...';
        aiMsg.thinkingDuration = '2s';
        this.scrollToBottom();
      }, 500);

      // 模拟回复
      setTimeout(() => {
        aiMsg.thinkingExpanded = false;
        aiMsg.content = `这是对"${userMessage}"的模拟回复。\n\n后端服务尚未接入，当前仅展示界面效果。接入后端后，此处将显示真实的AI回复内容。`;
        aiMsg.contentParts = [
          { type: 'text', content: aiMsg.content }
        ];
        this.isLoading = false;
        this.scrollToBottom();
      }, 2000);
    },

    /**
     * 通过 Office.js 将内容插入到 Word 文档
     */
    async insertToWord(msg) {
      try {
        await Word.run(async (context) => {
          const body = context.document.body;
          body.insertText(msg.content, Word.InsertLocation.end);
          await context.sync();
        });
      } catch (error) {
        console.error('插入文档失败:', error);
      }
    }
  }
};
</script>

<style scoped>
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f7f8fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
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
</style>

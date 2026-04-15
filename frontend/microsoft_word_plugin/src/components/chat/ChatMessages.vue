<template>
  <div ref="messagesContainer" class="chat-messages">
    <!-- 显示历史记录按钮 -->
    <div v-if="hasHistory && !historyLoaded" class="history-hint" @click="$emit('load-history')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
      <span>显示历史聊天记录</span>
    </div>
    <!-- 空状态 -->
    <div v-if="messages.length === 0 && !isLoading" class="empty-state">
      <img class="empty-icon" src="/assets/robot.svg" alt="WenCe AI" />
      <div class="empty-text-container">
        <span class="empty-text">我能做什么</span>
        <a href="https://visresearch.github.io/WordAgent/" target="_blank" class="help-icon">
          <svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
            <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.5" />
            <path d="M8 12v-1M8 9V8a1.5 1.5 0 0 1 1-1.415A1.5 1.5 0 1 0 6.5 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
          </svg>
        </a>
      </div>
    </div>
    <!-- 消息列表 -->
    <div
      v-for="(msg, index) in messages"
      :key="index"
      :class="['message-wrapper', msg.role === 'user' ? 'user-wrapper' : 'ai-wrapper']"
    >
      <div :class="['message', msg.role === 'user' ? 'user-message' : 'ai-message']">
        <!-- 选区上下文 -->
        <div v-if="msg.selectionContext && msg.selectionContext.length" class="selection-context">
          <div class="context-header">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
              <path d="M14 1H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z" />
              <path d="M3 4h10v1H3V4zm0 3h10v1H3V7zm0 3h6v1H3v-1z" />
            </svg>
            <span>引用选区 ({{ msg.selectionContext.length }})</span>
          </div>
          <div v-for="(ctx, ctxIdx) in msg.selectionContext" :key="ctxIdx" class="context-item">
            <span class="context-text">{{ ctx.startText }} → {{ ctx.endText }}</span>
          </div>
        </div>
        <div class="message-content">
          <span
            v-if="msg.role === 'assistant' && !msg.content && !msg.thinking && !msg.statusText && !(msg.contentParts && msg.contentParts.length > 0) && isLoading"
            class="typing"
          >💭 AI正在准备中</span>
          <span v-if="msg.statusText" class="typing">{{ msg.statusText }}</span>
          <!-- Thinking 块 -->
          <div v-if="msg.thinking" class="thinking-block" :class="{ expanded: msg.thinkingExpanded }">
            <div class="thinking-header" @click="$emit('toggle-thinking', index)">
              <svg class="thinking-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
              <span class="thinking-label">{{ msg.thinkingDone ? '深度思考（已结束）' : '深度思考' }}</span>
              <svg class="thinking-arrow" :class="{ rotated: msg.thinkingExpanded }" width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 10.293L3.854 6.146a.5.5 0 1 1 .708-.707L8 8.879l3.438-3.44a.5.5 0 0 1 .708.708L8 10.293z" />
              </svg>
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-show="msg.thinkingExpanded" class="thinking-content markdown-body" v-html="renderMarkdown(msg.thinking)"></div>
          </div>
          <!-- 用户消息 -->
          <span v-else-if="msg.role === 'user'">{{ msg.content }}</span>
          <!-- AI 消息 contentParts -->
          <template v-else-if="msg.contentParts && msg.contentParts.length > 0">
            <div v-for="(part, partIndex) in msg.contentParts" :key="partIndex">
              <div v-if="part.type === 'status'" class="status-line">
                <span class="typing">{{ part.content }}</span>
                <span v-if="part.loading" class="loading-spinner"></span>
              </div>
              <!-- eslint-disable-next-line vue/no-v-html -->
              <div v-else-if="part.type === 'text'" class="markdown-body" v-html="renderMarkdown(part.content)"></div>
            </div>
          </template>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div v-else-if="msg.content" class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
        </div>
      </div>
      <!-- AI 消息操作按钮 -->
      <div v-if="msg.role === 'assistant' && msg.content && !isLoading" class="message-icon-actions">
        <div class="icon-btn-wrapper">
          <button class="icon-btn" @click="$emit('insert-to-word', msg)">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
              <path fill-rule="evenodd" d="M6 12.5a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-8a.5.5 0 0 0-.5.5v2a.5.5 0 0 1-1 0v-2A1.5 1.5 0 0 1 6.5 2h8A1.5 1.5 0 0 1 16 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 5 12.5v-2a.5.5 0 0 1 1 0v2z" />
              <path fill-rule="evenodd" d="M.146 8.354a.5.5 0 0 1 0-.708l3-3a.5.5 0 1 1 .708.708L1.707 7.5H10.5a.5.5 0 0 1 0 1H1.707l2.147 2.146a.5.5 0 0 1-.708.708l-3-3z" />
            </svg>
          </button>
          <span class="icon-tooltip">输出到文档</span>
        </div>
        <div class="icon-btn-wrapper">
          <button class="icon-btn" @click="$emit('copy', msg.content)">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
              <path d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zM10 4a1 1 0 0 0 1 1h2.5L10 1.5V4z" />
            </svg>
          </button>
          <span class="icon-tooltip">复制</span>
        </div>
        <div class="icon-btn-wrapper">
          <button class="icon-btn" @click="$emit('retry', index)">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
              <path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z" />
              <path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z" />
            </svg>
          </button>
          <span class="icon-tooltip">重试</span>
        </div>
      </div>
    </div>
    <!-- 图片右键菜单 -->
    <div v-if="imgMenuVisible" class="img-context-menu" :style="{ top: imgMenuY + 'px', left: imgMenuX + 'px' }">
      <div class="img-menu-item" @click="copyImage">复制图片</div>
      <div class="img-menu-item" @click="saveImage">保存图片</div>
    </div>
  </div>
</template>

<script>
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  typographer: true
});

export default {
  name: 'ChatMessages',
  props: {
    messages: { type: Array, required: true },
    isLoading: { type: Boolean, default: false },
    hasHistory: { type: Boolean, default: false },
    historyLoaded: { type: Boolean, default: false }
  },
  emits: ['load-history', 'insert-to-word', 'copy', 'retry', 'revert', 'toggle-thinking'],
  data() {
    return {
      imgMenuVisible: false,
      imgMenuX: 0,
      imgMenuY: 0,
      _contextImg: null,
    };
  },
  mounted() {
    this.$refs.messagesContainer?.addEventListener('contextmenu', this.handleImgContextMenu);
    document.addEventListener('click', this.hideImgMenu);
  },
  beforeUnmount() {
    this.$refs.messagesContainer?.removeEventListener('contextmenu', this.handleImgContextMenu);
    document.removeEventListener('click', this.hideImgMenu);
  },
  methods: {
    handleImgContextMenu(e) {
      const img = e.target.closest('img');
      if (!img || !img.closest('.markdown-body')) return;
      e.preventDefault();
      this._contextImg = img;
      const rect = this.$refs.messagesContainer.getBoundingClientRect();
      this.imgMenuX = e.clientX - rect.left;
      this.imgMenuY = e.clientY - rect.top;
      this.imgMenuVisible = true;
    },
    hideImgMenu() {
      this.imgMenuVisible = false;
    },
    async copyImage() {
      this.imgMenuVisible = false;
      const img = this._contextImg;
      if (!img) return;
      try {
        if (navigator.clipboard && typeof ClipboardItem !== 'undefined') {
          const canvas = document.createElement('canvas');
          canvas.width = img.naturalWidth;
          canvas.height = img.naturalHeight;
          canvas.getContext('2d').drawImage(img, 0, 0);
          const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
          await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
          return;
        }
      } catch (_) { /* fallback */ }
      try {
        const range = document.createRange();
        range.selectNode(img);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.execCommand('copy');
        sel.removeAllRanges();
      } catch (e) {
        console.error('复制图片失败:', e);
        alert('复制失败，请尝试右键 → 保存图片');
      }
    },
    saveImage() {
      this.imgMenuVisible = false;
      const img = this._contextImg;
      if (!img) return;
      const a = document.createElement('a');
      a.href = img.src;
      a.download = 'chart.png';
      a.click();
    },
    renderMarkdown(content) {
      if (!content) return '';
      return md.render(content);
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    }
  }
};
</script>

<style scoped>
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chat-messages::-webkit-scrollbar {
  width: 6px;
}
.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}
.chat-messages::-webkit-scrollbar-thumb {
  background: #c5cdd8;
  border-radius: 2px;
}

.history-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  margin-bottom: 4px;
  color: #666;
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s ease;
  user-select: none;
}
.history-hint:hover {
  color: #1a73e8;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  opacity: 0.5;
}
.empty-icon {
  width: 64px;
  height: 64px;
  color: #999;
}
.empty-text-container {
  display: flex;
  align-items: center;
  gap: 4px;
}
.empty-text {
  font-size: 14px;
  color: #999;
  font-weight: 500;
  user-select: none;
}
.help-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: #667eea;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
}
.help-icon:hover {
  color: #5568d3;
  transform: scale(1.15);
}
.help-icon svg {
  width: 100%;
  height: 100%;
}

/* Thinking block */
.thinking-block {
  margin-bottom: 8px;
  border-radius: 8px;
  background: linear-gradient(135deg, #f8f9fc 0%, #f0f4ff 100%);
  border: 1px solid #e0e6f6;
  overflow: hidden;
  transition: all 0.3s ease;
}
.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}
.thinking-header:hover {
  background: rgba(102, 126, 234, 0.08);
}
.thinking-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  color: #667eea;
  animation: pulse 2s ease-in-out infinite;
}
.thinking-block:not(.expanded) .thinking-icon {
  animation: none;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.thinking-label {
  font-size: 12px;
  font-weight: 500;
  color: #5a6378;
  flex: 1;
}
.thinking-duration {
  font-size: 11px;
  color: #8893a7;
  margin-right: 4px;
}
.thinking-arrow {
  color: #8893a7;
  transition: transform 0.3s ease;
}
.thinking-arrow.rotated {
  transform: rotate(180deg);
}
.thinking-content {
  padding: 0 12px 12px 40px;
  font-size: 12px;
  line-height: 1.6;
  color: #5a6378;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
  border-top: 1px solid #e8ecf4;
  padding-top: 10px;
}

/* Messages */
.message-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}
.user-wrapper {
  align-items: flex-end;
}
.ai-wrapper {
  align-items: flex-start;
}

.status-line {
  margin: 4px 0;
  padding: 2px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.loading-spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid #e0e0e0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.message {
  max-width: 90%;
  padding: 6px 8px;
  border-radius: 8px;
  line-height: 1.4;
  font-size: 12px;
}
.user-message {
  align-self: flex-end;
  background: #c7d1ff;
  color: #333;
  border-bottom-right-radius: 4px;
}
.ai-message {
  align-self: flex-start;
  background: transparent;
  color: #333;
  box-shadow: none;
  padding: 0;
  max-width: 100%;
}
.message-content {
  word-wrap: break-word;
}

/* Markdown styles */
.message-content :deep(.markdown-body) {
  font-size: 12px;
  line-height: 1.6;
}
.message-content :deep(.markdown-body) img {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  margin: 8px 0;
}
.message-content :deep(.markdown-body) p {
  margin: 0 0 8px 0;
}
.message-content :deep(.markdown-body) p:last-child {
  margin-bottom: 0;
}
.message-content :deep(.markdown-body) h1,
.message-content :deep(.markdown-body) h2,
.message-content :deep(.markdown-body) h3 {
  margin: 12px 0 8px 0;
  font-weight: 600;
  line-height: 1.3;
}
.message-content :deep(.markdown-body) h1 { font-size: 1.4em; }
.message-content :deep(.markdown-body) h2 { font-size: 1.25em; }
.message-content :deep(.markdown-body) h3 { font-size: 1.1em; }
.message-content :deep(.markdown-body) ul,
.message-content :deep(.markdown-body) ol {
  margin: 6px 0;
  padding-left: 24px;
}
.message-content :deep(.markdown-body) ul { list-style-type: disc; }
.message-content :deep(.markdown-body) ol { list-style-type: decimal; }
.message-content :deep(.markdown-body) li { margin: 4px 0; padding-left: 4px; }
.message-content :deep(.markdown-body) code {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 4px;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9em;
}
.message-content :deep(.markdown-body) pre {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}
.message-content :deep(.markdown-body) pre code {
  background: none;
  padding: 0;
  color: inherit;
  font-size: 11px;
}
.message-content :deep(.markdown-body) blockquote {
  margin: 8px 0;
  padding: 4px 12px;
  border-left: 3px solid #667eea;
  background: rgba(102, 126, 234, 0.08);
  color: #555;
}
.message-content :deep(.markdown-body) a {
  color: #667eea;
  text-decoration: none;
}
.message-content :deep(.markdown-body) a:hover {
  text-decoration: underline;
}
.message-content :deep(.markdown-body) table {
  border-collapse: collapse;
  margin: 8px 0;
  width: 100%;
}
.message-content :deep(.markdown-body) th,
.message-content :deep(.markdown-body) td {
  border: 1px solid #ddd;
  padding: 6px 8px;
  text-align: left;
}
.message-content :deep(.markdown-body) th {
  background: #f5f5f5;
  font-weight: 600;
}
.message-content :deep(.markdown-body) strong {
  font-weight: 700;
  color: #222;
}

/* Action icons */
.message-icon-actions {
  display: flex;
  flex-direction: row;
  gap: 2px;
}
.icon-btn-wrapper {
  position: relative;
}
.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: #999;
  transition: all 0.15s ease;
}
.icon-btn:hover {
  background: #f0f0f0;
  color: #333;
}
.icon-tooltip {
  position: absolute;
  left: 50%;
  bottom: 100%;
  transform: translateX(-50%);
  padding: 3px 6px;
  background: white;
  color: #333;
  font-size: 10px;
  border-radius: 4px;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s, visibility 0.2s;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border: 1px solid #e0e0e0;
  margin-bottom: 4px;
}
.icon-btn-wrapper:hover .icon-tooltip {
  opacity: 1;
  visibility: visible;
}

.typing {
  color: #888;
}

/* Selection context */
.selection-context {
  padding: 2px;
  margin-bottom: 8px;
  font-size: 11px;
}
.context-header {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #5566cc;
  font-weight: 500;
  margin-bottom: 4px;
}
.context-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #f7f8fa;
  border-radius: 4px;
  margin-top: 4px;
  font-size: 11px;
}
.context-text {
  color: #333;
  word-break: break-all;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.img-context-menu {
  position: absolute;
  z-index: 1000;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  padding: 4px 0;
  min-width: 100px;
}

.img-menu-item {
  padding: 6px 16px;
  font-size: 12px;
  color: #333;
  cursor: pointer;
  white-space: nowrap;
}

.img-menu-item:hover {
  background: #f0f0f0;
}
</style>

<template>
  <div ref="messagesContainer" class="chat-messages">
    <!-- 显示历史记录按钮 -->
    <div v-if="hasHistory && !historyLoaded" class="history-hint" @click="$emit('load-history')">
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
      <span>显示历史聊天记录</span>
    </div>
    <!-- 空状态显示 -->
    <div v-if="messages.length === 0 && !isLoading" class="empty-state">
      <svg class="empty-icon" viewBox="0 0 1144 1024" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M1080.018824 582.354824c-23.009882 129.505882-139.023059 227.930353-278.648471 227.930352H329.968941c-140.167529 0-256.602353-99.267765-278.889412-229.616941A47.164235 47.164235 0 0 1 0 533.684706l-0.060235-181.067294c0-26.021647 21.082353-47.164235 47.164235-47.164236C47.164235 153.419294 173.778824 30.117647 329.968941 30.117647h471.401412C957.620706 30.117647 1084.235294 153.419294 1084.235294 305.453176v6.625883a47.164235 47.164235 0 0 1 60.235294 45.296941v181.067294a47.164235 47.164235 0 0 1-64.451764 43.91153zM330.029176 144.865882c-91.136 0-164.984471 71.920941-164.98447 160.587294v229.496471c0 88.726588 73.848471 160.647529 165.044706 160.647529h471.341176c91.136 0 165.044706-71.920941 165.044706-160.647529v-229.496471c0-88.666353-73.908706-160.587294-165.044706-160.587294H329.968941zM400.685176 259.614118c39.092706 0 70.716235 31.623529 70.716236 70.656v122.819764a70.716235 70.716235 0 0 1-141.432471 0V330.270118c0-39.032471 31.683765-70.656 70.716235-70.656z m329.968942 0c39.092706 0 70.716235 31.623529 70.716235 70.656v122.819764a70.716235 70.716235 0 1 1-141.372235 0V330.270118c0-39.032471 31.623529-70.656 70.656-70.656zM420.502588 993.882353a137.697882 137.697882 0 0 1-137.637647-137.697882h565.669647a137.697882 137.697882 0 0 1-137.697882 137.697882h-290.334118z"
          fill="currentColor"
        />
      </svg>
      <div class="empty-text-container">
        <span class="empty-text">我能做什么</span>
        <a href="https://cmcblog.netlify.app/" target="_blank" class="help-icon">
          <svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
            <circle
              cx="8"
              cy="8"
              r="7"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
            />
            <path
              d="M8 12v-1M8 9V8a1.5 1.5 0 0 1 1-1.415A1.5 1.5 0 1 0 6.5 5"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
        </a>
      </div>
    </div>
    <!-- 消息容器：包含消息框和操作图标 -->
    <div
      v-for="(msg, index) in messages"
      :key="index"
      :class="['message-wrapper', msg.role === 'user' ? 'user-wrapper' : 'ai-wrapper']"
    >
      <div :class="['message', msg.role === 'user' ? 'user-message' : 'ai-message']">
        <!-- 显示选中内容上下文 -->
        <div v-if="msg.selectionContext" class="selection-context">
          <div class="context-header">
            <svg
              width="12"
              height="12"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path
                d="M14 1H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z"
              />
              <path d="M3 4h10v1H3V4zm0 3h10v1H3V7zm0 3h6v1H3v-1z" />
            </svg>
            <span>选中的内容</span>
          </div>
          <div class="context-preview">
            <span class="context-text">{{ msg.selectionContext.preview }}</span>
            <span v-if="msg.selectionContext.hasMore" class="context-more">...</span>
          </div>
          <div class="context-range">
            {{ msg.selectionContext.startText }} → {{ msg.selectionContext.endText }}
            <span class="context-stats">({{ msg.selectionContext.charCount }} 字符)</span>
          </div>
        </div>
        <div class="message-content">
          <span
            v-if="msg.role === 'assistant' && !msg.content && !msg.thinking && !msg.statusText && !(msg.contentParts && msg.contentParts.length > 0) && isLoading"
            class="typing"
          >💭 AI正在思考中</span>
          <!-- 状态提示文本 -->
          <span
            v-if="msg.statusText"
            class="typing"
          >{{ msg.statusText }}</span>
          <!-- Thinking 内容（深度思考过程） -->
          <div v-if="msg.thinking" class="thinking-block" :class="{ expanded: msg.thinkingExpanded }">
            <div class="thinking-header" @click="toggleThinking(index)">
              <svg
                class="thinking-icon"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
              <span class="thinking-label">深度思考</span>
              <span v-if="msg.thinkingDuration" class="thinking-duration">{{ msg.thinkingDuration }}</span>
              <svg
                class="thinking-arrow"
                :class="{ rotated: msg.thinkingExpanded }"
                width="12"
                height="12"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M8 10.293L3.854 6.146a.5.5 0 1 1 .708-.707L8 8.879l3.438-3.44a.5.5 0 0 1 .708.708L8 10.293z" />
              </svg>
            </div>
            <div v-show="msg.thinkingExpanded" class="thinking-content">
              {{ msg.thinking }}
            </div>
          </div>
          <!-- 用户消息直接显示文本 -->
          <span v-else-if="msg.role === 'user'">{{ msg.content }}</span>
          <!-- AI 消息使用 contentParts 渲染，区分 status 和 text -->
          <template v-else-if="msg.contentParts && msg.contentParts.length > 0">
            <div v-for="(part, partIndex) in msg.contentParts" :key="partIndex">
              <div v-if="part.type === 'status'" class="status-line">
                <span class="typing">{{ part.content }}</span>
                <span v-if="part.loading" class="loading-spinner"></span>
              </div>
              <div v-else-if="part.type === 'text'" class="markdown-body" v-html="renderMarkdown(part.content)"></div>
            </div>
          </template>
          <!-- 兼容旧的 content 字段 -->
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div v-else-if="msg.content" class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
        </div>
      </div>
      <!-- AI 消息的操作图标按钮（在消息框外下方） -->
      <div
        v-if="msg.role === 'assistant' && msg.content && !isLoading"
        class="message-icon-actions"
      >
        <div v-if="msg.documentJson" class="icon-btn-wrapper">
          <button class="icon-btn" @click="$emit('insert-to-word', msg, true)">
            <svg
              width="14"
              height="14"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M6 12.5a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-8a.5.5 0 0 0-.5.5v2a.5.5 0 0 1-1 0v-2A1.5 1.5 0 0 1 6.5 2h8A1.5 1.5 0 0 1 16 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 5 12.5v-2a.5.5 0 0 1 1 0v2z"
              />
              <path
                fill-rule="evenodd"
                d="M.146 8.354a.5.5 0 0 1 0-.708l3-3a.5.5 0 1 1 .708.708L1.707 7.5H10.5a.5.5 0 0 1 0 1H1.707l2.147 2.146a.5.5 0 0 1-.708.708l-3-3z"
              />
            </svg>
          </button>
          <span class="icon-tooltip">输出</span>
        </div>
        <div class="icon-btn-wrapper">
          <button class="icon-btn" @click="$emit('copy', msg.content)">
            <svg
              width="14"
              height="14"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path
                d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zM10 4a1 1 0 0 0 1 1h2.5L10 1.5V4z"
              />
            </svg>
          </button>
          <span class="icon-tooltip">复制</span>
        </div>
        <div class="icon-btn-wrapper">
          <button class="icon-btn" @click="$emit('retry', index)">
            <svg
              width="14"
              height="14"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path
                d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z"
              />
              <path
                fill-rule="evenodd"
                d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z"
              />
            </svg>
          </button>
          <span class="icon-tooltip">重试</span>
        </div>
        <div v-if="index > 0" class="icon-btn-wrapper">
          <button class="icon-btn" @click="$emit('revert', index)">
            <svg
              width="14"
              height="14"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path
                fill-rule="evenodd"
                d="M8 3a5 5 0 1 1-4.546 2.914.5.5 0 0 0-.908-.417A6 6 0 1 0 8 2v1z"
              />
              <path
                d="M8 4.466V.534a.25.25 0 0 0-.41-.192L5.23 2.308a.25.25 0 0 0 0 .384l2.36 1.966A.25.25 0 0 0 8 4.466z"
              />
            </svg>
          </button>
          <span class="icon-tooltip">撤消</span>
        </div>
      </div>
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
    messages: {
      type: Array,
      required: true
    },
    isLoading: {
      type: Boolean,
      default: false
    },
    hasHistory: {
      type: Boolean,
      default: false
    },
    historyLoaded: {
      type: Boolean,
      default: false
    }
  },
  emits: ['load-history', 'insert-to-word', 'copy', 'retry', 'revert', 'toggle-thinking'],
  methods: {
    /**
     * 渲染 Markdown 内容
     */
    renderMarkdown(content) {
      if (!content) {
        return '';
      }
      let cleaned = content.replace(/```json\s*```/g, '');
      return md.render(cleaned);
    },

    /**
     * 切换 thinking 内容的展开/收起状态
     */
    toggleThinking(index) {
      this.$emit('toggle-thinking', index);
    },

    /**
     * 滚动到底部
     */
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

/* 历史记录提示样式 */
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

.history-hint svg {
  flex-shrink: 0;
}

/* 空状态样式 */
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

/* Thinking 思考块样式 */
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
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 300px;
  overflow-y: auto;
  border-top: 1px solid #e8ecf4;
  margin-top: 0;
  padding-top: 10px;
}

.thinking-content::-webkit-scrollbar {
  width: 4px;
}

.thinking-content::-webkit-scrollbar-track {
  background: transparent;
}

.thinking-content::-webkit-scrollbar-thumb {
  background: #c5cdd8;
  border-radius: 2px;
}

/* 消息容器 */
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

/* Status 行样式 */
.status-line {
  margin: 4px 0;
  padding: 2px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-line .typing {
  display: inline;
}

/* 旋转加载圈圈 */
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
  to {
    transform: rotate(360deg);
  }
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

/* Markdown 渲染样式 - 使用 :deep() 穿透 scoped 限制 */
.message-content :deep(.markdown-body) {
  font-size: 12px;
  line-height: 1.6;
}

.message-content :deep(.markdown-body) p {
  margin: 0 0 8px 0;
}

.message-content :deep(.markdown-body) p:last-child {
  margin-bottom: 0;
}

.message-content :deep(.markdown-body) h1,
.message-content :deep(.markdown-body) h2,
.message-content :deep(.markdown-body) h3,
.message-content :deep(.markdown-body) h4,
.message-content :deep(.markdown-body) h5,
.message-content :deep(.markdown-body) h6 {
  margin: 12px 0 8px 0;
  font-weight: 600;
  line-height: 1.3;
}

.message-content :deep(.markdown-body) h1 {
  font-size: 1.4em;
}
.message-content :deep(.markdown-body) h2 {
  font-size: 1.25em;
}
.message-content :deep(.markdown-body) h3 {
  font-size: 1.1em;
}
.message-content :deep(.markdown-body) h4,
.message-content :deep(.markdown-body) h5,
.message-content :deep(.markdown-body) h6 {
  font-size: 1em;
}

.message-content :deep(.markdown-body) ul,
.message-content :deep(.markdown-body) ol {
  margin: 6px 0;
  padding-left: 24px;
  list-style-position: outside;
}

.message-content :deep(.markdown-body) ul {
  list-style-type: disc;
}

.message-content :deep(.markdown-body) ol {
  list-style-type: decimal;
}

.message-content :deep(.markdown-body) li {
  margin: 4px 0;
  padding-left: 4px;
}

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
  line-height: 1.4;
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

.message-content :deep(.markdown-body) hr {
  border: none;
  border-top: 1px solid #ddd;
  margin: 12px 0;
}

.message-content :deep(.markdown-body) strong {
  font-weight: 700;
  color: #222;
}

.message-content :deep(.markdown-body) em {
  font-style: italic;
}

/* AI 消息外部图标按钮 */
.message-icon-actions {
  display: flex;
  flex-direction: row;
  gap: 2px;
  margin-left: 0;
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

.icon-btn svg {
  width: 14px;
  height: 14px;
}

/* 图标按钮的 tooltip */
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
  transition:
    opacity 0.2s,
    visibility 0.2s;
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

/* 选中内容上下文样式 */
.selection-context {
  background: #dce4ff;
  border: 1px solid #c5d3ff;
  border-radius: 6px;
  padding: 8px;
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

.context-preview {
  background: white;
  border-radius: 4px;
  padding: 6px 8px;
  margin-bottom: 4px;
  color: #333;
  line-height: 1.4;
  max-height: 60px;
  overflow: hidden;
}

.context-text {
  word-break: break-all;
}

.context-more {
  color: #999;
}

.context-range {
  color: #888;
  font-size: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.context-stats {
  color: #999;
  margin-left: auto;
}
</style>

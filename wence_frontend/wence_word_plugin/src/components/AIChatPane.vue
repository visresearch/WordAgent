<template>
  <div class="ai-chat-container">
    <div ref="messagesContainer" class="chat-messages">
      <!-- 显示历史记录按钮 -->
      <div v-if="hasHistory && !historyLoaded" class="history-hint" @click="loadAndShowHistory">
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
          <path d="M1080.018824 582.354824c-23.009882 129.505882-139.023059 227.930353-278.648471 227.930352H329.968941c-140.167529 0-256.602353-99.267765-278.889412-229.616941A47.164235 47.164235 0 0 1 0 533.684706l-0.060235-181.067294c0-26.021647 21.082353-47.164235 47.164235-47.164236C47.164235 153.419294 173.778824 30.117647 329.968941 30.117647h471.401412C957.620706 30.117647 1084.235294 153.419294 1084.235294 305.453176v6.625883a47.164235 47.164235 0 0 1 60.235294 45.296941v181.067294a47.164235 47.164235 0 0 1-64.451764 43.91153zM330.029176 144.865882c-91.136 0-164.984471 71.920941-164.98447 160.587294v229.496471c0 88.726588 73.848471 160.647529 165.044706 160.647529h471.341176c91.136 0 165.044706-71.920941 165.044706-160.647529v-229.496471c0-88.666353-73.908706-160.587294-165.044706-160.587294H329.968941zM400.685176 259.614118c39.092706 0 70.716235 31.623529 70.716236 70.656v122.819764a70.716235 70.716235 0 0 1-141.432471 0V330.270118c0-39.032471 31.683765-70.656 70.716235-70.656z m329.968942 0c39.092706 0 70.716235 31.623529 70.716235 70.656v122.819764a70.716235 70.716235 0 1 1-141.372235 0V330.270118c0-39.032471 31.623529-70.656 70.656-70.656zM420.502588 993.882353a137.697882 137.697882 0 0 1-137.637647-137.697882h565.669647a137.697882 137.697882 0 0 1-137.697882 137.697882h-290.334118z" fill="currentColor" />
        </svg>
        <span class="empty-text">我能做什么？</span>
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
                <path d="M14 1H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z" />
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
            <span v-if="msg.role === 'assistant' && !msg.content && isLoading" class="typing">AI正在思考中...</span>
            <!-- 用户消息直接显示文本 -->
            <span v-else-if="msg.role === 'user'">{{ msg.content }}</span>
            <!-- AI 消息使用 Markdown 渲染 -->
            <div v-else class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>
        <!-- AI 消息的操作图标按钮（在消息框外下方） -->
        <div v-if="msg.role === 'assistant' && msg.content && !isLoading" class="message-icon-actions">
          <div v-if="msg.documentJson" class="icon-btn-wrapper">
            <button class="icon-btn" @click="insertToWord(msg)">
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zM10 4a1 1 0 0 0 1 1h2.5L10 1.5V4z" />
              </svg>
            </button>
            <span class="icon-tooltip">输出文档</span>
          </div>
          <div class="icon-btn-wrapper">
            <button class="icon-btn" @click="retryMessage(index)">
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z" />
                <path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z" />
              </svg>
            </button>
            <span class="icon-tooltip">重试</span>
          </div>
          <div v-if="index > 0" class="icon-btn-wrapper">
            <button class="icon-btn" @click="revertToMessage(index)">
              <svg
                width="14"
                height="14"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path fill-rule="evenodd" d="M8 3a5 5 0 1 1-4.546 2.914.5.5 0 0 0-.908-.417A6 6 0 1 0 8 2v1z" />
                <path d="M8 4.466V.534a.25.25 0 0 0-.41-.192L5.23 2.308a.25.25 0 0 0 0 .384l2.36 1.966A.25.25 0 0 0 8 4.466z" />
              </svg>
            </button>
            <span class="icon-tooltip">还原</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 当前选中内容预览 -->
    <div v-if="currentSelection" class="current-selection-bar">
      <div class="selection-bar-content">
        <div class="selection-bar-icon">
          <svg
            width="14"
            height="14"
            viewBox="0 0 16 16"
            fill="currentColor"
          >
            <path d="M14 1H2a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z" />
            <path d="M3 4h10v1H3V4zm0 3h10v1H3V7zm0 3h6v1H3v-1z" />
          </svg>
        </div>
        <div class="selection-bar-info">
          <span class="selection-bar-preview">{{ currentSelection.preview }}</span>
          <span class="selection-bar-range">{{ currentSelection.startText }} → {{ currentSelection.endText }}</span>
        </div>
        <button class="selection-bar-clear" title="清除选区" @click="clearSelection">
          <svg
            width="10"
            height="10"
            viewBox="0 0 16 16"
            fill="currentColor"
          >
            <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z" />
          </svg>
        </button>
      </div>
    </div>

    <div class="chat-input-area">
      <div class="input-container">
        <textarea 
          ref="chatInput"
          v-model="inputText" 
          placeholder="描述下一步要构建的内容"
          class="chat-input"
          rows="1"
          @keydown.enter.exact.prevent="sendMessage"
          @input="autoResize"
        ></textarea>
        <div class="input-toolbar">
          <div class="toolbar-left">
            <!-- 模式选择 -->
            <div class="custom-select" :class="{ open: modeDropdownOpen }">
              <div class="select-trigger" @click="toggleModeDropdown">
                <span>{{ mode === 'agent' ? 'Agent' : 'Ask' }}</span>
                <svg
                  class="select-arrow"
                  width="8"
                  height="8"
                  viewBox="0 0 12 12"
                >
                  <path
                    d="M3 4.5L6 7.5L9 4.5"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    fill="none"
                  />
                </svg>
              </div>
              <div class="select-dropdown">
                <div 
                  class="select-option" 
                  :class="{ active: mode === 'agent' }"
                  @click="selectMode('agent')"
                >
                  Agent
                </div>
                <div 
                  class="select-option" 
                  :class="{ active: mode === 'ask' }"
                  @click="selectMode('ask')"
                >
                  Ask
                </div>
              </div>
            </div>
            
            <!-- 模型选择 -->
            <div class="custom-select" :class="{ open: modelDropdownOpen, disabled: modelsLoading }">
              <div class="select-trigger" @click="toggleModelDropdown">
                <span v-if="modelsLoading">加载中...</span>
                <span v-else>{{ selectedModelName }}</span>
                <svg
                  class="select-arrow"
                  width="8"
                  height="8"
                  viewBox="0 0 12 12"
                >
                  <path
                    d="M3 4.5L6 7.5L9 4.5"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    fill="none"
                  />
                </svg>
              </div>
              <div class="select-dropdown model-dropdown">
                <div 
                  v-for="model in availableModels"
                  :key="model.id"
                  class="select-option"
                  :class="{ active: selectedModel === model.id }"
                  @click="selectModel(model.id)"
                >
                  {{ model.name }}
                </div>
              </div>
            </div>
          </div>
          <div class="toolbar-right">
            <div class="btn-wrapper">
              <button 
                class="setting-btn" 
                @click="openSetting"
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <path d="M12 15a3 3 0 100-6 3 3 0 000 6z" stroke="currentColor" stroke-width="2" />
                  <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09a1.65 1.65 0 00-1.08-1.51 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09a1.65 1.65 0 001.51-1.08 1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06a1.65 1.65 0 001.82.33h.08a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82v.08a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" stroke="currentColor" stroke-width="2" />
                </svg>
              </button>
              <span class="tooltip">设置</span>
            </div>
            <div class="btn-wrapper">
              <button 
                v-if="!isLoading"
                class="send-btn" 
                :disabled="!inputText.trim()" 
                @click="sendMessage"
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 16 16"
                  fill="none"
                >
                  <path
                    d="M1 8L15 1L8 15L7 9L1 8Z"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linejoin="round"
                  />
                </svg>
              </button>
              <button 
                v-else
                class="stop-btn" 
                @click="stopGeneration"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 16 16"
                  fill="none"
                >
                  <circle
                    cx="8"
                    cy="8"
                    r="7"
                    stroke="currentColor"
                    stroke-width="1.5"
                    fill="none"
                  />
                  <rect
                    x="5"
                    y="5"
                    width="6"
                    height="6"
                    rx="0.5"
                    fill="currentColor"
                  />
                </svg>
              </button>
              <span class="tooltip">{{ isLoading ? '终止' : '发送' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { parseDocxToJSON, generateDocxFromJSON } from './js/docxJsonConverter.js';
import api from './js/api.js';
import MarkdownIt from 'markdown-it';

// 初始化 markdown-it 实例
const md = new MarkdownIt({
  html: false,        // 禁用 HTML 标签（安全考虑）
  breaks: true,       // 把\n转换为<br>
  linkify: true,      // 自动识别链接
  typographer: true   // 启用排版优化
});

export default {
  name: 'AIChatPane',
  data() {
    return {
      inputText: '',
      mode: 'agent',
      selectedModel: '',
      availableModels: [],  // 可用模型列表
      modelsLoading: false,  // 模型加载状态
      messages: [],
      isLoading: false,
      lastReadJSON: null,  // 存储上次读取的文档JSON
      currentSelection: null,  // 当前选中的内容信息
      currentSelectionJSON: null,  // 当前选中内容的完整JSON
      selectionCheckInterval: null,  // 选区检查定时器
      currentStreamCtrl: null,  // 当前流式请求控制器
      currentDocId: null,  // 当前文档的唯一标识符
      currentDocName: null,  // 当前文档名称
      historyLoading: false,  // 历史记录加载状态
      hasHistory: false,  // 是否有历史记录可加载
      historyLoaded: false,  // 是否已加载历史记录
      modeDropdownOpen: false,  // 模式下拉框状态
      modelDropdownOpen: false  // 模型下拉框状态
    };
  },
  computed: {
    selectedModelName() {
      const model = this.availableModels.find(m => m.id === this.selectedModel);
      return model ? model.name : '选择模型';
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.autoResize();
    });
    // 启动选区监听
    this.startSelectionWatch();
    // 页面加载时获取模型列表
    this.loadModels();
    // 初始化文档标识并加载历史
    this.initDocumentAndLoadHistory();
    // 点击其他地方关闭下拉框
    document.addEventListener('click', this.closeDropdowns);
  },
  beforeUnmount() {
    // 清理定时器
    this.stopSelectionWatch();
    // 移除点击监听
    document.removeEventListener('click', this.closeDropdowns);
  },
  methods: {
    /**
     * 渲染 Markdown 内容
     */
    renderMarkdown(content) {
      if (!content) {
        return '';
      }
      // 去除空的 ```json 代码块（防止出现空黑框）
      let cleaned = content.replace(/```json\s*```/g, '');
      return md.render(cleaned);
    },
    
    /**
     * 重试生成 - 重新发送上一条用户消息
     */
    async retryMessage(aiMessageIndex) {
      if (this.isLoading) {
        return;
      }
      
      // 找到这条 AI 消息对应的用户消息（上一条）
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
      const selectionContext = userMsg.selectionContext || null;
      
      // 删除当前 AI 消息
      this.messages.splice(aiMessageIndex, 1);
      
      // 重新发送请求
      this.isLoading = true;
      this.scrollToBottom();
      
      // 创建新的 AI 消息占位
      const newAiMessageIndex = this.messages.length;
      this.messages.push({
        role: 'assistant',
        content: '',
        documentJson: null
      });
      
      // 用于检测并过滤 JSON 输出
      let jsonDetected = false;
      
      // 使用 api.js 封装的流式接口
      const streamCtrl = api.chatStream(userMessage, {
        mode: this.mode,
        model: this.selectedModel || 'auto',
        documentJson: this.currentSelectionJSON,
        history: this.messages.slice(0, -1).slice(-10),
        
        onMessage: (data) => {
          if (data.type === 'text' && data.content) {
            if (jsonDetected) {
              return;
            }
            
            const content = data.content;
            const currentContent = this.messages[newAiMessageIndex].content;
            const combined = currentContent + content;
            
            // 检测 JSON 开始的多种模式
            if (content.includes('{"') || content.includes('{\n') || content.includes('"paragraphs"') || content.includes('"text":')) {
              jsonDetected = true;
              console.log('[Filter] 检测到 JSON 输出，停止显示');
              return;
            }
            
            if (combined.trim().startsWith('{') && (combined.includes('"paragraphs"') || combined.includes('"text"'))) {
              jsonDetected = true;
              console.log('[Filter] 检测到累积内容为 JSON，停止显示');
              return;
            }
            
            this.messages[newAiMessageIndex].content += content;
            this.scrollToBottom();
          } else if (data.type === 'json' && data.content) {
            this.messages[newAiMessageIndex].documentJson = data.content;
            // 移除"正在生成文档"的临时提示
            const currentContent = this.messages[newAiMessageIndex].content;
            if (currentContent.includes('⏳ 正在生成文档...')) {
              this.messages[newAiMessageIndex].content = currentContent.replace(/\n*⏳ 正在生成文档\.\.\./, '');
            }
            this.scrollToBottom();
          }
        },
        
        onError: (error) => {
          console.error('重试请求失败:', error);
          this.messages[newAiMessageIndex].content = `网络错误：${error.message}`;
        },
        
        onComplete: () => {
          this.isLoading = false;
          this.scrollToBottom();
          
          // 保存新的 AI 回复到历史
          const aiMsg = this.messages[newAiMessageIndex];
          if (aiMsg.content) {
            this.saveMessageToHistory('assistant', aiMsg.content, aiMsg.documentJson, null);
          }
        }
      });
      
      this.currentStreamCtrl = streamCtrl;
    },
    
    /**
     * 还原到某条消息 - 删除该消息之后的所有消息
     */
    async revertToMessage(messageIndex) {
      if (this.isLoading) {
        return;
      }
      
      // 删除该消息之后的所有消息
      this.messages = this.messages.slice(0, messageIndex + 1);
      
      // 注意：这里只是前端删除，历史记录保留在后端
      // 如果需要同步删除后端记录，需要额外的 API 支持
    },
    
    /**
     * 切换模式下拉框
     */
    toggleModeDropdown(e) {
      e.stopPropagation();
      this.modelDropdownOpen = false;
      this.modeDropdownOpen = !this.modeDropdownOpen;
    },
    
    /**
     * 切换模型下拉框
     */
    toggleModelDropdown(e) {
      if (this.modelsLoading) {
        return;
      }
      e.stopPropagation();
      this.modeDropdownOpen = false;
      this.modelDropdownOpen = !this.modelDropdownOpen;
    },
    
    /**
     * 选择模式
     */
    selectMode(value) {
      this.mode = value;
      this.modeDropdownOpen = false;
    },
    
    /**
     * 选择模型
     */
    selectModel(id) {
      this.selectedModel = id;
      this.modelDropdownOpen = false;
    },
    
    /**
     * 关闭所有下拉框
     */
    closeDropdowns() {
      this.modeDropdownOpen = false;
      this.modelDropdownOpen = false;
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
        // 获取当前文档信息
        const docInfo = this.getDocumentInfo();
        if (docInfo) {
          this.currentDocId = docInfo.docId;
          this.currentDocName = docInfo.docName;
          // 检查是否有历史记录（只获取1条来判断）
          await this.checkHasHistory();
        }
      } catch (e) {
        console.warn('初始化文档信息失败:', e);
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
      
      try {
        const result = await api.getChatHistory(this.currentDocId, { limit: 1 });
        this.hasHistory = result.success && result.data?.messages && result.data.messages.length > 0;
      } catch (e) {
        console.warn('检查历史记录失败:', e);
        this.hasHistory = false;
      }
    },
    
    /**
     * 点击显示历史记录
     */
    async loadAndShowHistory() {
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
        
        // 使用文档的完整路径作为唯一标识
        // 如果是未保存的文档，使用文档名称 + 创建时间
        const fullPath = doc.FullName || '';
        const docName = doc.Name || 'Untitled';
        
        let docId;
        if (fullPath && fullPath !== docName) {
          // 已保存的文档，使用完整路径的 hash
          docId = this.hashString(fullPath);
        } else {
          // 未保存的文档，使用名称 + 时间戳（存储在本地）
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
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
      }
      return 'doc_' + Math.abs(hash).toString(36);
    },
    
    /**
     * 加载当前文档的聊天历史
     */
    async loadChatHistory() {
      if (!this.currentDocId) {
        return;
      }
      
      this.historyLoading = true;
      try {
        const result = await api.getChatHistory(this.currentDocId, { limit: 50 });
        if (result.success && result.data?.messages) {
          // 转换后端格式为前端格式
          this.messages = result.data.messages.map(msg => ({
            role: msg.role,
            content: msg.content,
            documentJson: msg.documentJson || null,
            selectionContext: msg.selectionContext || null
          }));
          this.historyLoaded = true;
          this.scrollToBottom();
        }
      } catch (e) {
        console.warn('加载历史记录失败:', e);
      }
      this.historyLoading = false;
    },
    
    /**
     * 保存消息到后端
     */
    async saveMessageToHistory(role, content, documentJson = null, selectionContext = null) {
      if (!this.currentDocId) {
        return;
      }
      
      try {
        await api.saveMessage({
          docId: this.currentDocId,
          docName: this.currentDocName,
          role,
          content,
          documentJson,
          selectionContext,
          model: this.selectedModel || 'auto',
          mode: this.mode
        });
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
          this.selectedModel = 'auto';
        } else {
          console.warn('获取模型列表失败:', result.error);
          // 请求失败显示 Auto
          this.availableModels = [{ id: 'auto', name: 'Auto' }];
          this.selectedModel = 'auto';
        }
      } catch (error) {
        console.error('加载模型列表失败:', error);
        // 请求失败显示 Auto
        this.availableModels = [{ id: 'auto', name: 'Auto' }];
        this.selectedModel = 'auto';
      }
      this.modelsLoading = false;
    },
    
    /**
     * 开始监听Word选区变化
     */
    startSelectionWatch() {
      // 每500ms检查一次选区
      this.selectionCheckInterval = setInterval(() => {
        this.updateCurrentSelection();
      }, 500);
    },
    
    /**
     * 停止监听选区
     */
    stopSelectionWatch() {
      if (this.selectionCheckInterval) {
        clearInterval(this.selectionCheckInterval);
        this.selectionCheckInterval = null;
      }
    },
    
    /**
     * 更新当前选区信息
     */
    updateCurrentSelection() {
      try {
        const selection = window.Application?.Selection;
        if (!selection) {
          this.currentSelection = null;
          this.currentSelectionJSON = null;
          return;
        }
        
        const range = selection.Range;
        if (!range) {
          this.currentSelection = null;
          this.currentSelectionJSON = null;
          return;
        }
        
        const text = range.Text || '';
        const cleanedText = text.replace(/[\r\n\u0007\f]/g, ' ').trim();
        
        // 如果没有选中内容或只选了一个字符（光标）
        if (!cleanedText || cleanedText.length < 2) {
          this.currentSelection = null;
          this.currentSelectionJSON = null;
          return;
        }
        
        // 解析选中内容为JSON
        const jsonData = parseDocxToJSON(range);
        if (jsonData.error) {
          console.warn('解析选区失败:', jsonData.error);
          return;
        }
        
        this.currentSelectionJSON = jsonData;
        
        // 生成预览信息
        const maxPreviewLen = 50;
        let preview = cleanedText;
        let hasMore = false;
        
        if (preview.length > maxPreviewLen) {
          preview = preview.substring(0, maxPreviewLen);
          hasMore = true;
        }
        
        // 获取开始和结束文字
        const startText = cleanedText.substring(0, Math.min(10, cleanedText.length));
        const endText = cleanedText.length > 10 
          ? cleanedText.substring(cleanedText.length - 10) 
          : cleanedText;
        
        this.currentSelection = {
          preview: preview + (hasMore ? '...' : ''),
          startText: startText + (cleanedText.length > 10 ? '...' : ''),
          endText: (cleanedText.length > 20 ? '...' : '') + endText,
          charCount: cleanedText.length,
          hasMore
        };
        
      } catch (e) {
        console.warn('获取选区信息失败:', e);
        this.currentSelection = null;
        this.currentSelectionJSON = null;
      }
    },
    
    /**
     * 清除当前选区
     */
    clearSelection() {
      this.currentSelection = null;
      this.currentSelectionJSON = null;
      // 尝试取消Word中的选区
      try {
        const selection = window.Application?.Selection;
        if (selection) {
          selection.Collapse(1); // wdCollapseStart
        }
      } catch (e) {
        console.warn('取消选区失败:', e);
      }
    },
    
    autoResize() {
      const textarea = this.$refs.chatInput;
      if (textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
      }
    },
    async sendMessage() {
      if (!this.inputText.trim() || this.isLoading) {
        return;
      }

      const userMessage = this.inputText.trim();
      
      // 创建用户消息对象
      const userMsgObj = {
        role: 'user',
        content: userMessage
      };
      
      // 如果有选中的内容，添加选区上下文
      let selectionContext = null;
      let documentJson = null;
      
      if (this.currentSelection && this.currentSelectionJSON) {
        selectionContext = { ...this.currentSelection };
        documentJson = this.currentSelectionJSON;
        userMsgObj.selectionContext = selectionContext;
      }
      
      this.messages.push(userMsgObj);
      this.inputText = '';
      this.historyLoaded = true;  // 用户开始发消息，隐藏历史提示
      this.$nextTick(() => {
        this.autoResize();
      });

      // 保存用户消息到历史
      this.saveMessageToHistory('user', userMessage, null, selectionContext);

      this.isLoading = true;
      this.scrollToBottom();
      
      // 创建 AI 消息占位，记录其索引
      const aiMessageIndex = this.messages.length;
      this.messages.push({
        role: 'assistant',
        content: '',
        documentJson: null  // 保存文档 JSON 数据
      });
      
      // 用于检测并过滤 JSON 输出
      let jsonDetected = false;
      
      // 使用 api.js 封装的流式接口
      const streamCtrl = api.chatStream(userMessage, {
        mode: this.mode,
        model: this.selectedModel || 'auto',
        documentJson: documentJson,
        history: this.messages.slice(0, -1).slice(-10),  // 排除刚添加的空消息
        
        onMessage: (data) => {
          if (data.type === 'text' && data.content) {
            // 一旦检测到 JSON，后续所有文本都跳过
            if (jsonDetected) {
              return;
            }
            
            const content = data.content;
            // 检测当前内容或累积内容是否包含 JSON 结构
            const currentContent = this.messages[aiMessageIndex].content;
            const combined = currentContent + content;
            
            // 检测 JSON 开始的多种模式
            if (content.includes('{"') || content.includes('{\n') || content.includes('{ \n') || content.includes('"paragraphs"') || content.includes('"text":')) {
              // 检测到 JSON 内容，停止显示
              jsonDetected = true;
              console.log('[Filter] 检测到 JSON 输出，停止显示后续内容');
              return;
            }
            
            // 检测是否是 JSON 的开头
            if (combined.trim().startsWith('{') && (combined.includes('"paragraphs"') || combined.includes('"text"'))) {
              jsonDetected = true;
              console.log('[Filter] 检测到累积内容为 JSON，停止显示');
              return;
            }
            
            this.messages[aiMessageIndex].content += content;
            this.scrollToBottom();
          } else if (data.type === 'json' && data.content) {
            // JSON 数据：保存用于文档转换
            this.messages[aiMessageIndex].documentJson = data.content;
            // 移除"正在生成文档"的临时提示
            const currentContent = this.messages[aiMessageIndex].content;
            if (currentContent.includes('⏳ 正在生成文档...')) {
              this.messages[aiMessageIndex].content = currentContent.replace(/\n*⏳ 正在生成文档\.\.\./, '');
            }
            this.scrollToBottom();
          } else if (data.content && typeof data.content === 'string') {
            // 兼容旧格式（没有 type 字段），但只接受字符串
            if (!jsonDetected) {
              this.messages[aiMessageIndex].content += data.content;
              this.scrollToBottom();
            }
          } else if (data.error) {
            this.messages[aiMessageIndex].content += `\n\n错误: ${data.error}`;
          }
        },
        
        onError: (error) => {
          console.error('发送请求失败:', error);
          this.messages[aiMessageIndex].content = `网络错误：${error.message}。请确保后端服务运行在 localhost:3880`;
        },
        
        onComplete: () => {
          // 清除已使用的选区
          if (documentJson) {
            this.clearSelection();
          }
          this.isLoading = false;
          this.scrollToBottom();
          
          // 保存 AI 回复到历史
          const aiMsg = this.messages[aiMessageIndex];
          if (aiMsg.content) {
            this.saveMessageToHistory('assistant', aiMsg.content, aiMsg.documentJson, null);
          }
        }
      });
      
      // 保存控制器以便需要时中断请求
      this.currentStreamCtrl = streamCtrl;
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer;
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    },
    insertToWord(msg) {
      try {
        // 获取当前活动文档
        const doc = window.Application.ActiveDocument;
        if (!doc) {
          alert('请先打开一个Word文档');
          return;
        }
        
        // 优先使用已保存的 documentJson
        let jsonData = msg.documentJson || null;
        const content = msg.content || '';
        
        // 如果没有预存的 JSON，尝试从内容解析
        if (!jsonData) {
          // 检查是否是 JSON 或包含 JSON 代码块
          if (content.includes('```json')) {
            // 提取 JSON 代码块
            const jsonMatch = content.match(/```json\s*([\s\S]*?)\s*```/);
            if (jsonMatch) {
              try {
                jsonData = JSON.parse(jsonMatch[1]);
              } catch (e) {
                console.log('JSON 代码块解析失败，使用纯文本模式');
              }
            }
          } else if (content.trim().startsWith('{') && content.trim().endsWith('}')) {
            // 尝试直接解析 JSON
            try {
              jsonData = JSON.parse(content);
            } catch (e) {
              console.log('不是有效 JSON，使用纯文本模式');
            }
          }
        }
        
        // 如果是有效的文档 JSON，使用 generateDocxFromJSON 生成
        if (jsonData && (jsonData.paragraphs || jsonData.tables)) {
          console.log('检测到文档 JSON，使用格式化输出');
          
          // 在当前光标位置插入
          const selection = window.Application.Selection;
          const insertPos = selection.Range.Start;
          
          // 使用导入的 generateDocxFromJSON 生成文档
          const result = generateDocxFromJSON(jsonData, doc);
          
          if (result.success) {
            console.log('带格式的文档内容已成功插入');
          } else {
            console.error('生成文档失败:', result.error);
            // 回退到纯文本插入
            this.insertPlainText(content);
          }
        } else {
          // 纯文本插入
          this.insertPlainText(content);
        }

      } catch (error) {
        console.error('插入文本失败:', error);
        alert('插入失败，请确保已打开Word文档');
      }
    },
    
    /**
     * 插入纯文本（作为后备方案）
     */
    insertPlainText(content) {
      try {
        const selection = window.Application.Selection;
        
        // 清理可能的 JSON 代码块标记
        let cleanContent = content;
        if (content.includes('```json')) {
          // 如果包含 JSON 代码块但解析失败，提取其中的文本
          cleanContent = content.replace(/```json\s*/g, '').replace(/```/g, '');
        }
        
        // 在当前光标位置插入文本
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
    },
    openSetting() {
      // 调用ribbon中的设置面板打开逻辑
      try {
        let tsId = window.Application.PluginStorage.getItem('setting_taskpane_id');
        if (!tsId) {
          const baseUrl = window.location.origin + window.location.pathname.replace(/\/[^/]*$/, '');
          let tskpane = window.Application.CreateTaskPane(baseUrl + '/#/setting');
          let id = tskpane.ID;
          window.Application.PluginStorage.setItem('setting_taskpane_id', id);
          tskpane.DockPosition = window.Application.Enum.msoCTPDockPositionRight;
          tskpane.Width = 350;
          tskpane.Visible = true;
        } else {
          let tskpane = window.Application.GetTaskPane(tsId);
          tskpane.Visible = !tskpane.Visible;
        }
      } catch (e) {
        console.error('打开设置失败:', e);
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
  background: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
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

.empty-text {
  font-size: 14px;
  color: #999;
  font-weight: 500;
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

.message {
  max-width: 90%;
  padding: 6px 8px;
  border-radius: 8px;
  line-height: 1.4;
  font-size: 12px;
}

.user-message {
  align-self: flex-end;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.ai-message {
  align-self: flex-start;
  background: white;
  color: #333;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
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

.message-content :deep(.markdown-body) h1 { font-size: 1.4em; }
.message-content :deep(.markdown-body) h2 { font-size: 1.25em; }
.message-content :deep(.markdown-body) h3 { font-size: 1.1em; }
.message-content :deep(.markdown-body) h4,
.message-content :deep(.markdown-body) h5,
.message-content :deep(.markdown-body) h6 { font-size: 1em; }

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
  margin-left: 4px;
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
  font-style: italic;
}

.chat-input-area {
  padding: 6px 10px;
  background: #f5f5f5;
  flex-shrink: 0;
}

.input-container {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}

.chat-input {
  width: 100%;
  padding: 6px 10px;
  padding-bottom: 0;
  border: none;
  resize: none;
  font-size: 12px;
  font-family: inherit;
  outline: none;
  background: transparent;
  color: #333;
  box-sizing: border-box;
  overflow: hidden;
  min-height: 20px;
  max-height: 150px;
  line-height: 1.4;
}

.chat-input::placeholder {
  color: #999;
}

.input-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 6px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 4px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-wrapper {
  position: relative;
  display: inline-flex;
}

.btn-wrapper .tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
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

.btn-wrapper:hover .tooltip {
  opacity: 1;
  visibility: visible;
}

/* 自定义下拉组件 */
.custom-select {
  position: relative;
  display: inline-flex;
  font-size: 8px;
}

.custom-select.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.select-trigger {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 4px;
  color: #666;
  cursor: pointer;
  border-radius: 3px;
  transition: color 0.2s;
}

.select-trigger:hover {
  color: #667eea;
}

.custom-select.open .select-trigger {
  color: #667eea;
}

.select-arrow {
  transition: transform 0.2s;
}

.custom-select.open .select-arrow {
  transform: rotate(180deg);
}

.select-dropdown {
  position: absolute;
  bottom: 100%;
  left: 0;
  min-width: 100%;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 2px 0;
  margin-bottom: 4px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(4px);
  transition: opacity 0.15s, visibility 0.15s, transform 0.15s;
  z-index: 100;
}

.custom-select.open .select-dropdown {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.model-dropdown {
  min-width: 100px;
}

.select-option {
  padding: 2px 10px;
  color: #333;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}

.select-option:hover {
  background: #f5f5f5;
}

.select-option.active {
  color: #667eea;
  background: #f0f4ff;
}

/* 保留旧样式兼容 */
.toolbar-select option {
  background: white;
  color: #333;
  padding: 4px 8px;
}

.toolbar-select:hover {
  color: #667eea;
}

.toolbar-select:focus {
  outline: none;
  color: #667eea;
}

.setting-btn {
  width: 18px;
  height: 18px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #888;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
}

.setting-btn:hover {
  background: #f0f0f0;
  color: #667eea;
}

.send-btn {
  width: 18px;
  height: 18px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #888;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: #f0f0f0;
  color: #667eea;
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.stop-btn {
  width: 18px;
  height: 18px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #e74c3c;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
}

.stop-btn:hover {
  background: #fef0ef;
  color: #c0392b;
}

/* 选中内容上下文样式 */
.selection-context {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.85) 0%, rgba(108, 115, 200, 0.85) 100%);
  border: 1px solid rgba(102, 126, 234, 0.5);
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 8px;
  font-size: 11px;
}

.context-header {
  display: flex;
  align-items: center;
  gap: 4px;
  color: rgba(255, 255, 255, 0.95);
  font-weight: 500;
  margin-bottom: 4px;
}

.context-preview {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 4px;
  padding: 6px 8px;
  margin-bottom: 4px;
  color: #444;
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
  color: rgba(255, 255, 255, 0.8);
  font-size: 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.context-stats {
  color: rgba(255, 255, 255, 0.7);
  margin-left: auto;
}

/* 当前选区预览条 */
.current-selection-bar {
  background: linear-gradient(135deg, #f8f9ff 0%, #f5f0ff 100%);
  border-top: 1px solid #e8e0f0;
  border-bottom: 1px solid #e8e0f0;
  padding: 6px 10px;
}

.selection-bar-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selection-bar-icon {
  flex-shrink: 0;
  color: #667eea;
  display: flex;
  align-items: center;
}

.selection-bar-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.selection-bar-preview {
  font-size: 11px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.selection-bar-range {
  font-size: 9px;
  color: #888;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.selection-bar-clear {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #999;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
}

.selection-bar-clear:hover {
  background: rgba(0, 0, 0, 0.1);
  color: #666;
}
</style>

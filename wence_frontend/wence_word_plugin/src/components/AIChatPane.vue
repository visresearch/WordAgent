<template>
  <div class="ai-chat-container">
    <div ref="messagesContainer" class="chat-messages">
      <div
        v-for="(msg, index) in messages"
        :key="index" 
        :class="['message', msg.role === 'user' ? 'user-message' : 'ai-message']"
      >
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
          {{ msg.content }}
        </div>
        <button
          v-if="msg.role === 'assistant'"
          class="insert-btn"
          title="输出到Word文档"
          @click="insertToWord(msg.content)"
        >
          📄 输出文档
        </button>
      </div>
      <div v-if="isLoading" class="message ai-message">
        <div class="message-content typing">
          AI正在思考中...
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
            <select v-model="mode" class="toolbar-select">
              <option value="agent">
                Agent
              </option>
              <option value="ask">
                Ask
              </option>
            </select>
            <select 
              v-model="selectedModel" 
              class="toolbar-select" 
              :disabled="modelsLoading"
            >
              <option v-if="modelsLoading" value="" disabled>
                加载中...
              </option>
              <option v-else-if="availableModels.length === 0" value="" disabled>
                选择模型
              </option>
              <option
                v-for="model in availableModels"
                :key="model.id"
                :value="model.id"
              >
                {{ model.name }}
              </option>
            </select>
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
                class="send-btn" 
                :disabled="!inputText.trim() || isLoading" 
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
              <span class="tooltip">发送</span>
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

export default {
  name: 'AIChatPane',
  data() {
    return {
      inputText: '',
      mode: 'agent',
      selectedModel: '',
      availableModels: [],  // 可用模型列表
      modelsLoading: false,  // 模型加载状态
      messages: [
        {
          role: 'assistant',
          content: '您好！我是AI写作助手，可以帮助您修改和优化文档内容。选中Word中的内容后，告诉我您想要如何修改。'
        }
      ],
      isLoading: false,
      lastReadJSON: null,  // 存储上次读取的文档JSON
      currentSelection: null,  // 当前选中的内容信息
      currentSelectionJSON: null,  // 当前选中内容的完整JSON
      selectionCheckInterval: null,  // 选区检查定时器
      currentStreamCtrl: null  // 当前流式请求控制器
    };
  },
  mounted() {
    this.$nextTick(() => {
      this.autoResize();
    });
    // 启动选区监听
    this.startSelectionWatch();
    // 页面加载时获取模型列表
    this.loadModels();
  },
  beforeUnmount() {
    // 清理定时器
    this.stopSelectionWatch();
  },
  methods: {
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
      this.$nextTick(() => {
        this.autoResize();
      });

      this.isLoading = true;
      this.scrollToBottom();
      
      // 创建 AI 消息占位，记录其索引
      const aiMessageIndex = this.messages.length;
      this.messages.push({
        role: 'assistant',
        content: '',
        modifiedJson: null
      });
      
      // 使用 api.js 封装的流式接口
      const streamCtrl = api.chatStream(userMessage, {
        mode: this.mode,
        model: this.selectedModel || 'auto',
        documentJson: documentJson,
        history: this.messages.slice(0, -1).slice(-10),  // 排除刚添加的空消息
        
        onMessage: (data) => {
          if (data.content) {
            this.messages[aiMessageIndex].content += data.content;
            this.scrollToBottom();
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
    insertToWord(content) {
      try {
        // 获取当前活动文档
        const doc = window.Application.ActiveDocument;
        if (!doc) {
          alert('请先打开一个Word文档');
          return;
        }
        
        // 尝试解析 JSON（如果 AI 返回的是带格式的 JSON）
        let jsonData = null;
        
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

.insert-btn {
  display: block;
  margin-top: 6px;
  padding: 3px 6px;
  font-size: 11px;
  background: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.insert-btn:hover {
  background: #e0e0e0;
  border-color: #667eea;
  color: #667eea;
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
  overflow: hidden;
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

.toolbar-select {
  padding: 1px 3px;
  font-size: 9px;
  background: #f8f8f8;
  border: 1px solid #e0e0e0;
  border-radius: 3px;
  color: #666;
  cursor: pointer;
  outline: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='8' viewBox='0 0 8 8'%3E%3Cpath fill='%23666' d='M0 2l4 4 4-4z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 3px center;
  padding-right: 12px;
}

.toolbar-select:hover {
  border-color: #ccc;
}

.toolbar-select:focus {
  border-color: #667eea;
  outline: none;
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

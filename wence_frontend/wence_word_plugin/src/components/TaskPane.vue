<template>
  <div class="global">
    <div class="divItem">
      <h2>🛠️ 调试面板</h2>
      <p style="color: #666; font-size: 13px;">按 <span style="font-weight: bolder">"F12"</span> 可以打开调试器</p>
    </div>
    <hr />
    
    <!-- 文档解析功能 -->
    <div class="divItem">
      <h3>📄 文档内容解析</h3>
      <div class="button-group">
        <button class="btn btn-primary" @click="parseSelection">解析选中内容</button>
        <button class="btn btn-success" @click="parseFullDocument">解析全文</button>
      </div>
    </div>

    <!-- 复制/下载功能 -->
    <div class="divItem" v-if="parsedData">
      <h3>📋 导出操作</h3>
      <div class="button-group">
        <button class="btn btn-warning" @click="copyToClipboard">复制到剪贴板</button>
        <button class="btn btn-info" @click="downloadJSON">下载JSON文件</button>
      </div>
    </div>

    <!-- 解析结果展示 -->
    <div class="divItem" v-if="parsedData">
      <h4>解析结果：</h4>
      <div class="stats">
        <span>段落: {{ parsedData.paragraphs?.length || 0 }}</span>
        <span>表格: {{ parsedData.tables?.length || 0 }}</span>
        <span>图片: {{ parsedData.images?.length || 0 }}</span>
        <span>字数: {{ parsedData.text?.length || 0 }}</span>
      </div>
      <div class="json-container">
        <pre>{{ formattedJSON }}</pre>
      </div>
    </div>

    <!-- 状态提示 -->
    <div class="divItem" v-if="statusMessage">
      <div :class="['status-message', statusType]">{{ statusMessage }}</div>
    </div>
  </div>
</template>

<script>
import { parseDocxToJSON } from './js/docxJsonConverter.js'

export default {
  name: 'TaskPane',
  data() {
    return {
      parsedData: null,
      statusMessage: '',
      statusType: 'info'
    }
  },
  computed: {
    formattedJSON() {
      return this.parsedData ? JSON.stringify(this.parsedData, null, 2) : ''
    }
  },
  methods: {
    // 显示状态消息
    showStatus(message, type = 'info') {
      this.statusMessage = message
      this.statusType = type
      setTimeout(() => {
        this.statusMessage = ''
      }, 3000)
    },

    // 解析选中内容
    parseSelection() {
      try {
        const app = window.Application
        if (!app) {
          this.showStatus('WPS 环境未就绪', 'error')
          return
        }

        const selection = app.Selection
        if (!selection || !selection.Range) {
          this.showStatus('请先选中文档内容', 'error')
          return
        }

        const text = selection.Text || ''
        if (!text || text.trim().length === 0) {
          this.showStatus('选中内容为空', 'error')
          return
        }

        const result = parseDocxToJSON(selection.Range)
        if (result.error) {
          this.showStatus(result.error, 'error')
          return
        }

        this.parsedData = result
        this.showStatus(`解析成功！共 ${result.paragraphs?.length || 0} 个段落`, 'success')
      } catch (e) {
        console.error('解析选中内容出错:', e)
        this.showStatus('解析出错: ' + e.message, 'error')
      }
    },

    // 解析全文
    parseFullDocument() {
      try {
        const app = window.Application
        if (!app) {
          this.showStatus('WPS 环境未就绪', 'error')
          return
        }

        const doc = app.ActiveDocument
        if (!doc) {
          this.showStatus('请先打开文档', 'error')
          return
        }

        const content = doc.Content
        if (!content) {
          this.showStatus('无法获取文档内容', 'error')
          return
        }

        const result = parseDocxToJSON(content)
        if (result.error) {
          this.showStatus(result.error, 'error')
          return
        }

        this.parsedData = result
        this.showStatus(`解析成功！共 ${result.paragraphs?.length || 0} 个段落`, 'success')
      } catch (e) {
        console.error('解析全文出错:', e)
        this.showStatus('解析出错: ' + e.message, 'error')
      }
    },

    // 复制到剪贴板
    async copyToClipboard() {
      if (!this.parsedData) {
        this.showStatus('请先解析文档内容', 'error')
        return
      }

      const jsonString = JSON.stringify(this.parsedData, null, 2)
      
      try {
        // 优先使用 Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(jsonString)
          this.showStatus('已复制到剪贴板！', 'success')
          return
        }

        // 降级方案：使用 execCommand
        const textarea = document.createElement('textarea')
        textarea.value = jsonString
        textarea.style.position = 'fixed'
        textarea.style.left = '-9999px'
        document.body.appendChild(textarea)
        textarea.select()
        
        const success = document.execCommand('copy')
        document.body.removeChild(textarea)
        
        if (success) {
          this.showStatus('已复制到剪贴板！', 'success')
        } else {
          this.showStatus('复制失败，请手动复制', 'error')
        }
      } catch (e) {
        console.error('复制失败:', e)
        this.showStatus('复制失败: ' + e.message, 'error')
      }
    },

    // 下载JSON文件
    downloadJSON() {
      if (!this.parsedData) {
        this.showStatus('请先解析文档内容', 'error')
        return
      }

      try {
        const jsonString = JSON.stringify(this.parsedData, null, 2)
        const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        const filename = `document_${timestamp}.json`
        
        const link = document.createElement('a')
        link.href = url
        link.download = filename
        link.style.display = 'none'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        
        URL.revokeObjectURL(url)
        this.showStatus(`已下载: ${filename}`, 'success')
      } catch (e) {
        console.error('下载失败:', e)
        this.showStatus('下载失败: ' + e.message, 'error')
      }
    }
  }
}
</script>

<style scoped>
.global {
  font-size: 14px;
  min-height: 95%;
  padding: 10px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.divItem {
  margin-bottom: 15px;
}

h2 {
  margin: 0 0 5px 0;
  color: #333;
}

h3 {
  margin: 0 0 10px 0;
  color: #444;
  font-size: 15px;
}

h4 {
  margin: 0 0 8px 0;
  color: #555;
  font-size: 14px;
}

hr {
  border: none;
  border-top: 1px solid #e0e0e0;
  margin: 15px 0;
}

.button-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn:hover {
  opacity: 0.85;
  transform: translateY(-1px);
}

.btn:active {
  opacity: 0.7;
  transform: translateY(0);
}

.btn-primary {
  background-color: #4CAF50;
  color: white;
}

.btn-success {
  background-color: #2196F3;
  color: white;
}

.btn-warning {
  background-color: #ff9800;
  color: white;
}

.btn-info {
  background-color: #00bcd4;
  color: white;
}

.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #666;
}

.stats span {
  background: #f0f0f0;
  padding: 3px 8px;
  border-radius: 4px;
}

.json-container {
  background-color: #1e1e1e;
  padding: 12px;
  border-radius: 6px;
  max-height: 400px;
  overflow: auto;
}

.json-container pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 11px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  color: #d4d4d4;
  line-height: 1.4;
}

.status-message {
  padding: 10px 15px;
  border-radius: 4px;
  font-size: 13px;
  text-align: center;
}

.status-message.success {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #a5d6a7;
}

.status-message.error {
  background-color: #ffebee;
  color: #c62828;
  border: 1px solid #ef9a9a;
}

.status-message.info {
  background-color: #e3f2fd;
  color: #1565c0;
  border: 1px solid #90caf9;
}
</style>

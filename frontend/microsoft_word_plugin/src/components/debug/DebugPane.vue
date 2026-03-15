<template>
  <div class="debug-container">
    <div class="debug-header">
      <h2>🛠️ 调试面板</h2>
      <p class="debug-hint">
        按 <span class="key-hint">F12</span> 可以打开浏览器调试器
      </p>
    </div>
    <hr />

    <!-- 文档解析功能 -->
    <div class="debug-section">
      <h3>📄 文档内容解析</h3>
      <div class="button-group">
        <button class="btn btn-primary" @click="parseSelection">解析选中内容</button>
        <button class="btn btn-docs" @click="getDocumentInfo">获取文档信息</button>
      </div>
    </div>

    <!-- JSON 转文档 -->
    <div class="debug-section">
      <h3>📥 JSON 转文档</h3>
      <textarea
        v-model="jsonInput"
        class="json-input"
        placeholder="粘贴 JSON 到此处..."
        rows="8"
      ></textarea>
      <div class="button-group" style="margin-top: 8px">
        <button class="btn btn-apply" @click="applyJSONToDocument">应用到文档</button>
        <button class="btn btn-warning" @click="jsonInput = ''">清空</button>
      </div>
    </div>

    <!-- 复制/下载功能 -->
    <div v-if="parsedData" class="debug-section">
      <h3>📋 导出操作</h3>
      <div class="button-group">
        <button class="btn btn-warning" @click="copyToClipboard">复制到剪贴板</button>
        <button class="btn btn-info" @click="downloadJSON">下载JSON文件</button>
      </div>
    </div>

    <!-- 解析结果展示 -->
    <div v-if="parsedData" class="debug-section">
      <h4>解析结果：</h4>
      <div class="stats">
        <span>段落: {{ parsedData.paragraphs?.length || 0 }}</span>
        <span>表格: {{ parsedData.tables?.length || 0 }}</span>
        <span>图片: {{ parsedData.images?.length || 0 }}</span>
        <span>字数: {{ totalCharCount }}</span>
      </div>
      <div class="json-container">
        <pre>{{ formattedJSON }}</pre>
      </div>
    </div>

    <!-- 状态提示 -->
    <div v-if="statusMessage" class="debug-section">
      <div :class="['status-message', statusType]">{{ statusMessage }}</div>
    </div>
  </div>
</template>

<script>
import { parseDocxToJSON, generateDocxFromJSON } from '../js/docxJsonConverter.js';

export default {
  name: 'DebugPane',
  data() {
    return {
      parsedData: null,
      statusMessage: '',
      statusType: 'info',
      jsonInput: ''
    };
  },
  computed: {
    formattedJSON() {
      return this.parsedData ? JSON.stringify(this.parsedData, null, 2) : '';
    },
    totalCharCount() {
      if (!this.parsedData || !this.parsedData.paragraphs) return 0;
      let count = 0;
      for (const para of this.parsedData.paragraphs) {
        if (para.runs) {
          for (const run of para.runs) {
            count += (run.text || '').length;
          }
        }
      }
      return count;
    }
  },
  methods: {
    showStatus(message, type = 'info') {
      this.statusMessage = message;
      this.statusType = type;
      setTimeout(() => { this.statusMessage = ''; }, 3000);
    },

    async parseSelection() {
      try {
        this.showStatus('正在解析选中内容...', 'info');
        const result = await parseDocxToJSON('selection');

        if (result.error) {
          this.showStatus(result.error, 'error');
          return;
        }

        this.parsedData = result;
        this.showStatus(`解析成功！共 ${result.paragraphs?.length || 0} 个段落`, 'success');
      } catch (e) {
        console.error('解析选中内容出错:', e);
        this.showStatus('解析出错: ' + e.message, 'error');
      }
    },

    async getDocumentInfo() {
      try {
        this.showStatus('正在获取文档信息...', 'info');
        const result = await parseDocxToJSON('body');

        if (result.error) {
          this.showStatus(result.error, 'error');
          return;
        }

        this.parsedData = result;
        this.showStatus(`文档解析成功！共 ${result.paragraphs?.length || 0} 个段落`, 'success');
      } catch (e) {
        console.error('获取文档信息失败:', e);
        this.showStatus('获取失败: ' + e.message, 'error');
      }
    },

    async applyJSONToDocument() {
      if (!this.jsonInput.trim()) {
        this.showStatus('请先粘贴 JSON 内容', 'error');
        return;
      }

      let jsonData;
      try {
        jsonData = JSON.parse(this.jsonInput);
      } catch (e) {
        this.showStatus('JSON 格式错误: ' + e.message, 'error');
        return;
      }

      try {
        this.showStatus('正在写入文档...', 'info');
        const result = await generateDocxFromJSON(jsonData, 'selection');

        if (result && result.error) {
          this.showStatus('转换失败: ' + result.error, 'error');
          return;
        }

        const paraCount = jsonData.paragraphs?.length || 0;
        const tableCount = jsonData.tables?.length || 0;
        this.showStatus(`已写入文档：${paraCount} 段落 / ${tableCount} 表格`, 'success');
      } catch (e) {
        console.error('JSON 转文档出错:', e);
        this.showStatus('写入失败: ' + e.message, 'error');
      }
    },

    async copyToClipboard() {
      if (!this.parsedData) {
        this.showStatus('请先解析文档内容', 'error');
        return;
      }
      const jsonString = JSON.stringify(this.parsedData, null, 2);
      try {
        await navigator.clipboard.writeText(jsonString);
        this.showStatus('已复制到剪贴板！', 'success');
      } catch (e) {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = jsonString;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        this.showStatus('已复制到剪贴板！', 'success');
      }
    },

    downloadJSON() {
      if (!this.parsedData) {
        this.showStatus('请先解析文档内容', 'error');
        return;
      }
      try {
        const jsonString = JSON.stringify(this.parsedData, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        const filename = `document_${timestamp}.json`;
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        this.showStatus(`已下载: ${filename}`, 'success');
      } catch (e) {
        this.showStatus('下载失败: ' + e.message, 'error');
      }
    }
  }
};
</script>

<style scoped>
.debug-container {
  font-size: 14px;
  min-height: 100%;
  padding: 16px;
}

.debug-header h2 {
  margin: 0 0 5px 0;
  color: #333;
}

.debug-hint {
  color: #666;
  font-size: 13px;
  margin: 0;
}

.key-hint {
  font-weight: bold;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

hr {
  border: none;
  border-top: 1px solid #e0e0e0;
  margin: 15px 0;
}

.debug-section {
  margin-bottom: 15px;
}

.debug-section h3 {
  margin: 0 0 10px 0;
  color: #444;
  font-size: 15px;
}

.debug-section h4 {
  margin: 0 0 8px 0;
  color: #555;
  font-size: 14px;
}

.button-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn:hover { opacity: 0.85; transform: translateY(-1px); }
.btn:active { opacity: 0.7; transform: translateY(0); }

.btn-primary { background-color: #4caf50; color: white; }
.btn-docs { background-color: #7e57c2; color: white; }
.btn-warning { background-color: #ff9800; color: white; }
.btn-info { background-color: #00bcd4; color: white; }
.btn-apply { background-color: #e91e63; color: white; }

.json-input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 11px;
  resize: vertical;
  box-sizing: border-box;
  background: #1e1e1e;
  color: #d4d4d4;
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
  font-family: 'Consolas', 'Monaco', monospace;
  color: #d4d4d4;
  line-height: 1.4;
}

.status-message {
  padding: 10px 15px;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
}

.status-message.success { background-color: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7; }
.status-message.error { background-color: #ffebee; color: #c62828; border: 1px solid #ef9a9a; }
.status-message.info { background-color: #e3f2fd; color: #1565c0; border: 1px solid #90caf9; }
</style>

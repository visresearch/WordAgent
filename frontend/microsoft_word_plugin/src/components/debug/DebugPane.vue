<template>
  <div class="global">
    <div class="divItem">
      <h2>🛠️ {{ $t('debug.title') }}</h2>
      <p style="color: #666; font-size: 13px">
        {{ $t('debug.hint') }}
      </p>
    </div>
    <hr />

    <div class="divItem">
      <h3>📄 {{ $t('debug.parse') }}</h3>
      <div class="button-group">
        <button class="btn btn-primary" @click="parseSelection">{{ $t('debug.parseSelection') }}</button>
        <button class="btn btn-docs" @click="listOpenDocuments">{{ $t('debug.showDocuments') }}</button>
      </div>
    </div>

    <div v-if="openDocuments.length" class="divItem">
      <h4>{{ $t('debug.openDocuments', { count: openDocuments.length }) }}</h4>
      <div class="docs-container">
        <ul class="docs-list">
          <li v-for="(name, index) in openDocuments" :key="`${name}-${index}`">
            {{ name }}
          </li>
        </ul>
      </div>
    </div>

    <div class="divItem">
      <h3>🗑️ {{ $t('debug.deleteParagraphs') }}</h3>
      <textarea
        v-model="deletePositionsInput"
        class="json-input"
        :placeholder="$t('debug.deletePlaceholder')"
        rows="3"
      ></textarea>
      <div class="button-group" style="margin-top: 8px">
        <button class="btn btn-danger" @click="deleteDocxPara">{{ $t('debug.deleteAction') }}</button>
        <button class="btn btn-warning" @click="deletePositionsInput = ''">{{ $t('debug.clear') }}</button>
      </div>
    </div>

    <div class="divItem">
      <h3>📥 {{ $t('debug.jsonToDoc') }}</h3>
      <textarea
        v-model="jsonInput"
        class="json-input"
        :placeholder="$t('debug.jsonPlaceholder')"
        rows="8"
      ></textarea>
      <div class="button-group" style="margin-top: 8px">
        <button class="btn btn-apply" @click="applyJSONToDocument">{{ $t('debug.apply') }}</button>
        <button class="btn btn-warning" @click="jsonInput = ''">{{ $t('debug.clear') }}</button>
      </div>
    </div>

    <div v-if="parsedData" class="divItem">
      <h3>📋 {{ $t('debug.export') }}</h3>
      <div class="button-group">
        <button class="btn btn-warning" @click="copyToClipboard">{{ $t('debug.copy') }}</button>
        <button class="btn btn-info" @click="downloadJSON">{{ $t('debug.download') }}</button>
      </div>
    </div>

    <div v-if="parsedData" class="divItem">
      <h4>{{ $t('debug.result') }}</h4>
      <div class="stats">
        <span>{{ $t('debug.paragraphs', { count: parsedData.paragraphs?.length || 0 }) }}</span>
        <span>{{ $t('debug.tables', { count: parsedData.tables?.length || 0 }) }}</span>
        <span>{{ $t('debug.images', { count: inlineImageRunCount }) }}</span>
        <span>{{ $t('debug.chars', { count: totalCharCount }) }}</span>
      </div>
      <div class="json-container">
        <pre>{{ formattedJSON }}</pre>
      </div>
    </div>

    <div v-if="statusMessage" class="divItem">
      <div :class="['status-message', statusType]">
        {{ statusMessage }}
      </div>
    </div>
  </div>
</template>

<script>
import {
  parseDocxToJSON,
  generateDocxFromJSON,
  deleteDocxPara as deleteDocxParaFn,
} from '../js/docxJsonConverter.js';

export default {
  name: 'DebugPane',
  data() {
    return {
      parsedData: null,
      openDocuments: [],
      statusMessage: '',
      statusType: 'info',
      jsonInput: '',
      deletePositionsInput: '',
    };
  },
  computed: {
    formattedJSON() {
      return this.parsedData ? JSON.stringify(this.parsedData, null, 2) : '';
    },
    totalCharCount() {
      if (!this.parsedData || !this.parsedData.paragraphs) {
        return 0;
      }
      let count = 0;
      for (const para of this.parsedData.paragraphs) {
        if (para.runs) {
          for (const run of para.runs) {
            count += (run.text || '').length;
          }
        }
      }
      return count;
    },
    inlineImageRunCount() {
      if (!this.parsedData || !this.parsedData.paragraphs) {
        return 0;
      }
      let n = 0;
      for (const para of this.parsedData.paragraphs) {
        if (!para.runs) {
          continue;
        }
        for (const run of para.runs) {
          if (run && run.text == null && run.url) {
            n++;
          }
        }
      }
      return n;
    },
  },
  methods: {
    showStatus(message, type = 'info') {
      this.statusMessage = message;
      this.statusType = type;
      setTimeout(() => {
        this.statusMessage = '';
      }, 3000);
    },

    async deleteDocxPara() {
      if (!this.deletePositionsInput.trim()) {
        this.showStatus('请输入要删除的 paraID 列表', 'error');
        return;
      }

      let indices;
      try {
        indices = this.deletePositionsInput
          .split(/[,，\s]+/)
          .filter((s) => s.trim() !== '')
          .map((s) => {
            const n = Number(s.trim());
            if (isNaN(n)) {
              throw new Error(`"${s.trim()}" 不是有效数字`);
            }
            return n;
          });
      } catch (e) {
        this.showStatus('输入格式错误: ' + e.message, 'error');
        return;
      }

      if (indices.length === 0) {
        this.showStatus('未解析到有效的 paraID', 'error');
        return;
      }

      try {
        const result = await deleteDocxParaFn(indices);
        if (result.success) {
          this.showStatus(result.message, 'success');
        } else {
          this.showStatus(result.message || '删除失败', 'error');
        }
      } catch (e) {
        console.error('删除段落出错:', e);
        this.showStatus('删除失败: ' + e.message, 'error');
      }
    },

    async parseSelection() {
      try {
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

    listOpenDocuments() {
      try {
        let name = '未命名文档';
        const url = Office?.context?.document?.url || '';
        if (url) {
          name = decodeURIComponent(url.split('/').pop().split('\\').pop() || name);
        }

        this.openDocuments = [name];
        this.showStatus(`共找到 ${this.openDocuments.length} 个已打开文档`, 'success');
      } catch (e) {
        console.error('获取文档列表失败:', e);
        this.showStatus('获取文档列表失败: ' + e.message, 'error');
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
        const rawInsertParaID = jsonData.insertParaID;
        const insertParaID = Number.isInteger(rawInsertParaID)
          ? rawInsertParaID
          : rawInsertParaID !== null && rawInsertParaID !== undefined && Number.isInteger(Number(rawInsertParaID))
            ? Number(jsonData.insertParaID)
            : null;
        if (insertParaID === null) {
          this.showStatus('转换失败: 缺少必填 insertParaID（空文档首次写入使用 0）', 'error');
          return;
        }
        const result = await generateDocxFromJSON(jsonData, 'selection', insertParaID);
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
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(jsonString);
          this.showStatus('已复制到剪贴板！', 'success');
          return;
        }

        const textarea = document.createElement('textarea');
        textarea.value = jsonString;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();

        const success = document.execCommand('copy');
        document.body.removeChild(textarea);

        if (success) {
          this.showStatus('已复制到剪贴板！', 'success');
        } else {
          this.showStatus('复制失败，请手动复制', 'error');
        }
      } catch (e) {
        console.error('复制失败:', e);
        this.showStatus('复制失败: ' + e.message, 'error');
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
        console.error('下载失败:', e);
        this.showStatus('下载失败: ' + e.message, 'error');
      }
    },
  },
};
</script>

<style scoped>
.global {
  font-size: 14px;
  height: 100%;
  padding: 10px;
  overflow-y: auto;
  box-sizing: border-box;
  background-color: #f7f8fa;
  font-family:
    -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
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
  background-color: #4caf50;
  color: white;
}

.btn-success {
  background-color: #2196f3;
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

.btn-docs {
  background-color: #7e57c2;
  color: white;
}

.btn-apply {
  background-color: #e91e63;
  color: white;
}

.btn-danger {
  background-color: #f44336;
  color: white;
}

.json-input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 11px;
  resize: vertical;
  box-sizing: border-box;
  background: #1e1e1e;
  color: #d4d4d4;
}

.docs-container {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #fafafa;
  padding: 8px 10px;
}

.docs-list {
  margin: 0;
  padding-left: 18px;
  color: #333;
  font-size: 13px;
  line-height: 1.6;
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

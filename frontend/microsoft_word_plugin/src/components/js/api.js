/**
 * WenCe AI Writing Assistant - API 请求库 (Microsoft Office 版)
 *
 * 封装所有与后端的 HTTP 请求和 WebSocket 通信
 * 基于 Office.js Word API，功能对标 WPS 版本
 *
 * 使用方式：
 * import api from './js/api.js'
 *
 * // 流式聊天
 * api.chatStream(message, { onMessage, onError, onComplete })
 *
 * // 获取模型列表
 * const result = await api.getModels()
 */

/* global Word */

import { parseDocxToJSON } from './docxJsonConverter.js';

// ============== 配置 ==============

const CONFIG = {
  baseURL: 'http://localhost:3880',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
};

// ============== 工具函数 ==============

/**
 * 发送 HTTP 请求的基础函数
 * @param {string} url - 请求地址（相对路径）
 * @param {Object} options - 请求选项
 * @returns {Promise<Object>} - 响应数据或错误对象
 */
async function request(url, options = {}) {
  const fullURL = `${CONFIG.baseURL}${url}`;

  const fetchOptions = {
    method: options.method || 'GET',
    headers: {
      ...CONFIG.headers,
      ...options.headers
    },
    ...options
  };

  if (options.body && typeof options.body === 'object') {
    fetchOptions.body = JSON.stringify(options.body);
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || CONFIG.timeout);

    fetchOptions.signal = controller.signal;

    const response = await fetch(fullURL, fetchOptions);
    clearTimeout(timeoutId);

    const contentType = response.headers.get('content-type');
    let data;

    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      return {
        success: false,
        error: data.message || data.error || `HTTP ${response.status}: ${response.statusText}`,
        status: response.status,
        data
      };
    }

    return {
      success: true,
      data,
      status: response.status
    };
  } catch (error) {
    if (error.name === 'AbortError') {
      return {
        success: false,
        error: '请求超时，请稍后重试',
        code: 'TIMEOUT'
      };
    }

    return {
      success: false,
      error: error.message || '网络请求失败',
      code: 'NETWORK_ERROR'
    };
  }
}

// ============== WebSocket 管理 ==============

/**
 * WebSocket 连接管理器
 * 维护一个持久的 WebSocket 连接，支持自动重连
 */
const wsManager = {
  /** @type {WebSocket|null} */
  ws: null,
  connected: false,
  onMessage: null,
  onError: null,
  onComplete: null,
  _reconnectTimer: null,
  _reconnectAttempts: 0,
  _maxReconnectAttempts: 5,
  _connectPromise: null,

  getWsURL() {
    const wsBase = CONFIG.baseURL.replace(/^http/, 'ws');
    return `${wsBase}/api/chat/ws`;
  },

  connect() {
    if (this.ws && this.connected) {
      return Promise.resolve(this.ws);
    }

    if (this._connectPromise) {
      return this._connectPromise;
    }

    this._connectPromise = new Promise((resolve, reject) => {
      const url = this.getWsURL();
      console.log('[WebSocket] 正在连接:', url);

      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('[WebSocket] 连接成功');
        this.ws = ws;
        this.connected = true;
        this._reconnectAttempts = 0;
        this._connectPromise = null;
        resolve(ws);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'done') {
            if (this.onComplete) {
              this.onComplete();
            }
            return;
          }

          if (data.type === 'error') {
            if (this.onError) {
              this.onError(new Error(data.content || '未知错误'));
            }
            return;
          }

          if (this.onMessage) {
            this.onMessage(data);
          }
        } catch (e) {
          console.error('[WebSocket] 解析消息失败:', e, event.data);
        }
      };

      ws.onerror = (event) => {
        console.error('[WebSocket] 连接错误:', event);
        this._connectPromise = null;
        if (!this.connected) {
          reject(new Error('WebSocket 连接失败'));
        }
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] 连接关闭:', event.code, event.reason);
        this.connected = false;
        this.ws = null;
        this._connectPromise = null;

        if (event.code !== 1000 && this._reconnectAttempts < this._maxReconnectAttempts) {
          this._scheduleReconnect();
        }
      };
    });

    return this._connectPromise;
  },

  async send(data) {
    if (!this.ws || !this.connected) {
      await this.connect();
    }
    this.ws.send(JSON.stringify(data));
  },

  close() {
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close(1000, '主动关闭');
      this.ws = null;
      this.connected = false;
    }
  },

  /**
   * 处理后端的文档读取请求：使用 Office.js 解析文档并通过 WebSocket 回传
   */
  async _handleDocumentRequest(startParaIndex = 0, endParaIndex = -1) {
    try {
      // Office.js 版暂不支持按段落范围解析，始终返回全文
      const docData = await parseDocumentRange();

      if (docData.error) {
        throw new Error(docData.error);
      }

      await this.send({
        type: 'document_response',
        documentJson: docData
      });

      console.log('[WebSocket] 已回传文档，段落数:', docData.paragraphs?.length || 0);
    } catch (err) {
      console.error('[WebSocket] 解析/回传文档失败:', err);
      await this.send({
        type: 'document_response',
        documentJson: {},
        error: err?.message || String(err)
      });
    }
  },

  /**
   * 处理后端的文档查询请求：解析全文后执行查询并回传
   * Office.js 版暂时返回全文段落作为查询结果
   * @param {Object} query - Query DSL 对象
   */
  async _handleQueryRequest(query) {
    try {
      const docData = await parseDocumentRange();

      if (docData.error) {
        throw new Error(docData.error);
      }

      // Office.js 版暂无 docxQuery，返回全文段落供后端处理
      const paragraphs = docData.paragraphs || [];
      const matches = paragraphs.map((p, index) => ({
        index,
        text: (p.runs || []).map(r => r.text || '').join(''),
        pStyle: p.pStyle
      })).filter(m => m.text);

      await this.send({
        type: 'query_response',
        matches: matches,
        matchCount: matches.length
      });

      console.log('[WebSocket] 已回传查询结果，段落数:', matches.length);
    } catch (err) {
      console.error('[WebSocket] 查询文档失败:', err);
      await this.send({
        type: 'query_response',
        matches: [],
        matchCount: 0,
        error: err.message
      });
    }
  },

  _scheduleReconnect() {
    if (this._reconnectTimer) {
      return;
    }

    this._reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this._reconnectAttempts - 1), 10000);
    console.log(`[WebSocket] ${delay}ms 后重连 (${this._reconnectAttempts}/${this._maxReconnectAttempts})`);

    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this.connect().catch(() => {
        console.log('[WebSocket] 重连失败');
      });
    }, delay);
  }
};

/**
 * 流式聊天 API（WebSocket）
 *
 * @param {string} message - 用户消息
 * @param {Object} options - 配置选项
 * @returns {Object} - 包含 abort 方法的控制对象
 */
function chatStream(message, options = {}) {
  const {
    onMessage,
    onError,
    onComplete,
    mode = 'agent',
    model = 'auto',
    documentRange = null,
    history = []
  } = options;

  wsManager.onMessage = onMessage;
  wsManager.onError = onError;
  wsManager.onComplete = onComplete;

  const execute = async () => {
    try {
      await wsManager.connect();

      await wsManager.send({
        type: 'chat',
        message: message.trim(),
        mode,
        model,
        documentRange,
        history,
        timestamp: Date.now()
      });
    } catch (error) {
      if (onError) {
        onError(error);
      }
    }
  };

  execute();

  return {
    abort: () => {
      wsManager.send({ type: 'stop' }).catch(() => {});
    }
  };
}

// ============== 文档处理 API ==============

/**
 * 解析文档（使用 Office.js Word API）
 * 默认解析全文（body）
 *
 * @param {string} [scope='body'] - 'body' 解析全文, 'selection' 解析选区
 * @returns {Promise<Object>} - 解析结果
 */
async function parseDocumentRange(scope = 'body') {
  try {
    const result = await parseDocxToJSON(scope);

    if (!result.error) {
      result._meta = {
        isFullDocument: scope === 'body',
        parsedAt: new Date().toISOString()
      };
    }

    return result;
  } catch (error) {
    return { error: '解析文档失败: ' + error.message };
  }
}

/**
 * 获取可用模型列表
 *
 * @returns {Promise<Object>} - 模型列表
 */
async function getModels() {
  return await request('/api/chat/models', {
    method: 'GET'
  });
}

// ============== 会话管理 API ==============

/**
 * 获取会话列表
 */
async function getSessions(options = {}) {
  const { limit = 50 } = options;
  const params = new URLSearchParams({ limit: String(limit) });
  return await request(`/api/sessions?${params}`, { method: 'GET' });
}

/**
 * 创建新会话
 */
async function createSession(data = {}) {
  return await request('/api/sessions', {
    method: 'POST',
    body: data
  });
}

/**
 * 获取最新会话（含消息）
 */
async function getLatestSession() {
  return await request('/api/sessions/latest', { method: 'GET' });
}

/**
 * 获取会话详情（含消息）
 */
async function getSession(sessionId) {
  return await request(`/api/sessions/${sessionId}`, { method: 'GET' });
}

/**
 * 重命名会话
 */
async function renameSessionApi(sessionId, title) {
  return await request(`/api/sessions/${sessionId}`, {
    method: 'PATCH',
    body: { title }
  });
}

/**
 * 删除会话
 */
async function deleteSessionApi(sessionId) {
  return await request(`/api/sessions/${sessionId}`, { method: 'DELETE' });
}

/**
 * 获取会话消息列表
 */
async function getSessionMessages(sessionId, options = {}) {
  const { limit = 200, offset = 0 } = options;
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return await request(`/api/sessions/${sessionId}/messages?${params}`, { method: 'GET' });
}

/**
 * 向会话添加消息
 */
async function addSessionMessage(sessionId, messageData) {
  return await request(`/api/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: messageData
  });
}

/**
 * 清空所有会话及消息
 */
async function clearAllSessions() {
  return await request('/api/sessions', {
    method: 'DELETE'
  });
}

// ============== 设置管理 API ==============

/**
 * 获取用户设置
 */
async function getSettings() {
  try {
    const response = await request('/api/settings', {
      method: 'GET'
    });

    if (!response.success) {
      console.error('获取设置失败:', response.error);
      return { providers: [] };
    }

    return response.data;
  } catch (error) {
    console.error('获取设置异常:', error);
    return { providers: [] };
  }
}

/**
 * 保存用户设置
 */
async function saveSettings(settings) {
  try {
    const response = await request('/api/settings', {
      method: 'POST',
      body: settings
    });

    if (!response.success) {
      throw new Error(response.error || '保存设置失败');
    }

    return response;
  } catch (error) {
    console.error('保存设置异常:', error);
    throw error;
  }
}

/**
 * 获取指定 API 提供商支持的模型列表
 */
async function fetchAvailableModels({ baseUrl, apiKey }) {
  try {
    const result = await request('/api/chat/providers/models', {
      method: 'POST',
      body: {
        base_url: baseUrl,
        api_key: apiKey
      }
    });

    if (result.success && result.data?.success && result.data?.models) {
      return {
        success: true,
        models: result.data.models
      };
    }

    throw new Error(result.data?.error || result.error || '获取模型列表失败');
  } catch (error) {
    console.error('获取模型列表失败:', error);
    throw new Error(error.message || '获取模型列表失败');
  }
}

// ============== 缓存管理 API ==============

/**
 * 扫描缓存
 */
async function scanCache() {
  const response = await request('/api/cache/scan', { method: 'GET' });
  if (!response.success) {
    throw new Error(response.error || '扫描缓存失败');
  }
  return response.data;
}

/**
 * 清除缓存
 */
async function clearCache() {
  const response = await request('/api/cache/clear', { method: 'DELETE' });
  if (!response.success) {
    throw new Error(response.error || '清除缓存失败');
  }
  return response.data;
}

/**
 * 更新配置
 */
function updateConfig(newConfig) {
  if (newConfig.baseURL) {
    CONFIG.baseURL = newConfig.baseURL;
  }
  if (newConfig.timeout) {
    CONFIG.timeout = newConfig.timeout;
  }
  if (newConfig.headers) {
    CONFIG.headers = { ...CONFIG.headers, ...newConfig.headers };
  }
}

/**
 * 获取当前配置
 */
function getConfig() {
  return { ...CONFIG };
}

// ============== 导出 ==============

export default {
  chatStream,
  getModels,
  fetchAvailableModels,

  parseDocumentRange,

  wsManager,

  getSessions,
  createSession,
  getLatestSession,
  getSession,
  renameSessionApi,
  deleteSessionApi,
  getSessionMessages,
  addSessionMessage,
  clearAllSessions,

  getSettings,
  saveSettings,

  scanCache,
  clearCache,

  updateConfig,
  getConfig,

  request
};

export {
  chatStream,
  getModels,
  fetchAvailableModels,
  parseDocumentRange,

  wsManager,

  getSessions,
  createSession,
  getLatestSession,
  getSession,
  renameSessionApi,
  deleteSessionApi,
  getSessionMessages,
  addSessionMessage,
  clearAllSessions,

  getSettings,
  saveSettings,
  scanCache,
  clearCache,
  updateConfig,
  getConfig,
  request
};
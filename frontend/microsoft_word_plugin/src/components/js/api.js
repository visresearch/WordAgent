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

import { parseDocxToJSON } from "./docxJsonConverter.js";
import { executeStyleQuery } from "./docxQuery.js";

// ============== 配置 ==============

const CONFIG = {
  baseURL: "http://localhost:3880",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
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
    method: options.method || "GET",
    headers: {
      ...CONFIG.headers,
      ...options.headers,
    },
    ...options,
  };

  if (options.body && typeof options.body === "object") {
    fetchOptions.body = JSON.stringify(options.body);
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || CONFIG.timeout);

    fetchOptions.signal = controller.signal;

    const response = await fetch(fullURL, fetchOptions);
    clearTimeout(timeoutId);

    const contentType = response.headers.get("content-type");
    let data;

    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      return {
        success: false,
        error: data.message || data.error || `HTTP ${response.status}: ${response.statusText}`,
        status: response.status,
        data,
      };
    }

    return {
      success: true,
      data,
      status: response.status,
    };
  } catch (error) {
    if (error.name === "AbortError") {
      return {
        success: false,
        error: "请求超时，请稍后重试",
        code: "TIMEOUT",
      };
    }

    return {
      success: false,
      error: error.message || "网络请求失败",
      code: "NETWORK_ERROR",
    };
  }
}

/**
 * 获取当前文档全局元信息（随用户 chat 请求发送给后端）
 * 注意：Word.run 返回 Promise，需在 chatStream 调用处 await
 * @returns {Promise<Object|null>}
 */
async function getCurrentDocumentMeta() {
  try {
    return await Word.run(async (context) => {
      const paragraphs = context.document.body.paragraphs;
      paragraphs.load("items");
      await context.sync();

      let documentName = "";
      try {
        const url = Office?.context?.document?.url;
        if (url) {
          documentName = decodeURIComponent(url.split("/").pop().split("\\\\").pop() || "");
        }
      } catch (e) {}

      return {
        totalParas: paragraphs.items.length,
        documentName,
        pageCount: 0,
        isReadOnly: false,
        parsedAt: new Date().toISOString(),
      };
    });
  } catch (error) {
    console.warn("[Meta] 获取文档元信息失败:", error);
    return null;
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

  // 文档缓存：{documentJson: {...}, timestamp: number}
  _documentCache: null,
  // 缓存有效期（毫秒），默认 5 分钟
  _cacheMaxAge: 5 * 60 * 1000,

  /**
   * 获取缓存的文档 JSON，如果缓存过期或不存在则返回 null
   * @returns {Object|null}
   */
  getCachedDocument() {
    if (!this._documentCache) {
      return null;
    }
    const age = Date.now() - this._documentCache.timestamp;
    if (age > this._cacheMaxAge) {
      console.log("[WebSocket] 文档缓存已过期，清除缓存");
      this._documentCache = null;
      return null;
    }
    return this._documentCache.documentJson;
  },

  /**
   * 缓存文档 JSON
   * @param {Object} docJson - 文档 JSON 对象
   */
  setCachedDocument(docJson) {
    this._documentCache = {
      documentJson: docJson,
      timestamp: Date.now()
    };
    console.log("[WebSocket] 文档已缓存，段落数:", docJson?.paragraphs?.length || 0);
  },

  /**
   * 清除文档缓存
   */
  clearDocumentCache() {
    this._documentCache = null;
    console.log("[WebSocket] 文档缓存已清除");
  },

  getWsURL() {
    const wsBase = CONFIG.baseURL.replace(/^http/, "ws");
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
      console.log("[WebSocket] 正在连接:", url);

      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log("[WebSocket] 连接成功");
        this.ws = ws;
        this.connected = true;
        this._reconnectAttempts = 0;
        this._connectPromise = null;
        resolve(ws);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "done") {
            if (this.onComplete) {
              this.onComplete();
            }
            return;
          }

          if (data.type === "error") {
            if (this.onError) {
              this.onError(new Error(data.content || "未知错误"));
            }
            return;
          }

          if (this.onMessage) {
            this.onMessage(data);
          }
        } catch (e) {
          console.error("[WebSocket] 解析消息失败:", e, event.data);
        }
      };

      ws.onerror = (event) => {
        console.error("[WebSocket] 连接错误:", event);
        this._connectPromise = null;
        if (!this.connected) {
          reject(new Error("WebSocket 连接失败"));
        }
      };

      ws.onclose = (event) => {
        console.log("[WebSocket] 连接关闭:", event.code, event.reason);
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
      this.ws.close(1000, "主动关闭");
      this.ws = null;
      this.connected = false;
    }
  },

  /**
   * 处理后端的文档读取请求：使用 Office.js 解析文档并通过 WebSocket 回传
   */
  async _handleDocumentRequest(startParaIndex = 0, endParaIndex = -1) {
    try {
      const docData = await parseDocumentRange(startParaIndex, endParaIndex);

      if (docData.error) {
        throw new Error(docData.error);
      }

      // 如果是读取全文（0 到末尾），更新缓存
      if (startParaIndex === 0 && endParaIndex === -1) {
        this.setCachedDocument(docData);
      }

      await this.send({
        type: "document_response",
        documentJson: docData,
      });

      console.log("[WebSocket] 已回传文档，段落数:", docData.paragraphs?.length || 0);
    } catch (err) {
      console.error("[WebSocket] 解析/回传文档失败:", err);
      await this.send({
        type: "document_response",
        documentJson: {},
        error: err?.message || String(err),
      });
    }
  },

  /**
   * 处理后端的文档查询请求：解析全文后执行查询并回传
   * 优先使用缓存的文档 JSON，避免重复解析
   * @param {Object} query - Query DSL 对象
   */
  async _handleQueryRequest(query) {
    try {
      // 优先使用缓存的文档 JSON
      let docData = this.getCachedDocument();

      if (!docData) {
        console.log("[WebSocket] 文档缓存未命中，解析全文...");
        docData = await parseDocumentRange(0, -1);

        if (docData.error) {
          throw new Error(docData.error);
        }

        // 缓存解析结果
        this.setCachedDocument(docData);
      } else {
        console.log("[WebSocket] 使用缓存的文档进行搜索，段落数:", docData.paragraphs?.length || 0);
      }

      const result = executeStyleQuery(docData, query || {});
      const matchedParaIndices = [
        ...new Set(
          (result.matches || [])
            .map((m) => m?.paragraphIndex)
            .filter((idx) => Number.isInteger(idx))
        ),
      ].sort((a, b) => a - b);

      await this.send({
        type: "query_response",
        matches: result.matches,
        matchCount: result.matchCount,
      });

      console.log("[WebSocket] 已回传查询结果，匹配数:", result.matchCount);
      console.log("[WebSocket] 匹配段落索引:", matchedParaIndices);
    } catch (err) {
      console.error("[WebSocket] 查询文档失败:", err);
      await this.send({
        type: "query_response",
        matches: [],
        matchCount: 0,
        error: err.message,
      });
    }
  },

  _scheduleReconnect() {
    if (this._reconnectTimer) {
      return;
    }

    this._reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this._reconnectAttempts - 1), 10000);
    console.log(
      `[WebSocket] ${delay}ms 后重连 (${this._reconnectAttempts}/${this._maxReconnectAttempts})`
    );

    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this.connect().catch(() => {
        console.log("[WebSocket] 重连失败");
      });
    }, delay);
  },
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
    mode = "agent",
    model = "auto",
    provider = "",
    documentRange = null,
    history = [],
    files = [],
    enableThinking = true,
  } = options;

  wsManager.onMessage = onMessage;
  wsManager.onError = onError;
  wsManager.onComplete = onComplete;

  const execute = async () => {
    try {
      await wsManager.connect();

      // 文档全局元信息：随用户提问发送，不放在 read_document 回包里
      const documentMeta = await getCurrentDocumentMeta();

      await wsManager.send({
        type: "chat",
        message: message.trim(),
        mode,
        model,
        provider,
        documentRange,
        documentMeta,
        history,
        files,
        enableThinking,
        timestamp: Date.now(),
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
      wsManager.send({ type: "stop" }).catch(() => {});
    },
  };
}

// ============== 文档处理 API ==============

/**
 * 解析文档（使用 Office.js Word API）
 * 不传参数或传 (0, -1) 时解析全文，传入具体索引则解析指定范围
 *
 * @param {number} [startParaIndex=0] - 起始段落索引（0-based），0 表示文档开头
 * @param {number} [endParaIndex=-1] - 结束段落索引（0-based），-1 表示文档结尾
 * @returns {Promise<Object>} - 解析结果
 */
async function parseDocumentRange(startParaIndex = 0, endParaIndex = -1) {
  try {
    // read_document / search_documnet 回包仅返回文档内容，不携带全局 meta。
    // 全局 meta 在 chatStream 中通过 documentMeta 单独发送。
    const result = await parseDocxToJSON("body", startParaIndex, endParaIndex);
    return result;
  } catch (error) {
    return { error: "解析文档失败: " + error.message };
  }
}

/**
 * 获取可用模型列表
 *
 * @returns {Promise<Object>} - 模型列表
 */
async function getModels() {
  return await request("/api/chat/models", {
    method: "GET",
  });
}

// ============== 会话管理 API ==============

/**
 * 获取会话列表
 */
async function getSessions(options = {}) {
  const { limit = 50 } = options;
  const params = new URLSearchParams({ limit: String(limit) });
  return await request(`/api/sessions?${params}`, { method: "GET" });
}

/**
 * 创建新会话
 */
async function createSession(data = {}) {
  return await request("/api/sessions", {
    method: "POST",
    body: data,
  });
}

/**
 * 获取最新会话（含消息）
 */
async function getLatestSession() {
  return await request("/api/sessions/latest", { method: "GET" });
}

/**
 * 获取会话详情（含消息）
 */
async function getSession(sessionId) {
  return await request(`/api/sessions/${sessionId}`, { method: "GET" });
}

/**
 * 重命名会话
 */
async function renameSessionApi(sessionId, title) {
  return await request(`/api/sessions/${sessionId}`, {
    method: "PATCH",
    body: { title },
  });
}

/**
 * 删除会话
 */
async function deleteSessionApi(sessionId) {
  return await request(`/api/sessions/${sessionId}`, { method: "DELETE" });
}

/**
 * 获取会话消息列表
 */
async function getSessionMessages(sessionId, options = {}) {
  const { limit = 200, offset = 0 } = options;
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return await request(`/api/sessions/${sessionId}/messages?${params}`, { method: "GET" });
}

/**
 * 向会话添加消息
 */
async function addSessionMessage(sessionId, messageData) {
  return await request(`/api/sessions/${sessionId}/messages`, {
    method: "POST",
    body: messageData,
  });
}

/**
 * 清空所有会话及消息
 */
async function clearAllSessions() {
  return await request("/api/sessions", {
    method: "DELETE",
  });
}

/**
 * 上传文件到后端
 * @param {File[]} files - 要上传的文件列表
 * @returns {Promise<Object>} - { success, files: [{file_id, filename, size, content_type, is_image}] }
 */
async function uploadFiles(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  try {
    const response = await fetch(`${CONFIG.baseURL}/api/chat/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      return { success: false, error: `HTTP ${response.status}`, files: [] };
    }

    return await response.json();
  } catch (error) {
    return { success: false, error: error.message, files: [] };
  }
}

// ============== 设置管理 API ==============

/**
 * 获取用户设置
 */
async function getSettings() {
  try {
    const response = await request("/api/settings", {
      method: "GET",
    });

    if (!response.success) {
      console.error("获取设置失败:", response.error);
      return { providers: [], mcpServers: [] };
    }

    return response.data;
  } catch (error) {
    console.error("获取设置异常:", error);
    return { providers: [], mcpServers: [] };
  }
}

/**
 * 保存用户设置
 */
async function saveSettings(settings) {
  try {
    const response = await request("/api/settings", {
      method: "POST",
      body: settings,
    });

    if (!response.success) {
      throw new Error(response.error || "保存设置失败");
    }

    return response;
  } catch (error) {
    console.error("保存设置异常:", error);
    throw error;
  }
}

/**
 * 获取指定 API 提供商支持的模型列表
 */
async function fetchAvailableModels({ baseUrl, apiKey, apiType = "openai" }) {
  try {
    const result = await request("/api/chat/providers/models", {
      method: "POST",
      body: {
        base_url: baseUrl,
        api_key: apiKey,
        api_type: apiType,
      },
    });

    if (result.success && result.data?.success && result.data?.models) {
      return {
        success: true,
        models: result.data.models,
      };
    }

    throw new Error(result.data?.error || result.error || "获取模型列表失败");
  } catch (error) {
    console.error("获取模型列表失败:", error);
    throw new Error(error.message || "获取模型列表失败");
  }
}

/**
 * 测试 MCP 服务器连接
 */
async function testMcpServer({ name, config }) {
  const response = await request("/api/settings/mcp/test", {
    method: "POST",
    body: {
      name,
      config,
    },
  });

  if (!response.success) {
    throw new Error(response.error || "测试 MCP 服务器连接失败");
  }

  return response.data;
}

/**
 * 获取前端图片导出目录（wence_data/temp）
 * @returns {Promise<Object>} { dir: string }
 */
async function getWenceTempDir() {
  const response = await request("/api/settings/wence-temp-dir", { method: "GET" });
  if (!response.success) {
    throw new Error(response.error || "获取临时目录失败");
  }
  return response.data;
}

// ============== 缓存管理 API ==============

/**
 * 扫描缓存
 */
async function scanCache() {
  const response = await request("/api/cache/scan", { method: "GET" });
  if (!response.success) {
    throw new Error(response.error || "扫描缓存失败");
  }
  return response.data;
}

/**
 * 清除缓存
 */
async function clearCache() {
  const response = await request("/api/cache/clear", { method: "DELETE" });
  if (!response.success) {
    throw new Error(response.error || "清除缓存失败");
  }
  return response.data;
}

// ============== Skill 管理 API ==============

/**
 * 获取已下载 skill 列表
 * @returns {Promise<Array>} skills
 */
async function getSkills() {
  const response = await request("/api/skills", { method: "GET" });
  if (!response.success) {
    throw new Error(response.data?.detail || response.error || "获取 skill 列表失败");
  }
  return Array.isArray(response.data?.skills) ? response.data.skills : [];
}

/**
 * 上传 skill 压缩包（zip）
 * @param {File} file
 * @returns {Promise<Object>}
 */
async function uploadSkillPackage(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${CONFIG.baseURL}/api/skills/upload`, {
    method: "POST",
    body: formData,
  });

  let data;
  try {
    data = await response.json();
  } catch (_) {
    data = null;
  }

  if (!response.ok) {
    const detail = data?.detail || `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return data;
}

/**
 * 设置 skill 启用状态
 * @param {string} folder
 * @param {boolean} enabled
 * @returns {Promise<Object>}
 */
async function setSkillEnabled(folder, enabled) {
  const response = await request(`/api/skills/${encodeURIComponent(folder)}/enabled`, {
    method: "PUT",
    body: { enabled: !!enabled },
  });
  if (!response.success) {
    throw new Error(response.data?.detail || response.error || "更新 skill 状态失败");
  }
  return response.data;
}

/**
 * 删除 skill
 * @param {string} folder
 * @returns {Promise<Object>}
 */
async function deleteSkill(folder) {
  const response = await request(`/api/skills/${encodeURIComponent(folder)}`, {
    method: "DELETE",
  });
  if (!response.success) {
    throw new Error(response.data?.detail || response.error || "删除 skill 失败");
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
  uploadFiles,

  getSettings,
  saveSettings,
  testMcpServer,
  getWenceTempDir,

  scanCache,
  clearCache,

  getSkills,
  uploadSkillPackage,
  setSkillEnabled,
  deleteSkill,

  updateConfig,
  getConfig,

  request,
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
  uploadFiles,
  getSettings,
  saveSettings,
  testMcpServer,
  getWenceTempDir,
  scanCache,
  clearCache,
  getSkills,
  uploadSkillPackage,
  setSkillEnabled,
  deleteSkill,
  updateConfig,
  getConfig,
  request,
};

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

import { createBackendApi } from '../../../../shared/js/backendApi.mjs';
import { adjustPageMargins } from './pageMargins.js';
import { assertRevisionDocumentTarget } from "./revisionPreview.mjs";

import {
  parseDocxToJSON,
  parseDocxToJSONLightweight,
  findParaIndexRangeByParaIDs,
} from "./docxJsonConverter.js";
import { executeStyleQuery } from "./docxQuery.js";

// ============== 配置 ==============

const CONFIG = {
  baseURL: "http://localhost:3880",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
};

function setGlobalBaseURL(value) {
  const normalized = String(value || "").replace(/\/+$/, "");
  if (!normalized) {
    return;
  }
  try {
    if (typeof window !== "undefined") {
      window.__WENCE_API_BASE__ = normalized;
    }
  } catch (e) {}
  try {
    localStorage.setItem("wence_api_base", normalized);
  } catch (e) {}
}

setGlobalBaseURL(CONFIG.baseURL);

function normalizeParaIdValue(value) {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  return null;
}

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
        error: (Array.isArray(data?.detail)
          ? data.detail.map(item => `${item.loc?.at(-1) || ''}: ${item.msg}`).join('; ')
          : data?.detail) || data?.message || data?.error || `HTTP ${response.status}: ${response.statusText}`,
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
      const doc = context.document;
      const paragraphs = doc.body.paragraphs;
      paragraphs.load("items");
      await context.sync();

      let documentName = "";

      try {
        // 优先使用 fileName（本地文档）
        const fileName = Office?.context?.document?.fileName;
        if (fileName) {
          documentName = decodeURIComponent(fileName);
        } else {
          const url = Office?.context?.document?.url;
          if (url) {
            documentName = decodeURIComponent(url.split("/").pop().split("\\\\").pop() || "");
          }
        }
      } catch (e) {}

      // 只保留文件名，去掉路径
      if (documentName) {
        documentName = documentName
          .split(/[/\\]/)
          .pop()
          .replace(/\.docx?$/i, "");
      }

      // 判断文档是否为空
      let isEmpty = paragraphs.items.length === 0;
      if (!isEmpty && paragraphs.items.length > 0) {
        try {
          const firstParaText = paragraphs.items[0].getText();
          await context.sync();
          isEmpty = firstParaText.trim().length === 0 && paragraphs.items.length <= 2;
        } catch (e) {
          isEmpty = false;
        }
      }

      // Office.js binds this task pane to its own document; docId=0 refers to that document.
      return {
        documentId: 0,
        documentName: documentName || "current_document",
        totalParas: paragraphs.items.length,
        isReadOnly: false,
        isEmpty,
        parsedAt: new Date().toISOString(),
      };
    });
  } catch (error) {
    console.warn("[Meta] 获取文档元信息失败:", error);
    return {
      documentId: 0,
      documentName: "current_document",
      totalParas: 0,
      isReadOnly: false,
      isEmpty: true,
      parsedAt: new Date().toISOString(),
    };
  }
}

// ============== WebSocket 管理 ==============

/**
 * WebSocket 连接管理器
 * 维护一个持久的 WebSocket 连接，支持自动重连
 */
const DOCUMENT_TOOL_RESPONSES = {
  read_document: 'document_response',
  search_document: 'query_response',
  edit_document: 'edit_document_response',
  delete_document: 'delete_response',
  insert_break: 'insert_break_response',
  adjust_document: 'adjust_document_response',
  create_document: 'create_document_response',
  save_document_template: 'save_document_template_response',
  view_document: 'view_document_response',
  copy_document: 'copy_document_response',
  json: 'generate_document_response'
};

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
  /** 防止重复调用 onComplete / onError（与 WPS 版一致） */
  _completeCalled: false,
  /** 空闲超时：长时间无任何 WS 消息（含后端 ping）则判定超时 */
  _requestTimeoutTimer: null,
  _requestTimeout: 180000,

  _armIdleTimeout() {
    if (this._requestTimeoutTimer) {
      clearTimeout(this._requestTimeoutTimer);
    }
    this._requestTimeoutTimer = setTimeout(() => {
      if (!this._completeCalled && this.connected) {
        const seconds = Math.round(this._requestTimeout / 1000);
        console.warn(`[WebSocket] 已 ${seconds}s 未收到任何消息，判定为超时`);
        this._completeCalled = true;
        if (this.onError) {
          this.onError(new Error(`请求超时：${seconds}s 内未收到任何响应（含心跳），请稍后重试`));
        }
        if (this.ws) {
          this.ws.close();
        }
      }
    }, this._requestTimeout);
  },

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
      timestamp: Date.now(),
    };
    console.log("[WebSocket] 文档已缓存，内容块数:", docJson?.paragraphs?.length || 0);
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
        if (this.ws !== ws) return;
        let data;
        try {
          data = JSON.parse(event.data);

          // 收到任何消息（包括后端 keepalive 的 ping）都重置空闲超时计时
          if (this._requestTimeoutTimer) {
            this._armIdleTimeout();
          }

          if (data.type === 'done') {
            // 防重复调用 onComplete
            if (!this._completeCalled) {
              this._completeCalled = true;
              // 清除超时定时器
              if (this._requestTimeoutTimer) {
                clearTimeout(this._requestTimeoutTimer);
                this._requestTimeoutTimer = null;
              }
              if (this.onComplete) {
                this.onComplete();
              }
            }
            return;
          }

          if (data.type === 'error') {
            // 清除超时定时器
            if (this._requestTimeoutTimer) {
              clearTimeout(this._requestTimeoutTimer);
              this._requestTimeoutTimer = null;
            }
            if (!this._completeCalled) {
              this._completeCalled = true;
              if (this.onError) {
                this.onError(new Error(data.content || '未知错误'));
              }
            }
            return;
          }

          // 后端 keepalive ping：仅用于保活和重置空闲超时，不上抛
          if (data.type === 'ping') {
            return;
          }

          // 所有消息类型（text, json, status, read_document 等）都透传给上层
          if (this.onMessage) {
            this.reportToolProgress(data, 'received');
            const handling = this.onMessage(data);
            if (handling?.then) {
              Promise.resolve(handling).catch(error => this._reportToolFailure(data, error));
            }
          } else if (DOCUMENT_TOOL_RESPONSES[data.type]) {
            this._reportToolFailure(data, new Error('聊天页面未注册工具处理器'));
          }
        } catch (e) {
          console.error('[WebSocket] 处理消息失败:', e, { type: data?.type, requestId: data?.requestId });
          this._reportToolFailure(data, e);
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
        if (this.ws !== ws) return;
        console.log('[WebSocket] 连接关闭:', event.code, event.reason);
        this.connected = false;
        this.ws = null;
        this._connectPromise = null;
        if (this._requestTimeoutTimer) {
          clearTimeout(this._requestTimeoutTimer);
          this._requestTimeoutTimer = null;
        }

        const willReconnect =
          event.code !== 1000 && this._reconnectAttempts < this._maxReconnectAttempts;

        // 断线后的自动重连只恢复连接，不会重放已经中断的请求。
        const isIdleTimeoutClose = event.code === 1011 && event.reason === 'idle-timeout';
        if (!this._completeCalled) {
          this._completeCalled = true;
          if (this.onError) {
            const error = new Error(
              isIdleTimeoutClose
                ? '⛔ 网络超时连接，自动断开'
                : 'WebSocket 连接意外中断，本次请求已失败'
            );
            error.reconnecting = willReconnect;
            this.onError(error);
          }
        }

        if (willReconnect) {
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

  reportToolProgress(data, phase, elapsedMs = 0) {
    if (!DOCUMENT_TOOL_RESPONSES[data?.type] || (data.type === 'json' && !data.requestId)) {
      return;
    }
    this.send({ type: 'frontend_tool_progress', tool: data.type, phase,
      requestId: data.requestId || null, docId: data.docId, paraID: data.paraID,
      elapsedMs: Math.round(elapsedMs) }).catch(error => console.warn('[WebSocket] 回传工具进度失败:', error));
  },

  _reportToolFailure(data, error) {
    const type = DOCUMENT_TOOL_RESPONSES[data?.type];
    if (!type || (data.type === 'json' && !data.requestId)) {
      return;
    }
    this.send({ type, requestId: data.requestId || null, docId: data.docId, paraID: data.paraID,
      success: false, requiresRead: true, documentJson: {}, matches: [], matchCount: 0,
      error: `前端处理 ${data.type} 失败: ${error?.message || String(error)}`
    }).catch(sendError => console.error('[WebSocket] 回传工具失败结果失败:', sendError));
  },

  close() {
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    if (this._requestTimeoutTimer) {
      clearTimeout(this._requestTimeoutTimer);
      this._requestTimeoutTimer = null;
    }
    const socket = this.ws;
    this.ws = null;
    this.connected = false;
    this._connectPromise = null;
    if (socket) {
      socket.onmessage = socket.onerror = socket.onclose = null;
      socket.close(1000, "主动关闭");
    }
  },

  /**
   * 处理后端的文档读取请求：使用 Office.js 解析文档并通过 WebSocket 回传
   */
  async _handleDocumentRequest(startParaIndexOrParams = 0, endParaIndexArg = -1) {
    const socket = this.ws;
    const startedAt = Date.now();
    const request = { ...(typeof startParaIndexOrParams === "object" ? startParaIndexOrParams : {}), type: "read_document" };
    const progress = phase => this.reportToolProgress(request, phase, Date.now() - startedAt);
    try {
      let startParaIndex = null;
      let endParaIndex = null;
      let startParaID = null;
      let endParaID = null;
      let docId = 0;
      let mode = "full";

      if (
        typeof startParaIndexOrParams === "object" &&
        startParaIndexOrParams !== null &&
        !Array.isArray(startParaIndexOrParams)
      ) {
        startParaIndex =
          startParaIndexOrParams.startParaIndex === undefined
            ? null
            : startParaIndexOrParams.startParaIndex;
        endParaIndex =
          startParaIndexOrParams.endParaIndex === undefined
            ? null
            : startParaIndexOrParams.endParaIndex;
        startParaID =
          startParaIndexOrParams.startParaID === undefined
            ? null
            : startParaIndexOrParams.startParaID;
        endParaID =
          startParaIndexOrParams.endParaID === undefined ? null : startParaIndexOrParams.endParaID;
        docId =
          startParaIndexOrParams.docId === undefined || startParaIndexOrParams.docId === null
            ? 0
            : startParaIndexOrParams.docId;
        mode = startParaIndexOrParams.mode === "lightweight" ? "lightweight" : "full";
      } else {
        startParaIndex =
          startParaIndexOrParams === undefined || startParaIndexOrParams === null
            ? 0
            : startParaIndexOrParams;
        endParaIndex =
          endParaIndexArg === undefined || endParaIndexArg === null ? -1 : endParaIndexArg;
      }

      progress("parse_start");
      const docData = await parseDocumentRange(
        startParaIndex,
        endParaIndex,
        docId,
        startParaID,
        endParaID,
        mode
      );

      if (socket && this.ws !== socket) return;
      progress("parse_finish");
      if (docData.error) {
        throw new Error(docData.error);
      }

      // 如果是读取全文（0 到末尾），更新缓存
      if (
        (startParaID === null || startParaID === undefined) &&
        startParaIndex === 0 &&
        endParaIndex === -1
      ) {
        this.setCachedDocument(docData);
      }

      await this.send({
        type: "document_response",
        requestId: request.requestId || null,
        docId,
        documentJson: docData,
      });
      progress("response_sent");

      const tableCount = (docData.paragraphs || []).reduce(
        (count, block) => count + (Array.isArray(block?.tables) ? block.tables.length : 0),
        0
      );
      console.log(
        "[WebSocket] 已回传文档，内容块数:",
        docData.paragraphs?.length || 0,
        "表格数:",
        tableCount
      );
    } catch (err) {
      if (socket && this.ws !== socket) return;
      console.error("[WebSocket] 解析/回传文档失败:", err);
      await this.send({
        type: "document_response",
        requestId: request.requestId || null,
        success: false,
        requiresRead: true,
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
  async _handleQueryRequest(query, docId = 0) {
    const socket = this.ws;
    try {
      // 仅活动文档使用缓存（Microsoft Word 当前为单文档，但保持兼容）
      let docData = null;
      if (docId === null || docId === undefined || Number(docId) === 0) {
        docData = this.getCachedDocument();
      }

      if (!docData) {
        console.log(
          "[WebSocket] 文档缓存未命中，解析全文...",
          docId ? `docId=${docId}` : "(active)"
        );
        docData = await parseDocumentRange(0, -1, docId, null, null, 'full', false);
        if (socket && this.ws !== socket) return;

        if (docData.error) {
          throw new Error(docData.error);
        }

        // 缓存解析结果
        if (docId === null || docId === undefined || Number(docId) === 0) {
          this.setCachedDocument(docData);
        }
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
      const matchedParaIds = [
        ...new Set(
          (result.matches || []).map((m) => normalizeParaIdValue(m?.paragraphId)).filter((id) => id)
        ),
      ];

      await this.send({
        type: "query_response",
        matches: result.matches,
        matchCount: result.matchCount,
        matchedParaIndices,
        matchedParaIDs: matchedParaIds,
      });

      console.log("[WebSocket] 已回传查询结果，匹配数:", result.matchCount);
      console.log("[WebSocket] 匹配段落索引:", matchedParaIndices);
      console.log("[WebSocket] 匹配段落ID:", matchedParaIds);
    } catch (err) {
      if (socket && this.ws !== socket) return;
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
    selectionContext = null,
    history = [],
    files = [],
    sessionId = null,
    userResponse = null,
  } = options;

  let stopped = false;
  let requestSent = false;
  wsManager._completeCalled = false;
  if (wsManager._requestTimeoutTimer) {
    clearTimeout(wsManager._requestTimeoutTimer);
    wsManager._requestTimeoutTimer = null;
  }

  wsManager.onMessage = data => {
    if (!stopped) return onMessage?.(data);
  };
  wsManager.onError = error => {
    if (!stopped) onError?.(error);
  };
  wsManager.onComplete = () => {
    if (!stopped) onComplete?.();
  };

  const execute = async () => {
    try {
      await wsManager.connect();
      if (stopped) return;
      wsManager._armIdleTimeout();

      // 文档全局元信息：随用户提问发送，不放在 read_document 回包里
      const documentMeta = await getCurrentDocumentMeta();
      // Office.js 读取是异步的，停止后不能继续发送这轮聊天请求。
      if (stopped) return;

      requestSent = true;
      await wsManager.send({
        type: "chat",
        message: message.trim(),
        mode,
        model,
        provider,
        sessionId,
        userResponse,
        documentRange,
        selectionContext,
        documentMeta,
        history,
        files,
        timestamp: Date.now(),
      });
    } catch (error) {
      if (stopped) return;
      if (wsManager._requestTimeoutTimer) {
        clearTimeout(wsManager._requestTimeoutTimer);
        wsManager._requestTimeoutTimer = null;
      }
      if (onError) {
        onError(error);
      }
    }
  };

  execute();

  return {
    abort: () => {
      if (stopped) return;
      stopped = true;
      if (wsManager._requestTimeoutTimer) {
        clearTimeout(wsManager._requestTimeoutTimer);
        wsManager._requestTimeoutTimer = null;
      }
      if (requestSent) {
        wsManager.send({ type: "stop" }).catch(() => {});
        // 停止后的缓冲帧留在旧连接，下一轮对话使用新连接。
        wsManager.close();
      }
      onComplete?.();
    },
  };
}

// ============== 文档处理 API ==============

/**
 * 解析文档（使用 Office.js Word API）
 * 不传参数或传 (0, -1) 时解析全文，传入具体索引则解析指定范围
 *
 * @param {number|null} [startParaIndex=0] - 起始段落索引（0-based）
 * @param {number|null} [endParaIndex=-1] - 结束段落索引（0-based）
 * @param {number|null} [docId=0] - 文档 ID，Microsoft Word 当前固定为 0
 * @param {string|number|null} [startParaID=null] - 起始段落 paraID（优先于索引）
 * @param {string|number|null} [endParaID=null] - 结束段落 paraID
 * @param {"full"|"lightweight"} [mode="full"] - 完整样式读取或轻量文本读取
 * @returns {Promise<Object>} - 解析结果
 */
async function parseDocumentRange(
  startParaIndex = 0,
  endParaIndex = -1,
  docId = 0,
  startParaID = null,
  endParaID = null,
  mode = "full",
  includeMeta = true
) {
  try {
    assertRevisionDocumentTarget(docId);
    const useParaIDMode = startParaID !== null && startParaID !== undefined;
    let resolvedStartIndex = startParaIndex;
    let resolvedEndIndex = endParaIndex;

    if (useParaIDMode) {
      const rangeResult = await findParaIndexRangeByParaIDs(startParaID, endParaID);
      if (!rangeResult.success) {
        return { error: rangeResult.error || "按 paraID 定位段落失败" };
      }
      resolvedStartIndex = rangeResult.startParaIndex;
      resolvedEndIndex = rangeResult.endParaIndex;
    }

    return mode === "lightweight"
      ? await parseDocxToJSONLightweight(resolvedStartIndex, resolvedEndIndex, includeMeta)
      : await parseDocxToJSON("body", resolvedStartIndex, resolvedEndIndex, includeMeta);
  } catch (error) {
    return { error: "解析文档失败: " + error.message };
  }
}

async function adjustDocument(docId, pageMarginsCm) {
  try {
    if (docId == null || (typeof docId !== 'number' && typeof docId !== 'string')
        || String(docId).trim() === '' || !Number.isInteger(Number(docId))) {
      throw new Error('docId 必须是有效整数。');
    }
    assertRevisionDocumentTarget(docId);
    return await adjustPageMargins(pageMarginsCm);
  } catch (error) {
    return { success: false, error: error?.message || String(error) };
  } finally {
    wsManager.clearDocumentCache();
  }
}

// ============== 会话管理 API ==============

/**
 * 清空所有会话及消息
 */
async function clearAllSessions() {
  const response = await request("/api/sessions", {
    method: "DELETE",
  });
  if (!response.success || response.data?.success === false) {
    throw new Error(response.data?.error || response.error || "删除会话失败");
  }
  return response;
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
  const response = await request("/api/settings", { method: "GET" });
  if (!response.success) {
    throw new Error(response.error || "获取设置失败");
  }
  return response.data;
}

// ============== Skill 管理 API ==============

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
 * 更新配置
 */
function updateConfig(newConfig) {
  if (newConfig.baseURL) {
    CONFIG.baseURL = newConfig.baseURL;
    setGlobalBaseURL(CONFIG.baseURL);
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

/**
 * 创建并打开一个新的空白 DOCX 文档。
 * Office.js 通过 Word.Application.createDocument 创建临时文档，
 * 再调用 DocumentCreated.open() 在 Word 中打开它。
 */
async function createDocument(base64File) {
  try {
    if (typeof Word === 'undefined' || typeof Word.run !== 'function') {
      throw new Error('Microsoft Word API 不可用');
    }

    await Word.run(async (context) => {
      const application = context.application;
      if (typeof application.createDocument !== 'function') {
        throw new Error('当前 Office.js 版本不支持创建新文档');
      }

      const createdDocument = base64File ? application.createDocument(base64File) : application.createDocument();
      await context.sync();
      if (!createdDocument || typeof createdDocument.open !== 'function') {
        throw new Error('Word 未返回可打开的新文档对象');
      }
      createdDocument.open();
      await context.sync();
    });

    wsManager.clearDocumentCache();
    return { success: true, documentId: 0 };
  } catch (error) {
    console.error('[Word] 创建新 DOCX 文档失败:', error);
    return { success: false, error: error?.message || String(error) };
  }
}

const {
  getModels,
  getSessions,
  createSession,
  getLatestSession,
  getSession,
  renameSessionApi,
  deleteSessionApi,
  getSessionMessages,
  addSessionMessage,
  getAppVersion,
  testModelConnection,
  saveSettings,
  fetchAvailableModels,
  testMcpServer,
  getWenceTempDir,
  scanCache,
  clearCache,
  getMemory,
  saveMemory,
  getSkills,
  setSkillEnabled,
  openSkillFolder,
  deleteSkill,
  getPlugins,
  installPlugin,
  removePlugin,
  getPluginOperation,
} = createBackendApi(request);

// ============== 导出 ==============

export default {
  chatStream,
  getModels,
  fetchAvailableModels,
  testModelConnection,

  parseDocumentRange,
  adjustDocument,

  wsManager,
  createDocument,

  getSessions,
  createSession,
  getLatestSession,
  getSession,
  renameSessionApi,
  deleteSessionApi,
  getSessionMessages,
  addSessionMessage,
  clearAllSessions,
  getAppVersion,
  uploadFiles,

  getSettings,
  saveSettings,
  testMcpServer,
  getWenceTempDir,

  scanCache,
  clearCache,

  getMemory,
  saveMemory,

  getSkills,
  uploadSkillPackage,
  setSkillEnabled,
  openSkillFolder,
  deleteSkill,
  getPlugins,
  installPlugin,
  removePlugin,
  getPluginOperation,

  updateConfig,
  getConfig,

  request,
};

export {
  chatStream,
  getModels,
  fetchAvailableModels,
  testModelConnection,
  parseDocumentRange,
  adjustDocument,
  wsManager,
  createDocument,
  getSessions,
  createSession,
  getLatestSession,
  getSession,
  renameSessionApi,
  deleteSessionApi,
  getSessionMessages,
  addSessionMessage,
  clearAllSessions,
  getAppVersion,
  uploadFiles,
  getSettings,
  saveSettings,
  testMcpServer,
  getWenceTempDir,
  scanCache,
  clearCache,
  getMemory,
  saveMemory,
  getSkills,
  uploadSkillPackage,
  setSkillEnabled,
  openSkillFolder,
  deleteSkill,
  getPlugins,
  installPlugin,
  removePlugin,
  getPluginOperation,
  updateConfig,
  getConfig,
  request,
};

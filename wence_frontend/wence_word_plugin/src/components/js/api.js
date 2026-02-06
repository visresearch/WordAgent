/**
 * WenCe AI Writing Assistant - API 请求库
 *
 * 封装所有与后端的 HTTP 请求和响应处理
 *
 * 使用方式：
 * import api from './js/api.js'
 *
 * // 发送文档修改请求
 * const result = await api.modifyDocument(jsonData, userQuestion)
 *
 * // 发送普通聊天请求
 * const result = await api.chat(message)
 */

import { parseDocxToJSON } from './docxJsonConverter.js';

// ============== 配置 ==============

const CONFIG = {
  baseURL: 'http://localhost:3880',
  timeout: 30000, // 30秒超时
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

  // 如果有 body，序列化为 JSON
  if (options.body && typeof options.body === 'object') {
    fetchOptions.body = JSON.stringify(options.body);
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || CONFIG.timeout);

    fetchOptions.signal = controller.signal;

    const response = await fetch(fullURL, fetchOptions);
    clearTimeout(timeoutId);

    // 解析响应
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

// ============== API 方法 ==============

// ============== WebSocket 管理 ==============

/**
 * WebSocket 连接管理器
 * 维护一个持久的 WebSocket 连接，支持自动重连
 */
const wsManager = {
  /** @type {WebSocket|null} */
  ws: null,
  /** 连接状态 */
  connected: false,
  /** 当前消息回调（每次 chatStream 设置） */
  onMessage: null,
  onError: null,
  onComplete: null,
  /** 重连计时器 */
  _reconnectTimer: null,
  /** 重连次数 */
  _reconnectAttempts: 0,
  /** 最大重连次数 */
  _maxReconnectAttempts: 5,
  /** 连接 Promise（确保 connect 不会并发） */
  _connectPromise: null,

  /**
   * 获取 WebSocket URL
   */
  getWsURL() {
    // 将 http:// 替换为 ws://
    const wsBase = CONFIG.baseURL.replace(/^http/, 'ws');
    return `${wsBase}/api/chat/ws`;
  },

  /**
   * 建立连接
   * @returns {Promise<WebSocket>}
   */
  connect() {
    // 如果已连接，直接返回
    if (this.ws && this.connected) {
      return Promise.resolve(this.ws);
    }

    // 如果正在连接，返回现有 Promise
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

          // 后端请求读取文档：自动解析并回传，对上层透明
          if (data.type === 'read_document') {
            console.log('[WebSocket] 后端请求读取文档, startPos:', data.startPos, 'endPos:', data.endPos);
            this._handleDocumentRequest(data.startPos, data.endPos);
            return;
          }

          // 其他消息类型：text, json, status 等
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

        // 如果不是主动关闭，尝试重连
        if (event.code !== 1000 && this._reconnectAttempts < this._maxReconnectAttempts) {
          this._scheduleReconnect();
        }
      };
    });

    return this._connectPromise;
  },

  /**
   * 发送消息
   * @param {Object} data - 要发送的数据
   */
  async send(data) {
    if (!this.ws || !this.connected) {
      await this.connect();
    }
    this.ws.send(JSON.stringify(data));
  },

  /**
   * 关闭连接
   */
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
   * 处理后端的文档读取请求：根据 startPos/endPos 解析文档并通过 WebSocket 回传
   * @param {number} startPos - 起始位置，-1 表示文档开头
   * @param {number} endPos - 结束位置，-1 表示文档结尾
   */
  async _handleDocumentRequest(startPos = -1, endPos = -1) {
    // 通知上层显示状态
    if (this.onMessage) {
      this.onMessage({ type: 'status', content: `📑 正在读取文档(${startPos} - ${endPos})`, loading: true });
    }

    try {
      const docData = await parseDocumentRange(startPos, endPos);

      if (docData.error) {
        throw new Error(docData.error);
      }

      // 通过 WebSocket 回传文档给后端
      await this.send({
        type: 'document_response',
        documentJson: docData
      });

      console.log('[WebSocket] 已回传文档，段落数:', docData.paragraphs?.length || 0);
      // if (this.onMessage) {
      //   this.onMessage({ type: 'status', content: '✅ 文档读取完成' });
      // }
    } catch (err) {
      console.error('[WebSocket] 解析/回传文档失败:', err);
      // if (this.onMessage) {
      //   this.onMessage({ type: 'status', content: '❌ 解析失败: ' + err.message });
      // }
    }
  },

  /**
   * 安排重连
   */
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
 * 通过 WebSocket 双向通信，支持后端请求前端操作
 *
 * @param {string} message - 用户消息
 * @param {Object} options - 配置选项
 * @param {Function} options.onMessage - 收到消息时的回调
 * @param {Function} options.onError - 发生错误时的回调
 * @param {Function} options.onComplete - 完成时的回调
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

  // 设置当前会话的回调
  wsManager.onMessage = onMessage;
  wsManager.onError = onError;
  wsManager.onComplete = onComplete;

  const execute = async () => {
    try {
      // 确保 WebSocket 已连接
      await wsManager.connect();

      // 发送聊天请求
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
      // 发送停止请求
      wsManager.send({ type: 'stop' }).catch(() => {});
    }
  };
}

// ============== 文档处理 API ==============

/**
 * 异步解析文档范围（推迟到下一个事件循环，避免阻塞 UI）
 * 不传参数或传 (-1, -1) 时解析全文，传入具体位置则解析指定范围
 *
 * @param {number} [startPos=-1] - 起始位置，-1 表示文档开头
 * @param {number} [endPos=-1] - 结束位置，-1 表示文档结尾
 * @returns {Promise<Object>} - 解析结果
 */
async function parseDocumentRange(startPos = -1, endPos = -1) {
  return new Promise((resolve) => {
    // 使用 setTimeout 将任务推迟到下一个事件循环
    // 这样可以让 UI 有时间响应，避免卡顿
    setTimeout(() => {
      try {
        const doc = window.Application?.ActiveDocument;
        if (!doc) {
          resolve({ error: '没有打开的文档' });
          return;
        }

        const isFullDocument = (startPos === -1 && endPos === -1);
        let result;

        if (isFullDocument) {
          // 解析全文
          const fullRange = doc.Content;
          if (!fullRange) {
            resolve({ error: '无法获取文档内容' });
            return;
          }
          result = parseDocxToJSON(fullRange);
        } else {
          // 解析指定范围
          result = parseDocxToJSON(startPos, endPos);
        }

        if (!result.error) {
          result._meta = {
            isFullDocument,
            startPos: isFullDocument ? 0 : startPos,
            endPos: isFullDocument ? doc.Content.End : endPos,
            documentName: doc.Name || '',
            parsedAt: new Date().toISOString()
          };
        }

        resolve(result);
      } catch (error) {
        resolve({ error: '解析文档失败: ' + error.message });
      }
    }, 0);
  });
}

/**
 * 发送文档 JSON 到后端 /api/chat/doc 接口
 * @param {Object} options - 配置选项
 * @param {Object} options.doc - WPS Document 对象（可选）
 * @param {Object} options.documentJson - 已解析的文档 JSON（可选，不传则自动解析）
 * @returns {Promise<Object>} - 后端返回结果
 */
async function sendDocument(options = {}) {
  const { doc = null, documentJson = null } = options;

  // 如果没有传入 documentJson，则自动解析
  let docData = documentJson;
  let docName = '';

  if (!docData) {
    const currentDoc = doc || window.Application?.ActiveDocument;
    // 使用异步解析
    docData = await parseDocumentRange();
    if (docData.error) {
      return { success: false, error: docData.error };
    }
    docName = currentDoc?.Name || '';
  } else {
    // 从 documentJson 的 _meta 中获取文档名
    docName = docData._meta?.documentName || '';
  }

  console.log('[sendDocument] 发送文档:', docName);

  return await request('/api/chat/doc', {
    method: 'POST',
    body: {
      documentJson: docData,
      documentName: docName,
      timestamp: Date.now()
    }
  });
}

// /**
//  * 阶段1：定位 - 发送文档摘要，获取 Query DSL
//  * 
//  * @param {string} message - 用户消息
//  * @param {Object} options - 配置选项
//  * @param {Object} options.documentSummary - 文档摘要（由 generateSummary 生成）
//  * @param {Function} options.onQuery - 收到 Query DSL 时的回调
//  * @param {Function} options.onText - 收到纯文本回复时的回调
//  * @param {Function} options.onError - 发生错误时的回调
//  * @param {Function} options.onComplete - 完成时的回调
//  * @returns {Object} - 包含 abort 方法的控制对象
//  */
// function locateContent(message, options = {}) {
//   const {
//     documentSummary = null,
//     model = 'auto',
//     onQuery,
//     onText,
//     onStatus,
//     onError,
//     onComplete
//   } = options;

//   const controller = new AbortController();

//   const execute = async () => {
//     try {
//       const response = await fetch(`${CONFIG.baseURL}/api/chat/locate`, {
//         method: 'POST',
//         headers: CONFIG.headers,
//         body: JSON.stringify({
//           message: message.trim(),
//           documentSummary,
//           model
//         }),
//         signal: controller.signal
//       });

//       if (!response.ok) {
//         throw new Error(`HTTP ${response.status}: ${response.statusText}`);
//       }

//       const reader = response.body.getReader();
//       const decoder = new TextDecoder();
//       let buffer = '';

//       while (true) {
//         const { done, value } = await reader.read();

//         if (done) {
//           if (onComplete) {
//             onComplete();
//           }
//           break;
//         }

//         buffer += decoder.decode(value, { stream: true });
//         const lines = buffer.split('\n');
//         buffer = lines.pop() || '';

//         for (const line of lines) {
//           if (line.startsWith('data: ')) {
//             const data = line.slice(6);
//             if (data === '[DONE]') {
//               if (onComplete) {
//                 onComplete();
//               }
//               return;
//             }
//             try {
//               const parsed = JSON.parse(data);
//               if (parsed.type === 'query' && onQuery) {
//                 onQuery(parsed.queryDSL, parsed.message);
//               } else if (parsed.type === 'text' && onText) {
//                 onText(parsed.content);
//               } else if (parsed.type === 'status' && onStatus) {
//                 onStatus(parsed.content);
//               } else if (parsed.type === 'error' && onError) {
//                 onError(new Error(parsed.content));
//               }
//             } catch (e) {
//               console.error('解析响应失败:', e);
//             }
//           }
//         }
//       }
//     } catch (error) {
//       if (error.name !== 'AbortError' && onError) {
//         onError(error);
//       }
//     }
//   };

//   execute();
//   return { abort: () => controller.abort() };
// }

// /**
//  * 阶段2：修改 - 发送匹配的段落，获取修改结果
//  * 
//  * @param {string} message - 用户消息
//  * @param {Object} options - 配置选项
//  * @param {Array} options.matchedParagraphs - 匹配的段落数组
//  * @param {Array} options.originalIndices - 原始段落索引
//  * @param {Function} options.onMessage - 收到消息时的回调
//  * @param {Function} options.onError - 发生错误时的回调
//  * @param {Function} options.onComplete - 完成时的回调
//  * @returns {Object} - 包含 abort 方法的控制对象
//  */
// function modifyContent(message, options = {}) {
//   const {
//     matchedParagraphs = [],
//     originalIndices = [],
//     model = 'auto',
//     onMessage,
//     onError,
//     onComplete
//   } = options;

//   const controller = new AbortController();

//   const execute = async () => {
//     try {
//       const response = await fetch(`${CONFIG.baseURL}/api/chat/modify`, {
//         method: 'POST',
//         headers: CONFIG.headers,
//         body: JSON.stringify({
//           message: message.trim(),
//           matchedParagraphs,
//           originalIndices,
//           model
//         }),
//         signal: controller.signal
//       });

//       if (!response.ok) {
//         throw new Error(`HTTP ${response.status}: ${response.statusText}`);
//       }

//       const reader = response.body.getReader();
//       const decoder = new TextDecoder();
//       let buffer = '';

//       while (true) {
//         const { done, value } = await reader.read();

//         if (done) {
//           if (onComplete) {
//             onComplete();
//           }
//           break;
//         }

//         buffer += decoder.decode(value, { stream: true });
//         const lines = buffer.split('\n');
//         buffer = lines.pop() || '';

//         for (const line of lines) {
//           if (line.startsWith('data: ')) {
//             const data = line.slice(6);
//             if (data === '[DONE]') {
//               if (onComplete) {
//                 onComplete();
//               }
//               return;
//             }
//             try {
//               const parsed = JSON.parse(data);
//               if (onMessage) {
//                 onMessage(parsed);
//               }
//             } catch (e) {
//               if (onMessage) {
//                 onMessage({ content: data });
//               }
//             }
//           }
//         }
//       }
//     } catch (error) {
//       if (error.name !== 'AbortError' && onError) {
//         onError(error);
//       }
//     }
//   };

//   execute();
//   return { abort: () => controller.abort() };
// }

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

// ============== 聊天历史 API ==============

/**
 * 获取指定文档的聊天历史
 *
 * @param {string} docId - 文档唯一标识符
 * @param {Object} options - 选项
 * @param {number} options.limit - 返回消息数量限制
 * @param {number} options.offset - 偏移量
 * @returns {Promise<Object>} - 历史消息列表
 */
async function getChatHistory(docId, options = {}) {
  const { limit = 50, offset = 0 } = options;
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return await request(`/api/chat/history/${encodeURIComponent(docId)}?${params}`, {
    method: 'GET'
  });
}

/**
 * 保存聊天消息
 *
 * @param {Object} messageData - 消息数据
 * @param {string} messageData.docId - 文档唯一标识符
 * @param {string} messageData.docName - 文档名称
 * @param {string} messageData.role - 消息角色（user/assistant）
 * @param {string} messageData.content - 消息内容
 * @param {Object} messageData.documentJson - AI 生成的文档 JSON
 * @param {Object} messageData.selectionContext - 选区上下文
 * @param {string} messageData.model - 使用的模型
 * @param {string} messageData.mode - 使用的模式
 * @returns {Promise<Object>} - 保存结果
 */
async function saveMessage(messageData) {
  return await request('/api/chat/history/save', {
    method: 'POST',
    body: messageData
  });
}

/**
 * 清空指定文档的聊天历史
 *
 * @param {string} docId - 文档唯一标识符
 * @returns {Promise<Object>} - 操作结果
 */
async function clearChatHistory(docId) {
  return await request(`/api/chat/history/${encodeURIComponent(docId)}`, {
    method: 'DELETE'
  });
}

/**
 * 获取所有有聊天记录的文档列表
 *
 * @param {number} limit - 返回数量限制
 * @returns {Promise<Object>} - 文档列表
 */
async function getDocuments(limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) });
  return await request(`/api/chat/documents?${params}`, {
    method: 'GET'
  });
}

/**
 * 更新配置
 * @param {Object} newConfig - 新的配置项
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
 * @returns {Object} - 当前配置
 */
function getConfig() {
  return { ...CONFIG };
}

/**
 * 获取指定 API 提供商支持的模型列表
 * @param {Object} params - 请求参数
 * @param {string} params.baseUrl - API 基础地址
 * @param {string} params.apiKey - API 密钥
 * @returns {Promise<Object>} - 返回模型列表
 */
async function fetchAvailableModels({ baseUrl, apiKey }) {
  try {
    // 通过后端代理接口获取模型列表
    const result = await request('/api/chat/providers/models', {
      method: 'POST',
      body: {
        base_url: baseUrl,
        api_key: apiKey
      }
    });

    // result.data 是后端返回的 JSON：{ success, models } 或 { success, error, models }
    if (result.success && result.data?.success && result.data?.models) {
      return {
        success: true,
        models: result.data.models
      };
    }

    // 请求失败
    throw new Error(result.data?.error || result.error || '获取模型列表失败');
  } catch (error) {
    console.error('获取模型列表失败:', error);
    throw new Error(error.message || '获取模型列表失败');
  }
}

// ============== 设置管理 API ==============

/**
 * 获取用户设置
 * @returns {Promise<Object>} 设置数据
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
 * @param {Object} settings - 设置数据
 * @returns {Promise<Object>} 保存结果
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

// ============== 导出 ==============

export default {
  // API 方法
  chatStream,
  getModels,
  fetchAvailableModels,

  // 文档处理
  parseDocumentRange,
  sendDocument,

  // WebSocket 管理
  wsManager,

  // 聊天历史 API
  getChatHistory,
  saveMessage,
  clearChatHistory,
  getDocuments,

  // 设置管理 API
  getSettings,
  saveSettings,

  // 配置方法
  updateConfig,
  getConfig,

  // 底层请求方法（供扩展使用）
  request
};

// 也支持命名导出
export {
  chatStream,
  getModels,
  fetchAvailableModels,
  parseDocumentRange,
  sendDocument,
  wsManager,
  getChatHistory,
  saveMessage,
  clearChatHistory,
  getDocuments,
  getSettings,
  saveSettings,
  updateConfig,
  getConfig,
  request
};

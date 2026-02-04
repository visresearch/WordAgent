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
 * 防抖函数 - 防止频繁调用
 */
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

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

/**
 * 流式聊天 API（支持 SSE）
 * 用于实时接收 AI 回复
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
    documentJson = null,
    history = []
  } = options;

  const controller = new AbortController();

  const execute = async () => {
    try {
      // fetch 请求 流式响应
      const response = await fetch(`${CONFIG.baseURL}/api/chat/stream`, {
        method: 'POST',
        headers: CONFIG.headers,
        body: JSON.stringify({
          message: message.trim(),
          mode,
          model,
          documentJson,
          history,
          timestamp: Date.now()
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          if (onComplete) {
            onComplete();
          }
          break;
        }

        buffer += decoder.decode(value, { stream: true });

        // 处理 SSE 格式
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              if (onComplete) {
                onComplete();
              }
              return;
            }
            try {
              const parsed = JSON.parse(data);
              if (onMessage) {
                onMessage(parsed);
              }
            } catch (e) {
              // 如果不是 JSON，直接传递文本
              if (onMessage) {
                onMessage({ content: data });
              }
            }
          }
        }
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        if (onError) {
          onError(error);
        }
      }
    }
  };

  execute();

  return {
    abort: () => controller.abort()
  };
}

// ============== 文档处理 API ==============

// 文档解析缓存（避免重复解析）
const documentCache = new Map();
const CACHE_EXPIRE_TIME = 5000; // 5秒缓存有效期

/**
 * 生成文档缓存键
 */
function getDocumentCacheKey(doc) {
  if (!doc) return null;
  // 使用文档路径 + 修改时间作为缓存键
  const path = doc.FullName || doc.Name || '';
  const modified = doc.Saved ? '1' : '0'; // 检测是否有未保存的修改
  return `${path}_${modified}`;
}

/**
 * 异步解析文档（分片处理，避免阻塞 UI）
 * @param {Object} doc - WPS Document 对象
 * @param {Function} onProgress - 进度回调 (current, total)
 * @returns {Promise<Object>} - 解析结果
 */
async function parseDocumentAsync(doc, onProgress = null) {
  return new Promise((resolve) => {
    // 使用 setTimeout 将任务推迟到下一个事件循环
    // 这样可以让 UI 有时间响应
    setTimeout(() => {
      try {
        const fullRange = doc.Content;
        if (!fullRange) {
          resolve({ error: '无法获取文档内容' });
          return;
        }

        // 调用同步解析（WPS API 必须同步调用）
        // 但我们通过 setTimeout 将其推迟，避免立即阻塞
        const result = parseDocxToJSON(fullRange);

        if (!result.error) {
          result._meta = {
            isFullDocument: true,
            documentName: doc.Name || '',
            parsedAt: new Date().toISOString()
          };
        }

        resolve(result);
      } catch (error) {
        resolve({ error: '解析全文失败: ' + error.message });
      }
    }, 0);
  });
}

/**
 * 解析当前文档全文为 JSON（带缓存优化）
 * @param {Object} doc - WPS Document 对象（可选，默认使用当前活动文档）
 * @param {Object} options - 配置选项
 * @param {boolean} options.useCache - 是否使用缓存（默认 true）
 * @param {Function} options.onProgress - 进度回调
 * @returns {Promise<Object>} - JSON 数据或错误对象
 */
async function parseFullDocument(doc, options = {}) {
  const { useCache = true, onProgress = null } = options;

  try {
    if (!doc) {
      doc = window.Application.ActiveDocument;
      if (!doc) {
        return { error: '没有打开的文档' };
      }
    }

    // 检查缓存
    if (useCache) {
      const cacheKey = getDocumentCacheKey(doc);
      if (cacheKey) {
        const cached = documentCache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < CACHE_EXPIRE_TIME) {
          console.log('[parseFullDocument] 使用缓存');
          return cached.data;
        }
      }
    }

    // 异步解析
    const result = await parseDocumentAsync(doc, onProgress);

    // 保存到缓存
    if (useCache && !result.error) {
      const cacheKey = getDocumentCacheKey(doc);
      if (cacheKey) {
        documentCache.set(cacheKey, {
          data: result,
          timestamp: Date.now()
        });

        // 清理过期缓存
        setTimeout(() => {
          for (const [key, value] of documentCache.entries()) {
            if (Date.now() - value.timestamp > CACHE_EXPIRE_TIME) {
              documentCache.delete(key);
            }
          }
        }, CACHE_EXPIRE_TIME);
      }
    }

    return result;
  } catch (error) {
    return { error: '解析全文失败: ' + error.message };
  }
}

/**
 * 发送文档 JSON 到后端 /api/chat/doc 接口
 * @param {Object} options - 配置选项
 * @param {Object} options.doc - WPS Document 对象（可选）
 * @param {Object} options.documentJson - 已解析的文档 JSON（可选，不传则自动解析）
 * @param {Function} options.onProgress - 解析进度回调
 * @returns {Promise<Object>} - 后端返回结果
 */
async function sendDocument(options = {}) {
  const { doc = null, documentJson = null, onProgress = null } = options;

  // 如果没有传入 documentJson，则自动解析
  let docData = documentJson;
  let docName = '';

  if (!docData) {
    const currentDoc = doc || window.Application?.ActiveDocument;
    // 使用异步解析（带缓存）
    docData = await parseFullDocument(currentDoc, { onProgress });
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
  parseFullDocument,
  sendDocument,

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
  parseFullDocument,
  sendDocument,
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

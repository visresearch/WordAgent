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

// ============== 配置 ==============

const CONFIG = {
  baseURL: 'http://localhost:3880',
  timeout: 30000,  // 30秒超时
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
  const { onMessage, onError, onComplete, mode = 'agent', model = 'auto', documentJson = null, history = [] } = options;
  
  const controller = new AbortController();
  
  const execute = async () => {
    try {
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

/**
 * 健康检查 API
 * 检查后端服务是否可用
 * 
 * @returns {Promise<Object>} - 服务状态
 */
async function healthCheck() {
  return await request('/api/health', {
    method: 'GET',
    timeout: 5000
  });
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

// ============== 导出 ==============

export default {
  // API 方法
  chatStream,
  healthCheck,
  getModels,
  
  // 配置方法
  updateConfig,
  getConfig,
  
  // 底层请求方法（供扩展使用）
  request
};

// 也支持命名导出
export {
  chatStream,
  healthCheck,
  getModels,
  updateConfig,
  getConfig,
  request
};

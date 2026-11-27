export function createBackendApi(request) {
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
   * 获取后端应用版本号
   */
  async function getAppVersion() {
    return await request("/api/version", {
      method: "GET",
      timeout: 5000,
    });
  }

  /** Test the selected model using the current provider form values. */
  async function testModelConnection({ baseUrl, apiKey, apiType = 'openai', model }) {
    const result = await request('/api/chat/providers/test-connection', {
      method: 'POST',
      timeout: 25000,
      body: {
        base_url: baseUrl,
        api_key: apiKey,
        api_type: apiType,
        model
      }
    });
    if (!result.success || !result.data?.success) {
      const validationErrors = result.data?.detail;
      const detail = Array.isArray(validationErrors)
        ? validationErrors.map(error => `${error.loc?.at(-1) || ''}: ${error.msg}`).join('; ')
        : validationErrors;
      throw new Error(result.data?.error || detail || result.error || '连接测试失败');
    }
    if (!Number.isFinite(result.data.latency_ms) || result.data.latency_ms < 0) {
      throw new Error('连接测试返回了无效的延迟');
    }
    return result.data;
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
   * 获取前端图片导出目录（wence_data/project/temp）
   * @returns {Promise<Object>} { dir: string }
   */
  async function getWenceTempDir() {
    const response = await request("/api/settings/wence-temp-dir", { method: "GET" });
    if (!response.success) {
      throw new Error(response.error || "获取临时目录失败");
    }
    return response.data;
  }

  /**
   * 扫描项目缓存目录（temp + uploads）
   * @returns {Promise<Object>} { dir, dirs, fileCount, totalSize }
   */
  async function scanCache() {
    const response = await request("/api/settings/cache/scan", { method: "GET" });
    if (!response.success) {
      throw new Error(response.error || "扫描缓存失败");
    }
    return response.data;
  }

  /**
   * 清除项目缓存目录（temp + uploads）
   * @returns {Promise<Object>} { deleted, dirs }
   */
  async function clearCache() {
    const response = await request("/api/settings/cache/clear", { method: "DELETE" });
    if (!response.success) {
      throw new Error(response.error || "清除缓存失败");
    }
    return response.data;
  }

  /**
   * 获取长期记忆内容
   * @returns {Promise<string>} memory content
   */
  async function getMemory() {
    const response = await request("/api/settings/memory", { method: "GET" });
    if (!response.success) {
      throw new Error(response.error || "获取长期记忆失败");
    }
    return response.data.content || "";
  }

  /**
   * 保存长期记忆内容
   * @param {string} content - 记忆内容
   * @returns {Promise<Object>} { success }
   */
  async function saveMemory(content) {
    const response = await request("/api/settings/memory", {
      method: "POST",
      body: { content },
    });
    if (!response.success) {
      throw new Error(response.error || "保存长期记忆失败");
    }
    return response.data;
  }

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
   * 在系统文件管理器中打开 skill 文件夹
   */
  async function openSkillFolder(folder) {
    const response = await request(`/api/skills/${encodeURIComponent(folder)}/open`, {
      method: "POST",
    });
    if (!response.success) {
      throw new Error(response.data?.detail || response.error || "打开 skill 文件夹失败");
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

  async function getPlugins() {
    const response = await request('/api/plugins');
    if (!response.success) throw new Error(response.data?.detail || response.error);
    return response.data;
  }

  async function installPlugin(source) {
    const response = await request('/api/plugins/install', { method: 'POST', body: { source } });
    if (!response.success) throw new Error(response.data?.detail || response.error);
    return response.data;
  }

  async function removePlugin(pluginId) {
    const response = await request(`/api/plugins/${encodeURIComponent(pluginId)}`, { method: 'DELETE' });
    if (!response.success) throw new Error(response.data?.detail || response.error);
    return response.data;
  }

  async function getPluginOperation(operationId) {
    const response = await request(`/api/plugins/operations/${encodeURIComponent(operationId)}`);
    if (!response.success) throw new Error(response.data?.detail || response.error);
    return response.data;
  }

  return {
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
  };
}

<template>
  <div class="setting-container">
    <div class="setting-content">
      <!-- 服务器设置 -->
      <div class="setting-section">
        <h3>🌐 服务器配置</h3>
        <div class="setting-item">
          <label for="serverUrl">服务器地址</label>
          <input 
            id="serverUrl" 
            v-model="serverUrl" 
            type="text" 
            placeholder="请输入服务器地址，如: http://localhost:8080"
            class="setting-input"
          />
          <p class="setting-hint">
            留空则使用默认服务器
          </p>
        </div>
      </div>

      <!-- 用户登录 -->
      <div class="setting-section">
        <h3>👤 用户登录</h3>
        
        <!-- 未登录状态 -->
        <div v-if="!isLoggedIn" class="login-form">
          <div class="setting-item">
            <label for="username">用户名</label>
            <input 
              id="username" 
              v-model="username" 
              type="text" 
              placeholder="请输入用户名"
              class="setting-input"
            />
          </div>
          <div class="setting-item">
            <label for="password">密码</label>
            <input 
              id="password" 
              v-model="password" 
              type="password" 
              placeholder="请输入密码"
              class="setting-input"
              @keydown.enter="login"
            />
          </div>
          <div class="button-group">
            <button class="btn btn-primary" :disabled="isLoading" @click="login">
              {{ isLoading ? '登录中...' : '登录' }}
            </button>
            <button class="btn btn-secondary" :disabled="isLoading" @click="register">
              注册
            </button>
          </div>
          <p v-if="loginError" class="error-msg">
            {{ loginError }}
          </p>
        </div>

        <!-- 已登录状态 -->
        <div v-else class="user-info">
          <div class="user-avatar">
            <span class="avatar-icon">👤</span>
          </div>
          <div class="user-details">
            <p class="user-name">
              {{ userInfo.username }}
            </p>
            <p class="user-status">
              已登录
            </p>
          </div>
          <button class="btn btn-logout" @click="logout">
            退出登录
          </button>
        </div>
      </div>

      <!-- 保存按钮 -->
      <div class="setting-actions">
        <button class="btn btn-save" @click="saveSettings">
          💾 保存设置
        </button>
        <p v-if="saveMessage" :class="['save-msg', saveSuccess ? 'success' : 'error']">
          {{ saveMessage }}
        </p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SettingPane',
  data() {
    return {
      serverUrl: '',
      username: '',
      password: '',
      isLoggedIn: false,
      isLoading: false,
      loginError: '',
      saveMessage: '',
      saveSuccess: false,
      userInfo: {
        username: '',
        token: ''
      }
    };
  },
  mounted() {
    this.loadSettings();
  },
  methods: {
    loadSettings() {
      try {
        // 从 PluginStorage 加载设置
        const savedServerUrl = window.Application?.PluginStorage?.getItem('wence_server_url');
        const savedUserInfo = window.Application?.PluginStorage?.getItem('wence_user_info');
        
        if (savedServerUrl) {
          this.serverUrl = savedServerUrl;
        }
        
        if (savedUserInfo) {
          try {
            const userInfo = JSON.parse(savedUserInfo);
            this.userInfo = userInfo;
            this.isLoggedIn = true;
          } catch (e) {
            console.error('解析用户信息失败:', e);
          }
        }
      } catch (error) {
        console.error('加载设置失败:', error);
        // 尝试从 localStorage 加载
        this.loadFromLocalStorage();
      }
    },
    loadFromLocalStorage() {
      const savedServerUrl = localStorage.getItem('wence_server_url');
      const savedUserInfo = localStorage.getItem('wence_user_info');
      
      if (savedServerUrl) {
        this.serverUrl = savedServerUrl;
      }
      
      if (savedUserInfo) {
        try {
          const userInfo = JSON.parse(savedUserInfo);
          this.userInfo = userInfo;
          this.isLoggedIn = true;
        } catch (e) {
          console.error('解析用户信息失败:', e);
        }
      }
    },
    saveSettings() {
      try {
        // 保存到 PluginStorage
        if (window.Application?.PluginStorage) {
          window.Application.PluginStorage.setItem('wence_server_url', this.serverUrl);
        }
        
        // 同时保存到 localStorage 作为备份
        localStorage.setItem('wence_server_url', this.serverUrl);
        
        this.saveMessage = '设置已保存！';
        this.saveSuccess = true;
        
        setTimeout(() => {
          this.saveMessage = '';
        }, 2000);
      } catch (error) {
        console.error('保存设置失败:', error);
        this.saveMessage = '保存失败，请重试';
        this.saveSuccess = false;
      }
    },
    async login() {
      if (!this.username.trim() || !this.password.trim()) {
        this.loginError = '请输入用户名和密码';
        return;
      }
      
      this.isLoading = true;
      this.loginError = '';
      
      try {
        // 模拟登录请求（实际应连接到服务器）
        const serverUrl = this.serverUrl || 'http://localhost:8080';
        
        // TODO: 替换为实际的登录API
        // const response = await fetch(`${serverUrl}/api/login`, {
        //   method: 'POST',
        //   headers: { 'Content-Type': 'application/json' },
        //   body: JSON.stringify({ username: this.username, password: this.password })
        // })
        
        // 模拟登录成功
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // 模拟登录成功响应
        const userInfo = {
          username: this.username,
          token: 'mock_token_' + Date.now()
        };
        
        this.userInfo = userInfo;
        this.isLoggedIn = true;
        
        // 保存用户信息
        const userInfoStr = JSON.stringify(userInfo);
        if (window.Application?.PluginStorage) {
          window.Application.PluginStorage.setItem('wence_user_info', userInfoStr);
        }
        localStorage.setItem('wence_user_info', userInfoStr);
        
        // 清空表单
        this.username = '';
        this.password = '';
        
      } catch (error) {
        console.error('登录失败:', error);
        this.loginError = '登录失败，请检查网络连接或用户名密码';
      } finally {
        this.isLoading = false;
      }
    },
    async register() {
      if (!this.username.trim() || !this.password.trim()) {
        this.loginError = '请输入用户名和密码';
        return;
      }
      
      this.isLoading = true;
      this.loginError = '';
      
      try {
        // TODO: 替换为实际的注册API
        // const serverUrl = this.serverUrl || 'http://localhost:8080'
        // const response = await fetch(`${serverUrl}/api/register`, { ... })
        
        // 模拟注册
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        this.loginError = '';
        alert('注册功能开发中，请联系管理员获取账号');
        
      } catch (error) {
        console.error('注册失败:', error);
        this.loginError = '注册失败，请稍后重试';
      } finally {
        this.isLoading = false;
      }
    },
    logout() {
      this.isLoggedIn = false;
      this.userInfo = { username: '', token: '' };
      
      // 清除保存的用户信息
      if (window.Application?.PluginStorage) {
        window.Application.PluginStorage.setItem('wence_user_info', '');
      }
      localStorage.removeItem('wence_user_info');
    }
  }
};
</script>

<style scoped>
.setting-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 100vh;
  width: 100%;
  background: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  box-sizing: border-box;
}

.setting-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.setting-section {
  background: white;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.setting-section h3 {
  margin: 0 0 16px 0;
  font-size: 15px;
  color: #333;
  font-weight: 600;
}

.setting-item {
  margin-bottom: 16px;
}

.setting-item:last-child {
  margin-bottom: 0;
}

.setting-item label {
  display: block;
  font-size: 13px;
  color: #666;
  margin-bottom: 6px;
}

.setting-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.setting-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.setting-input::placeholder {
  color: #aaa;
}

.setting-hint {
  margin: 6px 0 0 0;
  font-size: 12px;
  color: #999;
}

.button-group {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-secondary {
  flex: 1;
  background: #f0f0f0;
  color: #666;
}

.btn-secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-save {
  width: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px;
}

.btn-save:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-logout {
  background: #ff6b6b;
  color: white;
  padding: 8px 16px;
  font-size: 13px;
}

.btn-logout:hover {
  background: #ee5a5a;
}

.error-msg {
  margin: 12px 0 0 0;
  padding: 10px;
  background: #fff0f0;
  border-radius: 6px;
  color: #dc3545;
  font-size: 13px;
}

.save-msg {
  margin: 12px 0 0 0;
  padding: 10px;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
}

.save-msg.success {
  background: #f0fff0;
  color: #28a745;
}

.save-msg.error {
  background: #fff0f0;
  color: #dc3545;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 10px;
}

.user-avatar {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-icon {
  font-size: 24px;
  filter: grayscale(1) brightness(10);
}

.user-details {
  flex: 1;
}

.user-name {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #333;
}

.user-status {
  margin: 4px 0 0 0;
  font-size: 12px;
  color: #28a745;
}

.setting-actions {
  margin-top: 8px;
}

.login-form {
  margin-top: 8px;
}
</style>

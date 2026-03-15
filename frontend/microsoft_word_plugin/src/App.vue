<template>
  <div class="app-container">
    <div class="top-nav">
      <router-link to="/aichat" class="nav-btn" active-class="active" title="AI对话">
        <img :src="robotIcon" width="18" height="18" />
      </router-link>
      <button
        class="nav-btn"
        :class="{ active: sessionState.visible }"
        title="历史会话"
        @click="toggleSession"
      >
        <img :src="sessionIcon" width="16" height="16" />
      </button>
      <router-link to="/setting" class="nav-btn" active-class="active" title="设置">
        <img :src="settingIcon" width="16" height="16" />
      </router-link>
      <router-link to="/about" class="nav-btn" active-class="active" title="关于">
        <img :src="aboutIcon" width="16" height="16" />
      </router-link>
      <router-link to="/debug" class="nav-btn" active-class="active" title="调试">
        <img :src="debugIcon" width="16" height="16" />
      </router-link>
    </div>
    <div class="app-content">
      <RouterView />
    </div>
  </div>
</template>

<script>
import robotIcon from '../assets/robot.svg';
import sessionIcon from '../assets/session.svg';
import settingIcon from '../assets/setting.svg';
import aboutIcon from '../assets/about.svg';
import debugIcon from '../assets/debug.svg';
import { sessionState } from './sessionState.js';

export default {
  name: 'App',
  data() {
    return {
      robotIcon,
      sessionIcon,
      settingIcon,
      aboutIcon,
      debugIcon,
      sessionState
    };
  },
  methods: {
    toggleSession() {
      // 如果不在 chat 页面，先跳转并打开
      if (this.$route.path !== '/aichat') {
        this.$router.push('/aichat');
        sessionState.manualValue = true;
        return;
      }
      // 在 chat 页面：切换显隐
      sessionState.manualValue = !sessionState.visible;
    }
  }
};
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}
.top-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 6px 8px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
}
.nav-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  color: #888;
  text-decoration: none;
  transition: all 0.2s;
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
}
.nav-btn:hover {
  background: #f0f0f0;
  color: #555;
}
.nav-btn.active {
  background: #f0f4ff;
  color: #667eea;
}
.app-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>

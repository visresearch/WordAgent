<template>
  <div class="app-container">
    <div class="top-nav">
      <a
        href="#"
        class="nav-btn"
        :class="{ active: $route.path === '/aichat' }"
        title="AI对话"
        @click.prevent="onNavAichat"
      >
        <img :src="robotIcon" width="18" height="18" alt="" />
      </a>
      <button
        type="button"
        class="nav-btn"
        :class="{ active: sessionState.visible, 'nav-btn-disabled': chatState.aiBusy }"
        :aria-disabled="chatState.aiBusy ? 'true' : 'false'"
        title="历史会话"
        @click="toggleSession"
      >
        <img :src="sessionIcon" width="16" height="16" alt="" />
      </button>
      <a
        href="#"
        class="nav-btn"
        :class="{ active: $route.path === '/setting', 'nav-btn-disabled': chatState.aiBusy }"
        :aria-disabled="chatState.aiBusy ? 'true' : 'false'"
        title="设置"
        @click.prevent="go('/setting')"
      >
        <img :src="settingIcon" width="16" height="16" alt="" />
      </a>
      <a
        href="#"
        class="nav-btn"
        :class="{ active: $route.path === '/about', 'nav-btn-disabled': chatState.aiBusy }"
        :aria-disabled="chatState.aiBusy ? 'true' : 'false'"
        title="关于"
        @click.prevent="go('/about')"
      >
        <img :src="aboutIcon" width="16" height="16" alt="" />
      </a>
      <a
        v-if="isDev"
        href="#"
        class="nav-btn"
        :class="{ active: $route.path === '/debug', 'nav-btn-disabled': chatState.aiBusy }"
        :aria-disabled="chatState.aiBusy ? 'true' : 'false'"
        title="调试"
        @click.prevent="go('/debug')"
      >
        <img :src="debugIcon" width="16" height="16" alt="" />
      </a>
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
import { chatState } from './chatState.js';

export default {
  name: 'App',
  data() {
    return {
      robotIcon,
      sessionIcon,
      settingIcon,
      aboutIcon,
      debugIcon,
      sessionState,
      chatState,
      isDev: __DEV__
    };
  },
  methods: {
    _navBlocked() {
      return !!this.chatState.aiBusy;
    },
    go(path) {
      if (this._navBlocked()) {
        return;
      }
      if (this.$route.path !== path) {
        this.$router.push(path);
      }
    },
    onNavAichat() {
      if (this._navBlocked()) {
        return;
      }
      if (this.$route.path !== '/aichat') {
        this.$router.push('/aichat');
      }
    },
    toggleSession() {
      if (this._navBlocked()) {
        return;
      }
      if (this.$route.path !== '/aichat') {
        this.$router.push('/aichat');
        sessionState.manualValue = true;
        return;
      }
      sessionState.manualValue = !sessionState.manualValue;
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
.nav-btn.nav-btn-disabled {
  opacity: 0.35;
  color: #b8b8b8;
  background: transparent;
  cursor: not-allowed;
  pointer-events: none;
}
.nav-btn.nav-btn-disabled:hover {
  background: transparent;
  color: #b8b8b8;
}
.app-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>

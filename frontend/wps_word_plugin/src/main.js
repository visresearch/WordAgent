import './assets/main.css';

import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import ribbon from './components/ribbon.js';
import { i18n } from './i18n/index.js';
import { startMcpBridge, stopMcpBridge } from './components/js/mcp-server.js';
import { installUiZoom } from './uiZoom.js';

const disposeUiZoom = installUiZoom();
if (import.meta.hot) {
  import.meta.hot.dispose(disposeUiZoom);
}

// WPS 的隐藏功能区页也会加载此入口，且首页会被路由重定向到 /aichat。
// 必须在路由初始化之前检查原始 URL，只让显式打开的 AI 侧栏连接 MCP。
const initialHashPath = window.location.hash.split('?')[0];
const initialQuery = window.location.hash.includes('?')
  ? window.location.hash.slice(window.location.hash.indexOf('?') + 1)
  : window.location.search;
const hasPaneWindowId = Boolean(new URLSearchParams(initialQuery).get('windowId'));
const isMcpTaskPane = hasPaneWindowId && (initialHashPath === '#/aichat'
  || (!initialHashPath && /\/aichat\/?$/.test(window.location.pathname)));

// 将 ribbon 挂载到全局，供 WPS 调用
window.ribbon = ribbon;

const app = createApp(App);

app.use(router);
app.use(i18n);

app.mount('#app');
if (isMcpTaskPane) {
  startMcpBridge();
  window.addEventListener('pagehide', stopMcpBridge);
  window.addEventListener('pageshow', startMcpBridge);
  if (import.meta.hot) {
    import.meta.hot.dispose(() => {
      window.removeEventListener('pagehide', stopMcpBridge);
      window.removeEventListener('pageshow', startMcpBridge);
      stopMcpBridge();
    });
  }
}

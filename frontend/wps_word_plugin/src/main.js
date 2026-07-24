import './assets/main.css';

import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import ribbon from './components/ribbon.js';
import { i18n } from './i18n/index.js';

// 将 ribbon 挂载到全局，供 WPS 调用
window.ribbon = ribbon;

const app = createApp(App);

app.use(router);
app.use(i18n);

app.mount('#app');

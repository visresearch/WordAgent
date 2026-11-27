import { createRouter, createWebHashHistory } from 'vue-router';
import api from '../components/js/api.js';
import { createDocumentFromTemplate } from '../components/js/templateDocuments.js';

const router = createRouter({
  history: createWebHashHistory(''),
  routes: [
    {
      path: '/',
      name: '首页',
      redirect: '/aichat'
    },
    {
      path: '/aichat',
      name: 'AI对话',
      component: () => import('../components/chat/AIChatPane.vue')
    },
    {
      path: '/templates',
      name: '文档模板',
      component: () => import('../../../shared/components/TemplatesPane.vue'),
      props: () => ({ baseUrl: api.getConfig().baseURL, createDocument: createDocumentFromTemplate })
    },
    {
      path: '/setting',
      name: '设置',
      component: () => import('../components/setting/SettingPane.vue')
    },
    {
      path: '/about',
      name: '关于',
      component: () => import('../components/about/AboutPane.vue')
    },
    {
      path: '/debug',
      name: '调试',
      component: () => import('../components/debug/DebugPane.vue')
    }
  ]
});

export default router;

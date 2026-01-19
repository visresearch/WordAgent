import { createRouter, createWebHashHistory } from 'vue-router';

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
      component: () => import('../components/AIChatPane.vue')
    },
    {
      path: '/setting',
      name: '设置',
      component: () => import('../components/SettingPane.vue')
    },
    {
      path: '/about',
      name: '关于',
      component: () => import('../components/AboutPane.vue')
    },
    {
      path: '/debug',
      name: '调试',
      component: () => import('../components/TaskPane.vue')
    }
  ]
});

export default router;

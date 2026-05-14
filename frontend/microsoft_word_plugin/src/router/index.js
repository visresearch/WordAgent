import { createRouter, createMemoryHistory } from "vue-router";

const routes = [
  {
    path: "/",
    name: "首页",
    redirect: "/aichat",
  },
  {
    path: "/aichat",
    name: "AI对话",
    component: () => import("../components/chat/AIChatPane.vue"),
  },
  {
    path: "/setting",
    name: "设置",
    component: () => import("../components/setting/SettingPane.vue"),
  },
  {
    path: "/about",
    name: "关于",
    component: () => import("../components/about/AboutPane.vue"),
  },
];

if (__DEV__) {
  routes.push({
    path: "/debug",
    name: "调试",
    component: () => import("../components/debug/DebugPane.vue"),
  });
}

const router = createRouter({
  history: createMemoryHistory(),
  routes,
});

export default router;

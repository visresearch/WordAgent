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
    path: "/debug",
    name: "调试",
    component: () => import("../components/debug/DebugPane.vue"),
  },
];

const router = createRouter({
  history: createMemoryHistory(),
  routes,
});

export default router;

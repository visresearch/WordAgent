/*
 * Copyright (c) WenCe Team. All rights reserved. Licensed under the MIT license.
 */

/* global Office */

import "../assets/main.css";
import { createApp } from "vue";
import App from "../App.vue";
import router from "../router";
import api from "../components/js/api.js";

/**
 * 检查是否需要在启动时自动显示 AI Chat 面板
 */
async function checkAutoShowPanel() {
  try {
    const settings = await api.getSettings();
    if (settings.showPanelOnStart) {
      // Microsoft Office 任务窗格默认已显示，不需要额外操作
      // 仅记录日志
      console.log("[Taskpane] 自动显示面板（showPanelOnStart=true）");
    }
  } catch (e) {
    console.warn("[Taskpane] 检查自动显示面板失败:", e);
  }
}

Office.onReady(() => {
  const app = createApp(App);
  app.use(router);
  app.mount("#app");

  // 检查是否需要自动显示面板
  checkAutoShowPanel();
});

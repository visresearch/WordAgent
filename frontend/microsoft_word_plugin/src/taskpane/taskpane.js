/*
 * Copyright (c) WenCe Team. All rights reserved. Licensed under the MIT license.
 */

/* global Office */

import "../assets/main.css";
import { createApp } from "vue";
import App from "../App.vue";
import router from "../router";

Office.onReady(() => {
  const app = createApp(App);
  app.use(router);
  app.mount("#app");
});

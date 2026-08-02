/* global URLSearchParams, window, document */

import "../assets/main.css";
import { createApp } from "vue";
import SettingPane from "../components/setting/SettingPane.vue";
import AboutPane from "../components/about/AboutPane.vue";
import { i18n, t } from "../i18n/index.js";

const views = {
  setting: {
    component: SettingPane,
    title: "windows.settings",
  },
  about: {
    component: AboutPane,
    title: "windows.about",
  },
};

const requestedView = new URLSearchParams(window.location.search).get("view");
const view = views[requestedView] ?? views.setting;

document.title = `${t(view.title)} - WenCe AI`;
createApp(view.component).use(i18n).mount("#app");

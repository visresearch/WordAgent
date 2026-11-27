/* global URLSearchParams, window, document */

import "../../../shared/assets/microsoft.css";
import { createApp } from "vue";
import SettingPane from "../components/setting/SettingPane.vue";
import AboutPane from "../components/about/AboutPane.vue";
import TemplatesPane from "../../../shared/components/TemplatesPane.vue";
import api from "../components/js/api.js";
import { i18n, t } from "../i18n/index.js";
import { createTemplateDialogRequester } from "../officeDialog.mjs";

const views = {
  setting: {
    component: SettingPane,
    title: "windows.settings",
  },
  about: {
    component: AboutPane,
    title: "windows.about",
  },
  templates: {
    component: TemplatesPane,
    title: "templates.title",
    props: {
      baseUrl: api.getConfig().baseURL,
      createDocument: createTemplateDialogRequester(),
      docxOnly: true,
    },
  },
};

const requestedView = new URLSearchParams(window.location.search).get("view");
const view = views[requestedView] ?? views.setting;

document.title = `${t(view.title)} - WenCe AI`;
createApp(view.component, view.props).use(i18n).mount("#app");

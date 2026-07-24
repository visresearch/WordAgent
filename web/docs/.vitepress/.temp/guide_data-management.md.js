import { ssrRenderAttrs, ssrRenderAttr } from "vue/server-renderer";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const _imports_0 = "/WordAgent/data.png";
const __pageData = JSON.parse('{"title":"数据管理","description":"","frontmatter":{},"headers":[],"relativePath":"guide/data-management.md","filePath":"guide/data-management.md"}');
const _sfc_main = { name: "guide/data-management.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}><h1 id="数据管理" tabindex="-1">数据管理 <a class="header-anchor" href="#数据管理" aria-label="Permalink to “数据管理”">​</a></h1><p><img${ssrRenderAttr("src", _imports_0)} alt=""></p><h2 id="清除缓存" tabindex="-1">清除缓存 <a class="header-anchor" href="#清除缓存" aria-label="Permalink to “清除缓存”">​</a></h2><p>因为加载项在解析图片的时候会产生图片缓存，所以用户可以手动清除缓存来释放存储空间。点击“清除缓存”按钮后，系统会删除所有已缓存的图片数据。</p><h2 id="长期记忆" tabindex="-1">长期记忆 <a class="header-anchor" href="#长期记忆" aria-label="Permalink to “长期记忆”">​</a></h2><p>长期记忆是AI的持久化记忆，影响AI对您的长期理解（越靠上越旧，越靠下越新）。每一行代表一条记忆，用户可以手动编辑长期记忆，也可以通过AI的提示词来影响AI的长期记忆。</p><h2 id="删除所有数据" tabindex="-1">删除所有数据 <a class="header-anchor" href="#删除所有数据" aria-label="Permalink to “删除所有数据”">​</a></h2><p>当用户想要完全重置加载项时，可以选择“删除所有数据”选项。点击此按钮后，系统会删除所有与加载项相关的数据，包括缓存、配置和历史记录等。这将使加载项恢复到初始状态，用户需要重新进行配置和授权。请谨慎使用此功能，因为它会导致所有数据的永久删除。</p></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("guide/data-management.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const dataManagement = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  dataManagement as default
};

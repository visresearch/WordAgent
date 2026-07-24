import { ssrRenderAttrs, ssrRenderAttr } from "vue/server-renderer";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const _imports_0 = "/WordAgent/QQ_group.jpg";
const __pageData = JSON.parse('{"title":"关于作者","description":"","frontmatter":{},"headers":[],"relativePath":"guide/about.md","filePath":"guide/about.md"}');
const _sfc_main = { name: "guide/about.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}><h1 id="关于作者" tabindex="-1">关于作者 <a class="header-anchor" href="#关于作者" aria-label="Permalink to “关于作者”">​</a></h1><p>与我交流：<a href="https://cmcblog.netlify.app/about/" target="_blank" rel="noreferrer">https://cmcblog.netlify.app/about/</a></p><h1 id="qq-交流群" tabindex="-1">QQ 交流群 <a class="header-anchor" href="#qq-交流群" aria-label="Permalink to “QQ 交流群”">​</a></h1><p><img${ssrRenderAttr("src", _imports_0)} alt=""></p></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("guide/about.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const about = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  about as default
};

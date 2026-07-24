import { ssrRenderAttrs, ssrRenderAttr } from "vue/server-renderer";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const _imports_0 = "/WordAgent/sponsor.jpg";
const __pageData = JSON.parse('{"title":"赞赏支持","description":"","frontmatter":{},"headers":[],"relativePath":"guide/sponsor.md","filePath":"guide/sponsor.md"}');
const _sfc_main = { name: "guide/sponsor.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}><h1 id="赞赏支持" tabindex="-1">赞赏支持 <a class="header-anchor" href="#赞赏支持" aria-label="Permalink to “赞赏支持”">​</a></h1><p>如果这个项目对你有帮助，欢迎扫码赞赏，你的支持是我持续维护的动力！</p><p><img${ssrRenderAttr("src", _imports_0)} alt=""></p></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("guide/sponsor.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const sponsor = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  sponsor as default
};

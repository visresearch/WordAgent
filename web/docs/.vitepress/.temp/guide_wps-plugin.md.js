import { ssrRenderAttrs, ssrRenderAttr } from "vue/server-renderer";
import { a as _imports_1, _ as _imports_2 } from "./pyQt.CkmmoHPa.js";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const _imports_0 = "/WordAgent/wps_install.png";
const __pageData = JSON.parse('{"title":"安装 WPS 加载项","description":"","frontmatter":{},"headers":[],"relativePath":"guide/wps-plugin.md","filePath":"guide/wps-plugin.md"}');
const _sfc_main = { name: "guide/wps-plugin.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}><h1 id="安装-wps-加载项" tabindex="-1">安装 WPS 加载项 <a class="header-anchor" href="#安装-wps-加载项" aria-label="Permalink to “安装 WPS 加载项”">​</a></h1><h2 id="前提条件" tabindex="-1">前提条件 <a class="header-anchor" href="#前提条件" aria-label="Permalink to “前提条件”">​</a></h2><ul><li>已完成 <a href="/WordAgent/guide/installation.html">安装方式</a> 中的后端服务部署</li><li>已安装 WPS Office 桌面版（Windows 或 Linux）</li><li>WPS版本要求：12.1.25225 及以上（建议使用最新版本以获得最佳兼容性）</li></ul><div class="info custom-block"><p class="custom-block-title">macOS 用户</p><p>当前 WPS 加载项自动安装流程面向 Windows 和 Linux。macOS 用户请使用 <a href="/WordAgent/guide/msword-plugin.html">Microsoft Word 加载项</a>。</p></div><h2 id="安装步骤" tabindex="-1">安装步骤 <a class="header-anchor" href="#安装步骤" aria-label="Permalink to “安装步骤”">​</a></h2><h3 id="_1-启动后端服务" tabindex="-1">1. 启动后端服务 <a class="header-anchor" href="#_1-启动后端服务" aria-label="Permalink to “1. 启动后端服务”">​</a></h3><p>双击运行 <code>wence_ai</code> 可执行文件（或通过源码启动），确保后端服务已正常运行。</p><h3 id="_2-安装加载项" tabindex="-1">2. 安装加载项 <a class="header-anchor" href="#_2-安装加载项" aria-label="Permalink to “2. 安装加载项”">​</a></h3><p>在后端服务 QT 界面中，点击 <strong>wence_word_plugin → 安装</strong> 按钮，系统会自动将加载项安装到 WPS 中。首次安装会弹出信任提示，选择 <strong>信任并安装</strong> 即可。</p><p><img${ssrRenderAttr("src", _imports_0)} alt=""></p><p><img${ssrRenderAttr("src", _imports_1)} alt="QT界面"></p><h3 id="_3-打开-wps-word" tabindex="-1">3. 打开 WPS Word <a class="header-anchor" href="#_3-打开-wps-word" aria-label="Permalink to “3. 打开 WPS Word”">​</a></h3><p>打开 WPS Word，首次加载时可能会弹出加载提示，选择 <strong>确认</strong> 即可。</p><p>安装成功后，你可以在 WPS Word 中看到文策 AI 的侧边面板和上边工具栏按钮。</p><p><img${ssrRenderAttr("src", _imports_2)} alt="WPS加载项"></p><h2 id="下一步" tabindex="-1">下一步 <a class="header-anchor" href="#下一步" aria-label="Permalink to “下一步”">​</a></h2><p>请参考 <a href="/WordAgent/guide/api-config.html">配置大模型服务</a>，添加并启用 DeepSeek V4 Pro 后开始使用。</p></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("guide/wps-plugin.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const wpsPlugin = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  wpsPlugin as default
};

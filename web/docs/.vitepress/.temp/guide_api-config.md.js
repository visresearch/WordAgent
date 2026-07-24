import { ssrRenderAttrs, ssrRenderAttr } from "vue/server-renderer";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const _imports_0 = "/WordAgent/model_setting.png";
const __pageData = JSON.parse('{"title":"配置大模型服务","description":"","frontmatter":{},"headers":[],"relativePath":"guide/api-config.md","filePath":"guide/api-config.md"}');
const _sfc_main = { name: "guide/api-config.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}><h1 id="配置大模型服务" tabindex="-1">配置大模型服务 <a class="header-anchor" href="#配置大模型服务" aria-label="Permalink to “配置大模型服务”">​</a></h1><p>文策 AI 需要连接支持工具调用的 LLM 服务。API Key、Base URL 和模型配置保存在本机，不会上传到文策 AI 的服务器。</p><h2 id="推荐服务商" tabindex="-1">推荐服务商 <a class="header-anchor" href="#推荐服务商" aria-label="Permalink to “推荐服务商”">​</a></h2><table tabindex="0"><thead><tr><th>服务商</th><th>推荐模型</th><th>获取地址</th></tr></thead><tbody><tr><td>DeepSeek 官方</td><td><strong>DeepSeek V4 Pro（推荐）</strong></td><td><a href="https://platform.deepseek.com/" target="_blank" rel="noreferrer">platform.deepseek.com</a></td></tr><tr><td>阿里云百炼</td><td>Qwen 3.6 Plus</td><td><a href="https://bailian.console.aliyun.com/" target="_blank" rel="noreferrer">bailian.console.aliyun.com</a></td></tr><tr><td>OpenRouter</td><td>多种 OpenAI 兼容模型</td><td><a href="https://openrouter.ai/" target="_blank" rel="noreferrer">openrouter.ai</a></td></tr></tbody></table><p>模型必须支持 Tool Calling。不同服务商展示的模型名称和模型 ID 可能不同，请以服务商控制台和“获取模型列表”的实际结果为准。</p><h2 id="使用-deepseek-v4-pro-配置" tabindex="-1">使用 DeepSeek V4 Pro 配置 <a class="header-anchor" href="#使用-deepseek-v4-pro-配置" aria-label="Permalink to “使用 DeepSeek V4 Pro 配置”">​</a></h2><p>以下以 <strong>DeepSeek 官方 API 提供的 DeepSeek V4 Pro</strong> 为例：</p><ol><li>启动文策 AI 后端，并在 WPS Word 或 Microsoft Word 中打开文策 AI 面板。</li><li>点击 <strong>设置 → 大模型 → 添加提供商</strong>。</li><li>填写提供商配置： <ul><li><strong>名称</strong>：<code>DeepSeek</code></li><li><strong>API Key</strong>：填写从 <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noreferrer">DeepSeek 官方平台</a> 获取的密钥</li><li><strong>Base URL</strong>：<code>https://api.deepseek.com</code></li><li><strong>API 类型</strong>：选择 <strong>OpenAI 兼容</strong></li></ul></li><li>点击 <strong>获取模型列表</strong>。</li><li>在返回的模型中找到 <strong>DeepSeek V4 Pro</strong>，点击添加并打开启用开关。</li><li>点击页面底部的 <strong>保存设置</strong>。</li><li>返回聊天页，在模型下拉列表中选择 <code>DeepSeek / DeepSeek V4 Pro</code>。</li></ol><p><img${ssrRenderAttr("src", _imports_0)} alt=""></p><div class="tip custom-block"><p class="custom-block-title">使用官方接口</p><p>请从 DeepSeek 官方平台创建 API Key，并使用官方 Base URL <code>https://api.deepseek.com</code>。不需要配置第三方中转服务。</p></div><h2 id="配置其他模型" tabindex="-1">配置其他模型 <a class="header-anchor" href="#配置其他模型" aria-label="Permalink to “配置其他模型”">​</a></h2><p>其他 OpenAI 兼容服务商使用相同步骤，只需替换名称、API Key、Base URL 和模型。Claude 原生接口请选择 <strong>Anthropic</strong> API 类型；DeepSeek 官方、Qwen 及其他 OpenAI 兼容接口选择 <strong>OpenAI 兼容</strong>。</p><h2 id="配置后没有模型" tabindex="-1">配置后没有模型 <a class="header-anchor" href="#配置后没有模型" aria-label="Permalink to “配置后没有模型”">​</a></h2><ul><li>确认 API Key 和 Base URL 没有多余空格。</li><li>确认 Base URL 是 API 地址，而不是服务商网站首页。</li><li>点击 <strong>获取模型列表</strong> 后，还需要将模型添加到“已添加模型”并启用。</li><li>保存设置后返回聊天页刷新模型列表。</li><li>如果服务商不支持模型列表接口，请确认其兼容协议和接口文档。</li></ul></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("guide/api-config.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const apiConfig = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  apiConfig as default
};

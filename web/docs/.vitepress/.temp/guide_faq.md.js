import { ssrRenderAttrs } from "vue/server-renderer";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const __pageData = JSON.parse('{"title":"常见问题","description":"","frontmatter":{},"headers":[],"relativePath":"guide/faq.md","filePath":"guide/faq.md"}');
const _sfc_main = { name: "guide/faq.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}><h1 id="常见问题" tabindex="-1">常见问题 <a class="header-anchor" href="#常见问题" aria-label="Permalink to “常见问题”">​</a></h1><h2 id="获取不到模型列表" tabindex="-1">获取不到模型列表 <a class="header-anchor" href="#获取不到模型列表" aria-label="Permalink to “获取不到模型列表”">​</a></h2><ul><li>检查 API Key 和 Base URL 是否正确，Base URL 应是 API 地址而不是服务商首页。</li><li>DeepSeek 官方 API 请选择 <strong>OpenAI 兼容</strong> API 类型，Base URL 使用 <code>https://api.deepseek.com</code>。</li><li>确认服务商账户可用且仍有额度。</li><li>如果使用代理，请在 <strong>设置 → 通用 → 网络代理</strong> 中确认地址和端口。</li></ul><p>详细配置见 <a href="/WordAgent/guide/api-config.html">配置大模型服务</a>。</p><h2 id="智能体没有生成文档" tabindex="-1">智能体没有生成文档 <a class="header-anchor" href="#智能体没有生成文档" aria-label="Permalink to “智能体没有生成文档”">​</a></h2><ul><li>确认当前使用 <strong>Agent</strong> 或 <strong>Plan</strong> 模式；Ask 模式不会修改文档。</li><li>确认模型支持 Tool Calling，推荐使用 <strong>DeepSeek V4 Pro</strong>。</li><li>查看文策 AI 桌面程序日志，确认是否存在 API 或工具调用错误。</li><li>如果界面出现待确认操作，需要点击 <strong>确认</strong> 才会写入 Word。</li></ul><h2 id="生成过程卡住或上下文过长" tabindex="-1">生成过程卡住或上下文过长 <a class="header-anchor" href="#生成过程卡住或上下文过长" aria-label="Permalink to “生成过程卡住或上下文过长”">​</a></h2><ul><li>点击停止按钮结束当前任务，再缩小处理范围或新建会话。</li><li>长文任务可改用 Plan 模式，或拆成“生成大纲 → 分节写作 → 总体审阅”。</li><li>暂时关闭不需要的 MCP Server 和 Skill，减少上下文与工具数量。</li></ul><h2 id="加载项在-word-中不显示" tabindex="-1">加载项在 Word 中不显示 <a class="header-anchor" href="#加载项在-word-中不显示" aria-label="Permalink to “加载项在 Word 中不显示”">​</a></h2><ul><li>确认文策 AI 后端仍在运行。</li><li>WPS 用户重新执行 <a href="/WordAgent/guide/wps-plugin.html">WPS 加载项安装</a>，并重启 WPS。</li><li>Microsoft Word 用户确认 HTTPS 服务、自签名证书和 <code>manifest.xml</code> 均已配置，参考 <a href="/WordAgent/guide/msword-plugin.html">Microsoft Word 加载项</a>。</li></ul><h2 id="macos-阻止打开-wence-ai" tabindex="-1">macOS 阻止打开 WenCe AI <a class="header-anchor" href="#macos-阻止打开-wence-ai" aria-label="Permalink to “macOS 阻止打开 WenCe AI”">​</a></h2><p>当前 macOS 应用通过 GitHub Release 分发。请在 Finder 中右键 <strong>WenCe AI.app → 打开</strong>；仍被阻止时，到 <strong>系统设置 → 隐私与安全性</strong> 中允许打开。请确认下载的是 Apple Silicon 对应的 <code>wence_ai-macos-arm64.dmg</code> 或 <code>.app.zip</code>。</p><h2 id="skill-上传提示同名" tabindex="-1">Skill 上传提示同名 <a class="header-anchor" href="#skill-上传提示同名" aria-label="Permalink to “Skill 上传提示同名”">​</a></h2><p>同名 Skill 不会被覆盖。请先备份需要保留的内容，再删除已有 Skill，然后重新上传。也可以点击 Skill 卡片上的文件夹按钮直接打开其目录。</p><h2 id="如何反馈其他问题" tabindex="-1">如何反馈其他问题 <a class="header-anchor" href="#如何反馈其他问题" aria-label="Permalink to “如何反馈其他问题”">​</a></h2><p>请在 <a href="https://github.com/visresearch/WordAgent/issues" target="_blank" rel="noreferrer">GitHub Issues</a> 提交问题，并附上系统、办公软件版本、模型名称、复现步骤和脱敏后的日志。</p></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("guide/faq.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const faq = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  faq as default
};

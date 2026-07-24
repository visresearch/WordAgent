import { ssrRenderAttrs, ssrRenderStyle } from "vue/server-renderer";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const __pageData = JSON.parse('{"title":"如何提问","description":"","frontmatter":{},"headers":[],"relativePath":"guide/how-to-ask.md","filePath":"guide/how-to-ask.md"}');
const _sfc_main = { name: "guide/how-to-ask.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}><h1 id="如何提问" tabindex="-1">如何提问 <a class="header-anchor" href="#如何提问" aria-label="Permalink to “如何提问”">​</a></h1><p>在加载项面板底部的输入框中，用自然语言描述你的写作需求即可。</p><h2 id="提问示例" tabindex="-1">提问示例 <a class="header-anchor" href="#提问示例" aria-label="Permalink to “提问示例”">​</a></h2><table tabindex="0"><thead><tr><th>场景</th><th>提问示例</th></tr></thead><tbody><tr><td>生成新文章</td><td>&quot;写一篇关于人工智能发展趋势的分析报告&quot;</td></tr><tr><td>联网搜索 + 写作</td><td>&quot;上网搜索伊朗战争相关新闻和资料，写一篇详细的战况分析报道&quot;</td></tr><tr><td>修改已有内容</td><td>&quot;把第3段改得更正式一些&quot;</td></tr><tr><td>扩展内容</td><td>&quot;对第2节的内容进行扩展，增加更多细节&quot;</td></tr><tr><td>生成大纲</td><td>&quot;帮我生成一个关于碳中和政策的文章大纲&quot;</td></tr></tbody></table><h2 id="使用技巧" tabindex="-1">使用技巧 <a class="header-anchor" href="#使用技巧" aria-label="Permalink to “使用技巧”">​</a></h2><ul><li><strong>选中文本再提问</strong>：先在 Word 中选中一段文本，然后提问，智能体会针对选中的内容进行操作</li><li><strong>描述尽量具体</strong>：说明你想要的文章类型、风格、字数等，效果更好</li><li><strong>分步进行</strong>：对于复杂的长文章，可以先生成大纲，再逐段扩展</li></ul><h2 id="演示视频" tabindex="-1">演示视频 <a class="header-anchor" href="#演示视频" aria-label="Permalink to “演示视频”">​</a></h2><iframe src="https://player.bilibili.com/player.html?bvid=BV1BYVP6VEyK&amp;page=1&amp;high_quality=1&amp;danmaku=0" title="文策 AI 演示视频" style="${ssrRenderStyle({ "width": "100%", "aspect-ratio": "16 / 9", "border": "0" })}" allowfullscreen></iframe></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("guide/how-to-ask.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const howToAsk = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  howToAsk as default
};

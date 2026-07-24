import { ssrRenderAttrs } from "vue/server-renderer";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const __pageData = JSON.parse('{"title":"","description":"","frontmatter":{"layout":"home","hero":{"name":"文策AI","text":"基于WPS/Microsoft Word加载项的AI辅助写作系统","tagline":"让写作有策略，让表达更智能","image":{"src":"/avatar.png","alt":""},"actions":[{"theme":"brand","text":"快速开始","link":"/guide/introduction"},{"theme":"alt","text":"使用说明","link":"/guide/wps-plugin"},{"theme":"alt","text":"GitHub","link":"https://github.com/visresearch/WordAgent"}]},"features":[{"icon":"🖥️","title":"跨平台适配","details":"同时支持 WPS 和 Microsoft Word，后端应用覆盖 Windows、Linux 和 macOS，让用户在熟悉的办公软件中直接使用 AI 写作能力。"},{"icon":"📝","title":"原生富文本生成","details":"智能体能够理解 Word 文章结构，生成符合 Word 文档结构的内容，支持文档样式、段落编辑，包括标题、正文、加粗、字体、缩进、行距等。"},{"icon":"🤖","title":"多智能体协作","details":"多智能体扮演不同专家角色（研究员、大纲师、写手、审阅者），以生成有深度的长文章为目标，协同完成写作任务。"},{"icon":"🔓","title":"自由开放","details":"支持自定义 API 或本地服务，兼容世界上大多数主流 LLM 服务商，用户可以根据需求选择不同的模型。"}]},"headers":[],"relativePath":"index.md","filePath":"index.md"}');
const _sfc_main = { name: "index.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("index.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const index = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  index as default
};

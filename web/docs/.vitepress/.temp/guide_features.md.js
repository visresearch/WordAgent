import { ssrRenderAttrs } from "vue/server-renderer";
import { useSSRContext } from "vue";
import { _ as _export_sfc } from "./plugin-vue_export-helper.1tPrXgE0.js";
const __pageData = JSON.parse('{"title":"功能按钮说明","description":"","frontmatter":{},"headers":[],"relativePath":"guide/features.md","filePath":"guide/features.md"}');
const _sfc_main = { name: "guide/features.md" };
function _sfc_ssrRender(_ctx, _push, _parent, _attrs, $props, $setup, $data, $options) {
  _push(`<div${ssrRenderAttrs(_attrs)}><h1 id="功能按钮说明" tabindex="-1">功能按钮说明 <a class="header-anchor" href="#功能按钮说明" aria-label="Permalink to “功能按钮说明”">​</a></h1><h2 id="智能体模式选择" tabindex="-1">智能体模式选择 <a class="header-anchor" href="#智能体模式选择" aria-label="Permalink to “智能体模式选择”">​</a></h2><p>文策 AI 提供三种智能体模式：</p><table tabindex="0"><thead><tr><th>模式</th><th>说明</th><th>适用场景</th></tr></thead><tbody><tr><td><strong>Agent模式</strong></td><td>一个 AI 智能体独立完成任务</td><td>简单写作、内容修改、快速问答</td></tr><tr><td><strong>Ask模式</strong></td><td>单 AI 智能体具有文档读取工具，不具有输出工具</td><td>复杂问题解答、文档分析、资料查询</td></tr><tr><td><strong>Plan模式</strong></td><td>多个专家智能体协作完成任务</td><td>复杂长文章、深度研究报告</td></tr></tbody></table><p>在聊天输入区的模式选择器中切换 Agent、Ask 或 Plan。</p><h2 id="主要操作" tabindex="-1">主要操作 <a class="header-anchor" href="#主要操作" aria-label="Permalink to “主要操作”">​</a></h2><ul><li><strong>发送按钮</strong>：输入提问后点击发送，智能体开始处理</li><li><strong>停止按钮</strong>：如果智能体正在生成内容，点击停止可中断当前任务</li><li><strong>设置按钮</strong>：打开设置面板，配置 API Key、模型等参数</li><li><strong>新建会话</strong>：清除当前对话历史，开始一个新的写作任务</li></ul><h2 id="文档操作工具" tabindex="-1">文档操作工具 <a class="header-anchor" href="#文档操作工具" aria-label="Permalink to “文档操作工具”">​</a></h2><p>智能体在工作过程中会自动调用工具，以下是各种模式智能体可用的工具列表：</p><table tabindex="0"><thead><tr><th>工具</th><th>功能</th><th>Agent</th><th>Ask</th><th>Plan</th></tr></thead><tbody><tr><td><strong>read_document</strong></td><td>读取文档中指定范围的内容</td><td>✅</td><td>✅</td><td>✅</td></tr><tr><td><strong>search_document</strong></td><td>查询某种格式或文字信息的段落位置</td><td>✅</td><td>✅</td><td>✅</td></tr><tr><td><strong>generate_document</strong></td><td>生成带格式的文档内容并插入到 Word 中</td><td>✅</td><td>❌</td><td>✅</td></tr><tr><td><strong>delete_document</strong></td><td>删除 Word 中指定范围的内容</td><td>✅</td><td>❌</td><td>✅</td></tr><tr><td><strong>run_sub_agent</strong></td><td>调用子智能体完成特定任务</td><td>✅</td><td>❌</td><td>❌</td></tr><tr><td><strong>mcp_tools</strong></td><td>调用已启用的 MCP 服务器工具</td><td>✅</td><td>视配置而定</td><td>✅</td></tr><tr><td><strong>load_skill_context</strong></td><td>加载已启用 Skill 的完整规则</td><td>✅</td><td>✅</td><td>✅</td></tr><tr><td><strong>list_file</strong></td><td>列出任务文件</td><td>✅</td><td>✅</td><td>✅</td></tr><tr><td><strong>read_file</strong></td><td>读取任务文件</td><td>✅</td><td>✅</td><td>✅</td></tr><tr><td><strong>edit_file</strong></td><td>编辑任务文件（不修改 Word 正文）</td><td>✅</td><td>✅</td><td>✅</td></tr><tr><td><strong>python_repl</strong></td><td>运行 Python 代码</td><td>✅</td><td>❌</td><td>❌</td></tr></tbody></table><div class="info custom-block"><p class="custom-block-title">说明</p><p>这些工具由智能体自动调用，你无需手动操作。智能体会根据你的提问自动判断需要使用哪些工具。</p></div></div>`);
}
const _sfc_setup = _sfc_main.setup;
_sfc_main.setup = (props, ctx) => {
  const ssrContext = useSSRContext();
  (ssrContext.modules || (ssrContext.modules = /* @__PURE__ */ new Set())).add("guide/features.md");
  return _sfc_setup ? _sfc_setup(props, ctx) : void 0;
};
const features = /* @__PURE__ */ _export_sfc(_sfc_main, [["ssrRender", _sfc_ssrRender]]);
export {
  __pageData,
  features as default
};

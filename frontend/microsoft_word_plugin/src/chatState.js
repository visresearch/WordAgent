import { reactive } from 'vue';

/** AI 流式对话进行中：用于禁用顶栏路由切换等（无提示，点击无效果） */
export const chatState = reactive({
  aiBusy: false,
});

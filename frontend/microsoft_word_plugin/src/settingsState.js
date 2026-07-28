import { reactive } from "vue";

// 全局共享的用户设置状态（跨路由页面共享）
export const settingsState = reactive({
  proofreadMode: "revision", // 兼容旧设置；文档预览固定使用 Word 原生修订
  enableLongTermMemory: false,
});

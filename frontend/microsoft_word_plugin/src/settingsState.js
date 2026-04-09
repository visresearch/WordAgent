import { reactive } from 'vue';

// 全局共享的用户设置状态（跨路由页面共享）
export const settingsState = reactive({
  proofreadMode: 'revision' // 'revision' = 批注模式, 'redblue' = 红蓝高亮模式
});

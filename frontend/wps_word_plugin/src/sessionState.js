import { reactive } from 'vue';

// 全局共享的 session 面板状态
export const sessionState = reactive({
  manualValue: null,  // null=由宽度自动决定, true/false=手动控制
  visible: false       // 当前是否实际可见（由 AIChatPane 同步）
});

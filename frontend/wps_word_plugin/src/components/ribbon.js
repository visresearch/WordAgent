// tskpane.Visible 先设置窗口可见再调整窗口大小,修复窗口大小设置无效的问题 20261013  by volun_leung
// btnShowAIChat函数 修复二次点击时界面不消失的问题                      20261013  by volun_leung

import Util from './js/util.js';
import { getActiveWindowId } from './js/windowContext.js';
import api from './js/api.js';
import { t } from '../i18n/index.js';

// WPS TaskPane 在加载项内共享，不能用活动文档窗口的 ID 判断是否已创建。
// windowId 仅用于固定面板的会话上下文，复用时必须沿用原 ID 发送信号。
function ensureTaskPane(storageKey, route, title, width) {
  const app = window.Application;
  const storage = app.PluginStorage;
  const taskPaneId = storage.getItem(storageKey);
  let taskPane = null;
  if (taskPaneId) {
    try {
      taskPane = app.GetTaskPane(taskPaneId);
    } catch (e) {
      console.warn('读取已缓存的面板失败:', e);
    }
  }
  if (taskPane) {
    return { taskPane, windowId: storage.getItem(`${storageKey}:windowId`), created: false };
  }

  const windowId = getActiveWindowId();
  taskPane = app.CreateTaskPane(
    Util.GetUrlPath() + Util.GetRouterHash() + `/${route}?windowId=${windowId}`,
    title
  );
  storage.setItem(storageKey, taskPane.ID);
  storage.setItem(`${storageKey}:windowId`, windowId);
  taskPane.DockPosition = app.Enum.msoCTPDockPositionRight;
  taskPane.Visible = true;
  taskPane.Width = width;
  return { taskPane, windowId, created: true };
}

function ensureAIChatPane() {
  return ensureTaskPane('ai_taskpane_id', 'aichat', t('windows.assistant'), window.devicePixelRatio * 500);
}

//这个函数在整个wps加载项中是第一个执行的
function OnAddinLoad(ribbonUI) {
  if (typeof window.Application.ribbonUI !== 'object') {
    window.Application.ribbonUI = ribbonUI;
  }

  if (typeof window.Application.Enum !== 'object') {
    // 如果没有内置枚举值
    window.Application.Enum = Util.WPS_Enum;
  }

  // 读取设置，如果 showPanelOnStart 为 true 则自动打开 AI Chat 面板
  checkAutoShowPanel();

  return true;
}

/**
 * 检查是否需要在启动时自动显示 AI Chat 面板
 */
async function checkAutoShowPanel() {
  try {
    const settings = await api.getSettings();

    if (settings.showPanelOnStart) {
      const { taskPane } = ensureAIChatPane();
      taskPane.Visible = true;
    }
  } catch (e) {
    console.warn('自动打开面板失败:', e);
  }
}

function OnAction(control) {
  const eleId = control.Id;
  switch (eleId) {
    case 'btnShowAIChat':
      {
        const { taskPane, created } = ensureAIChatPane();
        if (!created) {
          taskPane.Visible = !taskPane.Visible;
          if (taskPane.Visible) {
            taskPane.Width = window.devicePixelRatio * 500;
          }
        }
      }
      break;
    case 'btnShowSession':
      {
        // Session 已嵌入 AIChatPane，确保 AI Chat TaskPane 可见，然后发送切换信号
        const { taskPane, windowId } = ensureAIChatPane();
        taskPane.Visible = true;
        // 通过 localStorage 发送切换信号（storage 事件会在其他窗口/TaskPane 触发）
        try {
          localStorage.setItem(`wence_session_toggle:${windowId}`, String(Date.now()));
        } catch (e) {
          console.warn('session toggle 信号发送失败:', e);
        }
      }
      break;
    case 'btnShowSetting':
      {
        const windowId = getActiveWindowId();
        // 使用 WPS 原生对话框显示设置界面
        window.Application.ShowDialog(
          Util.GetUrlPath() + Util.GetRouterHash() + `/setting?windowId=${windowId}`,
          t('windows.settings'),
          900 * window.devicePixelRatio,
          600 * window.devicePixelRatio,
          false
        );
      }
      break;
    case 'btnShowAbout':
      {
        const windowId = getActiveWindowId();
        // 使用 WPS 原生对话框显示关于界面
        window.Application.ShowDialog(
          Util.GetUrlPath() + Util.GetRouterHash() + `/about?windowId=${windowId}`,
          t('windows.about'),
          900 * window.devicePixelRatio,
          600 * window.devicePixelRatio,
          false
        );
      }
      break;
    case 'btnShowDebug':
      {
        const { taskPane, created } = ensureTaskPane('debug_taskpane_id', 'debug', t('windows.debug'), 400);
        if (!created) {
          taskPane.Visible = !taskPane.Visible;
        }
      }
      break;
    default:
      break;
  }
  return true;
}

function GetImage(control) {
  const eleId = control.Id;
  switch (eleId) {
    case 'btnShowAIChat':
      return 'images/robot.svg';
    case 'btnShowSession':
      return 'images/session.svg';
    case 'btnShowSetting':
      return 'images/setting.svg';
    case 'btnShowAbout':
      return 'images/about.svg';
    case 'btnShowDebug':
      return 'images/debug.svg';
    default:
  }
  return 'images/newFromTemp.svg';
}

function OnGetEnabled(_control) {
  return true;
}

function OnGetVisible(control) {
  // 调试按钮只在开发环境显示，打包产物中隐藏
  if (control?.Id === 'btnShowDebug') {
    return import.meta.env.DEV;
  }
  return true;
}

function OnGetLabel(_control) {
  return '';
}

//这些函数是给wps客户端调用的
export default {
  OnAddinLoad,
  OnAction,
  GetImage,
  OnGetEnabled,
  OnGetVisible,
  OnGetLabel
};

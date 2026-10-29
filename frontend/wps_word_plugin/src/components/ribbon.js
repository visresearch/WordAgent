// tskpane.Visible 先设置窗口可见再调整窗口大小,修复窗口大小设置无效的问题 20261013  by volun_leung
// btnShowAIChat函数 修复二次点击时界面不消失的问题                      20261013  by volun_leung

import Util from './js/util.js';
import { getActiveWindowId } from './js/windowContext.js';
import api from './js/api.js';
import { t } from '../i18n/index.js';

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
    const windowId = getActiveWindowId();
    const settings = await api.getSettings();

    if (settings.showPanelOnStart) {
      // 自动创建并显示 AI Chat TaskPane
      let tsId = window.Application.PluginStorage.getItem(`ai_taskpane_id:${windowId}`);
      if (!tsId) {
        let tskpane = window.Application.CreateTaskPane(
          Util.GetUrlPath() + Util.GetRouterHash() + `/aichat?windowId=${windowId}`,
          t('windows.assistant')
        );
        let id = tskpane.ID;
        window.Application.PluginStorage.setItem(`ai_taskpane_id:${windowId}`, id);
        tskpane.DockPosition = window.Application.Enum.msoCTPDockPositionRight;
        tskpane.Visible = true;
        tskpane.Width = window.devicePixelRatio * 500;
        
      } else {
        let tskpane = window.Application.GetTaskPane(tsId);
        tskpane.Visible = true;
      }
    }
  } catch (e) {
    console.warn('自动打开面板失败:', e);
  }
}

function OnAction(control) {
  const eleId = control.Id;
  const windowId = getActiveWindowId();
  switch (eleId) {
    case 'btnShowAIChat':
      {
        let tsId = window.Application.PluginStorage.getItem(`ai_taskpane_id:${windowId}`);
        if (!tsId) {
          let tskpane = window.Application.CreateTaskPane(
            Util.GetUrlPath() + Util.GetRouterHash() + `/aichat?windowId=${windowId}`,
            t('windows.assistant')
          );
          let id = tskpane.ID;
          window.Application.PluginStorage.setItem(`ai_taskpane_id:${windowId}`, id);
          tskpane.DockPosition = window.Application.Enum.msoCTPDockPositionRight;
          tskpane.Visible = true;
          tskpane.Width = window.devicePixelRatio * 500;
          
        } else {
          let tskpane = window.Application.GetTaskPane(tsId);
          tskpane.Visible = !tskpane.Visible;
          tskpane.Width = window.devicePixelRatio * 500; 
          
        }
      }
      break;
    case 'btnShowSession':
      {
        // Session 已嵌入 AIChatPane，确保 AI Chat TaskPane 可见，然后发送切换信号
        let tsId = window.Application.PluginStorage.getItem(`ai_taskpane_id:${windowId}`);
        let tskpane = null;
        if (!tsId) {
          tskpane = window.Application.CreateTaskPane(
            Util.GetUrlPath() + Util.GetRouterHash() + `/aichat?windowId=${windowId}`,
            t('windows.assistant')
          );
          let id = tskpane.ID;
          window.Application.PluginStorage.setItem(`ai_taskpane_id:${windowId}`, id);
          tskpane.DockPosition = window.Application.Enum.msoCTPDockPositionRight;
          tskpane.Width = window.devicePixelRatio * 500;
          tskpane.Visible = true;
        } else {
          tskpane = window.Application.GetTaskPane(tsId);
          if (!tskpane.Visible) {
            tskpane.Visible = true;
          }
        }
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
        let tsId = window.Application.PluginStorage.getItem(`debug_taskpane_id:${windowId}`);
        if (!tsId) {
          let tskpane = window.Application.CreateTaskPane(
            Util.GetUrlPath() + Util.GetRouterHash() + `/debug?windowId=${windowId}`,
            t('windows.debug')
          );
          let id = tskpane.ID;
          window.Application.PluginStorage.setItem(`debug_taskpane_id:${windowId}`, id);
          tskpane.DockPosition = window.Application.Enum.msoCTPDockPositionRight;
          tskpane.Width = 400;
          tskpane.Visible = true;
        } else {
          let tskpane = window.Application.GetTaskPane(tsId);
          tskpane.Visible = !tskpane.Visible;
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

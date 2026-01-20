import Util from './js/util.js';

//这个函数在整个wps加载项中是第一个执行的
function OnAddinLoad(ribbonUI) {
  if (typeof window.Application.ribbonUI !== 'object') {
    window.Application.ribbonUI = ribbonUI;
  }

  if (typeof window.Application.Enum !== 'object') {
    // 如果没有内置枚举值
    window.Application.Enum = Util.WPS_Enum;
  }

  return true;
}

function OnAction(control) {
  const eleId = control.Id;
  switch (eleId) {
    case 'btnShowAIChat':
      {
        let tsId = window.Application.PluginStorage.getItem('ai_taskpane_id');
        if (!tsId) {
          let tskpane = window.Application.CreateTaskPane(
            Util.GetUrlPath() + Util.GetRouterHash() + '/aichat',
            '文策AI助手'
          );
          let id = tskpane.ID;
          window.Application.PluginStorage.setItem('ai_taskpane_id', id);
          tskpane.DockPosition = window.Application.Enum.msoCTPDockPositionRight;
          tskpane.Width = window.devicePixelRatio * 500; // 不知道为啥无效
          tskpane.Visible = true;
        } else {
          let tskpane = window.Application.GetTaskPane(tsId);
          tskpane.Width = window.devicePixelRatio * 500; // 不知道为啥无效
          tskpane.Visible = !tskpane.Visible;
        }
      }
      break;
    case 'btnShowSetting':
      {
        // 使用 WPS 原生对话框显示设置界面
        window.Application.ShowDialog(
          Util.GetUrlPath() + Util.GetRouterHash() + '/setting',
          '设置',
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
          Util.GetUrlPath() + Util.GetRouterHash() + '/about',
          '关于',
          900 * window.devicePixelRatio,
          600 * window.devicePixelRatio,
          false
        );
      }
      break;
    case 'btnShowDebug':
      {
        let tsId = window.Application.PluginStorage.getItem('debug_taskpane_id');
        if (!tsId) {
          let tskpane = window.Application.CreateTaskPane(
            Util.GetUrlPath() + Util.GetRouterHash() + '/debug',
            '调试面板'
          );
          let id = tskpane.ID;
          window.Application.PluginStorage.setItem('debug_taskpane_id', id);
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

function OnGetVisible(_control) {
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

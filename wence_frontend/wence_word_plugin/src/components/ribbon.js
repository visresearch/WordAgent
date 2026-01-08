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
          let tskpane = window.Application.CreateTaskPane(Util.GetUrlPath() + Util.GetRouterHash() + '/aichat', '文策AI助手');
          let id = tskpane.ID;
          window.Application.PluginStorage.setItem('ai_taskpane_id', id);
          tskpane.DockPosition = window.Application.Enum.msoCTPDockPositionRight;
          tskpane.Width = 350;
          tskpane.Visible = true;
        } else {
          let tskpane = window.Application.GetTaskPane(tsId);
          tskpane.Visible = !tskpane.Visible;
        }
      }
      break;
    case 'btnShowSetting':
      {
        let tsId = window.Application.PluginStorage.getItem('setting_taskpane_id');
        if (!tsId) {
          let tskpane = window.Application.CreateTaskPane(Util.GetUrlPath() + Util.GetRouterHash() + '/setting', '文策AI助手 - 设置');
          let id = tskpane.ID;
          window.Application.PluginStorage.setItem('setting_taskpane_id', id);
          tskpane.DockPosition = window.Application.Enum.msoCTPDockPositionRight;
          tskpane.Width = 350;
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
      return 'images/robot.png';
    case 'btnShowSetting':
      return 'images/setting.svg';
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

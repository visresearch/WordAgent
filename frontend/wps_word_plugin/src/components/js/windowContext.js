// PluginStorage is shared by WPS task panes. Only window-scoped keys belong here.
export function createChatId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  const hex = [...bytes].map(value => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

// Ribbon calls this on each action, before creating the owning window's pane.
export function getActiveWindowId() {
  const app = window.Application;
  const nativeId = app?.ActiveWindow?.Hwnd || app?.ActiveDocument?.DocID;
  if (!nativeId) throw new Error('无法识别当前 WPS 窗口');
  const key = `wence_window_id:${nativeId}`;
  let id = app.PluginStorage.getItem(key);
  if (!id) {
    id = createChatId();
    app.PluginStorage.setItem(key, id);
  }
  return id;
}

let paneWindowId;
export function getWindowId() {
  if (!paneWindowId) {
    const hash = globalThis.window?.location?.hash || '';
    const query = hash.includes('?') ? hash.slice(hash.indexOf('?') + 1) : globalThis.window?.location?.search || '';
    const params = new URLSearchParams(query);
    paneWindowId = params.get('windowId') || (globalThis.window?.Application ? getActiveWindowId() : createChatId());
  }
  return paneWindowId;
}

export function windowStorageKey(key) {
  return `${key}:${getWindowId()}`;
}

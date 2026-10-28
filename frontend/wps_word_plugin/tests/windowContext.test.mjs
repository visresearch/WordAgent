import assert from 'node:assert/strict';
import test from 'node:test';

test('WPS windows share PluginStorage but keep separate pane and conversation keys', async t => {
  const previous = globalThis.window;
  const storage = new Map();
  globalThis.window = {
    Application: {
      ActiveWindow: { Hwnd: 100 },
      PluginStorage: {
        getItem: key => storage.get(key),
        setItem: (key, value) => storage.set(key, value),
      },
    },
    location: { hash: '' },
  };
  t.after(() => { globalThis.window = previous; });
  const ribbon = await import('../src/components/js/windowContext.js?ribbon');
  const first = ribbon.getActiveWindowId();
  assert.equal(first, ribbon.getActiveWindowId());
  window.Application.ActiveWindow.Hwnd = 200;
  const second = ribbon.getActiveWindowId();
  assert.notEqual(first, second);
  // A pane keeps its owner even when another native window becomes active.
  window.location.hash = `#/aichat?windowId=${first}`;
  const a = await import('../src/components/js/windowContext.js?pane-a');
  storage.set(a.windowStorageKey('current_session_id'), 'session-a');
  window.location.hash = `#/aichat?windowId=${second}`;
  const b = await import('../src/components/js/windowContext.js?pane-b');
  assert.equal(storage.get(b.windowStorageKey('current_session_id')), undefined);
  storage.set(b.windowStorageKey('current_session_id'), 'session-b');
  assert.equal(storage.get(a.windowStorageKey('current_session_id')), 'session-a');
  assert.notEqual(a.windowStorageKey('ai_taskpane_id'), b.windowStorageKey('ai_taskpane_id'));
  assert.notEqual(a.windowStorageKey('wence_session_toggle'), b.windowStorageKey('wence_session_toggle'));
  window.location = { hash: '', search: `?windowId=${first}` };
  const filePane = await import('../src/components/js/windowContext.js?file-pane');
  assert.equal(filePane.getWindowId(), first);
});

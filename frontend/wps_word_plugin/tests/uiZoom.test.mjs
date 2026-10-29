import assert from 'node:assert/strict';
import test from 'node:test';
import { getUiRect, getUiViewport, getUiZoom, installUiZoom, UI_ZOOM_EVENT } from '../src/uiZoom.js';

function page(t, storedValue, storageAvailable = true) {
  const properties = new Map();
  const storage = new Map(storedValue === undefined ? [] : [['wence_wps_ui_zoom', storedValue]]);
  const win = new EventTarget();
  Object.assign(win, {
    innerWidth: 900,
    innerHeight: 600,
    localStorage: {
      getItem(key) {
        if (!storageAvailable) {
          throw new Error('Storage blocked');
        }
        return storage.get(key) ?? null;
      },
      setItem(key, value) {
        if (!storageAvailable) {
          throw new Error('Storage blocked');
        }
        storage.set(key, value);
      }
    }
  });
  const root = {
    style: {
      zoom: '',
      setProperty: (name, value) => properties.set(name, value),
      getPropertyValue: name => properties.get(name) || '',
      removeProperty: name => properties.delete(name)
    },
    getBoundingClientRect: () => ({ width: win.innerWidth / getUiZoom() })
  };
  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;
  globalThis.window = win;
  globalThis.document = { documentElement: root };
  const dispose = installUiZoom();
  t.after(() => {
    dispose();
    globalThis.window = previousWindow;
    globalThis.document = previousDocument;
  });
  return {
    win, root, storage, properties, dispose,
    send(type, values = {}) {
      const event = Object.assign(new Event(type, { cancelable: true }), values);
      win.dispatchEvent(event);
      return event;
    }
  };
}

test('Windows and Linux wheel deltas and units produce the same 10% zoom step', t => {
  const p = page(t);
  for (const [deltaY, deltaMode] of [[-120, 0], [-100, 0], [-53, 0], [-3, 1], [-1, 2]]) {
    assert.equal(p.send('wheel', { ctrlKey: true, deltaY, deltaMode }).defaultPrevented, true);
    assert.equal(getUiZoom(), 1.1);
    p.send('wheel', { ctrlKey: true, deltaY: -deltaY, deltaMode });
    assert.equal(getUiZoom(), 1);
  }
  for (const values of [
    { deltaY: 53 },
    { ctrlKey: true, deltaY: 0, deltaX: 53 },
    { ctrlKey: true, deltaY: NaN },
    ...['altKey', 'metaKey', 'shiftKey'].map(key => ({ ctrlKey: true, deltaY: -53, [key]: true }))
  ]) {
    assert.equal(p.send('wheel', values).defaultPrevented, false);
    assert.equal(getUiZoom(), 1);
  }
});

test('zoom stays within 50%-200%, suppresses native zoom at the limits, and Ctrl+0 resets it', t => {
  const p = page(t);
  for (let n = 0; n < 30; n++) {
    assert.equal(p.send('wheel', { ctrlKey: true, deltaY: -53 }).defaultPrevented, true);
  }
  assert.equal(getUiZoom(), 2);
  for (let n = 0; n < 30; n++) {
    assert.equal(p.send('wheel', { ctrlKey: true, deltaY: 53 }).defaultPrevented, true);
  }
  assert.equal(getUiZoom(), 0.5);
  assert.equal(p.send('keydown', { key: '0' }).defaultPrevented, false);
  assert.equal(getUiZoom(), 0.5);
  assert.equal(p.send('keydown', { ctrlKey: true, key: '0', code: 'Numpad0' }).defaultPrevented, true);
  assert.equal(getUiZoom(), 1);
  assert.equal(p.storage.get('wence_wps_ui_zoom'), '1');
});

test('saved zoom restores before rendering and changes in other WPS windows update layout', t => {
  const p = page(t, '1.5');
  assert.equal(getUiZoom(), 1.5);
  assert.equal(p.root.style.zoom, '1.5');
  assert.deepEqual(getUiViewport(), { width: 600, height: 400 });
  assert.equal(p.properties.get('--wps-viewport-height'), '400px');
  let changes = 0;
  p.win.addEventListener(UI_ZOOM_EVENT, () => changes++);
  p.send('storage', { key: 'unrelated', newValue: '2' });
  assert.equal(getUiZoom(), 1.5);
  p.send('storage', { key: 'wence_wps_ui_zoom', newValue: '1.2' });
  assert.equal(getUiZoom(), 1.2);
  assert.equal(changes, 1);
  assert.equal(p.storage.get('wence_wps_ui_zoom'), '1.5', 'a storage update must not write back');
  p.win.innerHeight = 900;
  p.send('resize');
  assert.equal(p.properties.get('--wps-viewport-height'), '750px');
  p.send('storage', { key: null, newValue: null });
  assert.equal(getUiZoom(), 1);
});

test('invalid saved values and storage failures do not break zoom', t => {
  const p = page(t, 'not-a-number', false);
  assert.equal(getUiZoom(), 1);
  p.send('wheel', { ctrlKey: true, deltaY: -53 });
  assert.equal(getUiZoom(), 1.1);
  for (const [value, expected] of [['bad', 1], ['-5', 1], ['9', 2], ['0.1', 0.5]]) {
    p.send('storage', { key: 'wence_wps_ui_zoom', newValue: value });
    assert.equal(getUiZoom(), expected);
  }
});

test('popup rectangles use layout coordinates in legacy and modern CEF at high DPI', t => {
  const p = page(t, '1.5');
  p.win.devicePixelRatio = 2;
  const expected = { left: 100, top: 120, right: 300, bottom: 150, width: 200, height: 30 };
  assert.deepEqual(getUiRect({ getBoundingClientRect: () => expected }), expected);
  // Standardized CSS zoom in newer Chromium includes root zoom in DOMRects.
  p.root.getBoundingClientRect = () => ({ width: p.win.innerWidth });
  const visual = Object.fromEntries(Object.entries(expected).map(([key, value]) => [key, value * 1.5]));
  assert.deepEqual(getUiRect({ getBoundingClientRect: () => visual }), expected);
});

test('disposing removes listeners and restores the previous document styles', t => {
  const p = page(t);
  p.send('wheel', { ctrlKey: true, deltaY: -53 });
  p.dispose();
  assert.equal(p.root.style.zoom, '');
  assert.equal(p.properties.size, 0);
  assert.equal(p.send('wheel', { ctrlKey: true, deltaY: -53 }).defaultPrevented, false);
  assert.equal(getUiZoom(), 1);
});

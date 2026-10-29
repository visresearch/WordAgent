import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { getUiRect, getUiViewport, getUiZoom, installUiZoom, UI_ZOOM_EVENT } from '../src/uiZoom.js';

const STORAGE_KEY = 'wence_wps_ui_zoom:window-a:aichat';

function page(t, storedValue, storageAvailable = true, location = { hash: '#/aichat?windowId=window-a' }) {
  const properties = new Map();
  const storage = new Map(storedValue === undefined ? [] : [[STORAGE_KEY, storedValue]]);
  const win = new EventTarget();
  Object.assign(win, {
    innerWidth: 900,
    innerHeight: 600,
    location,
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
  assert.equal(p.storage.get(STORAGE_KEY), '1');
});

test('saved pane zoom restores before rendering and ignores all external storage events', t => {
  const p = page(t, '1.5');
  assert.equal(getUiZoom(), 1.5);
  assert.equal(p.root.style.zoom, '1.5');
  assert.deepEqual(getUiViewport(), { width: 600, height: 400 });
  assert.equal(p.properties.get('--wps-viewport-height'), '400px');
  let changes = 0;
  p.win.addEventListener(UI_ZOOM_EVENT, () => changes++);
  p.send('storage', { key: 'unrelated', newValue: '2' });
  assert.equal(getUiZoom(), 1.5);
  for (const key of [STORAGE_KEY, 'wence_wps_ui_zoom', 'wence_wps_ui_zoom:window-b:aichat']) {
    p.send('storage', { key, newValue: '1.2' });
  }
  assert.equal(getUiZoom(), 1.5);
  assert.equal(changes, 0);
  assert.equal(p.storage.get(STORAGE_KEY), '1.5');
  p.win.innerHeight = 900;
  p.send('resize');
  assert.equal(p.properties.get('--wps-viewport-height'), '600px');
  p.send('storage', { key: null, newValue: null });
  assert.equal(getUiZoom(), 1.5);
});

test('invalid saved values and storage failures do not break zoom', t => {
  const p = page(t, 'not-a-number', false);
  assert.equal(getUiZoom(), 1);
  p.send('wheel', { ctrlKey: true, deltaY: -53 });
  assert.equal(getUiZoom(), 1.1);
});

for (const [value, expected] of [['bad', 1], ['-5', 1], ['9', 2], ['0.1', 0.5]]) {
  test(`saved pane zoom ${value} normalizes to ${expected}`, t => {
    page(t, value);
    assert.equal(getUiZoom(), expected);
  });
}

test('file-hosted panes resolve their owner from the URL query', t => {
  const p = page(t, '1.5', true, { pathname: '/plugin/aichat', search: '?windowId=window-a' });
  assert.equal(getUiZoom(), 1.5);
  p.send('wheel', { ctrlKey: true, deltaY: 53 });
  assert.equal(p.storage.get(STORAGE_KEY), '1.4');
});

test('panes without an owner do not use a shared zoom preference', t => {
  const p = page(t, '1.5', true, { hash: '#/aichat' });
  assert.equal(getUiZoom(), 1);
  p.send('wheel', { ctrlKey: true, deltaY: -53 });
  assert.equal(getUiZoom(), 1.1);
  assert.equal(p.storage.size, 1);
  assert.equal(p.storage.get(STORAGE_KEY), '1.5');
});

test('two WPS chat panes and settings zoom independently despite sharing localStorage', t => {
  const source = readFileSync(new URL('../src/uiZoom.js', import.meta.url), 'utf8').replace(/^export /gm, '');
  const storage = new Map([['wence_wps_ui_zoom', '1.8']]);
  const panes = [];
  const send = (win, type, values) => win.dispatchEvent(Object.assign(new Event(type, { cancelable: true }), values));
  function open(windowId, panel) {
    const win = new EventTarget();
    const properties = new Map();
    const root = { style: {
      zoom: '', setProperty: (key, value) => properties.set(key, value),
      getPropertyValue: key => properties.get(key) || '', removeProperty: key => properties.delete(key)
    } };
    Object.assign(win, {
      innerWidth: 900, innerHeight: 600,
      location: { hash: `#/${panel}?windowId=${windowId}` },
      localStorage: {
        getItem: key => storage.get(key) ?? null,
        setItem(key, value) {
          storage.set(key, value);
          for (const other of panes) {
            if (other.win !== win) send(other.win, 'storage', { key, newValue: value });
          }
        }
      }
    });
    // Each WPS WebView has its own JS realm but shares the same origin storage.
    const api = runInNewContext(`${source}\n({ installUiZoom, getUiZoom });`, {
      window: win, document: { documentElement: root }, Event, URLSearchParams
    });
    t.after(api.installUiZoom());
    const pane = { win, root, api };
    panes.push(pane);
    return pane;
  }
  const a = open('window-a', 'aichat');
  const b = open('window-b', 'aichat');
  const settings = open('window-a', 'setting');
  assert.deepEqual(panes.map(p => p.api.getUiZoom()), [1, 1, 1], 'old global preference is unused');
  send(a.win, 'wheel', { ctrlKey: true, deltaY: -120 });
  assert.deepEqual(panes.map(p => p.api.getUiZoom()), [1.1, 1, 1]);
  send(b.win, 'wheel', { ctrlKey: true, deltaY: 120 });
  send(settings.win, 'wheel', { ctrlKey: true, deltaY: -120 });
  send(settings.win, 'wheel', { ctrlKey: true, deltaY: -120 });
  assert.deepEqual(panes.map(p => p.api.getUiZoom()), [1.1, 0.9, 1.2]);
  send(a.win, 'keydown', { ctrlKey: true, key: '0' });
  assert.deepEqual(panes.map(p => p.api.getUiZoom()), [1, 0.9, 1.2]);
  assert.equal(open('window-b', 'aichat').api.getUiZoom(), 0.9);
  assert.equal(open('window-a', 'setting').api.getUiZoom(), 1.2);
  assert.equal(open('window-b', 'setting').api.getUiZoom(), 1);
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

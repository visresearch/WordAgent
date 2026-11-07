import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../src/main.js', import.meta.url), 'utf8')
  .replace(/^import .*;\n/gm, '')
  .replaceAll('import.meta.hot', 'hot');

function loadPage(hash, pathname = '/index.html', search = '') {
  const listeners = new Map();
  const disposals = [];
  const calls = [];
  const window = {
    location: { hash, pathname, search },
    addEventListener: (event, callback) => listeners.set(event, callback),
    removeEventListener: event => listeners.delete(event)
  };
  const router = {};
  const app = {
    use(plugin) {
      // The shared router redirects the hidden ribbon page to /aichat.
      if (plugin === router && ['', '#/'].includes(window.location.hash)) {
        window.location.hash = '#/aichat';
      }
    },
    mount() {}
  };
  vm.runInNewContext(source, {
    window, router, ribbon: {}, i18n: {}, App: {}, URLSearchParams,
    createApp: () => app,
    installUiZoom: () => () => calls.push('disposeZoom'),
    startMcpBridge: () => calls.push('start'),
    stopMcpBridge: () => calls.push('stop'),
    hot: { dispose: callback => disposals.push(callback) }
  });
  return { calls, listeners, disposals };
}

test('hidden ribbon pages do not register an MCP bridge even after the router redirects them to aichat', () => {
  for (const hash of ['', '#/', '#/aichat']) {
    const page = loadPage(hash);
    assert.deepEqual(page.calls, []);
    assert.equal(page.listeners.size, 0);
  }
});

test('settings, about and debug pages do not count as document sidebars', () => {
  for (const route of ['setting', 'about', 'debug']) {
    const page = loadPage(`#/${route}?windowId=window-a`);
    assert.deepEqual(page.calls, []);
    assert.equal(page.listeners.size, 0);
  }
});

test('explicit online and local-file AI sidebars connect, stop on unload and reconnect on restore', () => {
  for (const [hash, path, query] of [
    ['#/aichat?windowId=window-a', '/index.html', ''],
    ['', '/local/plugin/aichat', '?windowId=window-a']
  ]) {
    const page = loadPage(hash, path, query);
    assert.deepEqual(page.calls, ['start']);
    page.listeners.get('pagehide')();
    page.listeners.get('pageshow')();
    assert.deepEqual(page.calls, ['start', 'stop', 'start']);
  }
});

test('hot reload removes the old bridge and its lifecycle listeners', () => {
  const page = loadPage('#/aichat?windowId=window-a');
  for (const dispose of page.disposals) {
    dispose();
  }
  assert.deepEqual(page.calls, ['start', 'disposeZoom', 'stop']);
  assert.equal(page.listeners.size, 0);
});

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import { parse, compileScript } from 'vue/compiler-sfc';
import { computed, ref } from 'vue';
import locales from '../src/i18n/plugin-locales.js';
import api from '../src/components/js/api.js';

const source = readFileSync(new URL('../src/components/setting/PluginSetting.vue', import.meta.url), 'utf8');
const { descriptor } = parse(source);
const compiled = compileScript(descriptor, { id: 'plugin-setting-test' }).content;

function settings(api) {
  const context = vm.createContext({
    computed, ref, URL, api,
    onMounted() {}, onUnmounted() {},
    confirm() { assert.fail('Word deletion must not depend on a native browser dialog'); },
    t: key => locales['en-US'][key.replace('plugin.', '')]
  });
  const script = compiled.replace(/^import .*;\s*$/gm, '').replace('export default ', 'globalThis.component = ');
  vm.runInContext(script, context);
  return context.component.setup({}, { expose() {} });
}

test('delete calls the API immediately without confirmation', async () => {
  let requests = 0;
  const panel = settings({ async removePlugin(id) {
    assert.equal(id, 'ocr');
    requests++;
    return { operationId: 'remove-ocr', pluginId: id };
  } });
  const removal = panel.remove({ id: 'ocr', name: 'OCR' });
  assert.equal(requests, 1);
  await removal;
  assert.equal(panel.selectedOperation.value.action, 'remove');
});

test('delete runs once, polls completion, and refreshes installed status', async () => {
  let requests = 0;
  let resolveRequest;
  const panel = settings({
    removePlugin(id) {
      assert.equal(id, 'ocr');
      requests++;
      return new Promise(resolve => { resolveRequest = resolve; });
    },
    async getPluginOperation(id) {
      return { id, pluginId: 'ocr', action: 'remove', status: 'completed', logs: ['Removed ocr'] };
    },
    async getPlugins() { return { busy: [], plugins: [{ id: 'ocr', installed: false }] }; }
  });
  const first = panel.remove({ id: 'ocr', name: 'OCR' });
  assert.equal(panel.busy.value.includes('ocr'), true);
  await panel.remove({ id: 'ocr', name: 'OCR' });
  assert.equal(requests, 1);
  resolveRequest({ operationId: 'remove-ocr', pluginId: 'ocr' });
  await first;
  assert.equal(panel.selectedOperation.value.action, 'remove');
  await panel.poll();
  assert.equal(panel.message.value, 'Plugin removed');
  assert.equal(panel.messageError.value, false);
  assert.equal(panel.plugins.value[0].installed, false);
  assert.equal(panel.busy.value.length, 0);
});

test('failed delete request shows the error, unlocks the row, and allows retry', async () => {
  let requests = 0;
  const panel = settings({ async removePlugin() {
    if (++requests === 1) throw new Error('Plugin operation already running');
    return { operationId: 'retry', pluginId: 'ocr' };
  } });
  await panel.remove({ id: 'ocr', name: 'OCR' });
  assert.equal(panel.message.value, 'Plugin operation already running');
  assert.equal(panel.messageError.value, true);
  assert.equal(panel.busy.value.length, 0);
  await panel.remove({ id: 'ocr', name: 'OCR' });
  assert.equal(requests, 2);
  assert.equal(panel.selectedOperation.value.id, 'retry');
  assert.equal(panel.messageError.value, false);
});

test('failed background removal keeps the installed plugin and displays its logs', async () => {
  const panel = settings({
    async removePlugin() { return { operationId: 'failed', pluginId: 'ocr' }; },
    async getPluginOperation(id) { return { id, pluginId: 'ocr', action: 'remove', status: 'failed', error: 'File is in use', logs: ['File is in use'] }; },
    async getPlugins() { return { busy: [], plugins: [{ id: 'ocr', installed: true }] }; }
  });
  await panel.remove({ id: 'ocr', name: 'OCR' });
  await panel.poll();
  assert.equal(panel.plugins.value[0].installed, true);
  assert.equal(panel.message.value, 'File is in use');
  assert.equal(panel.messageError.value, true);
  assert.equal(panel.selectedOperation.value.logs[0], 'File is in use');
  assert.equal(panel.busy.value.length, 0);
});

test('removal API sends DELETE and unwraps operation metadata and backend errors', async t => {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push({ url, method: options.method });
    return new Response(JSON.stringify(calls.length === 1
      ? { operationId: 'op', pluginId: 'ocr' }
      : { detail: 'Plugin is not installed' }), {
      status: calls.length === 1 ? 200 : 404, headers: { 'Content-Type': 'application/json' }
    });
  });
  assert.deepEqual(await api.removePlugin('ocr'), { operationId: 'op', pluginId: 'ocr' });
  assert.equal(calls[0].method, 'DELETE');
  assert.equal(new URL(calls[0].url).pathname, '/api/plugins/ocr');
  await assert.rejects(api.removePlugin('ocr'), /Plugin is not installed/);
});

test('custom installation still tracks and completes after the delete flow change', async () => {
  const panel = settings({
    async installPlugin(source) {
      assert.equal(source, 'https://github.com/owner/demo');
      return { operationId: 'custom', pluginId: 'demo' };
    },
    async getPluginOperation(id) { return { id, pluginId: 'demo', action: 'install', status: 'completed', logs: [] }; },
    async getPlugins() { return { busy: [], plugins: [{ id: 'demo', installed: true }] }; }
  });
  panel.customSource.value = 'https://github.com/owner/demo';
  await panel.installCustom();
  assert.equal(panel.customBusy.value, true);
  await panel.poll();
  assert.equal(panel.customBusy.value, false);
  assert.equal(panel.customSource.value, '');
  assert.equal(panel.message.value, 'Plugin installed');
});

test('catalog installation locks before the server responds and prevents duplicate clicks', async () => {
  let finish;
  let calls = 0;
  const panel = settings({ installPlugin(id) {
    assert.equal(id, 'demo');
    calls++;
    return new Promise(resolve => { finish = resolve; });
  } });
  const installation = panel.install('demo');
  assert.equal(panel.busy.value.includes('demo'), true);
  await panel.install('demo');
  assert.equal(calls, 1);
  finish({ operationId: 'install-demo', pluginId: 'demo' });
  await installation;
  assert.equal(panel.selectedOperation.value.action, 'install');
});

test('catalog installation failure unlocks the row and exposes retry', async () => {
  let calls = 0;
  const panel = settings({ async installPlugin() {
    if (++calls === 1) throw new Error('Download failed');
    return { operationId: 'retry', pluginId: 'demo' };
  } });
  await panel.install('demo');
  assert.equal(panel.message.value, 'Download failed');
  assert.equal(panel.busy.value.includes('demo'), false);
  await panel.install('demo');
  assert.equal(calls, 2);
  assert.equal(panel.selectedOperation.value.id, 'retry');
});

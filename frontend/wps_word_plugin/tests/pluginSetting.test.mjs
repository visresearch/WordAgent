import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import { parse, compileScript } from 'vue/compiler-sfc';
import { computed, ref } from 'vue';
import locales from '../src/i18n/plugin-locales.js';

const source = readFileSync(new URL('../src/components/setting/PluginSetting.vue', import.meta.url), 'utf8');
const { descriptor } = parse(source);
const compiled = compileScript(descriptor, { id: 'plugin-setting-test' }).content;

function settings(api) {
  const context = vm.createContext({
    computed, ref, URL, api,
    onMounted() {},
    onUnmounted() {},
    t: key => locales['en-US'][key.replace('plugin.', '')]
  });
  const script = compiled.replace(/^import .*;\s*$/gm, '').replace('export default ', 'globalThis.component = ');
  vm.runInContext(script, context);
  return context.component.setup({}, { expose() {} });
}

test('custom installation rejects a package name before calling the API', async () => {
  let requests = 0;
  const panel = settings({ installPlugin() {
    requests++; 
  } });
  panel.customSource.value = 'wordagent-plugin-demo==1.0.0';
  await panel.installCustom();
  assert.equal(requests, 0);
  assert.equal(panel.customBusy.value, false);
  assert.equal(panel.messageError.value, true);
  assert.match(panel.message.value, /GitHub/);
});

test('failed compatibility check preserves the URL and logs, and permits a successful retry', async () => {
  let requestCount = 0;
  let ready = false;
  const url = 'https://github.com/owner/demo/tree/main/plugin';
  const panel = settings({
    async installPlugin(source) {
      assert.equal(source, url);
      return { operationId: `op-${++requestCount}`, pluginId: 'demo' };
    },
    async getPluginOperation(id) {
      return {
        id, pluginId: 'demo', action: 'install',
        status: ready ? 'completed' : 'failed',
        error: ready ? '' : 'Incompatible plugin API version 2',
        logs: ['Checking WordAgent plugin interface and compatibility']
      };
    },
    async getPlugins() {
      return { busy: [], plugins: ready ? [{ id: 'demo', installed: true }] : [] };
    }
  });
  panel.customSource.value = url;
  await panel.installCustom();
  assert.equal(panel.customBusy.value, true);
  assert.equal(panel.customSource.value, url);
  await panel.poll();
  assert.equal(panel.customBusy.value, false);
  assert.equal(panel.customSource.value, url);
  assert.match(panel.message.value, /Incompatible plugin API/);
  assert.equal(panel.selectedOperation.value.logs.length, 1);
  assert.equal(panel.plugins.value.length, 0);

  ready = true;
  await panel.installCustom();
  await panel.poll();
  assert.equal(panel.customBusy.value, false);
  assert.equal(panel.customSource.value, '');
  assert.equal(panel.messageError.value, false);
  assert.equal(panel.plugins.value[0].installed, true);
});

test('another completed operation does not unlock a custom installation in progress', async () => {
  const panel = settings({
    async installPlugin() {
      return { operationId: 'custom', pluginId: 'demo' }; 
    },
    async getPluginOperation(id) {
      return {
        id, pluginId: id, action: 'install', logs: [],
        status: id === 'custom' ? 'running' : 'completed'
      };
    },
    async getPlugins() {
      return { busy: ['demo'], plugins: [] }; 
    }
  });
  panel.customSource.value = 'https://github.com/owner/demo';
  await panel.installCustom();
  panel.operations.value.other = { id: 'other', status: 'running' };
  await panel.poll();
  assert.equal(panel.customBusy.value, true);
  assert.equal(panel.customSource.value, 'https://github.com/owner/demo');
  assert.equal(panel.message.value, '');
});

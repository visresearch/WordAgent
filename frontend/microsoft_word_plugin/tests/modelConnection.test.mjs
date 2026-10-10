import assert from 'node:assert/strict';
import test from 'node:test';
import { testModelConnection } from '../src/components/js/api.js';

const params = { baseUrl: 'https://provider.example', apiKey: 'test-key', apiType: 'anthropic', model: 'selected-model' };

test('connection test sends the current form and selected model and preserves millisecond latency', async (t) => {
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, 'http://localhost:3880/api/chat/providers/test-connection');
    assert.equal(options.method, 'POST');
    assert.deepEqual(JSON.parse(options.body), {
      base_url: params.baseUrl, api_key: params.apiKey, api_type: 'anthropic', model: 'selected-model'
    });
    return Response.json({ success: true, latency_ms: 123 });
  });
  assert.deepEqual(await testModelConnection(params), { success: true, latency_ms: 123 });
});

test('connection test surfaces provider and request validation errors', async (t) => {
  const fetch = t.mock.method(globalThis, 'fetch');
  fetch.mock.mockImplementation(async () => Response.json({ success: false, error: 'HTTP 401: Invalid API key' }));
  await assert.rejects(testModelConnection(params), /HTTP 401: Invalid API key/);
  fetch.mock.mockImplementation(async () => Response.json({ detail: [{ loc: ['body', 'base_url'], msg: 'Invalid URL' }] }, { status: 422 }));
  await assert.rejects(testModelConnection(params), /base_url: Invalid URL/);
});

test('connection test rejects missing latency but accepts a valid zero', async (t) => {
  const fetch = t.mock.method(globalThis, 'fetch', async () => Response.json({ success: true }));
  await assert.rejects(testModelConnection(params), /延迟/);
  fetch.mock.mockImplementation(async () => Response.json({ success: true, latency_ms: 0 }));
  assert.equal((await testModelConnection(params)).latency_ms, 0);
});

// Exercise the actual form behavior, including Office-friendly inline feedback.
import { readFileSync } from 'node:fs';
import { ref, watch, computed, nextTick, effectScope, createSSRApp } from 'vue';
import { renderToString } from 'vue/server-renderer';
import { parse } from '@vue/compiler-sfc';

const modelSource = readFileSync(new URL('../src/components/setting/ModelSetting.vue', import.meta.url), 'utf8');
const modelScript = modelSource.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/^import[\s\S]*?;\s*/gm, '');
function modelForm(t, connectionTest, providers = [{
  name: 'Local', baseUrl: ' http://localhost:8000/v1 ', apiKey: ' local-key ',
  apiType: 'openai', models: [{ id: 'qwen3-4b', name: 'Qwen', enabled: true }]
}]) {
  const component = new Function('ref', 'watch', 'computed', 'nextTick', 'api', 't', 'iconConnect', 'iconSetting', 'iconDelete', 'ModelParameterDialog',
    modelScript.replace('export default', 'return'))(ref, watch, computed, nextTick, { testModelConnection: connectionTest },
      (key, params = {}) => `${key} ${JSON.stringify(params)}`, '', '', '', {});
  const scope = effectScope();
  t.after(() => scope.stop());
  return scope.run(() => component.setup({ providers }, { emit() {} }));
}

test('模型参数按 provider 和 model 保存，取消关闭保留原值', t => {
  const vm = modelForm(t, () => {}, [
    { name: 'A', models: [{ id: 'same-id', enabled: true, parameters: { temperature: 0.5 } }] },
    { name: 'B', models: [{ id: 'same-id', enabled: true, parameters: { temperature: 0.8 } }] }
  ]);
  vm.openModelSettings(1, vm.localProviders.value[1].models[0]);
  assert.equal(vm.editingModel.value.parameters.temperature, 0.8);
  vm.editingTarget.value = null;
  assert.equal(vm.localProviders.value[1].models[0].parameters.temperature, 0.8);
  vm.openModelSettings(1, vm.localProviders.value[1].models[0]);
  const parameters = { temperature: 0, topP: 0.9, maxTokens: 8192, reasoningEffort: 'none' };
  vm.applyModelSettings(parameters);
  assert.deepEqual(vm.localProviders.value[1].models[0].parameters, parameters);
  assert.equal(vm.localProviders.value[0].models[0].parameters.temperature, 0.5);
  assert.equal(vm.editingTarget.value, null);
});

test('model form tests unsaved settings, prevents duplicate requests and shows model and latency', async t => {
  let finish;
  const requests = [];
  const vm = modelForm(t, params => {
    requests.push(params);
    return new Promise(resolve => { finish = resolve; });
  });
  vm.localProviders.value[0].baseUrl = ' http://localhost:9000/v1 ';
  const model = vm.localProviders.value[0].models[0];
  const testing = vm.testConnection(0, model);
  assert.equal(vm.isTestingModel(0, model.id), true);
  await vm.testConnection(0, model);
  assert.equal(requests.length, 1);
  assert.deepEqual(requests[0], {
    baseUrl: 'http://localhost:9000/v1', apiKey: 'local-key', apiType: 'openai', model: 'qwen3-4b'
  });
  finish({ success: true, latency_ms: 123 });
  await testing;
  assert.equal(vm.testingConnection.value, null);
  assert.equal(vm.connectionFeedback.value.error, false);
  assert.match(vm.connectionFeedback.value.message, /Qwen/);
  assert.match(vm.connectionFeedback.value.message, /123/);
});

test('model form renders failures and releases the loading state for a later retry', async t => {
  let count = 0;
  const vm = modelForm(t, async () => {
    if (++count === 1) throw new Error('HTTP 401');
    return { success: true, latency_ms: 0 };
  });
  const model = vm.localProviders.value[0].models[0];
  await vm.testConnection(0, model);
  assert.equal(vm.connectionFeedback.value.error, true);
  assert.match(vm.connectionFeedback.value.message, /HTTP 401/);
  assert.equal(vm.testingConnection.value, null);
  await vm.testConnection(0, model);
  assert.equal(vm.connectionFeedback.value.error, false);
});

test('missing model credentials are shown without sending a request', async t => {
  const vm = modelForm(t, () => assert.fail('must not send request'));
  vm.localProviders.value[0].apiKey = ' ';
  await vm.testConnection(0, vm.localProviders.value[0].models[0]);
  assert.equal(vm.connectionFeedback.value.error, true);
  assert.match(vm.connectionFeedback.value.message, /credentialsRequired/);
  assert.equal(vm.testingConnection.value, null);
});

test('connection feedback renders after the tested provider card, even when collapsed or reordered', async t => {
  const providers = ['First', 'Tested', 'Last'].map(name => ({
    name, apiKey: 'key', baseUrl: 'http://localhost:8000/v1',
    models: [{ id: 'model', name: 'Deepseek V4 Flash', enabled: true }], expanded: false
  }));
  const vm = modelForm(t, async () => ({ latency_ms: 1127 }), providers);
  const testedProvider = vm.localProviders.value[1];
  await vm.testConnection(1, testedProvider.models[0]);
  assert.equal(vm.connectionFeedback.value.provider, testedProvider);
  const renderForm = async () => {
    const app = createSSRApp({
      template: parse(modelSource).descriptor.template.content,
      setup: () => vm
    });
    app.config.globalProperties.$t = key => key;
    return renderToString(app);
  };
  const html = await renderForm();
  const feedbackIndex = html.indexOf('class="connection-feedback"');
  assert.equal(html.match(/class="connection-feedback"/g).length, 1);
  assert.ok(feedbackIndex > html.indexOf('provider-name">Tested'));
  assert.ok(feedbackIndex < html.indexOf('provider-name">Last'));
  // With collapsed cards, both provider-header and provider-card end before feedback.
  assert.match(html.slice(0, feedbackIndex).replace(/<!--[\s\S]*?-->/g, ''), /<\/div>\s*<\/div>\s*<div $/);
  assert.match(html, /Deepseek V4 Flash/);
  assert.match(html, /1127/);
  vm.localProviders.value.reverse();
  const reorderedHtml = await renderForm();
  assert.ok(reorderedHtml.indexOf('class="connection-feedback"') > reorderedHtml.indexOf('provider-name">Tested'));
  assert.ok(reorderedHtml.indexOf('class="connection-feedback"') < reorderedHtml.indexOf('provider-name">First'));
  vm.localProviders.value.splice(1, 1);
  assert.doesNotMatch(await renderForm(), /class="connection-feedback"/);
});

test('a removed provider cannot attach an in-flight result to the next card', async t => {
  let finish;
  const providers = ['Removed', 'Remaining'].map(name => ({
    name, apiKey: 'key', baseUrl: 'http://localhost:8000/v1', models: [{ id: 'same-model' }]
  }));
  const vm = modelForm(t, () => new Promise(resolve => { finish = resolve; }), providers);
  const request = vm.testConnection(0, vm.localProviders.value[0].models[0]);
  vm.localProviders.value.splice(0, 1);
  assert.equal(vm.isTestingModel(0, 'same-model'), false);
  finish({ latency_ms: 50 });
  await request;
  assert.equal(vm.connectionFeedback.value, null);
  assert.equal(vm.testingConnection.value, null);
});

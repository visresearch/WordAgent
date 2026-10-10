import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as vue from 'vue';
import api from '../src/components/js/api.js';

// Run the real component handlers with Vue reactivity. Office hosts may reject
// native dialogs, so any accidental confirm/alert call fails these tests.
function panel(t, file, props = {}, backend = {}, emit = () => {}) {
  const source = readFileSync(new URL(`../src/components/setting/${file}.vue`, import.meta.url), 'utf8');
  const script = source.match(/<script>([\s\S]*?)<\/script>/)[1];
  const locale = vue.ref('en-US');
  const context = {
    ...vue, api: backend, locale, settingsState: {},
    setLocale(value) { locale.value = value; },
    t: (key, values = {}) => `${key} ${JSON.stringify(values)}`,
    onMounted() {}, onBeforeUnmount() {}, setTimeout() {},
    console: { error() {} },
    confirm() { assert.fail('Native confirm is unavailable in Office'); },
    alert() { assert.fail('Native alert is unavailable in Office'); }
  };
  context.window = { confirm: context.confirm, alert: context.alert };
  for (const match of script.matchAll(/^import (\w+) from /gm)) {
    if (!(match[1] in context)) context[match[1]] = {};
  }
  vm.runInContext(script.replace(/^import[\s\S]*?;\s*/gm, '')
    .replace('export default', 'globalThis.component ='), vm.createContext(context));
  const scope = vue.effectScope();
  t.after(() => scope.stop());
  return scope.run(() => context.component.setup(props, { emit }));
}

const initialSettings = (language = 'zh-CN') => ({
  language, showPanelOnStart: true, enableLongTermMemory: false,
  customPrompt: 'Original prompt', proxy: { enabled: false, host: '', port: 0 },
  providers: [{ name: 'Demo', baseUrl: 'https://example.test', apiKey: 'key',
    models: [{ id: 'model', enabled: true, parameters: { maxTokens: 8192, reasoningEffort: 'medium' } }] }],
  mcpServers: []
});
const dataProps = () => vue.reactive({ cacheInfo: { dir: 'cache', fileCount: 3, totalSize: 4096 }, enableLongTermMemory: false });

test('clear prompt and overwrite template update the parent and persist via Save', async t => {
  let saved;
  const parent = panel(t, 'SettingPane', {}, {
    getSettings: async () => initialSettings(), saveSettings: async data => { saved = data; }
  });
  await parent.loadSettings();
  const child = panel(t, 'PersonalizationSetting', { settings: parent.personalizationSettings.value }, {},
    (event, value) => { assert.equal(event, 'update:settings'); parent.onPersonalizationChange(value); });
  child.clearCustomPrompt();
  assert.equal(child.localSettings.value.customPrompt, '');
  await parent.saveSettings();
  assert.equal(saved.customPrompt, '');
  child.applyTemplate({ prompt: 'New template' });
  child.applyTemplate({ prompt: 'Replacement template' });
  await parent.saveSettings();
  assert.equal(saved.customPrompt, 'Replacement template');
});

test('provider trash removes only the selected provider and saves its removal', async t => {
  let saved;
  const parent = panel(t, 'SettingPane', {}, {
    getSettings: async () => initialSettings(), saveSettings: async data => { saved = data; }
  });
  await parent.loadSettings();
  const child = panel(t, 'ModelSetting', { providers: parent.settings.providers }, {},
    (_, value) => parent.onProvidersChange(value));
  child.addNewProvider();
  child.removeProvider(1);
  await parent.saveSettings();
  assert.equal(saved.providers.length, 1);
  assert.equal(saved.providers[0].models[0].parameters.reasoningEffort, 'medium');
  child.removeProvider(0);
  await parent.saveSettings();
  assert.equal(saved.providers.length, 0);
});

test('adding fetched models preserves the open model list and provider identity after parent sync', async t => {
  const props = vue.reactive({ providers: initialSettings().providers });
  const child = panel(t, 'ModelSetting', props, {
    fetchAvailableModels: async () => ({ models: ['one', 'two'] })
  }, (_, providers) => { props.providers = providers.map(provider => ({ ...provider })); });
  await child.fetchModelsForProvider(0);
  const provider = child.localProviders.value[0];
  child.addModelFromAvailable(0, provider.availableModels[0]);
  await vue.nextTick();
  assert.equal(child.localProviders.value[0], provider);
  assert.equal(provider.availableModels.length, 2);
  child.addModelFromAvailable(0, provider.availableModels[1]);
  await vue.nextTick();
  assert.equal(provider.models.length, 3);
  assert.equal(props.providers[0].models.length, 3);
  child.hideAvailableModels(0);
  assert.equal(provider.availableModels.length, 0);
});

test('model discovery validation and API failures use visible inline feedback', async t => {
  const child = panel(t, 'ModelSetting', { providers: [{ name: 'Demo', models: [] }] }, {
    fetchAvailableModels: async () => { throw new Error('Provider unavailable'); }
  });
  await child.fetchModelsForProvider(0);
  assert.match(child.connectionFeedback.value.message, /credentialsRequired/);
  Object.assign(child.localProviders.value[0], { apiKey: 'key', baseUrl: 'https://example.test' });
  await child.fetchModelsForProvider(0);
  assert.match(child.connectionFeedback.value.message, /Provider unavailable/);
  assert.equal(child.connectionFeedback.value.provider, child.localProviders.value[0]);
  assert.equal(child.localProviders.value[0].fetchingModels, false);
});

test('skill deletion calls the backend once, updates the list, and protects builtins', async t => {
  let finish;
  let requests = 0;
  const child = panel(t, 'SkillSetting', {}, {
    deleteSkill(folder) { assert.equal(folder, 'custom'); requests++; return new Promise(resolve => { finish = resolve; }); }
  });
  child.skills.value = [{ folder: 'builtin', builtin: true }, { folder: 'custom' }];
  await child.removeSkillItem(child.skills.value[0]);
  assert.equal(requests, 0);
  const deletion = child.removeSkillItem(child.skills.value[1]);
  await child.removeSkillItem(child.skills.value[1]);
  assert.equal(requests, 1);
  assert.equal(child.skills.value.length, 2);
  finish({ success: true });
  await deletion;
  assert.equal(child.skills.value.length, 1);
  assert.equal(child.busyFolder.value, '');
});

test('skill deletion failures leave the skill installed and allow retry', async t => {
  let requests = 0;
  const child = panel(t, 'SkillSetting', {}, {
    async deleteSkill() { if (++requests === 1) throw new Error('Folder in use'); }
  });
  const skill = { folder: 'custom' };
  child.skills.value = [skill];
  await child.removeSkillItem(skill);
  assert.equal(child.skills.value.length, 1);
  assert.equal(child.messageType.value, 'error');
  assert.equal(child.message.value, 'Folder in use');
  assert.equal(child.busyFolder.value, '');
  await child.removeSkillItem(skill);
  assert.equal(child.skills.value.length, 0);
});

test('skill enable failure restores the checkbox to its previous state', async t => {
  const child = panel(t, 'SkillSetting', {}, {
    setSkillEnabled: async () => { throw new Error('Write denied'); }
  });
  const skill = { folder: 'custom', enabled: true };
  const event = { target: { checked: false } };
  await child.toggleSkill(skill, event);
  assert.equal(event.target.checked, true);
  assert.equal(skill.enabled, true);
  assert.equal(child.message.value, 'Write denied');
});

test('memory toggle stays consistent with global Save and resets on failure', async t => {
  let saved;
  let fail = false;
  const backend = { getSettings: async () => initialSettings(), getMemory: async () => 'Memory',
    async saveSettings(data) { if (fail) throw new Error('Offline'); saved = data; }
  };
  const parent = panel(t, 'SettingPane', {}, backend);
  await parent.loadSettings();
  const props = dataProps();
  const child = panel(t, 'DataManagementSetting', props, backend, (event, value) => {
    if (event === 'update:enable-long-term-memory') {
      parent.onMemoryEnabledChange(value);
      props.enableLongTermMemory = value;
    }
  });
  child.enableLongTermMemory.value = true;
  await child.saveMemoryToggle();
  await vue.nextTick();
  await parent.saveSettings();
  assert.equal(saved.enableLongTermMemory, true);
  fail = true;
  child.enableLongTermMemory.value = false;
  await child.saveMemoryToggle();
  assert.equal(child.enableLongTermMemory.value, true);
  assert.equal(parent.settings.enableLongTermMemory, true);
  assert.equal(child.resultSuccess.value, false);
  assert.equal(child.memoryToggleSaving.value, false);
});

test('cache clear works without native dialogs and failed scans preserve existing information', async t => {
  let deletions = 0;
  const child = panel(t, 'DataManagementSetting', dataProps(), {
    getMemory: async () => '', scanCache: async () => { throw new Error('Scan unavailable'); },
    clearCache: async () => { deletions++; return { deleted: 3 }; }
  });
  await child.scanCache();
  assert.equal(child.cacheFileCount.value, 3);
  assert.equal(child.resultSuccess.value, false);
  assert.equal(child.resultMessage.value, 'Scan unavailable');
  await child.clearCache();
  await child.clearCache();
  assert.equal(deletions, 1);
  assert.equal(child.cacheFileCount.value, 0);
  assert.equal(child.resultSuccess.value, true);
});

test('failed chat-data deletion reports failure and preserves the Vue confirmation for retry', async t => {
  const child = panel(t, 'DataManagementSetting', dataProps(), {
    getMemory: async () => '', clearAllSessions: async () => { throw new Error('Database locked'); }
  });
  child.showDeleteConfirm.value = true;
  child.confirmText.value = 'DELETE';
  await child.confirmDelete();
  assert.equal(child.resultSuccess.value, false);
  assert.match(child.resultMessage.value, /Database locked/);
  assert.equal(child.showDeleteConfirm.value, true);
  assert.equal(child.deleting.value, false);
});

test('all six language selections survive settings reload and Save', async t => {
  for (const language of ['zh-CN', 'en-US', 'id-ID', 'ja-JP', 'ko-KR', 'vi-VN']) {
    let saved;
    const child = panel(t, 'SettingPane', {}, {
      getSettings: async () => initialSettings(language), saveSettings: async data => { saved = data; }
    });
    await child.loadSettings();
    await child.saveSettings();
    assert.equal(child.settings.language, language);
    assert.equal(saved.language, language);
  }
});

test('settings load failure blocks empty overwrites and exposes retry', async t => {
  let fail = true;
  let saves = 0;
  const child = panel(t, 'SettingPane', {}, {
    async getSettings() { if (fail) throw new Error('Backend unavailable'); return initialSettings(); },
    async saveSettings() { saves++; }
  });
  await child.loadSettings();
  await child.saveSettings();
  assert.equal(saves, 0);
  assert.equal(child.settingsLoaded.value, false);
  assert.equal(child.saveMessage.value, 'Backend unavailable');
  fail = false;
  await child.loadSettings();
  await child.saveSettings();
  assert.equal(saves, 1);
});

test('invalid enabled MCP drafts prevent false successful saves and can be corrected', async t => {
  let saves = 0;
  const parent = panel(t, 'SettingPane', {}, {
    getSettings: async () => ({ ...initialSettings(), mcpServers: [{ name: 'Demo', config: { command: 'demo' }, enabled: true }] }),
    async saveSettings() { saves++; }
  });
  await parent.loadSettings();
  const child = panel(t, 'MCPserverSetting', { mcpServers: parent.settings.mcpServers }, {},
    (_, servers) => parent.onMcpServersChange(servers));
  const server = child.localServers.value[0];
  server.configSource = '{invalid';
  child.onConfigChange(server, 0);
  await parent.saveSettings();
  assert.equal(saves, 0);
  assert.equal(parent.saveSuccess.value, false);
  assert.match(parent.saveMessage.value, /jsonError/);
  server.configSource = '{"command":"updated"}';
  child.onConfigChange(server, 0);
  await parent.saveSettings();
  assert.equal(saves, 1);
  assert.equal(parent.settings.mcpServers[0].config.command, 'updated');
});

test('settings, model, MCP, skill, memory and cache actions use the existing backend endpoints', async t => {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push({ path: new URL(url).pathname, method: options.method, body: options.body });
    return Response.json({ success: true, models: [], skills: [], content: 'Memory' });
  });
  await api.getSettings();
  await api.saveSettings({ customPrompt: '' });
  await api.fetchAvailableModels({ baseUrl: 'https://example.test', apiKey: 'key' });
  await api.testMcpServer({ name: 'Test', config: { command: 'demo' } });
  await api.getSkills();
  await api.setSkillEnabled('my skill', false);
  await api.openSkillFolder('my skill');
  await api.deleteSkill('my skill');
  await api.uploadSkillPackage(new Blob(['zip']));
  await api.scanCache();
  await api.clearCache();
  await api.getMemory();
  await api.saveMemory('Updated');
  await api.clearAllSessions();
  assert.deepEqual(calls.map(({ method, path }) => `${method} ${path}`), [
    'GET /api/settings', 'POST /api/settings', 'POST /api/chat/providers/models',
    'POST /api/settings/mcp/test', 'GET /api/skills', 'PUT /api/skills/my%20skill/enabled',
    'POST /api/skills/my%20skill/open', 'DELETE /api/skills/my%20skill', 'POST /api/skills/upload',
    'GET /api/settings/cache/scan', 'DELETE /api/settings/cache/clear',
    'GET /api/settings/memory', 'POST /api/settings/memory', 'DELETE /api/sessions'
  ]);
  assert.deepEqual(JSON.parse(calls[1].body), { customPrompt: '' });
  assert.deepEqual(JSON.parse(calls[5].body), { enabled: false });
  assert.equal(calls[8].body.has('file'), true);
  assert.deepEqual(JSON.parse(calls[12].body), { content: 'Updated' });
});

test('settings and data APIs surface backend failures rather than returning empty or successful data', async t => {
  const fetch = t.mock.method(globalThis, 'fetch', async () => Response.json({ detail: 'Database locked' }, { status: 500 }));
  await assert.rejects(api.getSettings(), /Database locked/);
  await assert.rejects(api.clearAllSessions(), /Database locked/);
  fetch.mock.mockImplementation(async () => Response.json({ success: false, error: 'Deletion failed' }));
  await assert.rejects(api.clearAllSessions(), /Deletion failed/);
  fetch.mock.mockImplementation(async () => Response.json({ detail: [{ loc: ['body', 'proxy', 'port'], msg: 'Invalid port' }] }, { status: 422 }));
  await assert.rejects(api.saveSettings({ proxy: { port: -1 } }), /port: Invalid port/);
});

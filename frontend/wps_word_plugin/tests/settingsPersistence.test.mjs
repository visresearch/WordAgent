import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as vue from 'vue';

function panel(t, file, props, backend, emit = () => {}) {
  const source = readFileSync(new URL(`../src/components/setting/${file}.vue`, import.meta.url), 'utf8');
  const script = source.match(/<script>([\s\S]*?)<\/script>/)[1];
  const locale = vue.ref('zh-CN');
  const context = { ...vue, api: backend, locale, setLocale(value) {
    locale.value = value; 
  },
  t: key => key, onMounted() {}, setTimeout() {}, console: { error() {} } };
  for (const match of script.matchAll(/^import (\w+) from /gm)) {
    if (!(match[1] in context)) {
      context[match[1]] = {};
    }
  }
  vm.runInContext(script.replace(/import[\s\S]*?from\s+['"][^'"]+['"];?/g, '')
    .replace('export default', 'globalThis.component ='), vm.createContext(context));
  const scope = vue.effectScope();
  t.after(() => scope.stop());
  return scope.run(() => context.component.setup(props, { emit }));
}

test('memory switch loads from settings, submits only on Save, and survives reopening', async t => {
  let stored = { language: 'ja-JP', enableLongTermMemory: true, customPrompt: 'Original', providers: [] };
  const writes = [];
  const backend = { getSettings: async () => structuredClone(stored),
    saveSettings: async data => {
      writes.push(data); stored = JSON.parse(JSON.stringify(data)); 
    } };
  const parent = panel(t, 'SettingPane', {}, backend);
  assert.equal(parent.settings.enableLongTermMemory, undefined);
  await parent.loadSettings();
  assert.equal(parent.settings.language, 'ja-JP');
  assert.equal(parent.personalizationSettings.value.enableLongTermMemory, true);
  const child = panel(t, 'PersonalizationSetting', { settings: parent.personalizationSettings.value }, backend,
    (_, data) => parent.onPersonalizationChange(data));
  child.onMemoryEnabledChange(false);
  assert.equal(writes.length, 0);
  assert.equal(parent.settings.enableLongTermMemory, false);
  await parent.saveSettings();
  assert.equal(writes.length, 1);
  assert.equal(writes[0].enableLongTermMemory, false);
  assert.equal(writes[0].customPrompt, 'Original');
  assert.equal('proofreadMode' in writes[0], false);
  const reopened = panel(t, 'SettingPane', {}, backend);
  await reopened.loadSettings();
  assert.equal(reopened.personalizationSettings.value.enableLongTermMemory, false);
});

test('a failed settings read cannot submit a default disabled memory switch', async t => {
  let writes = 0;
  let online = false;
  const parent = panel(t, 'SettingPane', {}, {
    getSettings: async () => {
      if (!online) {
        throw new Error('offline');
      } return { enableLongTermMemory: true }; 
    },
    saveSettings: async () => {
      writes++; 
    }
  });
  await parent.loadSettings();
  await parent.saveSettings();
  assert.equal(parent.settings.enableLongTermMemory, undefined);
  assert.equal(parent.settingsLoaded.value, false);
  assert.equal(parent.saveMessage.value, 'settings.loadFailed');
  assert.equal(writes, 0);
  online = true;
  await parent.loadSettings();
  assert.equal(parent.settingsLoaded.value, true);
  assert.equal(parent.settings.enableLongTermMemory, true);
  assert.equal(parent.saveMessage.value, '');
});

test('failed Save retains the edited memory switch for retry', async t => {
  let fail = true;
  let stored = { enableLongTermMemory: true, providers: [] };
  const parent = panel(t, 'SettingPane', {}, {
    getSettings: async () => structuredClone(stored),
    saveSettings: async data => {
      if (fail) {
        throw new Error('offline');
      } stored = JSON.parse(JSON.stringify(data)); 
    }
  });
  await parent.loadSettings();
  parent.onPersonalizationChange({ customPrompt: '', enableLongTermMemory: false });
  await parent.saveSettings();
  assert.equal(stored.enableLongTermMemory, true);
  assert.equal(parent.settings.enableLongTermMemory, false);
  assert.equal(parent.saveSuccess.value, false);
  fail = false;
  await parent.saveSettings();
  assert.equal(stored.enableLongTermMemory, false);
  assert.equal(parent.saveSuccess.value, true);
});

test('memory content still loads and saves through the memory API independently', async t => {
  let saved;
  const child = panel(t, 'LongTermMemorySetting', { enabled: true }, {
    getMemory: async () => 'Known preferences', saveMemory: async content => {
      saved = content; 
    }
  });
  await child.loadMemory();
  assert.equal(child.memoryContent.value, 'Known preferences');
  child.memoryContent.value = 'Updated preferences';
  child.onMemoryInput();
  await child.saveMemory();
  assert.equal(saved, 'Updated preferences');
  assert.equal(child.memoryHasChanged.value, false);
});

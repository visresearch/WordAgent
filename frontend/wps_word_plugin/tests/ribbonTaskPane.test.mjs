import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const windowContextSource = readFileSync(new URL('../src/components/js/windowContext.js', import.meta.url), 'utf8');
const ribbonSource = readFileSync(new URL('../src/components/ribbon.js', import.meta.url), 'utf8');

function createHost() {
  const storage = new Map();
  const signals = new Map();
  const panes = new Map();
  const created = [];
  const app = {
    ActiveWindow: { Hwnd: 100 },
    ActiveDocument: { DocID: 1 },
    Enum: { msoCTPDockPositionRight: 2 },
    PluginStorage: {
      getItem: key => storage.get(key),
      setItem: (key, value) => storage.set(key, value)
    },
    GetTaskPane: id => panes.get(id),
    CreateTaskPane(url, title) {
      let visible = false;
      const pane = {
        ID: created.length + 1,
        url,
        title,
        get Visible() {
          return visible;
        },
        set Visible(value) {
          visible = value;
        },
        set Width(value) {
          assert.equal(visible, true, 'WPS only applies pane width after it becomes visible');
          this.width = value;
        }
      };
      panes.set(pane.ID, pane);
      created.push(pane);
      return pane;
    }
  };
  return {
    app, storage, signals, panes, created,
    switchDocument() {
      app.ActiveWindow.Hwnd += 100;
      app.ActiveDocument.DocID++;
    }
  };
}

function loadRibbon(host, getSettings = async () => ({ showPanelOnStart: true })) {
  const context = vm.createContext({
    window: { Application: host.app, devicePixelRatio: 1.5 },
    crypto: { randomUUID },
    localStorage: { setItem: (key, value) => host.signals.set(key, value) },
    Util: { GetUrlPath: () => 'http://localhost:3889', GetRouterHash: () => '/#' },
    api: { getSettings },
    t: key => key,
    console
  });
  vm.runInContext(windowContextSource.replace(/^export /gm, ''), context);
  vm.runInContext(ribbonSource.replace(/^import .*;\n/gm, '')
    .replace('import.meta.env.DEV', 'false')
    .replace('export default', 'globalThis.ribbon ='), context);
  return {
    click: id => context.ribbon.OnAction({ Id: id }),
    autoShow: () => context.checkAutoShowPanel()
  };
}

test('switching documents reuses the AI pane and sends the session signal to its original context', () => {
  const host = createHost();
  const ribbon = loadRibbon(host);
  ribbon.click('btnShowAIChat');
  const pane = host.created[0];
  const ownerId = new URL(pane.url.split('#')[1], 'http://localhost').searchParams.get('windowId');
  const sessionKey = `current_session_id:${ownerId}`;
  host.storage.set(sessionKey, 'existing-session');
  pane.width = 900;

  host.switchDocument();
  ribbon.click('btnShowSession');

  assert.equal(host.created.length, 1);
  assert.equal(pane.Visible, true);
  assert.equal(pane.width, 900, 'session toggle preserves the existing pane width');
  assert.deepEqual([...host.signals.keys()], [`wence_session_toggle:${ownerId}`]);
  assert.equal(host.storage.get(sessionKey), 'existing-session');
  assert.equal(host.storage.get('ai_taskpane_id'), pane.ID);
});

test('AI button toggles the same pane after switching documents', () => {
  const host = createHost();
  const ribbon = loadRibbon(host);
  ribbon.click('btnShowSession');
  const pane = host.created[0];
  host.switchDocument();
  ribbon.click('btnShowAIChat');
  assert.equal(pane.Visible, false);
  ribbon.click('btnShowAIChat');
  assert.equal(pane.Visible, true);
  assert.equal(pane.width, 750);
  assert.equal(host.created.length, 1);
});

test('delayed startup settings reuse a pane opened manually in another document', async () => {
  const host = createHost();
  let finishSettings;
  const settings = new Promise(resolve => {
    finishSettings = resolve;
  });
  const ribbon = loadRibbon(host, () => settings);
  const startup = ribbon.autoShow();
  ribbon.click('btnShowAIChat');
  const pane = host.created[0];
  host.switchDocument();
  finishSettings({ showPanelOnStart: true });
  await startup;
  assert.equal(host.created.length, 1);
  assert.equal(pane.Visible, true);

  // Ribbon pages share PluginStorage, so reloading one must also reuse the pane.
  const reloaded = loadRibbon(host);
  await reloaded.autoShow();
  reloaded.click('btnShowSession');
  assert.equal(host.created.length, 1);
  const ownerId = host.storage.get('ai_taskpane_id:windowId');
  assert.equal(host.signals.has(`wence_session_toggle:${ownerId}`), true);
});

test('a missing cached pane is recreated with a matching session signal context', () => {
  const host = createHost();
  const ribbon = loadRibbon(host);
  ribbon.click('btnShowAIChat');
  host.panes.clear();
  host.switchDocument();
  ribbon.click('btnShowSession');
  const replacement = host.created[1];
  const ownerId = host.storage.get('ai_taskpane_id:windowId');
  assert.equal(host.created.length, 2);
  assert.equal(host.storage.get('ai_taskpane_id'), replacement.ID);
  assert.equal(replacement.url.endsWith(`windowId=${ownerId}`), true);
  assert.equal(host.signals.has(`wence_session_toggle:${ownerId}`), true);
});

test('debug button reuses its own pane across documents without replacing the AI pane', () => {
  const host = createHost();
  const ribbon = loadRibbon(host);
  ribbon.click('btnShowAIChat');
  ribbon.click('btnShowDebug');
  const debug = host.created[1];
  host.switchDocument();
  ribbon.click('btnShowDebug');
  assert.equal(debug.Visible, false);
  ribbon.click('btnShowDebug');
  assert.equal(debug.Visible, true);
  assert.equal(host.created.length, 2);
  assert.notEqual(host.storage.get('ai_taskpane_id'), host.storage.get('debug_taskpane_id'));
});

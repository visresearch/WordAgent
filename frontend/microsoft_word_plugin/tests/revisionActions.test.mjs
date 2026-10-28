import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import { compileTemplate, parse } from '@vue/compiler-sfc';
import { createSSRApp } from 'vue';
import { renderToString } from 'vue/server-renderer';

function component(file, bindings) {
  const source = readFileSync(new URL(`../src/components/chat/${file}.vue`, import.meta.url), 'utf8');
  const script = source.match(/<script>([\s\S]*?)<\/script>/)[1];
  const context = {
    ...bindings, t: key => key, performance,
    console: { log() {}, warn() {}, error() {} }
  };
  for (const match of script.matchAll(/^import (\w+) from /gm)) {
    if (!(match[1] in context)) context[match[1]] = {};
  }
  vm.runInContext(script.replace(/^import[\s\S]*?;\s*/gm, '')
    .replace('export default', 'globalThis.component ='), vm.createContext(context));
  const options = context.component;
  return { source, options, instance: Object.assign(options.data(), options.methods, { scrollToBottom() {} }) };
}

test('删除成功但修订读取失败时保留实际删除数，要求重读且不自动Undo', async () => {
  const sent = [];
  const { instance } = component('AIChatPane', {
    api: { wsManager: { send: async data => sent.push(data), clearDocumentCache() {} } },
    beginTrackedEdit: async () => ({}), abortTrackedEdit: async () => {},
    deleteDocxPara: async () => ({ success: true, deletedCount: 3, missingParaIDs: [] }),
    finishTrackedEdit: async () => { throw new Error('Cannot load tracked changes'); },
    Word: { run() { assert.fail('Must not undo a completed deletion'); } }
  });
  assert.equal(await instance._applyImmediateDelete({ docId: 0, paraIDs: [10, 20, 30], requestId: 'delete-1' }), false);
  assert.equal(sent.length, 1);
  assert.equal(sent[0].deletedCount, 3);
  assert.equal(sent[0].requiresRead, true);
  assert.equal(sent[0].requestId, 'delete-1');
  assert.match(sent[0].error, /Cannot load/);
});

test('接受和拒绝使用同一文档结算流程，生成中和重复点击不会执行', async () => {
  let finish;
  let calls = 0;
  const { instance } = component('AIChatPane', {
    api: { wsManager: { clearDocumentCache() {} } },
    getPendingRevisionCount: async () => 0,
    hasRevisionBatch: () => false,
    settleDocumentRevisions: action => {
      assert.equal(action, 'reject');
      calls++;
      return new Promise(resolve => { finish = resolve; });
    }
  });
  instance.isLoading = true;
  await instance.acceptPendingRevisions();
  assert.equal(calls, 0);
  instance.isLoading = false;
  const pending = { _revisionBatchId: 'batch', msg: { _revisionBatchId: 'batch' } };
  instance.pendingEdits = [pending];
  const rejecting = instance.rejectPendingRevisions();
  await Promise.resolve();
  await instance.acceptPendingRevisions();
  assert.equal(calls, 1);
  finish({ success: true, handled: 1, settledBatchIds: ['batch'] });
  await rejecting;
  assert.equal(pending.msg._revisionBatchId, null);
  assert.equal(instance.pendingEdits.length, 0);
  assert.equal(instance.settlingRevisions, false);
});

test('只有文档中的AI修订也显示接受和拒绝；生成过程中按钮可见且禁用', async () => {
  const { source, options } = component('ChatInput', {});
  const descriptor = parse(source).descriptor;
  const compiled = compileTemplate({ source: descriptor.template.content, filename: 'ChatInput.vue', id: 'test' });
  const context = { ...await import('vue') };
  const code = compiled.code.replace(/^import \{(.*?)\} from "vue"/m, (_, names) =>
    `const { ${names.replace(/\bas\b/g, ':')} } = globalThis;`).replace('export function render', 'function render');
  vm.runInContext(`${code}\nglobalThis.render = render;`, vm.createContext(context));
  options.render = context.render;
  const app = createSSRApp(options, { pendingRevisionCount: 2, isLoading: true });
  app.config.globalProperties.$t = key => key;
  const html = await renderToString(app);
  assert.match(html, /class="pending-btn accept-btn" disabled/);
  assert.match(html, /class="pending-btn reject-btn" disabled/);
  assert.match(html, /chat.acceptRevision/);
  assert.match(html, /chat.rejectRevision/);
});

test('停止会跳过尚未开始的 Word 文档操作，并冻结该轮聊天内容', async t => {
  for (const type of ['edit_document', 'delete_document', 'insert_break', 'json']) {
    await t.test(type, async () => {
      let events;
      let releaseQueue;
      let writes = 0;
      const { instance } = component('AIChatPane', {
        api: { chatStream(message, options) { events = options; return { abort() {} }; } },
        assertRevisionDocumentTarget() {},
        insertBreakAfterParagraph: async () => { writes++; return { success: true }; }
      });
      instance._refreshRevisionPreview = async () => {};
      for (const method of ['_applyImmediateEdit', '_applyImmediateDelete', '_applyImmediateInsertion']) {
        instance[method] = async () => { writes++; return true; };
      }
      instance.currentSessionId = 'session-a';
      instance._insertQueue = new Promise(resolve => { releaseQueue = resolve; });
      instance._sendStreamRequest('edit', null);
      events.onMessage({ type: 'thinking', content: 'original thinking' });
      events.onMessage({ type, docId: 0, paraID: '12', paraIDs: ['12'],
        runs: [], content: type === 'json' ? { insertParaID: '12', paragraphs: [] } : undefined });
      instance.stopGeneration();
      const assistant = instance.messages[0];
      const snapshot = JSON.stringify(assistant);
      events.onMessage({ type: 'thinking', content: 'late thinking' });
      events.onMessage({ type: 'text', content: 'late answer' });
      releaseQueue();
      await instance._insertQueue;
      assert.equal(writes, 0);
      assert.equal(JSON.stringify(assistant), snapshot);
      assert.equal(assistant.thinkingDone, true);
      assert.equal(assistant.contentParts.some(part => part.loading), false);
    });
  }
});

test('等待 Office.js 开启修订期间停止，不再提交文档写入或回传旧结果', async t => {
  for (const method of ['_applyImmediateDelete', '_applyImmediateEdit', '_applyImmediateInsertion']) {
    await t.test(method, async () => {
      let finishTracking;
      let writes = 0;
      let aborted = 0;
      const sent = [];
      const write = async () => {
        writes++;
        return { success: true, deletedCount: 1, deletedParaIDs: ['12'], missingParaIDs: [], insertedParaIDs: [] };
      };
      const { instance } = component('AIChatPane', {
        api: { wsManager: { send: async data => sent.push(data), clearDocumentCache() {}, reportToolProgress() {} } },
        beginTrackedEdit: () => new Promise(resolve => { finishTracking = resolve; }),
        abortTrackedEdit: async () => { aborted++; },
        finishTrackedEdit: async () => ({ batchId: 'batch-1', revisionCount: 1 }),
        editDocxParagraph: write, deleteDocxPara: write, generateDocxFromJSON: write
      });
      const msg = { contentParts: [] };
      const operation = instance[method]({ docId: 0, paraID: '12', paraIDs: ['12'], runs: [],
        insertParaID: '12', documentJson: { paragraphs: [] }, requestId: 'operation-1', msg, streamMessage: msg });
      assert.equal(typeof finishTracking, 'function');
      msg._streamStopped = true;
      finishTracking({});
      await operation;
      assert.equal(writes, 0);
      assert.equal(aborted, 1);
      assert.deepEqual(sent, []);
    });
  }
});

test('JSON 无效或缺失插入 ID 时不回退纯文本写入', async () => {
  const { instance } = component('AIChatPane', {});
  let errors = 0;
  let writes = 0;
  instance._showPendingActionError = () => { errors++; };
  instance._refreshRevisionPreview = async () => {};
  instance._insertPlainText = async () => { writes++; };
  instance._applyImmediateInsertion = async () => { writes++; };
  for (const msg of [
    { documentJson: { paragraphs: [] } },
    { documentJson: { tables: [] }, _insertParaID: 0 },
    { content: '```json\n{invalid\n```' },
  ]) await instance.insertToWord(msg);
  assert.equal(errors, 3);
  assert.equal(writes, 0);
});

test('停止后仍可主动将已生成的内容插入 Word', async () => {
  let writes = 0;
  const { instance } = component('AIChatPane', {
    api: { wsManager: { clearDocumentCache() {} } },
    beginTrackedEdit: async () => ({}),
    finishTrackedEdit: async () => ({ batchId: 'manual-insert', revisionCount: 1 }),
    generateDocxFromJSON: async () => { writes++; return { success: true, insertedParaIDs: [] }; }
  });
  const msg = { _streamStopped: true, contentParts: [] };
  assert.equal(await instance._applyImmediateInsertion({ documentJson: { paragraphs: [] }, docId: 0, insertParaID: '0', msg }), true);
  assert.equal(writes, 1);
  assert.equal(instance.pendingInsertions.length, 1);
});

import assert from 'node:assert/strict';
import test from 'node:test';
import { chatStream, parseDocumentRange, wsManager } from '../src/components/js/api.js';

async function socket(t, handler) {
  t.mock.method(console, 'log', () => {});
  t.mock.method(console, 'error', () => {});
  const previous = globalThis.WebSocket;
  let ws;
  globalThis.WebSocket = class {
    constructor() { ws = this; this.sent = []; }
    send(data) { this.sent.push(JSON.parse(data)); }
    close() { this.closed = true; this.onclose?.({ code: 1000, reason: 'test close' }); }
  };
  wsManager.ws = null;
  wsManager.connected = false;
  wsManager.onMessage = handler;
  t.after(() => {
    globalThis.WebSocket = previous;
    wsManager.ws = null;
    wsManager.connected = false;
    wsManager.onMessage = null;
  });
  const connected = wsManager.connect();
  ws.onopen();
  await connected;
  return ws;
}

test('an edit dispatch exception is returned with its requestId instead of silently waiting 60 seconds', async t => {
  const ws = await socket(t, () => { throw new Error('Native API unavailable'); });
  ws.onmessage({ data: JSON.stringify({ type: 'edit_document', requestId: 'edit-1', docId: 9, paraID: 101 }) });
  assert.equal(ws.sent[0].type, 'frontend_tool_progress');
  const result = ws.sent[1];
  assert.equal(result.type, 'edit_document_response');
  assert.equal(result.requestId, 'edit-1');
  assert.equal(result.success, false);
  assert.equal(result.requiresRead, true);
  assert.match(result.error, /Native API unavailable/);
});

test('read and search dispatch failures return the correct response type', async t => {
  const ws = await socket(t, () => { throw new Error('UI handler failed'); });
  for (const [type, response] of [['read_document', 'document_response'], ['search_document', 'query_response']]) {
    ws.onmessage({ data: JSON.stringify({ type, docId: 9 }) });
    assert.equal(ws.sent.at(-1).type, response);
    assert.match(ws.sent.at(-1).error, /UI handler failed/);
  }
});

test('an asynchronous handler failure also reports failure, while ordinary chat messages produce no tool reply', async t => {
  const ws = await socket(t, async () => { throw new Error('Async handler failed'); });
  ws.onmessage({ data: JSON.stringify({ type: 'edit_document', requestId: 'edit-2', docId: 9, paraID: 101 }) });
  await Promise.resolve();
  assert.equal(ws.sent.at(-1).type, 'edit_document_response');
  assert.equal(ws.sent.at(-1).requestId, 'edit-2');
  const count = ws.sent.length;
  ws.onmessage({ data: JSON.stringify({ type: 'text', content: 'hello' }) });
  await Promise.resolve();
  assert.equal(ws.sent.length, count);
});

test('a nonzero document ID cannot be read through the current Word task pane', async t => {
  t.mock.method(console, 'error', () => {});
  const previous = globalThis.Word;
  globalThis.Word = { run() { assert.fail('A foreign document ID must not reach Office.js'); } };
  t.after(() => { globalThis.Word = previous; });
  const result = await parseDocumentRange(0, -1, 12);
  assert.match(result.error, /docId=0/);
});

test('stopping retires the active socket so buffered output cannot enter the next request', async t => {
  const ws = await socket(t, () => {});
  const previousWord = globalThis.Word;
  globalThis.Word = { run: async callback => callback({
    document: { body: { paragraphs: { items: [], load() {} } } }, sync: async () => {}
  }) };
  t.after(() => { globalThis.Word = previousWord; wsManager.onComplete = null; wsManager.onError = null; });
  t.mock.method(wsManager, '_armIdleTimeout', () => {});
  let completions = 0;
  const control = chatStream('edit document', { onComplete: () => completions++ });
  await new Promise(resolve => setImmediate(resolve));
  control.abort();
  assert.deepEqual(ws.sent.map(body => body.type), ['chat', 'stop']);
  assert.equal(ws.closed, true);
  assert.equal(wsManager.ws, null);
  assert.equal(completions, 1);
});

test('late events from a retired socket cannot dispatch content or close its replacement', async t => {
  const old = await socket(t, () => {});
  const lateMessage = old.onmessage;
  const lateClose = old.onclose;
  wsManager.close();
  const messages = [];
  const replacement = await socket(t, data => messages.push(data));
  lateMessage({ data: JSON.stringify({ type: 'thinking', content: 'old output' }) });
  lateMessage({ data: JSON.stringify({ type: 'done' }) });
  lateClose({ code: 1000, reason: 'old close' });
  assert.deepEqual(messages, []);
  assert.equal(wsManager.ws, replacement);
  assert.equal(wsManager.connected, true);
});

test('a document read finishing after stop cannot answer or replace the next connection cache', async t => {
  for (const method of ['_handleDocumentRequest', '_handleQueryRequest']) {
    await t.test(method, async t => {
      await socket(t, () => {});
      let finishRead;
      const previousWord = globalThis.Word;
      globalThis.Word = { run: () => new Promise(resolve => { finishRead = resolve; }) };
      t.after(() => { globalThis.Word = previousWord; });
      t.mock.method(wsManager, 'getCachedDocument', () => null);
      const cached = [];
      t.mock.method(wsManager, 'setCachedDocument', data => cached.push(data));
      const reading = method === '_handleDocumentRequest'
        ? wsManager[method]({ startParaIndex: 0, endParaIndex: -1, docId: 0 })
        : wsManager[method]({}, 0);
      assert.equal(typeof finishRead, 'function');
      wsManager.close();
      const replacement = await socket(t, () => {});
      finishRead({ paragraphs: [] });
      await reading;
      assert.deepEqual(replacement.sent, []);
      assert.deepEqual(cached, []);
    });
  }
});

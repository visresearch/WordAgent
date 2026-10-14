import assert from 'node:assert/strict';
import test from 'node:test';
import { wsManager } from '../src/components/js/api.js';

async function socket(t, handler) {
  t.mock.method(console, 'log', () => {});
  t.mock.method(console, 'error', () => {});
  const previous = globalThis.WebSocket;
  let ws;
  globalThis.WebSocket = class {
    constructor() {
      ws = this; this.sent = []; 
    }
    send(data) {
      this.sent.push(JSON.parse(data)); 
    }
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
  const ws = await socket(t, () => {
    throw new Error('Native API unavailable'); 
  });
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
  const ws = await socket(t, () => {
    throw new Error('UI handler failed'); 
  });
  for (const [type, response] of [['read_document', 'document_response'], ['search_document', 'query_response']]) {
    ws.onmessage({ data: JSON.stringify({ type, docId: 9 }) });
    assert.equal(ws.sent.at(-1).type, response);
    assert.match(ws.sent.at(-1).error, /UI handler failed/);
  }
});

test('an asynchronous handler failure also reports failure, while ordinary chat messages produce no tool reply', async t => {
  const ws = await socket(t, async () => {
    throw new Error('Async handler failed'); 
  });
  ws.onmessage({ data: JSON.stringify({ type: 'edit_document', requestId: 'edit-2', docId: 9, paraID: 101 }) });
  await Promise.resolve();
  assert.equal(ws.sent.at(-1).type, 'edit_document_response');
  assert.equal(ws.sent.at(-1).requestId, 'edit-2');
  const count = ws.sent.length;
  ws.onmessage({ data: JSON.stringify({ type: 'text', content: 'hello' }) });
  await Promise.resolve();
  assert.equal(ws.sent.length, count);
});

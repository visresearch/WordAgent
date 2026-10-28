import assert from 'node:assert/strict';
import test from 'node:test';
import { chatStream, wsManager } from '../src/components/js/api.js';

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
  wsManager._activeChat = { chatId: 'chat-a', sessionId: 'session-a' };
  wsManager._completeCalled = false;
  wsManager._stopping = false;
  t.after(() => {
    globalThis.WebSocket = previous;
    wsManager.ws = null;
    wsManager.connected = false;
    wsManager.onMessage = null;
    wsManager._activeChat = null;
  });
  const connected = wsManager.connect();
  ws.onopen();
  await connected;
  const onmessage = ws.onmessage;
  ws.onmessage = event => {
    const data = { ...wsManager._activeChat, ...JSON.parse(event.data) };
    onmessage({ data: JSON.stringify(data) });
  };
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

test('late events and tool replies from another turn cannot affect the active turn', async t => {
  const received = [];
  const ws = await socket(t, data => received.push(data));
  for (const type of ['edit_document', 'text', 'done', 'error']) {
    ws.onmessage({ data: JSON.stringify({ type, chatId: 'old-chat', sessionId: 'old-session' }) });
  }
  await wsManager.send({ type: 'document_response', chatId: 'old-chat', sessionId: 'old-session' });
  assert.deepEqual(received, []);
  assert.deepEqual(ws.sent, []);
  assert.equal(wsManager._completeCalled, false);
  ws.onmessage({ data: JSON.stringify({ type: 'text', content: 'current' }) });
  assert.equal(received[0].content, 'current');
});

test('a second session in the same pane cannot replace active callbacks', async t => {
  const handler = () => {};
  const ws = await socket(t, handler);
  let error;
  chatStream('second', { sessionId: 'session-b', onError: e => { error = e; } });
  await Promise.resolve();
  assert.match(error.message, /当前窗口正在生成/);
  assert.equal(wsManager.onMessage, handler);
  assert.equal(wsManager._activeChat.sessionId, 'session-a');
  assert.deepEqual(ws.sent, []);
});

test('every turn gets a fresh chatId and old stop controls cannot stop the next turn', async t => {
  const previousWindow = globalThis.window;
  globalThis.window = {};
  t.after(() => { globalThis.window = previousWindow; });
  const ws = await socket(t, () => {});
  t.mock.method(wsManager, '_armIdleTimeout', () => {});
  wsManager._completeCalled = true;
  const first = chatStream('first', { sessionId: 'session-a' });
  await Promise.resolve();
  const firstChat = ws.sent[0];
  ws.onmessage({ data: JSON.stringify({ type: 'done' }) });
  chatStream('second', { sessionId: 'session-b' });
  await Promise.resolve();
  const secondChat = ws.sent[1];
  assert.notEqual(firstChat.chatId, secondChat.chatId);
  assert.equal(firstChat.windowId, secondChat.windowId);
  first.abort();
  assert.equal(ws.sent.length, 2);
});

test('stop keeps the pane reserved until done and suppresses late tool execution', async t => {
  const previousWindow = globalThis.window;
  globalThis.window = {};
  t.after(() => { globalThis.window = previousWindow; });
  const ws = await socket(t, () => {});
  t.mock.method(wsManager, '_armIdleTimeout', () => {});
  wsManager._completeCalled = true;
  let tools = 0;
  const control = chatStream('work', { sessionId: 'session-a', onMessage: () => tools++ });
  await Promise.resolve();
  control.abort();
  assert.equal(ws.sent.at(-1).type, 'stop');
  assert.equal(wsManager._completeCalled, false);
  ws.onmessage({ data: JSON.stringify({ type: 'edit_document', requestId: 'late' }) });
  assert.equal(tools, 0);
  ws.onmessage({ data: JSON.stringify({ type: 'done' }) });
  assert.equal(wsManager._completeCalled, true);
});

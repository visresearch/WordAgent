import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../src/components/js/mcp-server.js', import.meta.url), 'utf8')
  .replace(/^import[\s\S]*?;\s*/gm, '')
  .replace(/export function /g, 'function ');

function setup(overrides = {}) {
  const sockets = [];
  const timers = new Map();
  const calls = [];
  let nextTimer = 0;
  class WebSocket {
    static OPEN = 1;
    constructor(url) { this.url = url; this.readyState = 1; this.sent = []; sockets.push(this); }
    send(data) { this.sent.push(JSON.parse(data)); }
    close() { this.readyState = 3; this.onclose?.(); }
    request(tool, args = {}, requestId = tool) {
      this.onmessage({ data: JSON.stringify({ requestId, tool, arguments: args }) });
    }
  }
  const record = name => async (...args) => {
    calls.push([name, ...args]);
    return name === 'parse' ? { paragraphs: [{ paraID: '123', runs: [{ text: 'hello' }] }] } : { success: true };
  };
  const context = vm.createContext({
    WebSocket, console: { warn() {} },
    setTimeout(callback, delay) { const id = nextTimer++; timers.set(id, { callback, delay }); return id; },
    clearTimeout(id) { timers.delete(id); },
    parseDocumentRange: record('parse'),
    executeStyleQuery(doc, query) { calls.push(['search', doc, query]); return { matches: [], matchCount: 0 }; },
    deleteDocxPara: record('delete'), editDocxParagraph: record('edit'),
    insertBreakAfterParagraph: record('break'), generateDocxFromJSON: record('generate'),
    createDocument: record('create'), wsManager: { clearDocumentCache() { calls.push(['clear']); } },
    ...overrides,
  });
  vm.runInContext(source, context);
  // Compare serialized values across VM realms.
  const plain = value => JSON.parse(JSON.stringify(value));
  return { context, sockets, timers, calls, plain, flush: () => vm.runInContext('workQueue', context) };
}

test('Word dispatches all seven tools with Office signatures and returns matching request IDs', async () => {
  const h = setup();
  h.context.startMcpBridge();
  h.context.startMcpBridge();
  assert.equal(h.sockets.length, 1);
  const socket = h.sockets[0];
  assert.equal(socket.url, 'ws://127.0.0.1:3880/api/mcp/bridge?host=word');
  socket.request('read_document', { startParaIndex: 2, endParaIndex: 4, startParaID: 123, endParaID: 456, mode: 'lightweight' });
  socket.request('search_document', { query: { type: 'paragraph', filters: { text: 'hello' } } });
  socket.request('delete_document', { paraIDs: [123] });
  socket.request('edit_document', { paraID: 123, runs: [{ text: 'new' }] });
  socket.request('insert_break', { paraID: 123, breakType: 'wdPageBreak' });
  socket.request('generate_document', { document: { paragraphs: [], styles: {} }, insertParaID: 123 });
  socket.request('create_document');
  await h.flush();
  const calls = h.plain(h.calls);
  assert.deepEqual(calls[0], ['parse', 2, 4, 0, 123, 456, 'lightweight']);
  assert.deepEqual(calls[1], ['parse', 0, -1, 0]);
  assert.deepEqual(calls.find(c => c[0] === 'delete'), ['delete', [123]]);
  assert.deepEqual(calls.find(c => c[0] === 'edit'), ['edit', 123, [{ text: 'new' }]]);
  assert.deepEqual(calls.find(c => c[0] === 'break'), ['break', 123, 'wdPageBreak']);
  assert.deepEqual(calls.find(c => c[0] === 'generate'), ['generate', { paragraphs: [], styles: {} }, 'selection', 123]);
  assert.equal(calls.filter(c => c[0] === 'clear').length, 4);
  assert.equal(socket.sent.length, 7);
  assert.ok(socket.sent.every(r => r.result && !r.error));
  assert.equal(socket.sent[0].requestId, 'read_document');
  assert.equal(socket.sent[0].result.docId, 0);
  assert.match(socket.sent[6].result.message, /新文档/);
});

test('nonzero docId is rejected before accessing any document; errors do not stop later calls', async () => {
  const h = setup({ editDocxParagraph: async () => ({ success: false, error: 'missing paragraph' }) });
  h.context.startMcpBridge();
  const socket = h.sockets[0];
  socket.onmessage({ data: '{invalid' });
  socket.onmessage({ data: JSON.stringify({ requestId: [], tool: 'delete_document' }) });
  socket.request('delete_document', { docId: 12, paraIDs: [123] });
  socket.request('edit_document', { paraID: 123, runs: [] });
  socket.request('unknown');
  socket.request('read_document');
  await h.flush();
  assert.equal(h.calls.some(c => c[0] === 'delete'), false);
  assert.match(socket.sent[0].error, /docId=0/);
  assert.equal(socket.sent[1].error, 'missing paragraph');
  assert.match(socket.sent[2].error, /未知的 MCP 工具/);
  assert.ok(socket.sent[3].result);
  assert.equal(h.calls.filter(c => c[0] === 'clear').length, 1);
});

test('reads wait for edits to finish; stopping cancels queued work and reconnects safely', async () => {
  let finish;
  const h = setup({ editDocxParagraph: () => new Promise(resolve => { finish = resolve; }) });
  h.context.startMcpBridge();
  const socket = h.sockets[0];
  socket.request('edit_document', { paraID: 123, runs: [] });
  socket.request('read_document');
  await Promise.resolve();
  assert.equal(h.calls.length, 0);
  h.context.stopMcpBridge();
  finish({ success: true });
  await h.flush();
  assert.equal(socket.sent.length, 0);
  assert.equal(h.calls.some(c => c[0] === 'parse'), false);
  assert.equal(h.timers.size, 0);
  h.context.startMcpBridge();
  const current = h.sockets[1];
  socket.request('delete_document', { paraIDs: [123] });
  current.close();
  assert.equal(h.timers.size, 1);
  const [id, timer] = [...h.timers][0];
  assert.equal(timer.delay, 1000);
  h.timers.delete(id);
  timer.callback();
  assert.equal(h.sockets.length, 3);
  h.sockets[2].onopen();
  h.sockets[2].request('read_document');
  await h.flush();
  assert.equal(h.sockets[2].sent.length, 1);
  assert.equal(h.calls.some(c => c[0] === 'delete'), false);
  h.sockets[2].close();
  h.context.stopMcpBridge();
  assert.equal(h.timers.size, 0);
});

test('a failed send does not poison the request queue', async () => {
  const h = setup();
  h.context.startMcpBridge();
  const socket = h.sockets[0];
  const send = socket.send.bind(socket);
  socket.send = () => { socket.send = send; throw new Error('closed'); };
  socket.request('read_document', {}, 'first');
  socket.request('read_document', {}, 'second');
  await h.flush();
  assert.equal(socket.sent.length, 1);
  assert.equal(socket.sent[0].requestId, 'second');
});

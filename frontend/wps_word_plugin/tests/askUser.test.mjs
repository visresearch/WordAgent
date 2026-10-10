import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { createSSRApp } from 'vue';
import { renderToString } from 'vue/server-renderer';
import { chatStream, wsManager } from '../src/components/js/api.js';

// Exercise the component's Options API without requiring a DOM in the Node suite.
const source = readFileSync(new URL('../src/components/chat/UserQuestion.vue', import.meta.url), 'utf8');
const script = source.match(/<script>([\s\S]*?)<\/script>/)[1];
const component = new Function(script.replace('export default', 'return'))();
function questionForm() {
  const emitted = [];
  const vm = {
    ...component.data(), disabled: false,
    request: { questions: [{ id: 'first', options: ['正式', '轻松'] }, { id: 'second', options: [] }] },
    $emit: (...args) => emitted.push(args)
  };
  for (const [name, getter] of Object.entries(component.computed)) {
    Object.defineProperty(vm, name, { get: () => getter.call(vm) });
  }
  return { vm, emitted, submit: () => component.methods.submit.call(vm) };
}

test('requires an explicit answer to every question and accepts choices with free text', () => {
  const { vm, emitted, submit } = questionForm();
  assert.equal(vm.canSubmit, false);
  vm.choices.first = '正式';
  submit();
  assert.equal(emitted.length, 0);
  vm.choices.second = null;
  vm.customAnswers.second = '  约 800 字  ';
  assert.equal(vm.canSubmit, true);
  submit();
  assert.deepEqual(emitted, [['answer', { answers: [{ id: 'first', answer: '正式' }, { id: 'second', answer: '约 800 字' }] }]]);
});

test('custom answer replaces a selected option; blank answers and repeated submits are blocked', () => {
  const { vm, emitted, submit } = questionForm();
  vm.choices.first = '正式';
  vm.choices.second = null;
  vm.customAnswers.second = '800 字';
  vm.choices.first = null;
  vm.customAnswers.first = '  ';
  assert.equal(vm.canSubmit, false);
  vm.customAnswers.first = '学术风格';
  vm.disabled = true;
  submit();
  assert.equal(emitted.length, 0);
  vm.disabled = false;
  submit();
  assert.equal(emitted[0][1].answers[0].answer, '学术风格');
});

test('resume transport keeps session and correlated answers in the chat request', async t => {
  const oldWindow = globalThis.window;
  globalThis.window = {};
  t.after(() => {
    globalThis.window = oldWindow; 
  });
  t.mock.method(wsManager, 'connect', async () => {});
  t.mock.method(wsManager, '_armIdleTimeout', () => {});
  const sent = [];
  t.mock.method(wsManager, 'send', async body => sent.push(body));
  const userResponse = { answers: [{ id: 'interrupt:0', answer: '正式' }] };
  // A stale caller must not reintroduce the removed per-chat thinking override.
  chatStream('正式', { sessionId: 'same-session', userResponse, enableThinking: false });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(sent.length, 1);
  assert.equal(sent[0].type, 'chat');
  assert.equal(sent[0].sessionId, 'same-session');
  assert.deepEqual(sent[0].userResponse, userResponse);
  assert.equal('enableThinking' in sent[0], false);
});

const paneSource = readFileSync(new URL('../src/components/chat/AIChatPane.vue', import.meta.url), 'utf8');
const paneScript = paneSource.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/^import[\s\S]*?;\s*/gm, '');
function chatPane(t, apiOverrides = {}) {
  const previousWindow = globalThis.window;
  globalThis.window = { dispatchEvent() {} };
  t.after(() => {
    globalThis.window = previousWindow; 
  });
  t.mock.method(console, 'log', () => {});
  t.mock.method(console, 'warn', () => {});
  t.mock.method(console, 'error', () => {});
  const streams = [];
  const api = {
    chatStream(message, options) {
      streams.push(options); return { abort() {} }; 
    },
    getSession: async () => ({ success: true, data: { pendingQuestion: null } }),
    ...apiOverrides
  };
  const pane = new Function('api', 't', 'ChatMessages', 'ChatInput', 'SessionPane', 'sessionState',
    paneScript.replace('export default', 'return'))(api, key => key, {}, {}, {}, {});
  const container = { scrollTop: 42 };
  const vm = {
    ...pane.data(), currentSessionId: 'session-a', scrollCalls: 0,
    $refs: { chatMessages: { $refs: { messagesContainer: container } } },
    $nextTick: callback => Promise.resolve().then(callback)
  };
  for (const [name, method] of Object.entries(pane.methods)) {
    vm[name] = method.bind(vm);
  }
  vm.scrollToBottom = () => {
    vm.scrollCalls++; 
  };
  return { vm, streams, container };
}
const pendingQuestion = () => ({ type: 'ask_user', questions: [{ id: 'i:0', question: '采用哪种风格？', options: ['正式', '轻松'] }] });
function pauseWithHistory(vm, streams) {
  vm._sendStreamRequest('整理文档', null);
  const events = streams[0];
  events.onMessage({ type: 'thinking', content: '先检查已有文档，再确定写作风格。' });
  events.onMessage({ type: 'status', content: '已读取 18 个段落' });
  events.onMessage({ type: 'text', content: '已阅读文档。' });
  events.onMessage({ type: 'mcp_tool_call', toolName: 'mcp_search', args: { query: '报告' } });
  events.onMessage({ type: 'mcp_tool_result', toolName: 'mcp_search', outputPreview: '找到资料', isError: false });
  return events;
}

test('asking preserves prior text, tools, thinking, transcript identity and scroll position', async t => {
  const { vm, streams, container } = chatPane(t);
  const events = pauseWithHistory(vm, streams);
  const transcript = vm.messages;
  const assistant = transcript[0];
  const oldParts = structuredClone(assistant.contentParts);
  const oldThinking = assistant.thinking;
  const scrollCalls = vm.scrollCalls;
  events.onMessage(pendingQuestion());
  events.onComplete();
  await Promise.resolve();
  assert.equal(vm.messages, transcript);
  assert.equal(vm.messages[0], assistant);
  assert.deepEqual(assistant.contentParts.slice(0, oldParts.length), oldParts);
  assert.equal(assistant.thinking, oldThinking);
  assert.equal(assistant.thinkingExpanded, true);
  assert.equal(assistant.thinkingDone, true);
  assert.match(assistant.content, /^已阅读文档。\n\n/);
  assert.equal(vm._streamingCache['session-a'], transcript);
  assert.equal(vm.scrollCalls, scrollCalls);
  assert.equal(container.scrollTop, 42);
});

test('submitting keeps the question card and selected answer while preserving earlier output', t => {
  const { vm, streams } = chatPane(t);
  const events = pauseWithHistory(vm, streams);
  events.onMessage(pendingQuestion());
  events.onComplete();
  const assistant = vm.messages[0];
  const snapshot = structuredClone(assistant);
  const response = { answers: [{ id: 'i:0', answer: '正式' }] };
  vm.answerQuestion(response);
  assert.equal(vm.pendingQuestions['session-a'], null);
  assert.equal(vm.isLoading, true);
  assert.equal(streams.length, 2);
  assert.equal(vm.messages.length, 3);
  const card = assistant.contentParts.at(-1);
  assert.equal(card.type, 'ask_user');
  assert.equal(card.pending, false);
  assert.deepEqual(card.response, response);
  assert.deepEqual(assistant.contentParts.slice(0, -1), snapshot.contentParts.slice(0, -1));
  assert.equal(assistant.thinking, snapshot.thinking);
  assert.deepEqual(streams[1].userResponse, response);
  vm.answerQuestion(response);
  assert.equal(streams.length, 2);
});

test('failed resume restores the question while keeping both old and newly streamed content', async t => {
  const request = pendingQuestion();
  const { vm, streams } = chatPane(t, { getSession: async () => {
    throw new Error('offline'); 
  } });
  const events = pauseWithHistory(vm, streams);
  events.onMessage(request);
  events.onComplete();
  const oldMessage = structuredClone(vm.messages[0]);
  oldMessage.contentParts.at(-1).response = null;
  vm.answerQuestion({ answers: [{ id: 'i:0', answer: '正式' }] });
  streams[1].onMessage({ type: 'text', content: '恢复后的输出' });
  streams[1].onError(new Error('offline'));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(vm.pendingQuestions['session-a'], request);
  assert.deepEqual(vm.messages[0], oldMessage);
  assert.equal(vm.messages[2].content, '恢复后的输出');
  assert.equal(vm.messages[2].contentParts[0].content, '恢复后的输出');
});

test('late history response cannot replace messages generated while the fetch was pending', async t => {
  let resolveHistory;
  const { vm, streams } = chatPane(t, { getSession: () => new Promise(resolve => {
    resolveHistory = resolve; 
  }) });
  const loading = vm.loadSessionMessages('session-a');
  const events = pauseWithHistory(vm, streams);
  events.onMessage(pendingQuestion());
  events.onComplete();
  const currentTranscript = vm.messages;
  resolveHistory({ success: true, data: { messages: [], pendingQuestion: null } });
  await loading;
  assert.equal(vm.messages, currentTranscript);
  assert.equal(vm.pendingQuestions['session-a'].questions[0].id, 'i:0');
  assert.equal(vm.historyLoading, false);
});

test('a stale pending-question fetch cannot overwrite a newer question', async t => {
  let resolveQuestion;
  const { vm, streams } = chatPane(t, { getSession: () => new Promise(resolve => {
    resolveQuestion = resolve; 
  }) });
  const events = pauseWithHistory(vm, streams);
  const refreshing = vm.refreshPendingQuestion('session-a');
  const request = pendingQuestion();
  events.onMessage(request);
  resolveQuestion({ success: true, data: { pendingQuestion: null } });
  await refreshing;
  assert.equal(vm.pendingQuestions['session-a'], request);
});

test('answered cards restore option or custom answer and cannot submit again', () => {
  const { vm, emitted, submit } = questionForm();
  vm.readonly = true;
  component.watch.response.handler.call(vm, { answers: [
    { id: 'first', answer: '轻松' }, { id: 'second', answer: '约 800 字' }
  ] });
  assert.equal(vm.choices.first, '轻松');
  assert.equal(vm.choices.second, null);
  assert.equal(vm.customAnswers.second, '约 800 字');
  assert.equal(vm.canSubmit, true);
  submit();
  assert.equal(emitted.length, 0);
});

test('history reload restores answered cards alongside thinking and tool output', async t => {
  const request = pendingQuestion();
  const { vm } = chatPane(t, { getSession: async () => ({ success: true, data: {
    pendingQuestion: null,
    messages: [
      { role: 'assistant', content: '已阅读文档。', thinking: '先检查文档。', contentParts: [
        { type: 'status', content: '读取完成' }, { type: 'ask_user', request }
      ] },
      { role: 'user', content: '正式' },
      { role: 'assistant', content: '继续整理。', toolJson: { calls: [
        { tool: 'ask_user', input: request.questions[0], output: '正式' }
      ] } }
    ]
  } }) });
  await vm.loadSessionMessages('session-a');
  const card = vm.messages[0].contentParts.at(-1);
  assert.equal(card.pending, false);
  assert.deepEqual(card.response, { answers: [{ id: 'i:0', answer: '正式' }] });
  assert.equal(vm.messages[0].thinking, '先检查文档。');
  assert.equal(vm.messages[0].contentParts[0].content, '读取完成');
});

test('legacy pending question is appended to history without replacing previous output', async t => {
  const request = pendingQuestion();
  const { vm } = chatPane(t, { getSession: async () => ({ success: true, data: {
    pendingQuestion: request,
    messages: [{ role: 'assistant', content: '已阅读文档。', thinking: '检查文档。' }]
  } }) });
  await vm.loadSessionMessages('session-a');
  assert.equal(vm.messages.length, 1);
  assert.equal(vm.messages[0].contentParts[0].content, '已阅读文档。');
  assert.equal(vm.messages[0].contentParts[1].type, 'ask_user');
  assert.equal(vm.messages[0].contentParts[1].pending, true);
  vm.syncQuestionRecords('session-a');
  assert.equal(vm.messages[0].contentParts.length, 2);
});

test('rendered cards retain options, disable confirmed answers and remove only the submit button', async () => {
  const renderCard = async props => {
    const app = createSSRApp({ ...component, template: source.match(/<template>([\s\S]*?)<\/template>/)[1] }, props);
    app.config.globalProperties.$t = key => key;
    return renderToString(app);
  };
  const request = pendingQuestion();
  const pendingHtml = await renderCard({ request });
  assert.match(pendingHtml, /question-submit/);
  const answeredHtml = await renderCard({ request, readonly: true,
    response: { answers: [{ id: 'i:0', answer: '正式' }] } });
  assert.match(answeredHtml, /user-question answered/);
  assert.match(answeredHtml, /<fieldset disabled/);
  assert.match(answeredHtml, /<input(?=[^>]*\bchecked)(?=[^>]*value="正式")[^>]*>/);
  assert.match(answeredHtml, /轻松/);
  assert.doesNotMatch(answeredHtml, /question-submit/);
  const customHtml = await renderCard({ request, readonly: true,
    response: { answers: [{ id: 'i:0', answer: '采用学术风格' }] } });
  assert.match(customHtml, /采用学术风格/);
  assert.doesNotMatch(customHtml, /question-submit/);
});

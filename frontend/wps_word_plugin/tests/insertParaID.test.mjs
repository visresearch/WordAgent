import assert from 'node:assert/strict';
import test from 'node:test';

import { generateDocxFromJSON, isDocumentStartInsertParaID } from '../src/components/js/docxJsonConverter.js';

test('insertParaID 0 和字符串 0 都表示文档开头', () => {
  assert.equal(isDocumentStartInsertParaID(0), true);
  assert.equal(isDocumentStartInsertParaID('0'), true);
  assert.equal(isDocumentStartInsertParaID(' 0 '), true);
});

test('空值和非零 paraID 不表示文档开头', () => {
  for (const value of [null, undefined, '', ' ', 1, '1', -1, '-1']) {
    assert.equal(isDocumentStartInsertParaID(value), false);
  }
});

test('缺失、无效或不存在的插入 ID 不访问光标，也不写入空文档或非空文档', t => {
  const previous = globalThis.window;
  let selectionReads = 0;
  let rangeCalls = 0;
  globalThis.window = { Application: {
    get Selection() { selectionReads++; return { Range: { Start: 1 } }; },
  } };
  t.after(() => { globalThis.window = previous; });
  const payload = { paragraphs: [{ pStyle: 'pS_1', runs: [{ text: 'new' }] }], styles: {} };

  for (const text of ['existing\r', '\r']) {
    const doc = {
      Content: { Start: 0, End: text.length, Text: text, Tables: { Count: 0 } },
      Paragraphs: { Count: 1, Item: () => ({ ParaID: 101, Range: { Start: 0, End: text.length, Text: text } }) },
      Range() { rangeCalls++; throw new Error('Unexpected write'); },
    };
    for (const id of [undefined, null, '', ' ', false, true, 1.5, 'bad', 999, '999', -1]) {
      const result = generateDocxFromJSON(payload, doc, id);
      assert.notEqual(result.success, true);
      assert.match(result.error, /insertParaID/);
    }
  }
  assert.equal(selectionReads, 0);
  assert.equal(rangeCalls, 0);
});

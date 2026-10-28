import assert from 'node:assert/strict';
import test from 'node:test';

import { generateDocxFromJSON, isDocumentStartInsertParaID } from '../src/components/js/docxJsonConverter.js';

test('insertParaID 0 和字符串 0 都表示文档开头', () => {
  assert.equal(isDocumentStartInsertParaID(0), true);
  assert.equal(isDocumentStartInsertParaID('0'), true);
  assert.equal(isDocumentStartInsertParaID(' 0 '), true);
});

test('空值、无效值和非零 paraID 不表示文档开头', () => {
  for (const value of [null, undefined, '', ' ', 1, '1', -1, '-1', 'abc']) {
    assert.equal(isDocumentStartInsertParaID(value), false);
  }
});

test('缺失或无效插入 ID 在调用 Office 前失败', async t => {
  const previous = globalThis.Word;
  let nativeCalls = 0;
  globalThis.Word = { run() { nativeCalls++; throw new Error('Unexpected native call'); } };
  t.after(() => { globalThis.Word = previous; });
  for (const id of [undefined, null, '', ' ', false, true, 1.5, 'bad']) {
    const result = await generateDocxFromJSON({ paragraphs: [], styles: {} }, id);
    assert.match(result.error, /insertParaID/);
  }
  assert.equal(nativeCalls, 0);
});

test('不存在的插入 ID 不写入文档，也不创建书签或使用选区', async t => {
  const previous = globalThis.Word;
  t.after(() => { globalThis.Word = previous; });
  t.mock.method(console, 'warn', () => {});
  let writes = 0;
  let selections = 0;
  const paragraph = {
    getRange() {
      return {
        getBookmarks: () => ({ value: ['_111111111_p'] }),
        insertBookmark() { writes++; },
      };
    },
    insertParagraph() { writes++; },
  };
  globalThis.Word = { run: callback => callback({
    document: {
      body: { paragraphs: { items: [paragraph], load() {} }, insertParagraph() { writes++; } },
      getSelection() { selections++; },
    },
    async sync() {},
  }) };
  const result = await generateDocxFromJSON({ paragraphs: [], styles: {} }, 999999999);
  assert.match(result.error, /未找到/);
  assert.equal(writes, 0);
  assert.equal(selections, 0);
});

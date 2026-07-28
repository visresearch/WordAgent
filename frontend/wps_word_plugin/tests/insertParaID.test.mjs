import assert from 'node:assert/strict';
import test from 'node:test';

import { isDocumentStartInsertParaID } from '../src/components/js/docxJsonConverter.js';

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

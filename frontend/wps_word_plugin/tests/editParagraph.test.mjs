import assert from 'node:assert/strict';
import test from 'node:test';

import { editDocxParagraph } from '../src/components/js/docxJsonConverter.js';

function mockDocument() {
  const operations = [];
  const para = {
    ParaID: 101,
    Range: { Start: 10, End: 16 }
  };
  return {
    Paragraphs: { Count: 1, Item: () => para },
    Content: { End: 100 },
    Range(start, end) {
      const range = { Start: start, End: end, Font: {} };
      Object.defineProperty(range, 'Text', {
        set(value) {
          operations.push({ type: 'text', start, end, value }); 
        }
      });
      range.Delete = () => operations.push({ type: 'delete', start, end });
      return range;
    },
    operations
  };
}

test('编辑段落时只删除内容范围，不删除段落标记', () => {
  const doc = mockDocument();
  const result = editDocxParagraph(101, [{ text: '新内容' }], doc);

  assert.equal(result.success, true);
  assert.deepEqual(doc.operations.slice(0, 2), [
    { type: 'delete', start: 10, end: 15 },
    { type: 'text', start: 10, end: 10, value: '新内容' }
  ]);
});

test('空 runs 清空段落正文但保留段落', () => {
  const doc = mockDocument();
  const result = editDocxParagraph(101, [], doc);

  assert.equal(result.success, true);
  assert.deepEqual(doc.operations, [{ type: 'delete', start: 10, end: 15 }]);
});

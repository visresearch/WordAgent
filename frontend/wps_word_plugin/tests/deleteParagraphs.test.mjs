import assert from 'node:assert/strict';
import test from 'node:test';

import { deleteDocxPara } from '../src/components/js/docxJsonConverter.js';

function paragraph(paraID, start, end) {
  return {
    ParaID: paraID,
    Range: { Start: start, End: end }
  };
}

function mockDocument(paragraphs, failingStarts = []) {
  const calls = [];
  return {
    Paragraphs: {
      Count: paragraphs.length,
      Item(index) {
        return paragraphs[index - 1];
      }
    },
    Content: { End: 1000 },
    Range(start, end) {
      return {
        Delete() {
          calls.push({ start, end });
          if (failingStarts.includes(start)) {
            throw new Error('mock delete failure');
          }
        }
      };
    },
    calls
  };
}

test('按文档位置逆序删除，并报告找不到的 paraID', () => {
  const doc = mockDocument([
    paragraph(101, 0, 10),
    paragraph(202, 10, 20),
    paragraph(303, 20, 30)
  ]);

  const result = deleteDocxPara([101, 303, 999], doc);

  assert.equal(result.success, false);
  assert.equal(result.deletedCount, 2);
  assert.deepEqual(result.deletedParaIDs, [303, 101]);
  assert.deepEqual(result.failedParaIDs, []);
  assert.deepEqual(result.missingParaIDs, [999]);
  assert.deepEqual(doc.calls, [
    { start: 20, end: 30 },
    { start: 0, end: 10 }
  ]);
});

test('单个 Range.Delete 失败时不再把整批误报为成功', () => {
  const doc = mockDocument([
    paragraph(101, 0, 10),
    paragraph(202, 10, 20)
  ], [10]);

  const result = deleteDocxPara([101, 202], doc);

  assert.equal(result.success, false);
  assert.equal(result.deletedCount, 1);
  assert.deepEqual(result.deletedParaIDs, [101]);
  assert.deepEqual(result.failedParaIDs, [202]);
  assert.deepEqual(result.missingParaIDs, []);
});

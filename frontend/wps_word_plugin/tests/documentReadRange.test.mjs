import assert from 'node:assert/strict';
import test from 'node:test';
import { parseDocumentRange } from '../src/components/js/api.js';

for (const [start, end, expectedIndices] of [
  [0, -1, [0, 1, 2]],
  [0, 0, [0]],
  [1, -1, [1, 2]],
  [1, 1, [1]],
]) {
  test(`lightweight read [${start}, ${end}] preserves the requested coverage`, async t => {
    t.mock.method(console, 'log', () => {});
    const previous = globalThis.window;
    const paragraphs = ['第一段\r', '\r', '最后一段\r'].map((text, index) => ({
      ParaID: 101 + index,
      Range: { Text: text },
    }));
    globalThis.window = {
      Application: {
        ActiveDocument: {
          Paragraphs: {
            Count: paragraphs.length,
            Item(index) { return paragraphs[index - 1]; },
          },
        },
      },
    };
    t.after(() => { globalThis.window = previous; });

    const result = await parseDocumentRange(start, end, 0, null, null, 'lightweight');

    assert.equal(result.error, undefined);
    assert.equal(Object.hasOwn(result, 'fields'), false);
    assert.deepEqual(result.paragraphs.map(p => p.paraIndex), expectedIndices);
    assert.deepEqual(result.paragraphs.map(p => p.paraID), expectedIndices.map(i => 101 + i));
    if (expectedIndices.includes(1)) assert.deepEqual(result.paragraphs.find(p => p.paraIndex === 1).runs, []);
  });
}

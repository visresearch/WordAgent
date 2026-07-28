import assert from 'node:assert/strict';
import test from 'node:test';

import { insertBreakAfterParagraph } from '../src/components/js/docxJsonConverter.js';

function makeDocument() {
  const calls = [];
  const paragraphs = [
    { ParaID: 10, Range: { Start: 4, End: 12 } },
    { ParaID: 20, Range: { Start: 12, End: 25 } }
  ];
  return {
    calls,
    Paragraphs: {
      Count: paragraphs.length,
      Item(index) {
        return paragraphs[index - 1];
      }
    },
    Range(start, end) {
      calls.push({ start, end });
      return { InsertBreak: (type) => calls.push({ type }) };
    }
  };
}

test('maps all break types to native WPS constants at paragraph end', () => {
  for (const [breakType, nativeType] of Object.entries({ wdLineBreak: 6, wdPageBreak: 7, wdSectionBreakNextPage: 2 })) {
    const doc = makeDocument();
    const result = insertBreakAfterParagraph('20', breakType, doc);
    assert.deepEqual(result, {
      success: true,
      paraID: 20,
      breakType,
      position: 24,
      paragraphAfterBreak: {
        paraID: 20,
        paraIndex: 1,
        pageStart: null,
        pageEnd: null
      }
    });
    assert.ok(doc.calls.some((call) => call.type === nativeType));
  }
});

test('returns an error for an unknown paragraph or break type', () => {
  const doc = makeDocument();
  assert.equal(insertBreakAfterParagraph(99, 'wdLineBreak', doc).success, false);
  assert.equal(insertBreakAfterParagraph(10, 'page', doc).success, false);
});

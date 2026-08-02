import assert from 'node:assert/strict';
import test from 'node:test';

import { parseCellParagraphs } from '../src/components/js/docxJsonConverter.js';

function makeParagraph(paraID, text, alignment = 1) {
  return {
    ParaID: paraID,
    Range: { Text: text },
    Format: {
      Alignment: alignment,
      LineSpacing: 12,
      LeftIndent: 0,
      RightIndent: 0,
      FirstLineIndent: 0,
      SpaceBefore: 0,
      SpaceAfter: 0,
      LineSpacingRule: 0
    }
  };
}

test('空单元格保留带 paraID 的空段落', () => {
  const cellRange = {
    Paragraphs: {
      Count: 1,
      Item() {
        return makeParagraph(123456789, '\r\u0007');
      }
    }
  };

  const paragraphs = parseCellParagraphs(cellRange, null);

  assert.equal(paragraphs.length, 1);
  assert.deepEqual(paragraphs[0], {
    paraID: 123456789,
    pStyle: ['center', 12, 0, 0, 0, 0, 0, '', 0],
    runs: []
  });
});

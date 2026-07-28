import assert from 'node:assert/strict';
import test from 'node:test';

import { applyParagraphStyleAtPosition } from '../src/components/js/docxJsonConverter.js';

function makeDocument() {
  const paragraph = { Style: '', Format: {} };
  const calls = [];
  return {
    paragraph,
    calls,
    Range(start, end) {
      calls.push({ start, end });
      return {
        Paragraphs: {
          Item() {
            return paragraph;
          }
        }
      };
    }
  };
}

test('按段落起点完整应用 pStyle', () => {
  const doc = makeDocument();
  const pStyle = ['center', 18, 1, 2, 3, 4, 5, 'A毕设摘要题目', 1];

  assert.equal(applyParagraphStyleAtPosition(doc, 42, pStyle), true);
  assert.deepEqual(doc.calls, [{ start: 42, end: 42 }]);
  assert.equal(doc.paragraph.Style, 'A毕设摘要题目');
  assert.deepEqual(doc.paragraph.Format, {
    Alignment: 1,
    LeftIndent: 1,
    RightIndent: 2,
    FirstLineIndent: 3,
    SpaceBefore: 4,
    SpaceAfter: 5,
    LineSpacingRule: 1
  });
});

test('固定值行距同时应用行距值和规则', () => {
  const doc = makeDocument();
  const pStyle = ['justify', 24, 0, 0, 0, 0, 0, '正文', 4];

  assert.equal(applyParagraphStyleAtPosition(doc, 7, pStyle), true);
  assert.equal(doc.paragraph.Format.LineSpacing, 24);
  assert.equal(doc.paragraph.Format.LineSpacingRule, 4);
});

test('单倍行距会覆盖锚点段落继承的行距规则', () => {
  const doc = makeDocument();
  doc.paragraph.Format.LineSpacingRule = 5;

  assert.equal(
    applyParagraphStyleAtPosition(doc, 9, ['left', 12, 0, 0, 0, 0, 0, '正文', 0]),
    true
  );
  assert.equal(doc.paragraph.Format.LineSpacingRule, 0);
});

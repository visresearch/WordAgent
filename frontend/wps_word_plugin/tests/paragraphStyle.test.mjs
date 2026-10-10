import assert from 'node:assert/strict';
import test from 'node:test';

import { applyParagraphStyleAtPosition, generateDocxFromJSON } from '../src/components/js/docxJsonConverter.js';

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

// 模拟真实段落边界：插入结束符前，新文本与后面的标题仍是同一段。
function insertionDocument() {
  const paragraphs = [];
  const styleWrites = [];
  let nextID = 1;
  const paragraph = (text, style, format) => {
    let currentStyle = style;
    const item = {
      ParaID: nextID++, text, Format: { ...format },
      get Style() {
        return currentStyle;
      },
      set Style(value) {
        styleWrites.push(this);
        currentStyle = value;
      },
      get Range() {
        const start = paragraphs.slice(0, paragraphs.indexOf(this)).reduce((sum, p) => sum + p.text.length, 0);
        return { Start: start, End: start + this.text.length, Text: this.text };
      }
    };
    return item;
  };
  const anchor = paragraph('（3）原文\r', '正文', { FirstLineIndent: 24 });
  const heading = paragraph('1.2 个人目标\r', '标题 2', { FirstLineIndent: 0, LeftIndent: 0, SpaceBefore: 12, SpaceAfter: 6 });
  paragraphs.push(anchor, heading);
  const locate = (position) => paragraphs.find((p) => p.Range.Start <= position && position < p.Range.End) || paragraphs.at(-1);
  const doc = {
    TrackRevisions: true,
    Tables: { Count: 0 },
    get Content() {
      return { Start: 0, End: paragraphs.reduce((sum, p) => sum + p.text.length, 0), Tables: { Count: 0 }, Text: paragraphs.map((p) => p.text).join('') };
    },
    Paragraphs: { get Count() {
      return paragraphs.length;
    }, Item: (index) => paragraphs[index - 1] },
    Range(start, end) {
      return {
        Start: start, End: end, Font: {}, Select() {}, Information: () => 1,
        Paragraphs: { Item: () => locate(start) },
        set Text(value) {
          const item = locate(start);
          const offset = start - item.Range.Start;
          const text = item.text.slice(0, offset) + value + item.text.slice(offset);
          const segments = text.split('\r');
          const replacements = segments.slice(0, -1).map((part) => paragraph(`${part}\r`, item.Style, item.Format));
          item.text = segments.at(-1);
          // 原有段落标记及其格式属于最后一个有结束符的段落。
          if (!item.text) {
            item.text = replacements.pop().text;
          }
          paragraphs.splice(paragraphs.indexOf(item), 1, ...replacements, item);
        }
      };
    }
  };
  return { doc, heading, paragraphs, styleWrites };
}

test('在第（3）点后生成第（4）（5）点不会改动后面的标题格式', () => {
  const { doc, heading, paragraphs, styleWrites } = insertionDocument();
  const originalFormat = { ...heading.Format };
  const pStyle = ['justify', 24, 0, 0, 24, 0, 0, '正文缩进段落', 4];
  const result = generateDocxFromJSON({ paragraphs: [
    { pStyle, runs: [{ text: '（4）新增目标' }] },
    { pStyle, runs: [{ text: '（5）新增目标' }] }
  ] }, doc, 1);
  assert.equal(result.success, true);
  assert.deepEqual(paragraphs.map((p) => p.text), ['（3）原文\r', '（4）新增目标\r', '（5）新增目标\r', '1.2 个人目标\r']);
  assert.equal(heading.Style, '标题 2');
  assert.deepEqual(heading.Format, originalFormat);
  assert.equal(styleWrites.includes(heading), false);
  for (const item of paragraphs.slice(1, 3)) {
    assert.equal(item.Style, '正文缩进段落');
    assert.equal(item.Format.FirstLineIndent, 24);
  }
});

test('新段落中的多个 runs 与空段落均不会提前给原有标题套用样式', () => {
  const { doc, heading, styleWrites } = insertionDocument();
  const pStyle = ['left', 0, 0, 0, 18, 0, 0, '正文', 0];
  const result = generateDocxFromJSON({ paragraphs: [
    { pStyle, runs: [{ text: '第一部分' }, { text: '第二部分' }] },
    { pStyle, runs: [] }
  ] }, doc, 1);
  assert.equal(result.success, true);
  assert.equal(heading.Style, '标题 2');
  assert.equal(styleWrites.includes(heading), false);
});

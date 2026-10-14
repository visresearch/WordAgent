import assert from 'node:assert/strict';
import test from 'node:test';

import { editDocxParagraph } from '../src/components/js/docxJsonConverter.js';

function mockDocument() {
  const operations = [];
  const fonts = [];
  const paragraphStyle = { alignment: 'justify', firstLineIndent: 24 };
  const para = {
    ParaID: 101,
    Range: { Start: 10, End: 16, ParagraphFormat: paragraphStyle }
  };
  return {
    Paragraphs: { Count: 1, Item: () => para },
    Content: { End: 100 },
    Range(start, end) {
      const range = { Start: start, End: end, Font: {}, Select() {},
        set ParagraphFormat(_) {
          throw new Error('pStyle must not be modified'); 
        } };
      fonts.push(range.Font);
      Object.defineProperty(range, 'Text', {
        set(value) {
          operations.push({ type: 'text', start, end, value }); 
        }
      });
      range.Delete = () => operations.push({ type: 'delete', start, end });
      return range;
    },
    operations, fonts, paragraphStyle
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

test('字符样式分别应用于中英文 run，保留 pStyle 和段落标记', () => {
  const doc = mockDocument();
  const originalPStyle = structuredClone(doc.paragraphStyle);
  const style = font => [font, 12, false, false, 0, '#000000', '#000000', 0, false, false, false];
  const result = editDocxParagraph(101, [
    { text: '中文', rStyle: style('宋体') },
    { text: '2026', rStyle: style('Times New Roman') }
  ], doc);
  assert.equal(result.success, true);
  assert.deepEqual(doc.fonts.filter(f => f.Name).map(f => f.Name), ['宋体', 'Times New Roman']);
  assert.deepEqual(doc.paragraphStyle, originalPStyle);
  assert.deepEqual(doc.operations[0], { type: 'delete', start: 10, end: 15 });
  assert.ok(doc.fonts.filter(f => f.Name).every(f => f.Color === 0));
});

test('未解析的字符样式在删除旧内容之前被拒绝', () => {
  const doc = mockDocument();
  const result = editDocxParagraph(101, [{ text: '新内容', rStyle: 'rS_1' }], doc);
  assert.equal(result.success, false);
  assert.equal(doc.operations.length, 0);
});

for (const markerPositions of [1, 2]) {
  for (const text of ['', '旧内容']) {
    test(`表格单元格保留结束标记（原文长度 ${text.length}，结束标记占 ${markerPositions} 个坐标）`, () => {
      const start = 10;
      const end = start + text.length + markerPositions;
      const para = { ParaID: 101, Range: { Start: start, End: end, Text: `${text}\r\u0007` } };
      const deleted = [];
      const inserted = [];
      const doc = {
        Paragraphs: { Count: 1, Item: () => para },
        Range(from, to) {
          return {
            Font: {},
            get Text() {
              const body = text.slice(Math.max(0, from - start), Math.max(0, to - start));
              const suffix = to > start + text.length ? '\r' : '';
              return body + suffix;
            },
            set Text(value) {
              inserted.push(value); 
            },
            Delete() {
              assert.ok(to <= start + text.length, '不能删除段落或单元格结束标记');
              deleted.push([from, to]);
            },
            Select() {
              assert.fail('逐单元格编辑不能改变选区'); 
            }
          };
        }
      };
      const result = editDocxParagraph(101, [{ text: '新内容' }], doc);
      assert.equal(result.success, true);
      assert.deepEqual(deleted, text ? [[start, start + text.length]] : []);
      assert.deepEqual(inserted, ['新内容']);
      assert.equal(result.paragraph.paraID, 101);
    });
  }
}

test('大表格局部编辑只定位一次，不逐段读页码，也不会把上一段当作编辑结果', () => {
  const doc = mockDocument();
  const count = 500;
  let lookups = 0;
  let pageReads = 0;
  const target = { ParaID: 101, Range: { Start: 10, End: 16 } };
  doc.Paragraphs = {
    Count: count,
    Item(index) {
      lookups++;
      if (index === count) {
        return target;
      }
      return { ParaID: 1000 + index, get Range() {
        assert.fail('不能扫描前置段落的范围/页码'); 
      } };
    }
  };
  const range = doc.Range;
  doc.Range = (start, end) => {
    const result = range(start, end);
    result.Information = () => {
      pageReads++; return 1; 
    };
    return result;
  };
  const result = editDocxParagraph(101, [{ text: '新内容' }], doc);
  assert.equal(result.success, true);
  assert.equal(result.paragraph.paraID, 101);
  assert.equal(result.paragraph.paraIndex, count - 1);
  assert.equal(lookups, count + 1);
  assert.equal(pageReads, 2);
});

test('编辑成功后读取位置元信息失败不会把实际修改误报为失败', t => {
  t.mock.method(console, 'warn', () => {});
  const doc = mockDocument();
  const item = doc.Paragraphs.Item;
  let reads = 0;
  doc.Paragraphs.Item = index => {
    if (++reads > 1) {
      throw new Error('Position metadata unavailable');
    }
    return item(index);
  };
  const result = editDocxParagraph(101, [{ text: '新内容' }], doc);
  assert.equal(result.success, true);
  assert.equal(result.paragraph, null);
  assert.equal(doc.operations[1].value, '新内容');
});

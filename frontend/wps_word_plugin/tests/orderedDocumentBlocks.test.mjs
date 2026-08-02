import assert from 'node:assert/strict';
import test from 'node:test';

import {
  expandOrderedDocumentBlocks,
  orderReadDocumentBlocks
} from '../src/components/js/docxJsonConverter.js';

test('表格块严格保留在相邻段落之间', () => {
  const before = { pStyle: 'pS_1', runs: [{ text: '表格前', rStyle: 'rS_1' }] };
  const table = { rows: 1, columns: 1, cells: [[{ text: '值' }]], tStyle: 'tS_1' };
  const after = { pStyle: 'pS_1', runs: [{ text: '表格后', rStyle: 'rS_1' }] };

  const elements = expandOrderedDocumentBlocks([before, { tables: [table] }, after]);

  assert.deepEqual(
    elements.map((item) => item.type),
    ['paragraph', 'table', 'paragraph']
  );
  assert.equal(elements[1].data, table);
});

test('read_document 将顶层表格放入 paragraphs 的实际位置', () => {
  const before = { paraIndex: 4, paraID: 101, pStyle: 'pS_1', runs: [{ text: '表格前' }] };
  const tableCellParagraph = {
    paraIndex: 6,
    paraID: 102,
    inTable: true,
    runs: [{ text: '单元格段落' }]
  };
  const after = { paraIndex: 8, paraID: 103, pStyle: 'pS_1', runs: [{ text: '表格后' }] };
  const table = {
    paraIndex: 6,
    endParaIndex: 7,
    rows: 1,
    columns: 1,
    cells: [[{ text: '值', cStyle: 'cS_1' }]],
    tStyle: 'tS_1'
  };
  const styles = { pS_1: ['left'], cS_1: [1, 1, 'left', 0], tS_1: [0] };

  const result = orderReadDocumentBlocks({
    paragraphs: [before, tableCellParagraph, after],
    tables: [table],
    styles
  });

  assert.equal(Object.hasOwn(result, 'tables'), false);
  assert.equal(result.styles, styles);
  assert.deepEqual(result.paragraphs, [before, { tables: [table] }, after]);
});

test('read_document 即使没有表格也不返回顶层 tables', () => {
  const paragraph = { paraIndex: 0, paraID: 101, runs: [{ text: '正文' }] };
  const tableBlock = { tables: [{ rows: 1, columns: 1, cells: [], tStyle: 'tS_1' }] };
  const result = orderReadDocumentBlocks({
    paragraphs: [paragraph, tableBlock],
    tables: [],
    fields: []
  });

  assert.equal(Object.hasOwn(result, 'tables'), false);
  assert.deepEqual(result.paragraphs, [paragraph, tableBlock]);
});

test('read_document 表格文本只保留在 runs 中', () => {
  const result = orderReadDocumentBlocks({
    paragraphs: [
      {
        tables: [
          {
            cells: [[{
              text: '重复的单元格文本',
              rStyle: 'rS_1',
              paragraphs: [{
                text: '重复的段落文本',
                paraID: 101,
                pStyle: 'pS_1',
                rStyle: 'rS_1',
                runs: [{ text: '唯一保留的文本', rStyle: 'rS_1' }]
              }],
              cStyle: 'cS_1'
            }]]
          }
        ]
      }
    ]
  });

  const cell = result.paragraphs[0].tables[0].cells[0][0];
  assert.equal(Object.hasOwn(cell, 'text'), false);
  assert.equal(Object.hasOwn(cell, 'rStyle'), false);
  assert.equal(Object.hasOwn(cell.paragraphs[0], 'text'), false);
  assert.equal(Object.hasOwn(cell.paragraphs[0], 'rStyle'), false);
  assert.deepEqual(cell.paragraphs[0].runs, [{ text: '唯一保留的文本', rStyle: 'rS_1' }]);
});

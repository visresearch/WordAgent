import assert from 'node:assert/strict';
import test from 'node:test';
import { parseTable, generateTable } from '../src/components/js/docxJsonConverter.js';

function tableFixture() {
  const rows = [{ Height: 25, HeightRule: 1 }, { Height: 30, HeightRule: 2 }];
  const paragraphs = [{ ParaID: 101 }, { ParaID: 202 }];
  const range = { Start: 10, End: 50, Paragraphs: { Count: 2, Item: i => paragraphs[i - 1] } };
  return {
    rows,
    Range: range,
    Rows: { Count: 2, Alignment: 1, Item: i => rows[i - 1] },
    Columns: { Count: 1, Item: () => ({ Width: 120 }) },
    // Cell content parsing is covered by dedicated tests. A missing cell must
    // not suppress row dimensions and table-level location metadata.
    Cell() { throw new Error('No cell in fixture'); }
  };
}

test('read tables expose flat row heights, independent rules, boundary anchors and physical pages', () => {
  const table = tableFixture();
  const probes = [];
  const doc = { Range(start, end) { probes.push([start, end]); return { Information: () => start === 10 ? 2 : 4 }; } };
  const result = parseTable(table, doc);
  assert.deepEqual(result.rowHeights, [25, 30]);
  assert.deepEqual(result.rowHeightRules, [1, 2]);
  assert.deepEqual(result.columnWidths, [120]);
  assert.equal(result.paraID, 101);
  assert.equal(result.endParaID, 202);
  assert.equal(result.pageStart, 2);
  assert.equal(result.pageEnd, 4);
  assert.deepEqual(probes, [[10, 10], [49, 49]]);
});

test('unavailable pages are omitted and mixed auto-height rows retain their rule', () => {
  const table = tableFixture();
  table.rows[0] = { Height: 20, HeightRule: 0 };
  const result = parseTable(table, { Range() { throw new Error('Unsupported pages'); } });
  assert.deepEqual(result.rowHeights, [20, 30]);
  assert.deepEqual(result.rowHeightRules, [0, 2]);
  assert.equal('pageStart' in result, false);
  assert.equal('pageEnd' in result, false);
});

test('generation applies flat heights with minimum/exact/auto rules and accepts saved legacy pairs', () => {
  for (const dimensions of [
    { rowHeights: [25, 30, 0], rowHeightRules: [1, 2, 0] },
    { rowHeights: [[25, 1], [30, 2], [0, 0]] }
  ]) {
    const calls = [];
    const table = { Borders: {}, AutoFitBehavior() {}, Rows: { Item: i => ({ SetHeight: (h, rule) => calls.push([i, h, rule]) }) },
      Columns: { Item: () => ({}) }, Range: { End: 40 } };
    const doc = { Range: () => ({}), Tables: { Add: () => table } };
    generateTable(doc, { rows: 3, columns: 1, cells: [], ...dimensions }, 0, {});
    assert.deepEqual(calls, [[1, 25, 1], [2, 30, 2], [3, 0, 0]]);
  }
});

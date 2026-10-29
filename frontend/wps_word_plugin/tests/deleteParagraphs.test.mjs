import assert from 'node:assert/strict';
import test from 'node:test';
import { deleteDocxPara } from '../src/components/js/docxJsonConverter.js';

function documentFixture(ids = [900, 10, 500, -30, 200], tableBounds = [[10, 40]], fail = '') {
  const calls = [];
  const paragraphs = ids.map((ParaID, i) => ({ ParaID, Range: { Start: i * 10, End: i * 10 + 10 } }));
  const tables = tableBounds.map(([Start, End]) => ({ Range: { Start, End }, Delete() {
    calls.push(['table', Start, End]);
    if (fail === 'table') throw new Error('Table locked');
  } }));
  return {
    Paragraphs: { Count: paragraphs.length, Item: i => paragraphs[i - 1] },
    Content: { End: ids.length * 10, Tables: { Count: tables.length, Item: i => tables[i - 1] } },
    Range(start, end) { return { Delete() { calls.push(['range', start, end]); if (fail === 'range') throw new Error('Range locked'); } }; },
    calls
  };
}

test('deletes every paragraph between opaque endpoints and removes a complete table', () => {
  const doc = documentFixture();
  const result = deleteDocxPara(900, 200, doc);
  assert.equal(result.success, true);
  assert.equal(result.deletedCount, 5);
  assert.equal(result.deletedTableCount, 1);
  assert.deepEqual(new Set(result.deletedParaIDs), new Set([900, 10, 500, -30, 200]));
  assert.deepEqual(doc.calls, [['range', 40, 50], ['table', 10, 40], ['range', 0, 10]]);
  assert.equal(result.replacementInsertParaID, 0);
});

test('table first/last paragraph anchors delete exactly that table and preserve surrounding text', () => {
  const doc = documentFixture();
  const result = deleteDocxPara(10, -30, doc);
  assert.equal(result.success, true);
  assert.equal(result.deletedCount, 3);
  assert.equal(result.replacementInsertParaID, 900);
  assert.deepEqual(doc.calls, [['table', 10, 40]]);
});

test('missing/reversed endpoints, legacy ID lists and partial tables cause no deletion', () => {
  for (const [first, last] of [[900, 999], [999, 900], [200, 900], [[900, 200], null], [500, -30], [900, 500]]) {
    const doc = documentFixture();
    const result = deleteDocxPara(first, last, doc);
    assert.equal(result.success, false);
    assert.equal(result.deletedCount, 0);
    assert.deepEqual(doc.calls, []);
  }
});

test('a one-paragraph range defaults its end and never expands into its previous paragraph', () => {
  const doc = documentFixture([900, 200], []);
  const result = deleteDocxPara('200', null, doc);
  assert.equal(result.success, true);
  assert.equal(result.deletedCount, 1);
  assert.deepEqual(doc.calls, [['range', 10, 20]]);
  assert.equal(result.replacementInsertParaID, 900);
});

test('nested tables are removed by their outer table operation only', () => {
  const doc = documentFixture(undefined, [[10, 40], [20, 30]]);
  const result = deleteDocxPara(900, 200, doc);
  assert.equal(result.deletedTableCount, 2);
  assert.equal(doc.calls.filter(call => call[0] === 'table').length, 1);
});

test('a native table failure reports partial work and stops before deleting earlier text', () => {
  const doc = documentFixture(undefined, undefined, 'table');
  const result = deleteDocxPara(900, 200, doc);
  assert.equal(result.success, false);
  assert.equal(result.deletedCount, 1);
  assert.equal(result.deletedTableCount, 0);
  assert.deepEqual(result.deletedParaIDs, [200]);
  assert.equal(result.requiresRead, true);
  assert.deepEqual(doc.calls, [['range', 40, 50], ['table', 10, 40]]);
});

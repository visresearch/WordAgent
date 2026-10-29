import assert from 'node:assert/strict';
import test from 'node:test';
import { deleteDocxPara, generateDocxFromJSON } from '../src/components/js/docxJsonConverter.js';

const ids = [900000001, 100000002, 500000003, -300000004, 200000005];
function documentFixture(t, tableBounds = [[1, 3]], fail = false) {
  const previous = globalThis.Word;
  const calls = [];
  const bookmarks = [];
  const paras = ids.map((id, index) => ({
    uniqueLocalId: `p-${index}`,
    getRange() {
      return {
        parentContentControlOrNullObject: { isNullObject: true, load() {} },
        getBookmarks: () => ({ value: [`_${Math.abs(id)}_${id < 0 ? 'n' : 'p'}`] }),
        end: index,
        expandTo(last) { return { delete() { calls.push(['range', index, last.end]); } }; }
      };
    }
  }));
  const tables = tableBounds.map(([start, end, nestingLevel = 1]) => ({
    nestingLevel,
    getRange: () => ({ paragraphs: { items: paras.slice(start, end + 1), load() {} } }),
    delete() { calls.push(['table', start, end]); if (fail) throw new Error('Table locked'); }
  }));
  const context = { document: { body: {
    paragraphs: { items: paras, load() {} }, tables: { items: tables, load() {} }
  }, deleteBookmark: name => bookmarks.push(name) }, async sync() {} };
  globalThis.Word = { run: callback => callback(context) };
  t.after(() => { globalThis.Word = previous; });
  return { calls, bookmarks };
}

test('Word deletes a continuous range with a complete table rather than clearing its cells', async t => {
  const doc = documentFixture(t);
  const result = await deleteDocxPara(ids[0], ids[4]);
  assert.equal(result.success, true);
  assert.equal(result.deletedCount, 5);
  assert.equal(result.deletedTableCount, 1);
  assert.equal(result.replacementInsertParaID, '0');
  assert.deepEqual(doc.calls, [['range', 4, 4], ['table', 1, 3], ['range', 0, 0]]);
});

test('Word uses table boundary anchors to remove only the table', async t => {
  const doc = documentFixture(t);
  const result = await deleteDocxPara(ids[1], ids[3]);
  assert.equal(result.success, true);
  assert.equal(result.deletedCount, 3);
  assert.equal(result.replacementInsertParaID, String(ids[0]));
  assert.deepEqual(doc.calls, [['table', 1, 3]]);
});

test('Word rejects stale/reversed endpoints and partial tables before any delete', async t => {
  const doc = documentFixture(t);
  for (const [first, last] of [[123456789, ids[4]], [ids[4], ids[0]], [ids[0], ids[2]], [ids[2], ids[3]]]) {
    const result = await deleteDocxPara(first, last);
    assert.equal(result.success, false);
    assert.equal(result.deletedCount, 0);
  }
  assert.deepEqual(doc.calls, []);
  assert.deepEqual(doc.bookmarks, []);
});

test('Word native failures require a read and never report an unknown delete count as zero', async t => {
  const doc = documentFixture(t, undefined, true);
  const result = await deleteDocxPara(ids[0], ids[4]);
  assert.equal(result.success, false);
  assert.equal(result.deletedCount, null);
  assert.equal(result.requiresRead, true);
  assert.deepEqual(result.deletedParaIDs, [String(ids[4])]);
  assert.deepEqual(doc.calls, [['range', 4, 4], ['table', 1, 3]]);
});

test('Word defaults the range end to the start for one paragraph', async t => {
  const doc = documentFixture(t, []);
  const result = await deleteDocxPara(ids[4]);
  assert.equal(result.success, true);
  assert.equal(result.deletedCount, 1);
  assert.deepEqual(doc.calls, [['range', 4, 4]]);
});


test('Word deletes a nested table through its outer table even when paragraph boundaries coincide', async t => {
  const doc = documentFixture(t, [[1, 3, 1], [1, 3, 2]]);
  const result = await deleteDocxPara(ids[1], ids[3]);
  assert.equal(result.success, true);
  assert.equal(result.deletedTableCount, 2);
  assert.deepEqual(doc.calls, [['table', 1, 3]]);
});

test('Word rejects old ID lists instead of interpreting them as range endpoints', async () => {
  const result = await deleteDocxPara([ids[0]]);
  assert.equal(result.success, false);
  assert.equal(result.deletedCount, 0);
});

test('unsupported exact row heights are rejected before Word can change the document', async t => {
  const previous = globalThis.Word;
  globalThis.Word = { run() { assert.fail('Must validate height capabilities before insertion'); } };
  t.after(() => { globalThis.Word = previous; });
  const result = await generateDocxFromJSON({ paragraphs: [{ tables: [{ rows: 1, columns: 1,
    cells: [], rowHeights: [30], rowHeightRules: [2] }] }] }, 0);
  assert.match(result.error, /WordApiDesktop 1.4/);
});

import assert from 'node:assert/strict';
import test from 'node:test';
import { adjustDocument } from '../src/components/js/api.js';
import { readPageMargins } from '../src/components/js/pageMargins.js';

function pageSetup(leftMargin = 72) {
  return { topMargin: 72, bottomMargin: 72, leftMargin, rightMargin: 72, pageWidth: 595, pageHeight: 842, load() {} };
}

function installWord(t, setups, sync = async () => {}) {
  const previous = globalThis.Word;
  let runs = 0;
  globalThis.Word = { run(callback) {
    runs++;
    return callback({ document: { sections: { items: setups.map(pageSetup => ({ pageSetup })), load() {} } }, sync });
  } };
  t.after(() => { globalThis.Word = previous; });
  return () => runs;
}

test('sets only the supplied sides across the current Word document', async t => {
  const first = pageSetup();
  const second = pageSetup(80);
  const runs = installWord(t, [first, second]);
  assert.equal((await adjustDocument(7, { top: 2.5 })).success, false);
  assert.equal(runs(), 0);

  assert.deepEqual(await Word.run(readPageMargins), { top: 2.54, bottom: 2.54, left: null, right: 2.54 });
  assert.deepEqual(await adjustDocument(0, { top: 2.5, right: 2 }), {
    success: true, pageMarginsCm: { top: 2.5, bottom: 2.54, left: null, right: 2 }
  });
  assert.equal(first.leftMargin, 72);
  assert.equal(second.leftMargin, 80);
});

test('restores Word margins if the write batch fails after changes begin', async t => {
  const setup = pageSetup();
  let syncs = 0;
  installWord(t, [setup], async () => {
    if (++syncs === 3) throw new Error('Host rejected the write');
  });
  const result = await adjustDocument(0, { top: 2.5, right: 2 });
  assert.deepEqual(result, { success: false, error: 'Host rejected the write' });
  assert.equal(setup.topMargin, 72);
  assert.equal(setup.rightMargin, 72);
});

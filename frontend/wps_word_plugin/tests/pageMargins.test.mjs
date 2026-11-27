import assert from 'node:assert/strict';
import test from 'node:test';
import { adjustDocument } from '../src/components/js/api.js';
import { adjustPageMargins, readPageMargins } from '../src/components/js/pageMargins.js';

function pageSetup(left = 72) {
  return { TopMargin: 72, BottomMargin: 72, LeftMargin: left, RightMargin: 72, PageWidth: 595, PageHeight: 842 };
}

function withSections(...setups) {
  return { Sections: { Count: setups.length, Item: index => ({ PageSetup: setups[index - 1] }) } };
}

test('adjusts every WPS section and preserves the margins that were omitted', async t => {
  const first = pageSetup();
  const second = pageSetup(60);
  const active = pageSetup();
  const document = { DocID: 42, ...withSections(first, second) };
  const previous = globalThis.window;
  globalThis.window = { Application: { ActiveDocument: { DocID: 7, PageSetup: active }, Documents: {
    Count: 1, Item: () => document
  } } };
  t.after(() => { globalThis.window = previous; });

  assert.deepEqual(readPageMargins(document), { top: 2.54, bottom: 2.54, left: null, right: 2.54 });
  const invalidTarget = await adjustDocument(99, { top: 2.5 });
  assert.equal(invalidTarget.success, false);
  assert.equal(active.TopMargin, 72);
  const result = await adjustDocument(42, { top: 2.5, right: 2 });
  assert.deepEqual(result, { success: true, pageMarginsCm: { top: 2.5, bottom: 2.54, left: null, right: 2 } });
  assert.equal(first.TopMargin, second.TopMargin);
  assert.equal(first.LeftMargin, 72);
  assert.equal(second.LeftMargin, 60);
});

test('validates all WPS sections before applying a margin and restores prior writes when a setter fails', () => {
  const first = pageSetup();
  const second = { ...pageSetup(), PageWidth: 100, get TopMargin() { return 72; }, set TopMargin(_) { throw new Error('Host rejected the value'); } };
  const document = withSections(first, second);
  assert.throws(() => adjustPageMargins(document, { left: 2 }), /第 2 节/);
  assert.equal(first.LeftMargin, 72);

  second.PageWidth = 595;
  assert.throws(() => adjustPageMargins(document, { top: 2.5 }), /Host rejected/);
  assert.equal(first.TopMargin, 72);
});

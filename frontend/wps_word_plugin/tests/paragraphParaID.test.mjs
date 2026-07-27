import assert from 'node:assert/strict';
import test from 'node:test';

import { deduplicateStyles, getParagraphParaID } from '../src/components/js/docxJsonConverter.js';

test('returns only a real non-zero integer paragraph ID and never falls back to paraIndex', () => {
  assert.equal(getParagraphParaID({ ParaID: 123456 }), 123456);
  assert.equal(getParagraphParaID({ ParaID: '-987654' }), -987654);
  assert.equal(getParagraphParaID({ ParaID: null, ID: 456789 }), 456789);
  assert.equal(getParagraphParaID({}), null);
  assert.equal(getParagraphParaID({}, 26), null);
  assert.equal(getParagraphParaID({ ParaID: 0 }), null);
  assert.equal(getParagraphParaID({ ParaID: 'not-an-id' }), null);
});

test('removes top-level and table-cell paragraphs without a real paraID', () => {
  const result = deduplicateStyles({
    paragraphs: [
      { paraIndex: 26, paraID: null, pStyle: '', runs: [] },
      { paraIndex: 27, paraID: 1100978944, pStyle: '', runs: [] }
    ],
    tables: [
      {
        cells: [[
          {
            text: 'cell text remains available',
            paragraphs: [
              { paraID: null, pStyle: '', runs: [{ text: 'hidden', rStyle: '' }] },
              { paraID: 1995130182, pStyle: '', runs: [{ text: 'visible', rStyle: '' }] }
            ]
          }
        ]]
      }
    ]
  });

  assert.deepEqual(result.paragraphs.map((paragraph) => paragraph.paraID), [1100978944]);
  assert.deepEqual(result.tables[0].cells[0][0].paragraphs.map((paragraph) => paragraph.paraID), [1995130182]);
});

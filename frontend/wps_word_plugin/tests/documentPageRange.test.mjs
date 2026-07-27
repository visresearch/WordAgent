import assert from 'node:assert/strict';
import test from 'node:test';

import { getParagraphPageRange } from '../src/components/js/docxJsonConverter.js';

test('reads paragraph start and end pages from native WPS ranges', () => {
  const requestedRanges = [];
  const doc = {
    Range(start, end) {
      requestedRanges.push([start, end]);
      return {
        Information(kind) {
          assert.equal(kind, 3);
          return start === 10 ? 2 : 3;
        }
      };
    }
  };

  assert.deepEqual(getParagraphPageRange(doc, { Start: 10, End: 25 }), {
    pageStart: 2,
    pageEnd: 3
  });
  assert.deepEqual(requestedRanges, [[10, 10], [24, 24]]);
});

test('omits both page fields when WPS cannot return a valid page', () => {
  const doc = {
    Range() {
      return { Information: () => undefined };
    }
  };

  assert.deepEqual(getParagraphPageRange(doc, { Start: 10, End: 25 }), {});
});

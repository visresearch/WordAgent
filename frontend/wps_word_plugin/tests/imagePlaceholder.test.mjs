import assert from 'node:assert/strict';
import test from 'node:test';

import { isCharacterInsideInlineImage } from '../src/components/js/docxJsonConverter.js';

test('filters the slash placeholder returned by WPS for an inline image', () => {
  const image = [{ rangeStart: 100, rangeEnd: 101 }];

  assert.equal(isCharacterInsideInlineImage({ Start: 100, End: 101 }, image), true);
  assert.equal(isCharacterInsideInlineImage({ Start: 99, End: 100 }, image), false);
  assert.equal(isCharacterInsideInlineImage({ Start: 101, End: 102 }, image), false);
});

test('does not filter a normal slash outside the image range', () => {
  assert.equal(
    isCharacterInsideInlineImage({ Start: 20, End: 21 }, [{ rangeStart: 30, rangeEnd: 31 }]),
    false
  );
});

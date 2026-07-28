import assert from 'node:assert/strict';
import test from 'node:test';

import { makeInlineImageRun } from '../src/components/js/docxJsonConverter.js';

test('inline image runs expose the complete cross-host shape', () => {
  assert.deepEqual(makeInlineImageRun({
    width: 319.7454528808594,
    height: 83.78181457519531,
    altText: '',
    url: '/tmp/logo.png'
  }), {
    type: 'inline',
    width: 319.7454528808594,
    height: 83.78181457519531,
    left: null,
    top: null,
    wrapType: null,
    altText: '',
    url: '/tmp/logo.png'
  });
});

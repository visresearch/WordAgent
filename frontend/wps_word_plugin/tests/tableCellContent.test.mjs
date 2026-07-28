import assert from 'node:assert/strict';
import test from 'node:test';

import { getCellParagraphRuns } from '../src/components/js/docxJsonConverter.js';

test('表格单元格段落支持 text/rStyle 简写', () => {
  assert.deepEqual(
    getCellParagraphRuns({ text: '静态计算图', rStyle: 'rS_9' }),
    [{ text: '静态计算图', rStyle: 'rS_9' }]
  );
});

test('表格单元格段落优先使用显式 runs', () => {
  const runs = [{ text: 'TensorFlow', rStyle: 'rS_10' }];
  assert.equal(getCellParagraphRuns({ text: 'ignored', runs }), runs);
});

test('空白简写段落不会生成伪 run', () => {
  assert.deepEqual(getCellParagraphRuns({ text: '' }), []);
});

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  beginTrackedEdit,
  finishTrackedEdit,
  hasRevisionBatch,
  settleRevisionBatch
} from '../src/components/js/revisionPreview.js';

function revision({ type, start, end, text, author = 'tester', date = '2026-07-28' }) {
  return {
    Type: type,
    Author: author,
    Date: date,
    FormatDescription: '',
    Range: { Start: start, End: end, Text: text },
    accepted: 0,
    rejected: 0,
    Accept() {
      this.accepted += 1;
    },
    Reject() {
      this.rejected += 1;
    }
  };
}

function documentWith(revisions = []) {
  return {
    TrackRevisions: false,
    TrackFormatting: true,
    ShowRevisions: false,
    ActiveWindow: { View: { ShowFormatChanges: true } },
    _items: revisions,
    get Revisions() {
      const doc = this;
      return {
        get Count() {
          return doc._items.length;
        },
        Item(index) {
          const item = doc._items[index - 1];
          item.Index = index;
          return item;
        }
      };
    }
  };
}

test('只接受本次跟踪编辑产生的修订', () => {
  const existing = revision({ type: 1, start: 1, end: 3, text: 'old', date: '2026-07-27' });
  const doc = documentWith([existing]);
  const state = beginTrackedEdit(doc);

  assert.equal(doc.TrackRevisions, true);
  assert.equal(doc.TrackFormatting, false);
  assert.equal(doc.ShowRevisions, true);
  assert.equal(doc.ActiveWindow.View.ShowFormatChanges, false);

  const created = revision({ type: 1, start: 10, end: 14, text: 'new' });
  doc._items.push(created);
  const batch = finishTrackedEdit(state, { start: 10, end: 14 }, 'insert');

  assert.equal(doc.TrackRevisions, false);
  assert.equal(doc.TrackFormatting, true);
  assert.equal(batch.revisionCount, 1);
  assert.equal(hasRevisionBatch(batch.batchId), true);

  const result = settleRevisionBatch(batch.batchId, 'accept');
  assert.equal(result.handled, 1);
  assert.equal(created.accepted, 1);
  assert.equal(existing.accepted, 0);
  assert.equal(doc.ShowRevisions, false);
  assert.equal(doc.ActiveWindow.View.ShowFormatChanges, true);
});

test('新增批次忽略格式修订和删除修订', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  const inserted = revision({ type: 1, start: 10, end: 14, text: 'new' });
  const formatting = revision({ type: 3, start: 10, end: 14, text: 'new' });
  const deletion = revision({ type: 2, start: 10, end: 14, text: 'old' });
  doc._items.push(inserted, formatting, deletion);

  const batch = finishTrackedEdit(state, { start: 10, end: 14 }, 'insert');
  assert.equal(batch.revisionCount, 1);

  const result = settleRevisionBatch(batch.batchId, 'accept');
  assert.equal(result.handled, 1);
  assert.equal(inserted.accepted, 1);
  assert.equal(formatting.accepted, 0);
  assert.equal(deletion.accepted, 0);
});

test('拒绝删除修订时恢复原文且不处理已有修订', () => {
  const existing = revision({ type: 1, start: 30, end: 34, text: 'old', date: '2026-07-27' });
  const doc = documentWith([existing]);
  const state = beginTrackedEdit(doc);
  const deleted = revision({ type: 2, start: 8, end: 12, text: 'gone' });
  doc._items.unshift(deleted);

  const batch = finishTrackedEdit(state, { start: 8, end: 12 }, 'delete');
  const result = settleRevisionBatch(batch.batchId, 'reject');

  assert.equal(result.handled, 1);
  assert.equal(deleted.rejected, 1);
  assert.equal(existing.rejected, 0);
});

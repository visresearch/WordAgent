import test from 'node:test';
import assert from 'node:assert/strict';

import {
  beginTrackedEdit,
  finishTrackedEdit,
  hasRevisionBatch,
  settleRevisionBatch
} from '../src/components/js/revisionPreview.js';

function revision({ type, start, end, text, author = 'tester', date = '2026-07-28', acceptFailures = 0 }) {
  return {
    Type: type,
    Author: author,
    Date: date,
    FormatDescription: '',
    Range: { Start: start, End: end, Text: text },
    accepted: 0,
    rejected: 0,
    Accept() {
      if (acceptFailures > 0) {
        acceptFailures -= 1;
        throw new Error('temporary accept failure');
      }
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
    ActiveWindow: {
      View: {
        RevisionsView: 1,
        ShowInsertionsAndDeletions: false,
        ShowFormatChanges: true
      }
    },
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
  assert.equal(doc.ActiveWindow.View.RevisionsView, 0);
  assert.equal(doc.ActiveWindow.View.ShowInsertionsAndDeletions, true);
  assert.equal(doc.ActiveWindow.View.ShowFormatChanges, false);

  const created = revision({ type: 1, start: 10, end: 14, text: 'new' });
  doc._items.push(created);
  const batch = finishTrackedEdit(state, { start: 10, end: 14 }, 'insert');

  assert.equal(doc.TrackRevisions, false);
  assert.equal(doc.TrackFormatting, true);
  assert.equal(batch.revisionCount, 1);
  assert.equal(hasRevisionBatch(batch.batchId), true);
  assert.equal(doc.ActiveWindow.View.RevisionsView, 0);
  assert.equal(doc.ActiveWindow.View.ShowInsertionsAndDeletions, true);

  const result = settleRevisionBatch(batch.batchId, 'accept');
  assert.equal(result.handled, 1);
  assert.equal(created.accepted, 1);
  assert.equal(existing.accepted, 0);
  assert.equal(doc.ShowRevisions, false);
  assert.equal(doc.ActiveWindow.View.RevisionsView, 1);
  assert.equal(doc.ActiveWindow.View.ShowInsertionsAndDeletions, false);
  assert.equal(doc.ActiveWindow.View.ShowFormatChanges, true);
});

test('确认新增批次会接受本轮格式和表格结构等附属修订', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  const inserted = revision({ type: 1, start: 10, end: 14, text: 'new' });
  const formatting = revision({ type: 3, start: 10, end: 14, text: 'new' });
  const deletion = revision({ type: 2, start: 10, end: 14, text: 'old' });
  doc._items.push(inserted, formatting, deletion);

  const batch = finishTrackedEdit(state, { start: 10, end: 14 }, 'insert');
  assert.equal(batch.revisionCount, 3);

  const result = settleRevisionBatch(batch.batchId, 'accept');
  assert.equal(result.handled, 3);
  assert.equal(inserted.accepted, 1);
  assert.equal(formatting.accepted, 1);
  assert.equal(deletion.accepted, 1);
});

test('连续两批新增在全部处理前始终显示最终状态修订', () => {
  const doc = documentWith();

  const firstState = beginTrackedEdit(doc);
  const chinese = revision({ type: 1, start: 0, end: 8, text: '中文摘要' });
  doc._items.push(chinese);
  const firstBatch = finishTrackedEdit(firstState, { start: 0, end: 8 }, 'insert');

  const secondState = beginTrackedEdit(doc);
  const english = revision({ type: 1, start: 9, end: 24, text: 'English abstract' });
  doc._items.push(english);
  const secondBatch = finishTrackedEdit(secondState, { start: 9, end: 24 }, 'insert');

  assert.equal(doc.ActiveWindow.View.RevisionsView, 0);
  assert.equal(doc.ActiveWindow.View.ShowInsertionsAndDeletions, true);

  assert.equal(settleRevisionBatch(firstBatch.batchId, 'accept').success, true);
  assert.equal(doc.ActiveWindow.View.RevisionsView, 0);
  assert.equal(doc.ActiveWindow.View.ShowInsertionsAndDeletions, true);

  assert.equal(settleRevisionBatch(secondBatch.batchId, 'accept').success, true);
  assert.equal(doc.ActiveWindow.View.RevisionsView, 1);
  assert.equal(doc.ActiveWindow.View.ShowInsertionsAndDeletions, false);
});

test('接受失败的修订会保留在批次中供再次确认', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  const inserted = revision({
    type: 1,
    start: 10,
    end: 14,
    text: 'new',
    acceptFailures: 1
  });
  doc._items.push(inserted);

  const batch = finishTrackedEdit(state, { start: 10, end: 14 }, 'insert');
  const first = settleRevisionBatch(batch.batchId, 'accept');
  assert.equal(first.success, false);
  assert.equal(hasRevisionBatch(batch.batchId), true);

  const second = settleRevisionBatch(batch.batchId, 'accept');
  assert.equal(second.success, true);
  assert.equal(inserted.accepted, 1);
  assert.equal(hasRevisionBatch(batch.batchId), false);
});

test('已有修订位置变化时不会被误认成本轮修订', () => {
  const existingBefore = revision({
    type: 1,
    start: 30,
    end: 34,
    text: 'existing',
    date: '2026-07-27'
  });
  const doc = documentWith([existingBefore]);
  const state = beginTrackedEdit(doc);

  const existingAfter = revision({
    type: 1,
    start: 50,
    end: 54,
    text: 'existing',
    date: '2026-07-27'
  });
  const inserted = revision({ type: 1, start: 10, end: 14, text: 'new' });
  doc._items = [inserted, existingAfter];

  const batch = finishTrackedEdit(state, { start: 10, end: 14 }, 'insert');
  assert.equal(batch.revisionCount, 1);
  settleRevisionBatch(batch.batchId, 'accept');
  assert.equal(inserted.accepted, 1);
  assert.equal(existingAfter.accepted, 0);
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

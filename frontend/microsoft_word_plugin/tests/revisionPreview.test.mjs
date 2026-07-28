import assert from 'node:assert/strict';
import test from 'node:test';

import {
  beginTrackedEdit,
  finishTrackedEdit,
  hasRevisionBatch,
  settleRevisionBatch
} from '../src/components/js/revisionPreview.mjs';

function trackedChange({ type, text, author = 'Word User', date = '2026-07-28T00:00:00.000Z' }) {
  return {
    type,
    text,
    author,
    date: new Date(date),
    accepted: 0,
    rejected: 0,
    tracked: false,
    load() {},
    track() {
      this.tracked = true;
    },
    untrack() {
      this.tracked = false;
    },
    accept() {
      this.accepted += 1;
    },
    reject() {
      this.rejected += 1;
    }
  };
}

function createWordMock(initialChanges = [], initialMode = 'Off', desktopViewSupported = false) {
  const revisionsFilter = {
    markup: 'Simple',
    view: 'Original',
    load() {}
  };
  const view = {
    areFormatChangesDisplayed: true,
    areInsertionsAndDeletionsDisplayed: false,
    revisionsFilter,
    load() {}
  };
  const document = {
    changeTrackingMode: initialMode,
    changes: [...initialChanges],
    load() {},
    activeWindow: { view },
    body: {
      getTrackedChanges() {
        return {
          get items() {
            return document.changes;
          },
          load() {}
        };
      }
    }
  };
  const context = {
    document,
    async sync() {}
  };

  globalThis.Office = {
    context: {
      requirements: {
        isSetSupported(name, version) {
          return (name === 'WordApi' && version === '1.6') ||
            (desktopViewSupported && name === 'WordApiDesktop' && version === '1.4');
        }
      }
    }
  };
  globalThis.Word = {
    async run(first, second) {
      const callback = typeof first === 'function' ? first : second;
      return callback(context);
    }
  };
  return { document, view, revisionsFilter };
}

test('只接受本轮新增及其格式修订，不处理文档已有修订', async () => {
  const existing = trackedChange({
    type: 'Added',
    text: 'existing',
    date: '2026-07-27T00:00:00.000Z'
  });
  const { document: doc } = createWordMock([existing], 'TrackMineOnly');
  const state = await beginTrackedEdit();
  assert.equal(doc.changeTrackingMode, 'TrackAll');

  const added = trackedChange({ type: 'Added', text: 'new paragraph' });
  const formatted = trackedChange({ type: 'Formatted', text: 'new paragraph' });
  doc.changes.push(added, formatted);
  const batch = await finishTrackedEdit(state, 'insert');

  assert.equal(doc.changeTrackingMode, 'TrackMineOnly');
  assert.equal(batch.revisionCount, 2);
  assert.equal(hasRevisionBatch(batch.batchId), true);

  const result = await settleRevisionBatch(batch.batchId, 'accept');
  assert.equal(result.success, true);
  assert.equal(added.accepted, 1);
  assert.equal(formatted.accepted, 1);
  assert.equal(existing.accepted, 0);
});

test('删除批次只拒绝本轮删除和格式修订', async () => {
  const existingAdded = trackedChange({
    type: 'Added',
    text: 'existing',
    date: '2026-07-27T00:00:00.000Z'
  });
  const { document: doc } = createWordMock([existingAdded]);
  const state = await beginTrackedEdit();
  const deleted = trackedChange({ type: 'Deleted', text: 'old paragraph' });
  const formatted = trackedChange({ type: 'Formatted', text: 'old paragraph' });
  doc.changes.push(deleted, formatted);

  const batch = await finishTrackedEdit(state, 'delete');
  const result = await settleRevisionBatch(batch.batchId, 'reject');

  assert.equal(result.success, true);
  assert.equal(deleted.rejected, 1);
  assert.equal(formatted.rejected, 1);
  assert.equal(existingAdded.rejected, 0);
});

test('没有预期文字修订时不建立批次', async () => {
  const { document: doc } = createWordMock();
  const state = await beginTrackedEdit();
  doc.changes.push(trackedChange({ type: 'Formatted', text: 'format only' }));

  const batch = await finishTrackedEdit(state, 'insert');
  assert.equal(batch.batchId, null);
  assert.equal(batch.revisionCount, 0);
  assert.equal(doc.changeTrackingMode, 'Off');
});

test('待确认期间隐藏格式修订，结算最后一个批次后恢复用户显示设置', async () => {
  const { document: doc, view, revisionsFilter } = createWordMock([], 'Off', true);
  const state = await beginTrackedEdit();
  assert.equal(view.areFormatChangesDisplayed, false);
  assert.equal(view.areInsertionsAndDeletionsDisplayed, true);
  assert.equal(revisionsFilter.markup, 'All');
  assert.equal(revisionsFilter.view, 'Final');

  doc.changes.push(trackedChange({ type: 'Added', text: 'visible insertion' }));
  const batch = await finishTrackedEdit(state, 'insert');
  await settleRevisionBatch(batch.batchId, 'accept');

  assert.equal(view.areFormatChangesDisplayed, true);
  assert.equal(view.areInsertionsAndDeletionsDisplayed, false);
  assert.equal(revisionsFilter.markup, 'Simple');
  assert.equal(revisionsFilter.view, 'Original');
});

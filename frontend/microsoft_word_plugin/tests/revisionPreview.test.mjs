import assert from 'node:assert/strict';
import test from 'node:test';

import {
  beginTrackedEdit,
  finishTrackedEdit,
  hasRevisionBatch,
  settleRevisionBatch,
  settleRevisionBatches
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
      this.remove?.();
    },
    reject() {
      this.rejected += 1;
      this.remove?.();
    }
  };
}

function createWordMock(initialChanges = [], initialMode = 'Off', desktopViewSupported = false) {
  const metrics = { runs: 0, syncs: 0, acceptAll: 0, rejectAll: 0 };
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
            for (const change of document.changes) {
              change.remove = () => { document.changes = document.changes.filter((item) => item !== change); };
            }
            return document.changes;
          },
          acceptAll() {
            metrics.acceptAll += 1;
            for (const change of [...document.changes]) change.accept();
          },
          rejectAll() {
            metrics.rejectAll += 1;
            for (const change of [...document.changes]) change.reject();
          },
          load() {},
          track() {},
          untrack() {}
        };
      }
    }
  };
  const context = {
    document,
    async sync() { metrics.syncs += 1; }
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
      metrics.runs += 1;
      const callback = typeof first === 'function' ? first : second;
      return callback(context);
    }
  };
  return { document, view, revisionsFilter, context, metrics };
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
  assert.equal(revisionsFilter.markup, 'Simple');
  assert.equal(revisionsFilter.view, 'Final');

  doc.changes.push(trackedChange({ type: 'Added', text: 'visible insertion' }));
  const batch = await finishTrackedEdit(state, 'insert');
  await settleRevisionBatch(batch.batchId, 'accept');

  assert.equal(view.areFormatChangesDisplayed, true);
  assert.equal(view.areInsertionsAndDeletionsDisplayed, false);
  assert.equal(revisionsFilter.markup, 'Simple');
  assert.equal(revisionsFilter.view, 'Original');
});

test('编辑批次同时拒绝本轮删除、插入和格式修订', async () => {
  const existing = trackedChange({
    type: 'Deleted',
    text: 'existing',
    date: '2026-07-27T00:00:00.000Z'
  });
  const { document: doc } = createWordMock([existing]);
  const state = await beginTrackedEdit();
  const deleted = trackedChange({ type: 'Deleted', text: 'old text' });
  const added = trackedChange({ type: 'Added', text: 'new text' });
  const formatted = trackedChange({ type: 'Formatted', text: 'new text' });
  doc.changes.push(deleted, added, formatted);

  const batch = await finishTrackedEdit(state, 'edit');
  assert.equal(batch.revisionCount, 3);

  const result = await settleRevisionBatch(batch.batchId, 'reject');
  assert.equal(result.success, true);
  assert.equal(deleted.rejected, 1);
  assert.equal(added.rejected, 1);
  assert.equal(formatted.rejected, 1);
  assert.equal(existing.rejected, 0);
});

test('一次确认可稳定接受多个原生修订批次', async () => {
  const { document: doc } = createWordMock();

  const firstState = await beginTrackedEdit();
  const firstAdded = trackedChange({ type: 'Added', text: 'first' });
  doc.changes.push(firstAdded);
  const firstBatch = await finishTrackedEdit(firstState, 'insert');

  const secondState = await beginTrackedEdit();
  const secondDeleted = trackedChange({ type: 'Deleted', text: 'second' });
  doc.changes.push(secondDeleted);
  const secondBatch = await finishTrackedEdit(secondState, 'delete');

  const result = await settleRevisionBatches(
    [firstBatch.batchId, secondBatch.batchId],
    'accept'
  );

  assert.equal(result.success, true);
  assert.equal(result.handled, 2);
  assert.deepEqual(result.settledBatchIds, [firstBatch.batchId, secondBatch.batchId]);
  assert.equal(firstAdded.accepted, 1);
  assert.equal(secondDeleted.accepted, 1);
  assert.equal(hasRevisionBatch(firstBatch.batchId), false);
  assert.equal(hasRevisionBatch(secondBatch.batchId), false);
});

test('多个批次统一接受或拒绝只运行一个 Word.run 和两次 sync', async () => {
  for (const action of ['accept', 'reject']) {
    const { document: doc, metrics, view } = createWordMock([], 'Off', true);
    const firstState = await beginTrackedEdit();
    doc.changes.push(trackedChange({ type: 'Added', text: 'first' }));
    const first = await finishTrackedEdit(firstState, 'insert');
    const secondState = await beginTrackedEdit();
    doc.changes.push(trackedChange({ type: 'Deleted', text: 'second' }));
    const second = await finishTrackedEdit(secondState, 'delete');
    const before = { ...metrics };
    const result = await settleRevisionBatches([first.batchId, second.batchId, first.batchId], action);
    assert.equal(result.success, true);
    assert.equal(result.bulk, true);
    assert.equal(metrics.runs - before.runs, 1);
    assert.equal(metrics.syncs - before.syncs, 2);
    assert.equal(metrics[action === 'accept' ? 'acceptAll' : 'rejectAll'], 1);
    assert.equal(doc.changes.length, 0);
    assert.equal(view.areFormatChangesDisplayed, true);
    assert.equal(result.timings.syncCount, 2);
  }
});

test('取消会恢复新增范围以外标题的格式修订，不留下格式标记', async () => {
  const { document: doc } = createWordMock();
  const state = await beginTrackedEdit();
  let headingStyle = '正文缩进段落';
  const added = trackedChange({ type: 'Added', text: '（4）新增\r（5）新增' });
  const formatted = trackedChange({ type: 'Formatted', text: '1.2 个人目标' });
  const reject = formatted.reject.bind(formatted);
  formatted.reject = () => { headingStyle = '标题 2'; reject(); };
  doc.changes.push(added, formatted);
  const batch = await finishTrackedEdit(state, 'insert');
  assert.equal((await settleRevisionBatch(batch.batchId, 'reject')).success, true);
  assert.equal(headingStyle, '标题 2');
  assert.equal(doc.changes.length, 0);
});

test('结算时重新读取修订对象，旧代理失效及已有修订位置变化不会误处理', async () => {
  const existing = trackedChange({ type: 'Added', text: 'user revision', date: '2026-07-27T00:00:00.000Z' });
  const { document: doc, metrics } = createWordMock([existing]);
  const state = await beginTrackedEdit();
  const stale = trackedChange({ type: 'Added', text: 'new' });
  doc.changes.push(stale);
  const batch = await finishTrackedEdit(state, 'insert');
  stale.accept = () => assert.fail('不得使用旧 RequestContext 的代理');
  const fresh = trackedChange({ type: 'Added', text: 'new' });
  const movedExisting = trackedChange({ type: 'Added', text: existing.text, date: existing.date });
  doc.changes = [fresh, movedExisting];
  assert.equal((await settleRevisionBatch(batch.batchId, 'accept')).success, true);
  assert.equal(metrics.acceptAll, 0);
  assert.equal(fresh.accepted, 1);
  assert.equal(movedExisting.accepted, 0);
  assert.deepEqual(doc.changes, [movedExisting]);
});

test('原生集合接口没有清理完时保留批次和预览，允许再次处理', async () => {
  for (const action of ['accept', 'reject']) {
    const { document: doc, view } = createWordMock([], 'Off', true);
    const state = await beginTrackedEdit();
    doc.changes.push(trackedChange({ type: 'Added', text: 'new' }));
    const batch = await finishTrackedEdit(state, 'insert');
    const getChanges = doc.body.getTrackedChanges;
    doc.body.getTrackedChanges = () => {
      const collection = getChanges();
      collection[action === 'accept' ? 'acceptAll' : 'rejectAll'] = () => {};
      return collection;
    };
    assert.equal((await settleRevisionBatch(batch.batchId, action)).success, false);
    assert.equal(hasRevisionBatch(batch.batchId), true);
    assert.equal(view.areFormatChangesDisplayed, false);
    doc.body.getTrackedChanges = getChanges;
    assert.equal((await settleRevisionBatch(batch.batchId, action)).success, true);
  }
});

test('接口部分成功后新建格式标记，重试仍会拒绝该残留', async () => {
  const { document: doc } = createWordMock();
  const state = await beginTrackedEdit();
  doc.changes.push(trackedChange({ type: 'Added', text: 'new' }), trackedChange({ type: 'Formatted', text: 'new title' }));
  const batch = await finishTrackedEdit(state, 'insert');
  const getChanges = doc.body.getTrackedChanges;
  doc.body.getTrackedChanges = () => {
    const collection = getChanges();
    collection.rejectAll = () => { doc.changes = [trackedChange({ type: 'Formatted', text: 'original title' })]; };
    return collection;
  };
  assert.equal((await settleRevisionBatch(batch.batchId, 'reject')).success, false);
  assert.equal(hasRevisionBatch(batch.batchId), true);
  doc.body.getTrackedChanges = getChanges;
  assert.equal((await settleRevisionBatch(batch.batchId, 'reject')).success, true);
  assert.equal(doc.changes.length, 0);
});

test('sync 失败时保留批次；已成功的部分不会在重试中重复接受', async () => {
  const { document: doc, context } = createWordMock();
  const state = await beginTrackedEdit();
  const added = trackedChange({ type: 'Added', text: 'new' });
  doc.changes.push(added);
  const batch = await finishTrackedEdit(state, 'insert');
  const sync = context.sync;
  let calls = 0;
  context.sync = async () => {
    if (++calls === 2) throw new Error('Office busy');
  };
  assert.equal((await settleRevisionBatch(batch.batchId, 'accept')).success, false);
  assert.equal(hasRevisionBatch(batch.batchId), true);
  context.sync = sync;
  assert.equal((await settleRevisionBatch(batch.batchId, 'accept')).success, true);
  assert.equal(added.accepted, 1);
});

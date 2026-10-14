import assert from 'node:assert/strict';
import test from 'node:test';

import {
  beginTrackedEdit,
  abortTrackedEdit,
  finishTrackedEdit,
  hasRevisionBatch,
  settleRevisionBatch,
  settleRevisionBatches,
  getPendingRevisionCount,
  settleDocumentRevisions,
  AI_REVISION_AUTHOR
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
      document: {},
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

test('接受和拒绝均隔离两个文档的相同修订，保留其他作者的修改', async () => {
  for (const action of ['accept', 'reject']) {
    const first = createWordMock();
    const firstOffice = globalThis.Office;
    const firstWord = globalThis.Word;
    const stateA = await beginTrackedEdit();
    const changeA = trackedChange({ type: 'Added', text: 'identical' });
    first.document.changes.push(changeA);
    const batchA = await finishTrackedEdit(stateA, 'insert');

    const otherAuthor = trackedChange({ type: 'Added', text: 'identical', author: 'Another author' });
    const second = createWordMock([otherAuthor]);
    const stateB = await beginTrackedEdit();
    const changeB = trackedChange({ type: 'Added', text: 'identical' });
    second.document.changes.push(changeB);
    await finishTrackedEdit(stateB, 'insert');
    const runCount = second.metrics.runs;
    assert.equal((await settleRevisionBatch(batchA.batchId, action)).success, false);
    assert.equal(second.metrics.runs, runCount);
    assert.equal((await settleDocumentRevisions(action)).success, true);
    assert.deepEqual(second.document.changes, [otherAuthor]);
    assert.equal(changeA.accepted + changeA.rejected, 0);
    assert.equal(changeB[action === 'accept' ? 'accepted' : 'rejected'], 1);

    globalThis.Office = firstOffice;
    globalThis.Word = firstWord;
    assert.equal(await getPendingRevisionCount(), 1);
    assert.equal((await settleDocumentRevisions(action)).success, true);
    assert.equal(first.document.changes.length, 0);
  }
});

test('重开面板可发现文策AI修订，只按固定作者名称处理，不兼容旧名称', async () => {
  for (const action of ['accept', 'reject']) {
    const ai = trackedChange({ type: 'Added', text: 'saved', author: AI_REVISION_AUTHOR });
    const human = trackedChange({ type: 'Deleted', text: 'saved', author: 'Author' });
    const legacy = trackedChange({ type: 'Added', text: 'saved', author: 'WenCe AI Assistant' });
    const { document: doc } = createWordMock([ai, human, legacy]);
    assert.equal(await getPendingRevisionCount(), 1);
    const result = await settleDocumentRevisions(action);
    assert.equal(result.success, true);
    assert.equal(result.handled, 1);
    assert.deepEqual(doc.changes, [human, legacy]);
    assert.equal(await getPendingRevisionCount(), 0);
  }
});

test('用户在原生审阅栏处理修订后清理批次并恢复显示设置', async () => {
  const { document: doc, view } = createWordMock([], 'Off', true);
  const state = await beginTrackedEdit();
  doc.changes.push(trackedChange({ type: 'Added', text: 'new' }));
  const batch = await finishTrackedEdit(state, 'insert');
  doc.changes = [];
  assert.equal(await getPendingRevisionCount(), 0);
  assert.equal(hasRevisionBatch(batch.batchId), false);
  assert.equal(view.areFormatChangesDisplayed, true);
});

test('非当前加载项的docId不能开启修订；文档变化不能恢复另一文档设置', async () => {
  const first = createWordMock();
  await assert.rejects(beginTrackedEdit(8), /docId=0/);
  assert.equal(first.document.changeTrackingMode, 'Off');
  const firstOffice = globalThis.Office;
  const firstWord = globalThis.Word;
  const state = await beginTrackedEdit();
  const second = createWordMock([], 'TrackMineOnly');
  await assert.rejects(finishTrackedEdit(state, 'insert'), /文档/);
  await assert.rejects(abortTrackedEdit(state), /文档/);
  assert.equal(second.document.changeTrackingMode, 'TrackMineOnly');
  globalThis.Office = firstOffice;
  globalThis.Word = firstWord;
  await abortTrackedEdit(state);
  assert.equal(first.document.changeTrackingMode, 'Off');
});

test('Word原生用户名下的AI批次保存到所属文档，刷新面板后仍可拒绝且保留原有修订', async () => {
  const existing = trackedChange({ type: 'Added', text: 'identical' });
  const { document: doc } = createWordMock([existing]);
  const stored = new Map();
  doc.settings = {
    add(key, value) { stored.set(key, value); },
    getItemOrNullObject(key) {
      return { isNullObject: !stored.has(key), value: stored.get(key), load() {} };
    }
  };
  const state = await beginTrackedEdit();
  const inserted = trackedChange({ type: 'Added', text: 'identical' });
  doc.changes.push(inserted);
  const batch = await finishTrackedEdit(state, 'insert');
  assert.equal(stored.size, 1);
  // A fresh module has no previous in-memory revision registry.
  const reopened = await import(`../src/components/js/revisionPreview.mjs?reopened=${Date.now()}`);
  globalThis.Office.context.document = {};
  assert.equal(await reopened.getPendingRevisionCount(), 1);
  assert.equal(reopened.hasRevisionBatch(batch.batchId), true);
  assert.equal((await reopened.settleDocumentRevisions('reject')).success, true);
  assert.deepEqual(doc.changes, [existing]);
  assert.equal(inserted.rejected, 1);
  assert.equal(existing.rejected, 0);
  assert.equal(JSON.parse([...stored.values()][0]).batches.length, 0);
});

test('写入过程中另一个作者同时修改时，不猜测归属，也不撤销已写入内容', async () => {
  const { document: doc } = createWordMock();
  const state = await beginTrackedEdit();
  const own = trackedChange({ type: 'Added', text: 'plugin insertion' });
  const human = trackedChange({ type: 'Added', text: 'collaborator insertion', author: 'Other Author' });
  doc.changes.push(own, human);
  await assert.rejects(finishTrackedEdit(state, 'insert'), /多个修订作者/);
  assert.deepEqual(doc.changes, [own, human]);
  assert.equal(doc.changeTrackingMode, 'Off');
  assert.equal(await getPendingRevisionCount(), 0);
});

test('批量处理后新出现的其他作者修订不会归入失败重试批次', async () => {
  const { document: doc } = createWordMock();
  const state = await beginTrackedEdit();
  const own = trackedChange({ type: 'Added', text: 'plugin insertion' });
  doc.changes.push(own);
  const batch = await finishTrackedEdit(state, 'insert');
  const getChanges = doc.body.getTrackedChanges;
  const human = trackedChange({ type: 'Added', text: 'new human change', author: 'Other Author' });
  doc.body.getTrackedChanges = () => {
    const collection = getChanges();
    collection.acceptAll = () => { own.accept(); doc.changes.push(human); };
    return collection;
  };
  assert.equal((await settleRevisionBatch(batch.batchId, 'accept')).success, true);
  assert.deepEqual(doc.changes, [human]);
  assert.equal(human.accepted, 0);
  assert.equal(hasRevisionBatch(batch.batchId), false);
});

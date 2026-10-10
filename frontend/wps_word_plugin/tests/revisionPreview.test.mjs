import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import {
  beginTrackedEdit,
  finishTrackedEdit,
  hasRevisionBatch,
  rejectRevisionBatches,
  settleRevisionBatch,
  settleAllDocumentRevisions
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
  const doc = {
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
    acceptAllCalls: 0,
    rejectAllCalls: 0,
    rangeRejectAllCalls: 0,
    Range(start, end) {
      const inRange = () => doc._items.filter((item) => item.Range.Start < end && item.Range.End > start);
      return {
        Revisions: {
          get Count() {
            return inRange().length;
          },
          Item(index) {
            const item = inRange()[index - 1];
            item.Index = doc._items.indexOf(item) + 1;
            return item;
          },
          RejectAll() {
            doc.rangeRejectAllCalls += 1;
            for (const item of inRange()) {
              item.rejected += 1;
              item.onReject?.();
              doc._items.splice(doc._items.indexOf(item), 1);
            }
          }
        }
      };
    },
    get Revisions() {
      return {
        get Count() {
          return doc._items.length;
        },
        Item(index) {
          const item = doc._items[index - 1];
          item.Index = index;
          if (!item._bound) {
            item._bound = true;
            for (const method of ['Accept', 'Reject']) {
              const original = item[method];
              item[method] = function () {
                if (!doc._items.includes(this)) {
                  throw new Error('stale COM revision');
                }
                original.call(this);
                doc._items.splice(doc._items.indexOf(this), 1);
                if (method === 'Reject') {
                  this.onReject?.();
                }
              };
            }
          }
          return item;
        },
        AcceptAll() {
          doc.acceptAllCalls += 1;
          for (const item of doc._items) {
            item.accepted += 1;
          }
          doc._items = [];
        },
        RejectAll() {
          doc.rejectAllCalls += 1;
          for (const item of doc._items) {
            item.rejected += 1;
            item.onReject?.();
          }
          doc._items = [];
        }
      };
    }
  };
  return doc;
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

test('删除批次不会接管因 WPS 合并而看起来新出现的纯插入修订', () => {
  const oldInsertion = revision({ type: 1, start: 8, end: 12, text: '新增段落' });
  const doc = documentWith([oldInsertion]);
  const state = beginTrackedEdit(doc);

  // WPS 在邻近删除后可能用新的 COM Revision 对象表示原有插入，且文本或范围发生变化。
  const recreatedInsertion = revision({ type: 1, start: 8, end: 18, text: '新增段落扩展' });
  const deleted = revision({ type: 2, start: 20, end: 24, text: '旧段落' });
  doc._items = [recreatedInsertion, deleted];

  const batch = finishTrackedEdit(state, { start: 20, end: 24 }, 'delete');
  assert.equal(batch.revisionCount, 1);

  const result = settleRevisionBatch(batch.batchId, 'accept');
  assert.equal(result.success, true);
  assert.equal(deleted.accepted, 1);
  assert.equal(recreatedInsertion.accepted, 0);
});

test('确认键使用 WPS 原生 AcceptAll 一次性接受增删修订', () => {
  const doc = documentWith();

  const insertState = beginTrackedEdit(doc);
  const inserted = revision({ type: 1, start: 10, end: 20, text: '新增内容' });
  doc._items.push(inserted);
  const insertBatch = finishTrackedEdit(insertState, { start: 10, end: 20 }, 'insert');

  const deleteState = beginTrackedEdit(doc);
  const deleted = revision({ type: 2, start: 30, end: 40, text: '旧内容' });
  doc._items.push(deleted);
  const deleteBatch = finishTrackedEdit(deleteState, { start: 30, end: 40 }, 'delete');

  const result = settleAllDocumentRevisions(doc, 'accept');

  assert.equal(result.success, true);
  assert.equal(result.handled, 2);
  assert.equal(inserted.accepted, 1);
  assert.equal(deleted.accepted, 1);
  assert.equal(hasRevisionBatch(insertBatch.batchId), false);
  assert.equal(hasRevisionBatch(deleteBatch.batchId), false);
  assert.equal(doc._items.length, 0);
});

test('确认期间暂停屏幕重绘，修订及视图恢复完成后只重新开启一次', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  doc._items.push(revision({ type: 1, start: 10, end: 20, text: '新增' }));
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  let updating = true;
  const updates = [];
  doc.Application = {
    get ScreenUpdating() {
      return updating;
    },
    set ScreenUpdating(value) {
      updating = value;
      updates.push(value);
    }
  };
  const view = doc.ActiveWindow.View;
  for (const key of ['RevisionsView', 'ShowInsertionsAndDeletions', 'ShowFormatChanges']) {
    let value = view[key];
    Object.defineProperty(view, key, {
      get: () => value,
      set(nextValue) {
        assert.equal(updating, false, '恢复显示设置时应暂停重绘');
        value = nextValue;
      }
    });
  }
  const collection = doc.Revisions;
  const accept = collection.AcceptAll;
  collection.AcceptAll = () => {
    assert.equal(updating, false, '接受修订时应暂停重绘');
    accept();
  };
  Object.defineProperty(doc, 'Revisions', { get: () => collection });
  const result = settleAllDocumentRevisions(doc, 'accept');
  assert.equal(result.success, true);
  assert.deepEqual(updates, [false, true]);
  assert.equal(hasRevisionBatch(batch.batchId), false);
  assert.equal(view.RevisionsView, 1);
  for (const duration of Object.values(result.timings)) {
    assert.ok(Number.isFinite(duration) && duration >= 0);
  }
});

test('接受修订失败时恢复屏幕更新并保留确认入口', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  doc._items.push(revision({ type: 1, start: 10, end: 20, text: '新增' }));
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  doc.Application = { ScreenUpdating: true };
  const collection = doc.Revisions;
  const accept = collection.AcceptAll;
  collection.AcceptAll = () => {
    throw new Error('WPS busy');
  };
  Object.defineProperty(doc, 'Revisions', { get: () => collection });
  const result = settleAllDocumentRevisions(doc, 'accept');
  assert.equal(result.success, false);
  assert.equal(doc.Application.ScreenUpdating, true);
  assert.equal(hasRevisionBatch(batch.batchId), true);
  assert.equal(doc.ShowRevisions, true);
  assert.ok(result.timings.totalMs >= result.timings.nativeMs);
  collection.AcceptAll = accept;
  assert.equal(settleAllDocumentRevisions(doc, 'accept').success, true);
});

test('外层关闭重绘或 WPS 不支持该属性时仍正常确认', () => {
  for (const initial of [false, true]) {
    const doc = documentWith([revision({ type: 1, start: 10, end: 20, text: '新增' })]);
    doc.Application = {
      get ScreenUpdating() {
        return initial;
      },
      set ScreenUpdating(_value) {
        throw new Error('ScreenUpdating unsupported');
      }
    };
    const result = settleAllDocumentRevisions(doc, 'accept');
    assert.equal(result.success, true);
    assert.equal(doc.Application.ScreenUpdating, initial);
  }
});

test('用户已手动接受完修订时跳过全文 AcceptAll 并恢复预览', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  doc._items.push(revision({ type: 1, start: 10, end: 20, text: '新增' }));
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  doc._items = [];
  const result = settleAllDocumentRevisions(doc, 'accept');
  assert.equal(result.success, true);
  assert.equal(result.handled, 0);
  assert.equal(doc.acceptAllCalls, 0);
  assert.equal(hasRevisionBatch(batch.batchId), false);
  assert.equal(doc.ShowRevisions, false);
});

test('AcceptAll 返回后仍残留修订时不能清除待确认状态', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  doc._items.push(revision({ type: 1, start: 10, end: 20, text: '新增' }));
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  const collection = doc.Revisions;
  const accept = collection.AcceptAll;
  collection.AcceptAll = () => {};
  Object.defineProperty(doc, 'Revisions', { get: () => collection });
  assert.equal(settleAllDocumentRevisions(doc, 'accept').success, false);
  assert.equal(hasRevisionBatch(batch.batchId), true);
  collection.AcceptAll = accept;
  assert.equal(settleAllDocumentRevisions(doc, 'accept').success, true);
});

test('取消一次性拒绝多批新增、删除及相邻标题上的格式修订', () => {
  const doc = documentWith();
  const insertState = beginTrackedEdit(doc);
  const inserted = revision({ type: 1, start: 10, end: 30, text: '（4）新增\r（5）新增\r' });
  // 该标记在新增范围之外，不能假设拒绝新增文字就会自动删除它。
  const formatting = revision({ type: 8, start: 30, end: 40, text: '1.2 个人目标\r' });
  formatting.Reject = () => assert.fail('格式修订应使用集合级拒绝');
  let headingStyle = '正文缩进段落';
  formatting.onReject = () => {
    headingStyle = '标题 2';
  };
  doc._items.push(inserted, formatting);
  const first = finishTrackedEdit(insertState, { start: 10, end: 30 }, 'insert');
  const deleteState = beginTrackedEdit(doc);
  const deleted = revision({ type: 2, start: 42, end: 46, text: '原文' });
  doc._items.push(deleted);
  const second = finishTrackedEdit(deleteState, { start: 42, end: 46 }, 'delete');

  const result = rejectRevisionBatches(doc, [first.batchId, second.batchId]);
  assert.equal(result.success, true);
  assert.equal(result.handled, 3);
  assert.equal(doc.rejectAllCalls, 1);
  assert.equal(doc.Revisions.Count, 0);
  assert.equal(headingStyle, '标题 2');
  assert.equal(hasRevisionBatch(first.batchId), false);
  assert.equal(hasRevisionBatch(second.batchId), false);
  assert.equal(doc.ActiveWindow.View.ShowFormatChanges, true);
});

test('文档已有修订时只拒绝本轮范围，包括新增范围之外的格式修订', () => {
  const existing = revision({ type: 8, start: 60, end: 80, text: '已有格式', date: '2026-07-27' });
  const doc = documentWith([existing]);
  doc.Comments = [{ Text: '用户批注' }];
  const state = beginTrackedEdit(doc);
  const inserted = revision({ type: 1, start: 10, end: 20, text: '新增' });
  const formatting = revision({ type: 8, start: 21, end: 35, text: '个人目标\r' });
  formatting.Reject = () => assert.fail('不能逐条 Reject 格式修订');
  doc._items.unshift(inserted, formatting);
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  assert.equal(settleRevisionBatch(batch.batchId, 'reject').success, true);
  assert.equal(doc.rejectAllCalls, 0);
  assert.equal(formatting.rejected, 1);
  assert.equal(inserted.rejected, 1);
  assert.equal(existing.rejected, 0);
  assert.deepEqual(doc._items, [existing]);
  assert.deepEqual(doc.Comments, [{ Text: '用户批注' }]);
});

test('范围内包含用户已有修订时保留待处理批次，不扩大拒绝范围', () => {
  const existing = revision({ type: 3, start: 21, end: 35, text: '个人目标\r', date: '2026-07-27' });
  const doc = documentWith([existing]);
  const state = beginTrackedEdit(doc);
  const inserted = revision({ type: 1, start: 10, end: 20, text: '新增' });
  const formatting = revision({ type: 8, start: 21, end: 35, text: '个人目标\r' });
  doc._items.push(inserted, formatting);
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  assert.equal(settleRevisionBatch(batch.batchId, 'reject').success, false);
  assert.equal(hasRevisionBatch(batch.batchId), true);
  assert.equal(existing.rejected, 0);
  assert.equal(formatting.rejected, 0);
  assert.equal(doc.rejectAllCalls, 0);
  // 用户手动处理已有修订后，可以再次取消。
  doc._items.splice(doc._items.indexOf(existing), 1);
  assert.equal(settleRevisionBatch(batch.batchId, 'reject').success, true);
});

test('WPS 拒绝接口没有实际清除修订时保留批次供重试', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  doc._items.push(revision({ type: 1, start: 10, end: 20, text: '新增' }));
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  const collection = doc.Revisions;
  const reject = collection.RejectAll;
  collection.RejectAll = () => {};
  Object.defineProperty(doc, 'Revisions', { get: () => collection });
  assert.equal(settleRevisionBatch(batch.batchId, 'reject').success, false);
  assert.equal(hasRevisionBatch(batch.batchId), true);
  assert.equal(doc.ShowRevisions, true);
  collection.RejectAll = reject;
  assert.equal(settleRevisionBatch(batch.batchId, 'reject').success, true);
});

test('RejectAll 部分成功后重建了格式标记，仍保留批次并在重试时清除残留', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  doc._items.push(
    revision({ type: 1, start: 10, end: 20, text: '新增' }),
    revision({ type: 8, start: 21, end: 35, text: '标题与新增文字' })
  );
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  const collection = doc.Revisions;
  const reject = collection.RejectAll;
  collection.RejectAll = () => {
    doc._items = [revision({ type: 8, start: 10, end: 24, text: '个人目标\r' })];
    throw new Error('partial rejection');
  };
  Object.defineProperty(doc, 'Revisions', { get: () => collection });
  assert.equal(settleRevisionBatch(batch.batchId, 'reject').success, false);
  assert.equal(hasRevisionBatch(batch.batchId), true);
  collection.RejectAll = reject;
  assert.equal(settleRevisionBatch(batch.batchId, 'reject').success, true);
  assert.equal(doc.Revisions.Count, 0);
});

test('逐次拒绝后 WPS 重建 COM 对象时重新定位，不操作失效的缓存对象', () => {
  const existing = revision({ type: 1, start: 60, end: 70, text: '用户修订', date: '2026-07-27' });
  const doc = documentWith([existing]);
  const state = beginTrackedEdit(doc);
  doc._items.push(
    revision({ type: 1, start: 10, end: 20, text: '新增 1' }),
    revision({ type: 1, start: 30, end: 40, text: '新增 2' })
  );
  const batch = finishTrackedEdit(state, { start: 10, end: 40 }, 'insert');
  doc.Range = () => ({}); // 退回逐条拒绝，模拟每次操作都会重建剩余 Revision。
  const rebuild = () => {
    doc._items = doc._items.map((item) => {
      const replacement = revision({ type: item.Type, start: item.Range.Start, end: item.Range.End, text: item.Range.Text, date: item.Date });
      replacement.onReject = rebuild;
      return replacement;
    });
  };
  for (const item of doc._items) {
    item.onReject = rebuild;
  }
  assert.equal(settleRevisionBatch(batch.batchId, 'reject').success, true);
  assert.equal(doc._items.length, 1);
  assert.equal(doc._items[0].Range.Text, '用户修订');
});

// 在 Node 中执行实际 Vue Options API，验证取消失败不会让按钮失去重试入口。
const paneSource = readFileSync(new URL('../src/components/chat/AIChatPane.vue', import.meta.url), 'utf8');
const paneScript = paneSource.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/import[\s\S]*?from\s+['"][^'"]+['"];?/g, '');
function chatPane(doc, alert) {
  let cacheClears = 0;
  const api = { wsManager: { clearDocumentCache() {
    cacheClears += 1;
  } } };
  const component = new Function('ChatMessages', 'ChatInput', 'SessionPane', 'hasRevisionBatch', 'rejectRevisionBatches', 'settleAllDocumentRevisions', 'api', 'alert', 't', paneScript.replace('export default', 'return'))(
    {}, {}, {}, hasRevisionBatch, rejectRevisionBatches, settleAllDocumentRevisions, api, alert, (_key, values) => values?.error
  );
  const vm = { pendingInsertions: [], pendingEdits: [], deleteRevisions: [], _streamInsertions: [] };
  Object.assign(vm, component.methods, { _resolveTargetDoc: () => doc });
  return { vm, cacheClears: () => cacheClears };
}

test('确认多个插入、编辑、删除批次时每个文档只查找一次且只 AcceptAll 一次', () => {
  const doc = documentWith([revision({ type: 1, start: 10, end: 20, text: '新增' })]);
  const { vm, cacheClears } = chatPane(doc, () => assert.fail('确认应成功'));
  let lookups = 0;
  vm._resolveTargetDoc = () => {
    lookups += 1;
    return doc;
  };
  for (const list of [vm.pendingInsertions, vm.pendingEdits, vm.deleteRevisions]) {
    list.push({ docId: 1, msg: { _revisionBatchId: 'batch' } });
    list.push({ docId: 1, msg: { _revisionBatchId: 'batch' } });
  }
  vm.confirmPending();
  assert.equal(lookups, 1);
  assert.equal(doc.acceptAllCalls, 1);
  assert.equal(vm.pendingInsertions.length + vm.pendingEdits.length + vm.deleteRevisions.length, 0);
  assert.equal(cacheClears(), 1);
});

test('取消失败保留 Vue 待确认项，重试成功后才清除并刷新文档缓存', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  doc._items.push(revision({ type: 1, start: 10, end: 20, text: '新增' }));
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  const collection = doc.Revisions;
  const reject = collection.RejectAll;
  collection.RejectAll = () => {
    throw new Error('WPS busy');
  };
  Object.defineProperty(doc, 'Revisions', { get: () => collection });
  const alerts = [];
  const { vm, cacheClears } = chatPane(doc, (message) => alerts.push(message));
  const msg = { _revisionBatchId: batch.batchId };
  const item = { docId: 1, _markingMode: 'revision', _revisionBatchId: batch.batchId, documentJson: { paragraphs: [{}] }, msg };
  vm.pendingInsertions.push(item);
  vm.cancelPending();
  assert.equal(vm.pendingInsertions.length, 1);
  assert.equal(item._revisionBatchId, batch.batchId);
  assert.equal(msg._revisionBatchId, batch.batchId);
  assert.match(alerts[0], /WPS busy/);
  collection.RejectAll = reject;
  vm.cancelPending();
  assert.equal(vm.pendingInsertions.length, 0);
  assert.equal(msg._revisionBatchId, null);
  assert.equal(vm.pendingDocument, null);
  assert.equal(cacheClears(), 2);
});

test('没有原生修订的回写路径暂时关闭修订追踪，避免取消再产生修订', () => {
  const doc = documentWith();
  doc.TrackRevisions = true;
  let restored = '';
  doc.Range = () => ({ set Text(value) {
    assert.equal(doc.TrackRevisions, false);
    restored = value;
  } });
  const { vm } = chatPane(doc, () => assert.fail('取消应成功'));
  vm.pendingEdits.push({ _markingMode: 'revision-unavailable', startPos: 10, endPos: 20, originalText: '原文' });
  vm.cancelPending();
  assert.equal(restored, '原文');
  assert.equal(doc.TrackRevisions, true);
  assert.equal(vm.pendingEdits.length, 0);
});

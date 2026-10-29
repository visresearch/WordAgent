import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createSSRApp } from 'vue';
import { renderToString } from 'vue/server-renderer';
import zhCN from '../../shared/locales/zh-CN.js';

import {
  AI_REVISION_AUTHOR,
  abortTrackedEdit,
  beginTrackedEdit,
  finishTrackedEdit,
  getAIRevisionCount,
  hasRevisionBatch,
  rejectRevisionBatches,
  settleRevisionBatch,
  settleAllDocumentRevisions
} from '../src/components/js/revisionPreview.js';

function revision({ type, start, end, text, author = AI_REVISION_AUTHOR, date = '2026-07-28', acceptFailures = 0 }) {
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
    Application: { UserName: '当前用户', Options: { UseLocalUserInfo: false } },
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
                this[method === 'Reject' ? 'onReject' : 'onAccept']?.();
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

test('AI 编辑使用文策AI作者，完成后恢复用户名且不接管协作者的修订', () => {
  const existing = revision({ type: 1, start: 1, end: 3, text: '已有内容', author: '张三' });
  const doc = documentWith([existing]);
  const state = beginTrackedEdit(doc);
  assert.equal(doc.Application.UserName, '文策AI');
  assert.equal(doc.Application.Options.UseLocalUserInfo, true);
  const inserted = revision({ type: 1, start: 10, end: 20, text: 'AI内容', author: doc.Application.UserName });
  const collaborator = revision({ type: 1, start: 10, end: 20, text: '协作者内容', author: '李四' });
  doc._items.push(inserted, collaborator);
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  assert.equal(doc.Application.UserName, '当前用户');
  assert.equal(doc.Application.Options.UseLocalUserInfo, false);
  assert.equal(batch.revisionCount, 1);
  assert.equal(hasRevisionBatch(batch.batchId), true);
  assert.equal(settleRevisionBatch(batch.batchId, 'accept').success, true);
  assert.deepEqual(doc._items, [existing, collaborator]);
  assert.equal(inserted.accepted, 1);
});

for (const action of ['accept', 'reject']) {
  test(`Linux WPS 把修订署为账户用户时仍只${action}本轮 AI 修订`, () => {
    const human = revision({ type: 2, start: 2, end: 6, text: '用户旧修订', author: '登录用户', date: '2026-07-27' });
    const doc = Object.assign(documentWith([human]), { DocID: 26 });
    let localMode = false;
    let localName = '本地用户';
    doc.Application = {
      Options: {
        get UseLocalUserInfo() { return localMode; },
        set UseLocalUserInfo(value) { localMode = value; }
      },
      get UserName() { return localMode ? localName : '登录用户'; },
      set UserName(value) { localName = value; }
    };
    const revisions = Object.getOwnPropertyDescriptor(doc, 'Revisions');
    let revisionReads = 0;
    Object.defineProperty(doc, 'Revisions', { get() {
      revisionReads += 1;
      if (revisionReads === 2) {
        assert.equal(localMode, true);
        assert.equal(doc.Application.UserName, AI_REVISION_AUTHOR);
      }
      return revisions.get.call(doc);
    } });
    const state = beginTrackedEdit(doc);
    assert.equal(localMode, true);
    assert.equal(doc.Application.UserName, AI_REVISION_AUTHOR);
    const created = revision({ type: 2, start: 20, end: 24, text: 'AI删除', author: '登录用户' });
    doc._items.push(created);
    const batch = finishTrackedEdit(state, { start: 20, end: 24 }, 'delete');
    assert.ok(batch.batchId);
    assert.equal(localMode, false);
    assert.equal(localName, '本地用户');
    assert.equal(getAIRevisionCount(doc), 1);

    const { vm } = chatPane(doc, () => assert.fail('处理本轮修订应成功'));
    vm.deleteRevisions.push({ docId: 26, _revisionBatchId: batch.batchId });
    vm._refreshAIRevisionPreview();
    assert.deepEqual(vm.aiRevisionDocuments, [{ docId: 26, count: 1 }]);
    vm[action === 'accept' ? 'acceptPendingRevisions' : 'rejectPendingRevisions']();
    assert.deepEqual(doc._items, [human]);
    assert.equal(created[action === 'accept' ? 'accepted' : 'rejected'], 1);
    assert.equal(human.accepted + human.rejected, 0);
    assert.equal(vm.deleteRevisions.length, 0);
  });
}

test('Linux WPS 改写同名修订后拒绝静默清除确认入口', () => {
  const doc = Object.assign(documentWith(), { DocID: 27 });
  doc.Application.UserName = '登录用户';
  const state = beginTrackedEdit(doc);
  doc._items.push(revision({ type: 2, start: 20, end: 24, text: 'AI删除', author: '登录用户' }));
  const batch = finishTrackedEdit(state, { start: 20, end: 24 }, 'delete');
  doc._items = [revision({ type: 2, start: 20, end: 24, text: 'WPS合并后的文本', author: '登录用户' })];
  const alerts = [];
  const { vm } = chatPane(doc, (message) => alerts.push(message));
  vm.deleteRevisions.push({ docId: 27, _revisionBatchId: batch.batchId });
  vm.rejectPendingRevisions();
  assert.equal(vm.deleteRevisions.length, 1);
  assert.equal(doc._items.length, 1);
  assert.equal(doc._items[0].rejected, 0);
  assert.match(alerts[0], /无法安全确认/);
});

test('Linux 旧版未记录归属的用户署名修订不会被按钮静默跳过', () => {
  const oldRevision = revision({ type: 2, start: 20, end: 24, text: '旧 AI 删除', author: '登录用户' });
  const doc = Object.assign(documentWith([oldRevision]), { DocID: 28 });
  const alerts = [];
  const { vm } = chatPane(doc, (message) => alerts.push(message));
  vm.pendingEdits.push({ docId: 28, _revisionBatchId: null });
  vm.acceptPendingRevisions();
  assert.equal(vm.pendingEdits.length, 1);
  assert.equal(oldRevision.accepted, 0);
  assert.match(alerts[0], /无法安全地自动接受或拒绝/);
});

test('Windows WPS 保持原有用户名切换路径', (t) => {
  const previousNavigator = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { platform: 'Win32' } });
  t.after(() => {
    if (previousNavigator) {
      Object.defineProperty(globalThis, 'navigator', previousNavigator);
    } else {
      delete globalThis.navigator;
    }
  });
  const doc = documentWith();
  Object.defineProperty(doc.Application, 'Options', { get() { assert.fail('Windows 不应访问本地用户信息设置'); } });
  const revisions = Object.getOwnPropertyDescriptor(doc, 'Revisions');
  let revisionReads = 0;
  Object.defineProperty(doc, 'Revisions', { get() {
    revisionReads += 1;
    if (revisionReads === 2) {
      assert.equal(doc.Application.UserName, '当前用户', 'Windows 保持先恢复用户名再读取修订的顺序');
    }
    return revisions.get.call(doc);
  } });
  const state = beginTrackedEdit(doc);
  doc._items.push(revision({ type: 1, start: 10, end: 20, text: '新增' }));
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  assert.ok(batch.batchId);
  assert.equal(doc.Application.UserName, '当前用户');
  assert.equal(settleAllDocumentRevisions(doc, 'accept').success, true);
});

test('中止 AI 编辑恢复原用户名和修订设置', () => {
  const doc = documentWith();
  doc.TrackRevisions = true;
  const state = beginTrackedEdit(doc);
  assert.equal(doc.Application.UserName, '文策AI');
  abortTrackedEdit(state);
  abortTrackedEdit(state);
  assert.equal(doc.Application.UserName, '当前用户');
  assert.equal(doc.TrackRevisions, true);
  assert.equal(doc.TrackFormatting, true);
  assert.equal(doc.ShowRevisions, false);
  assert.equal(doc.ActiveWindow.View.RevisionsView, 1);
});

test('无法设置 AI 作者时停止编辑，开启追踪失败时恢复原用户名', () => {
  const locked = documentWith();
  Object.defineProperty(locked.Application, 'UserName', {
    get: () => '当前用户',
    set: () => {}
  });
  assert.throws(() => beginTrackedEdit(locked), /无法将修订作者设为文策AI/);
  assert.equal(locked.TrackRevisions, false);
  assert.equal(locked.TrackFormatting, true);

  const doc = documentWith();
  Object.defineProperty(doc, 'TrackRevisions', {
    get: () => false,
    set(value) {
      if (value) {
        throw new Error('tracking unavailable');
      }
    }
  });
  assert.throws(() => beginTrackedEdit(doc), /tracking unavailable/);
  assert.equal(doc.Application.UserName, '当前用户');
  assert.equal(doc.TrackFormatting, true);
  assert.equal(doc.ShowRevisions, false);
});

test('完成编辑时读取修订失败也恢复原用户名和显示设置', () => {
  const doc = documentWith();
  const state = beginTrackedEdit(doc);
  Object.defineProperty(doc, 'Revisions', { get: () => ({ Count: 1, Item() {
    throw new Error('read failure');
  } }) });
  assert.throws(() => finishTrackedEdit(state, { start: 0, end: 10 }, 'edit'), /无法完整读取/);
  assert.equal(doc.Application.UserName, '当前用户');
  assert.equal(doc.TrackRevisions, false);
  assert.equal(doc.TrackFormatting, true);
  assert.equal(doc.ShowRevisions, false);
});

for (const action of ['accept', 'reject']) {
  test(`${action} 只处理文策AI的增删和格式修订，允许其他作者继续保留`, () => {
    const human = revision({ type: 1, start: 10, end: 20, text: '重叠用户内容', author: '张三' });
    const humanFormat = revision({ type: 8, start: 70, end: 80, text: '用户格式', author: '李四' });
    const translatedAuthor = revision({ type: 1, start: 90, end: 100, text: '其他作者', author: '其他 AI 助手' });
    const oldAI = revision({ type: 1, start: 1, end: 5, text: '之前的AI修订' });
    const doc = documentWith([human, humanFormat, translatedAuthor, oldAI]);
    doc.Comments = [{ Text: '用户批注' }];
    const state = beginTrackedEdit(doc);
    const created = [
      revision({ type: 1, start: 10, end: 20, text: 'AI插入' }),
      revision({ type: 8, start: 30, end: 40, text: 'AI格式' }),
      revision({ type: 2, start: 50, end: 60, text: 'AI删除' })
    ];
    if (action === 'reject') {
      created[1].Reject = () => assert.fail('格式修订应使用安全的范围集合接口');
    }
    doc._items.push(...created);
    const batch = finishTrackedEdit(state, { start: 10, end: 60 }, 'edit');
    const result = settleAllDocumentRevisions(doc, action);
    assert.equal(result.success, true);
    assert.equal(result.handled, 4);
    assert.deepEqual(doc._items, [human, humanFormat, translatedAuthor]);
    for (const item of [oldAI, ...created]) {
      assert.equal(item[action === 'accept' ? 'accepted' : 'rejected'], 1);
    }
    assert.equal(doc.acceptAllCalls, 0);
    assert.equal(doc.rejectAllCalls, 0);
    assert.equal(hasRevisionBatch(batch.batchId), false);
    assert.deepEqual(doc.Comments, [{ Text: '用户批注' }]);
  });

  test(`${action} 没有 AI 修订时不处理其他作者，也不调用全文接口`, () => {
    const human = revision({ type: 2, start: 10, end: 20, text: '用户内容', author: '张三' });
    const doc = documentWith([human]);
    const result = settleAllDocumentRevisions(doc, action);
    assert.equal(result.success, true);
    assert.equal(result.handled, 0);
    assert.deepEqual(doc._items, [human]);
    assert.equal(doc.acceptAllCalls + doc.rejectAllCalls + doc.rangeRejectAllCalls, 0);
  });
}

test('无效修订动作不会处理文档内容', () => {
  const human = revision({ type: 1, start: 10, end: 20, text: '用户内容', author: '张三' });
  const doc = documentWith([human]);
  assert.equal(settleAllDocumentRevisions(doc, 'invalid').success, false);
  assert.deepEqual(doc._items, [human]);
});

for (const action of ['accept', 'reject']) {
  test(`${action} 逐条处理时重新读取重建的 COM 对象并保留其他作者`, () => {
    const doc = documentWith([
      revision({ type: 1, start: 10, end: 20, text: '用户内容', author: '张三' }),
      revision({ type: 1, start: 10, end: 20, text: 'AI内容1' }),
      revision({ type: 1, start: 30, end: 40, text: 'AI内容2' })
    ]);
    doc.Range = () => ({});
    const rebuild = () => {
      doc._items = doc._items.map((item) => {
        const replacement = revision({ type: item.Type, start: item.Range.Start, end: item.Range.End,
          text: item.Range.Text, date: item.Date, author: item.Author });
        replacement[action === 'accept' ? 'onAccept' : 'onReject'] = rebuild;
        return replacement;
      });
    };
    for (const item of doc._items) {
      item[action === 'accept' ? 'onAccept' : 'onReject'] = rebuild;
    }
    const result = settleAllDocumentRevisions(doc, action);
    assert.equal(result.success, true);
    assert.equal(result.handled, 2);
    assert.equal(doc._items.length, 1);
    assert.equal(doc._items[0].Author, '张三');
    assert.equal(doc._items[0].accepted + doc._items[0].rejected, 0);
    assert.equal(doc.acceptAllCalls + doc.rejectAllCalls, 0);
  });
}

test('处理一个文档不清理其他文档批次，且正确识别同一 DocID 的 COM 包装对象', () => {
  for (const withIds of [false, true]) {
    const firstDoc = documentWith();
    const secondDoc = documentWith();
    if (withIds) {
      firstDoc.DocID = 101;
      secondDoc.DocID = 102;
    }
    const firstState = beginTrackedEdit(firstDoc);
    firstDoc._items.push(revision({ type: 1, start: 10, end: 20, text: '第一篇' }));
    const first = finishTrackedEdit(firstState, { start: 10, end: 20 }, 'insert');
    const secondState = beginTrackedEdit(secondDoc);
    secondDoc._items.push(revision({ type: 1, start: 10, end: 20, text: '第二篇' }));
    const second = finishTrackedEdit(secondState, { start: 10, end: 20 }, 'insert');
    const target = withIds
      ? { DocID: '101', Application: firstDoc.Application, get Revisions() {
        return firstDoc.Revisions;
      } }
      : firstDoc;
    assert.equal(settleAllDocumentRevisions(target, 'accept').success, true);
    assert.equal(hasRevisionBatch(first.batchId), false);
    assert.equal(firstDoc.ShowRevisions, false);
    assert.equal(hasRevisionBatch(second.batchId), true);
    assert.equal(secondDoc.ShowRevisions, true);
    assert.equal(secondDoc._items.length, 1);
    assert.equal(settleAllDocumentRevisions(secondDoc, 'reject').success, true);
  }
});

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
      const replacement = revision({ type: item.Type, start: item.Range.Start, end: item.Range.End, text: item.Range.Text, date: item.Date, author: item.Author });
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
function chatPane(doc, alert, documents = [doc], converters = {}) {
  doc.DocID ??= 1;
  let activeDoc = doc;
  const window = { Application: { ...doc.Application, get ActiveDocument() {
    return activeDoc; 
  } } };
  let cacheClears = 0;
  const responses = [];
  const api = { wsManager: { async send(response) {
    responses.push(response); 
  }, clearDocumentCache() {
    cacheClears += 1;
  } } };
  const component = new Function('ChatMessages', 'ChatInput', 'SessionPane', 'hasRevisionBatch', 'rejectRevisionBatches', 'settleAllDocumentRevisions', 'getAIRevisionCount', 'beginTrackedEdit', 'finishTrackedEdit', 'abortTrackedEdit', 'getDocumentById', 'api', 'alert', 't', 'window', 'generateDocxFromJSON', 'editDocxParagraph', 'deleteDocxPara', 'getParagraphParaID', paneScript.replace('export default', 'return'))(
    {}, {}, {}, hasRevisionBatch, rejectRevisionBatches, settleAllDocumentRevisions, getAIRevisionCount, beginTrackedEdit, finishTrackedEdit, abortTrackedEdit,
    id => documents.find(item => item.DocID === Number(id)) || activeDoc, api, alert, (_key, values) => values?.error, window,
    converters.generate, converters.edit, converters.delete, converters.paraID
  );
  const vm = Object.assign(component.data(), component.methods);
  vm._refreshAIRevisionPreview();
  return { vm, responses, cacheClears: () => cacheClears, resolveTargetDoc: component.methods._resolveTargetDoc.bind(vm),
    selectDocument(next) {
      activeDoc = next; 
    } };
}

for (const action of ['accept', 'reject']) {
  test(`聊天页重新打开后 ${action} 只处理文策AI，旧名称和大小写/空格变体均保留`, () => {
    const protectedAuthors = [
      '张三', 'WordAgent', 'wordagent', '文策Ai', ' 文策AI', '文策AI ', '文策 AI 助手',
      'WenCe AI Assistant', 'Asisten WenCe AI', 'WenCe AI アシスタント', 'WenCe AI 어시스턴트', 'WenCe AI Trợ lý'
    ].map((author, index) => revision({ type: 1, start: 90 + index * 20, end: 100 + index * 20, text: '其他作者内容', author }));
    const owned = [1, 8].map((type, index) => revision({
      type, start: index * 20, end: index * 20 + 10, text: 'AI内容', author: '文策AI'
    }));
    const doc = documentWith([...protectedAuthors, ...owned]);
    doc.DocID = 23;
    const { vm, cacheClears } = chatPane(doc, () => assert.fail('处理应成功'));
    assert.equal(getAIRevisionCount(doc), 2);
    assert.equal(vm.pendingInsertions.length + vm.pendingEdits.length + vm.deleteRevisions.length, 0);
    vm._refreshAIRevisionPreview(doc);
    assert.deepEqual(vm.aiRevisionDocuments, [{ docId: 23, count: 2 }]);
    vm[action === 'accept' ? 'acceptPendingRevisions' : 'rejectPendingRevisions']();
    assert.deepEqual(doc._items, protectedAuthors);
    assert.deepEqual(vm.aiRevisionDocuments, []);
    assert.equal(cacheClears(), 1);
    for (const item of owned) {
      assert.equal(item[action === 'accept' ? 'accepted' : 'rejected'], 1);
    }
    assert.equal(doc.acceptAllCalls + doc.rejectAllCalls, 0);
  });
}

test('临时读取修订失败保留入口，修订已手动处理后移除入口', () => {
  const doc = documentWith([revision({ type: 1, start: 10, end: 20, text: 'AI内容' })]);
  doc.DocID = 23;
  const { vm } = chatPane(doc, () => {});
  vm._refreshAIRevisionPreview(doc);
  const read = Object.getOwnPropertyDescriptor(doc, 'Revisions');
  Object.defineProperty(doc, 'Revisions', { get() {
    throw new Error('WPS busy');
  } });
  vm._refreshAIRevisionPreview(doc);
  assert.deepEqual(vm.aiRevisionDocuments, [{ docId: 23, count: 1 }]);
  Object.defineProperty(doc, 'Revisions', read);
  doc._items = [];
  vm._refreshAIRevisionPreview(doc);
  assert.deepEqual(vm.aiRevisionDocuments, []);
});

test('生成期间不处理修订，已有其他 AI 作者字样不会被模糊识别', () => {
  const human = revision({ type: 1, start: 30, end: 40, text: '用户内容', author: '其他 AI 助手' });
  const doc = documentWith([revision({ type: 1, start: 10, end: 20, text: 'AI内容' }), human]);
  doc.DocID = 23;
  const { vm } = chatPane(doc, () => {});
  vm._refreshAIRevisionPreview(doc);
  vm.isLoading = true;
  vm.acceptPendingRevisions();
  vm.rejectPendingRevisions();
  assert.deepEqual(vm.aiRevisionDocuments, [{ docId: 23, count: 1 }]);
  assert.equal(doc._items.length, 2);
  assert.equal(doc.acceptAllCalls + doc.rejectAllCalls + doc.rangeRejectAllCalls, 0);
});

test('文档里已有原生 AI 修订时，取消不再按旧 Range 重复删除正文', () => {
  const human = revision({ type: 1, start: 10, end: 20, text: '用户内容', author: '张三' });
  const inserted = revision({ type: 1, start: 10, end: 20, text: 'AI内容' });
  const doc = documentWith([human, inserted]);
  doc.DocID = 23;
  doc.Range = () => ({ Delete() {
    assert.fail('不能按旧范围再次删除正文');
  } });
  const { vm } = chatPane(doc, () => assert.fail('取消应成功'));
  vm.pendingInsertions.push({ docId: 23, insertStartPos: 10, insertEndPos: 20 });
  vm._refreshAIRevisionPreview(doc);
  vm.rejectPendingRevisions();
  assert.equal(vm.pendingInsertions.length, 0);
  assert.deepEqual(vm.aiRevisionDocuments, []);
  assert.deepEqual(doc._items, [human]);
  assert.equal(inserted.rejected, 1);
});

test('指定文档已经关闭时，不回退到另一个活动文档处理修订', () => {
  const doc = documentWith();
  doc.DocID = 24;
  const { resolveTargetDoc } = chatPane(doc, () => {});
  assert.equal(resolveTargetDoc(23), null);
  assert.equal(resolveTargetDoc(24), doc);
  assert.equal(resolveTargetDoc(0), doc);
});

test('纯文本插入也使用文策AI修订并立即登记确认栏', (t) => {
  const human = revision({ type: 1, start: 50, end: 60, text: '用户内容', author: '张三' });
  const doc = documentWith([human]);
  doc.DocID = 25;
  doc.Content = { End: 60 };
  const range = { Start: 10, End: 10 };
  doc.Application.ActiveDocument = doc;
  doc.Application.Selection = {
    Range: range,
    TypeText(text) {
      assert.equal(doc.Application.UserName, '文策AI');
      assert.equal(doc.TrackRevisions, true);
      range.End += text.length;
      doc._items.push(revision({ type: 1, start: range.Start, end: range.End, text, author: doc.Application.UserName }));
    },
    TypeParagraph() {
      range.End += 1;
    }
  };
  const previousWindow = Object.getOwnPropertyDescriptor(globalThis, 'window');
  Object.defineProperty(globalThis, 'window', { configurable: true, value: { Application: doc.Application } });
  t.after(() => {
    if (previousWindow) {
      Object.defineProperty(globalThis, 'window', previousWindow);
    } else {
      delete globalThis.window;
    }
  });
  const { vm } = chatPane(doc, () => {});
  const msg = {};
  vm.insertPlainText('纯文本内容', msg);
  assert.equal(doc.Application.UserName, '当前用户');
  assert.equal(doc.TrackRevisions, false);
  assert.equal(vm.pendingInsertions.length, 1);
  assert.ok(vm.pendingDocument);
  assert.equal(hasRevisionBatch(msg._revisionBatchId), true);
  assert.deepEqual(vm.aiRevisionDocuments, [{ docId: 25, count: 1 }]);
  vm.acceptPendingRevisions();
  assert.deepEqual(doc._items, [human]);
  assert.equal(vm.pendingDocument, null);
  assert.deepEqual(vm.aiRevisionDocuments, []);
});

const inputSource = readFileSync(new URL('../src/components/chat/ChatInput.vue', import.meta.url), 'utf8');
const inputScript = inputSource.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/import[\s\S]*?from\s+['"][^'"]+['"];?/g, '');
const translate = (key, params = {}) => String(key.split('.').reduce((value, part) => value?.[part], zhCN) ?? key)
  .replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? `{${name}}`));
const inputComponent = new Function('addIcon', 'agentIcon', 'askIcon', 'fileIcon', 'sendIcon', 't', inputScript.replace('export default', 'return'))(
  '', '', '', '', '', translate
);
async function renderInput(props) {
  const app = createSSRApp({ ...inputComponent, template: inputSource.match(/<template>([\s\S]*?)<\/template>/)[1] }, props);
  app.config.globalProperties.$t = translate;
  return renderToString(app);
}

test('实际 Vue 模板显示接受/拒绝栏，生成期间显示禁用按钮', async () => {
  const html = await renderInput({ pendingRevisionCount: 2 });
  assert.match(html, /pending-document-bar/);
  assert.match(html, /2 处修改/);
  const actions = html.match(/<div class="pending-actions">([\s\S]*?)<\/div>/)[1];
  assert.match(actions, /class="pending-btn accept-revision-btn">接受<\/button>/);
  assert.match(actions, /class="pending-btn reject-revision-btn">拒绝<\/button>/);
  assert.doesNotMatch(actions, /disabled/);
  const loading = await renderInput({ pendingRevisionCount: 2, isLoading: true });
  const loadingActions = loading.match(/<div class="pending-actions">([\s\S]*?)<\/div>/)[1];
  assert.equal(loadingActions.match(/<button\b[^>]*\bdisabled\b/g).length, 2);
  const empty = await renderInput({});
  assert.doesNotMatch(empty, /pending-document-bar/);
  assert.equal(zhCN.windows.assistant, '文策AI');
});

for (const action of ['accept', 'reject']) {
  test(`Vue ${action} 按作者处理后清理确认栏，保留同范围的其他作者修订`, () => {
    const human = revision({ type: 1, start: 10, end: 20, text: '用户内容', author: '张三' });
    const doc = documentWith([human]);
    const state = beginTrackedEdit(doc);
    const inserted = revision({ type: 1, start: 10, end: 20, text: 'AI内容' });
    doc._items.push(inserted);
    const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
    const { vm } = chatPane(doc, () => assert.fail('处理应成功'));
    const msg = { _revisionBatchId: batch.batchId };
    vm.pendingInsertions.push({ docId: 1, _markingMode: 'revision', _revisionBatchId: batch.batchId,
      documentJson: { paragraphs: [{}] }, msg });
    vm._syncPendingDocumentPreview();
    assert.ok(vm.pendingDocument, '处理前应有确认栏');
    vm[action === 'accept' ? 'acceptPendingRevisions' : 'rejectPendingRevisions']();
    assert.equal(vm.pendingInsertions.length, 0);
    assert.equal(vm.pendingDocument, null);
    assert.equal(msg._revisionBatchId, null);
    assert.equal(hasRevisionBatch(batch.batchId), false);
    assert.deepEqual(doc._items, [human]);
    assert.equal(inserted[action === 'accept' ? 'accepted' : 'rejected'], 1);
    assert.equal(doc.acceptAllCalls + doc.rejectAllCalls + doc.rangeRejectAllCalls, 0);
  });
}

test('Vue 取消遇到与其他作者重叠的格式修订时保留确认栏和重试入口', () => {
  const human = revision({ type: 3, start: 21, end: 35, text: '用户格式', author: '张三' });
  const doc = documentWith([human]);
  const state = beginTrackedEdit(doc);
  const formatting = revision({ type: 8, start: 21, end: 35, text: 'AI格式' });
  doc._items.push(revision({ type: 1, start: 10, end: 20, text: 'AI内容' }), formatting);
  const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
  const alerts = [];
  const { vm } = chatPane(doc, (message) => alerts.push(message));
  const msg = { _revisionBatchId: batch.batchId };
  vm.pendingInsertions.push({ docId: 1, _markingMode: 'revision', _revisionBatchId: batch.batchId,
    documentJson: { paragraphs: [{}] }, msg });
  vm.rejectPendingRevisions();
  assert.equal(vm.pendingInsertions.length, 1);
  assert.ok(vm.pendingDocument);
  assert.equal(msg._revisionBatchId, batch.batchId);
  assert.equal(hasRevisionBatch(batch.batchId), true);
  assert.match(alerts[0], /格式修订范围包含其他修订/);
  assert.equal(human.rejected, 0);
  assert.equal(formatting.rejected, 0);
  assert.equal(doc.rangeRejectAllCalls + doc.rejectAllCalls, 0);
  doc._items.splice(doc._items.indexOf(human), 1);
  vm.rejectPendingRevisions();
  assert.equal(vm.pendingInsertions.length, 0);
  assert.equal(vm.pendingDocument, null);
});

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
  vm.acceptPendingRevisions();
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
  vm.rejectPendingRevisions();
  assert.equal(vm.pendingInsertions.length, 1);
  assert.equal(item._revisionBatchId, batch.batchId);
  assert.equal(msg._revisionBatchId, batch.batchId);
  assert.match(alerts[0], /WPS busy/);
  collection.RejectAll = reject;
  vm.rejectPendingRevisions();
  assert.equal(vm.pendingInsertions.length, 0);
  assert.equal(msg._revisionBatchId, null);
  assert.equal(vm.pendingDocument, null);
  assert.equal(cacheClears(), 2);
});

test('原生修订已手动处理时拒绝不回写正文', () => {
  const doc = documentWith();
  doc.TrackRevisions = true;
  let restored = '';
  doc.Range = () => ({ set Text(value) {
    assert.equal(doc.TrackRevisions, false);
    restored = value;
  } });
  const { vm } = chatPane(doc, () => assert.fail('取消应成功'));
  vm.pendingEdits.push({ docId: doc.DocID, startPos: 10, endPos: 20, originalText: '原文' });
  vm.rejectPendingRevisions();
  assert.equal(restored, '');
  assert.equal(doc.TrackRevisions, true);
  assert.equal(vm.pendingEdits.length, 0);
});

for (const action of ['accept', 'reject']) {
  test(`${action} only affects the active DocID and retains the other document's batches`, () => {
    const docs = [31, 32].map(DocID => {
      const human = revision({ type: 1, start: 10, end: 20, text: 'Human', author: '张三' });
      const doc = Object.assign(documentWith([human]), { DocID, Name: `${DocID}.docx` });
      const state = beginTrackedEdit(doc);
      const ai = revision({ type: 1, start: 10, end: 20, text: 'AI' });
      doc._items.push(ai);
      const batch = finishTrackedEdit(state, { start: 10, end: 20 }, 'insert');
      return { doc, human, ai, batch };
    });
    const { vm, selectDocument } = chatPane(docs[0].doc, () => assert.fail('Should succeed'), docs.map(item => item.doc));
    for (const { doc, batch } of docs) {
      for (const key of ['pendingInsertions', 'pendingEdits', 'deleteRevisions']) {
        vm[key].push({ docId: doc.DocID, _revisionBatchId: batch.batchId,
          documentJson: { paragraphs: [{}] }, msg: { _revisionBatchId: batch.batchId } });
      }
    }
    vm._refreshAIRevisionPreview();
    assert.deepEqual(vm.aiRevisionDocuments, [{ docId: 31, count: 1 }]);
    assert.equal(vm.revisionDocumentName, '31.docx');
    const handler = action === 'accept' ? 'acceptPendingRevisions' : 'rejectPendingRevisions';
    vm[handler]();
    assert.deepEqual(docs[0].doc._items, [docs[0].human]);
    assert.deepEqual(docs[1].doc._items, [docs[1].human, docs[1].ai]);
    assert.equal(hasRevisionBatch(docs[1].batch.batchId), true);
    for (const key of ['pendingInsertions', 'pendingEdits', 'deleteRevisions']) {
      assert.deepEqual(vm[key].map(item => item.docId), [32]);
      assert.equal(vm[key][0].msg._revisionBatchId, docs[1].batch.batchId);
    }
    assert.equal(vm.pendingDocument, null);
    selectDocument(docs[1].doc);
    vm[handler](); // A's stale button must only refresh the panel.
    assert.equal(docs[1].ai.accepted + docs[1].ai.rejected, 0);
    assert.equal(vm.revisionDocumentName, '32.docx');
    assert.deepEqual(vm.aiRevisionDocuments, [{ docId: 32, count: 1 }]);
    vm[handler]();
    assert.deepEqual(docs[1].doc._items, [docs[1].human]);
    assert.equal(hasRevisionBatch(docs[1].batch.batchId), false);
    assert.equal(vm.pendingInsertions.length + vm.pendingEdits.length + vm.deleteRevisions.length, 0);
  });
}

test('closing a document, missing DocID, or lookup fallback cannot settle another document', () => {
  const a = Object.assign(documentWith([revision({ type: 1, start: 10, end: 20, text: 'A' })]), { DocID: 41 });
  const b = Object.assign(documentWith([revision({ type: 1, start: 10, end: 20, text: 'B' })]), { DocID: 42 });
  const { vm, selectDocument } = chatPane(a, () => assert.fail('No mutation'), [a, b]);
  vm._resolveTargetDoc = () => b;
  vm.acceptPendingRevisions();
  vm.rejectPendingRevisions();
  assert.equal(a._items.length, 1);
  assert.equal(b._items.length, 1);
  selectDocument(null);
  vm.rejectPendingRevisions();
  assert.equal(vm.activeRevisionDocId, null);
  selectDocument({ ...b, DocID: 0 });
  vm.acceptPendingRevisions();
  assert.deepEqual(vm.aiRevisionDocuments, []);
  assert.equal(b._items.length, 1);
  for (const action of ['accept', 'reject']) {
    assert.equal(settleAllDocumentRevisions(b, action, a.DocID).success, false);
  }
  assert.equal(b.acceptAllCalls + b.rejectAllCalls, 0);
});

test('inserting with docId zero binds the pending revision to the actual document immediately', () => {
  const doc = Object.assign(documentWith(), { DocID: 51 });
  const { vm } = chatPane(doc, () => assert.fail('Should succeed'), [doc], {
    generate(json, target) {
      assert.equal(target, doc);
      doc._items.push(revision({ type: 1, start: 10, end: 20, text: 'Generated' }));
      return { success: true, startPos: 10, endPos: 20 };
    }
  });
  const msg = {};
  const item = { docId: 0, insertParaID: 0, documentJson: { paragraphs: [{}] }, msg };
  assert.equal(vm._applyImmediateInsertion(item), true);
  assert.equal(item.docId, 51);
  assert.equal(msg._docId, 51);
  assert.deepEqual(vm.aiRevisionDocuments, [{ docId: 51, count: 1 }]);
  vm.rejectPendingRevisions();
  assert.equal(doc._items.length, 0);
});

test('删除成功但 WPS 未返回独立删除修订时仍回报成功，并要求重新读取', () => {
  const doc = Object.assign(documentWith(), { DocID: 61 });
  const range = { Start: 10, End: 20, get Duplicate() {
    return this; 
  }, Expand() {} };
  doc.Paragraphs = { Count: 1, Item: () => ({ ID: 101, Range: range }) };
  doc.Application.Undo = () => assert.fail('Deletion must never automatically undo');
  const { vm, responses } = chatPane(doc, () => {}, [doc], {
    paraID: para => para.ID, delete: () => ({ success: true, deletedCount: 1, deletedParaIDs: [101], targetRange: { start: 10, end: 20 } })
  });
  assert.equal(vm._applyImmediateDelete({ docId: 0, startParaID: 101, requestId: 'delete' }), true);
  assert.equal(responses[0].success, true);
  assert.equal(responses[0].deletedCount, 1);
  assert.equal(responses[0].revisionCount, 0);
  assert.equal(responses[0].requiresRead, true);
  assert.equal(vm.deleteRevisions.length, 0);
  assert.equal('rollbackVerified' in responses[0], false);
});

test('部分删除且没有新增修订时仍报告未完成的段落', () => {
  const doc = Object.assign(documentWith(), { DocID: 62 });
  const range = { Start: 10, End: 20, get Duplicate() { return this; }, Expand() {} };
  doc.Paragraphs = { Count: 2, Item: index => ({ ID: index === 1 ? 101 : 202, Range: range }) };
  const { vm, responses } = chatPane(doc, () => {}, [doc], {
    paraID: para => para.ID,
    delete: () => ({ success: false, deletedCount: 1, deletedParaIDs: [101], failedParaIDs: [202], targetRange: { start: 10, end: 20 } })
  });
  assert.equal(vm._applyImmediateDelete({ docId: 62, startParaID: 101, endParaID: 202, requestId: 'partial' }), false);
  assert.equal(responses[0].success, false);
  assert.equal(responses[0].deletedCount, 1);
  assert.deepEqual(responses[0].failedParaIDs, [202]);
  assert.equal(responses[0].requiresRead, true);
});

test('manual formatted insertion records the actual DocID in its message and pending item', () => {
  const doc = Object.assign(documentWith(), { DocID: 71, Content: { End: 20 } });
  const { vm } = chatPane(doc, () => assert.fail('Should succeed'), [doc], {
    generate() {
      doc._items.push(revision({ type: 1, start: 10, end: 20, text: 'Formatted' }));
      return { success: true, startPos: 10, endPos: 20 };
    }
  });
  const msg = { documentJson: { paragraphs: [{}] }, _insertParaID: 0 };
  vm.insertToWord(msg);
  assert.equal(vm.pendingInsertions[0].docId, 71);
  assert.equal(msg._docId, 71);
  vm.acceptPendingRevisions();
  assert.equal(vm.pendingInsertions.length, 0);
  assert.equal(doc._items.length, 0);
});

test('缺失插入 ID 直接回报失败，不进入文档写入', () => {
  const doc = documentWith();
  let writes = 0;
  const { vm, responses } = chatPane(doc, () => {}, [doc], {
    generate() { writes++; return { success: true }; }
  });
  assert.equal(vm._applyImmediateInsertion({ docId: 0, requestId: 'missing', documentJson: { paragraphs: [] } }), false);
  assert.equal(writes, 0);
  assert.equal(responses[0].success, false);
  assert.match(responses[0].error, /insertParaID/);
});

test('格式化插入失败、JSON 无效或缺失 ID 时均不回退纯文本写入', () => {
  const doc = Object.assign(documentWith(), { Content: { End: 20 } });
  const alerts = [];
  const { vm } = chatPane(doc, message => alerts.push(message), [doc], {
    generate() { return { error: 'Missing target paragraph' }; }
  });
  let plainTextWrites = 0;
  vm.insertPlainText = () => { plainTextWrites++; };
  for (const msg of [
    { documentJson: { paragraphs: [] }, _insertParaID: 999 },
    { documentJson: { paragraphs: [] } },
    { documentJson: { tables: [] }, _insertParaID: 0 },
    { content: '```json\n{invalid\n```' },
  ]) vm.insertToWord(msg);
  assert.equal(alerts.length, 4);
  assert.equal(plainTextWrites, 0);
  assert.equal(vm.pendingInsertions.length, 0);
});

test('edit and delete requests with docId zero also retain a concrete document identity', () => {
  const doc = Object.assign(documentWith(), { DocID: 81 });
  const range = { Start: 10, End: 20, get Duplicate() {
    return this; 
  }, Expand() {} };
  doc.Paragraphs = { Count: 1, Item: () => ({ ID: 101, Range: range }) };
  const { vm } = chatPane(doc, () => assert.fail('Should succeed'), [doc], {
    edit() {
      doc._items.push(revision({ type: 1, start: 10, end: 20, text: 'Edited' }));
      return { success: true, startPos: 10, endPos: 20 };
    },
    paraID: para => para.ID,
    delete() {
      doc._items.push(revision({ type: 2, start: 10, end: 20, text: 'Deleted' }));
      return { success: true, deletedCount: 1, deletedParaIDs: [101], targetRange: { start: 10, end: 20 } };
    }
  });
  assert.equal(vm._applyImmediateEdit({ docId: 0, paraID: 101, runs: [] }), true);
  assert.equal(vm.pendingEdits[0].docId, 81);
  assert.equal(vm._applyImmediateDelete({ docId: 0, startParaID: 101 }), true);
  assert.equal(vm.deleteRevisions[0].docId, 81);
  vm.acceptPendingRevisions();
  assert.equal(vm.pendingEdits.length + vm.deleteRevisions.length, 0);
});

test('native edits suspend redraw and restore the original state on completion or abort', () => {
  for (const initial of [true, false]) {
    for (const abort of [true, false]) {
      const doc = documentWith();
      doc.Application.ScreenUpdating = initial;
      const state = beginTrackedEdit(doc);
      assert.equal(doc.Application.ScreenUpdating, false);
      if (abort) {
        abortTrackedEdit(state);
      } else {
        doc._items.push(revision({ type: 1, start: 10, end: 20, text: 'AI' }));
        finishTrackedEdit(state, { start: 10, end: 20 }, 'edit');
      }
      assert.equal(doc.Application.ScreenUpdating, initial);
      assert.equal(doc.Application.UserName, '当前用户');
      assert.equal(doc.TrackRevisions, false);
    }
  }
});

test('redraw is also restored if collecting revisions fails after the edit', () => {
  const doc = documentWith();
  doc.Application.ScreenUpdating = true;
  const state = beginTrackedEdit(doc);
  Object.defineProperty(doc, 'Revisions', { get() {
    throw new Error('WPS busy'); 
  } });
  assert.throws(() => finishTrackedEdit(state, { start: 10, end: 20 }, 'edit'), /WPS busy/);
  assert.equal(doc.Application.ScreenUpdating, true);
  assert.equal(doc.Application.UserName, '当前用户');
});

test('revision preview polling does not scan native revisions while the agent is generating', () => {
  const doc = Object.assign(documentWith(), { DocID: 91 });
  const { vm } = chatPane(doc, () => {});
  vm.isLoading = true;
  let reads = 0;
  Object.defineProperty(doc, 'Revisions', { get() {
    reads++; throw new Error('Should not read during generation'); 
  } });
  vm.pendingEdits.push({ docId: 91 });
  vm._refreshAIRevisionPreview();
  assert.equal(reads, 0);
  assert.equal(vm.activeRevisionDocId, 91);
  assert.equal(vm.pendingEdits.length, 1);
});


test('unknown range deletion counts remain unknown in the WPS chat response', () => {
  const doc = Object.assign(documentWith(), { DocID: 90 });
  const { vm, responses } = chatPane(doc, () => {}, [doc], {
    delete: () => ({ success: false, deletedCount: null, requiresRead: true, message: 'Unknown deletion result' })
  });
  assert.equal(vm._applyImmediateDelete({ startParaID: 101, requestId: 'unknown' }), false);
  assert.equal(responses[0].deletedCount, null);
  assert.equal(responses[0].requiresRead, true);
});

/* global Office, Word */

const revisionBatches = new Map();
let previewDisplayState = null;
let nextBatchId = 1;

const ADDED_TYPE = 'added';
const DELETED_TYPE = 'deleted';
const FORMATTED_TYPE = 'formatted';

function normalizeType(type) {
  return String(type || '').trim().toLowerCase();
}

function dateValue(date) {
  if (date instanceof Date) {
    return date.toISOString();
  }
  return String(date || '');
}

function changeSignature(change) {
  return [
    normalizeType(change.type),
    String(change.author || ''),
    dateValue(change.date),
    String(change.text || '')
  ].join('\u0001');
}

export function subtractExistingChanges(before, after) {
  const counts = new Map();
  for (const item of before || []) {
    const signature = changeSignature(item);
    counts.set(signature, (counts.get(signature) || 0) + 1);
  }

  return (after || []).filter((item) => {
    const signature = changeSignature(item);
    const count = counts.get(signature) || 0;
    if (count <= 0) {
      return true;
    }
    counts.set(signature, count - 1);
    return false;
  });
}

export function selectBatchChanges(changes, kind) {
  const expectedTypes = kind === 'edit'
    ? new Set([ADDED_TYPE, DELETED_TYPE])
    : new Set([kind === 'delete' ? DELETED_TYPE : ADDED_TYPE]);
  const expected = (changes || []).filter((item) => expectedTypes.has(normalizeType(item.type)));
  if (expected.length === 0) {
    return [];
  }
  // 格式修订不展示，但仍归入本轮批次，确认后不能遗留在文档中。
  return (changes || []).filter((item) => {
    const type = normalizeType(item.type);
    return expectedTypes.has(type) || type === FORMATTED_TYPE;
  });
}

function isRequirementSupported(name, version) {
  try {
    return Boolean(Office?.context?.requirements?.isSetSupported(name, version));
  } catch (error) {
    return false;
  }
}

function assertNativeRevisionSupport() {
  if (!isRequirementSupported('WordApi', '1.6')) {
    throw new Error('当前 Microsoft Word 不支持原生修订预览（需要 WordApi 1.6）');
  }
}

function supportsDesktopRevisionView() {
  return isRequirementSupported('WordApiDesktop', '1.4');
}

function loadChanges(collection) {
  collection.load('items/author,items/date,items/text,items/type');
}

function snapshotChanges(items) {
  return (items || []).map((item) => ({
    author: item.author,
    date: item.date,
    text: item.text,
    type: item.type
  }));
}

function configureNativeRevisionView(view, filter) {
  if (!view) {
    return;
  }
  view.areFormatChangesDisplayed = false;
  view.areInsertionsAndDeletionsDisplayed = true;
  if (filter) {
    filter.markup = 'Simple';
    filter.view = 'Final';
  }
}

function restoreNativeRevisionView(view, filter, display) {
  if (!view || !display) {
    return;
  }
  view.areFormatChangesDisplayed = display.areFormatChangesDisplayed;
  view.areInsertionsAndDeletionsDisplayed = display.areInsertionsAndDeletionsDisplayed;
  if (filter && display.markup) {
    filter.markup = display.markup;
  }
  if (filter && display.revisionsView) {
    filter.view = display.revisionsView;
  }
}

function acquirePreviewDisplay(state) {
  if (!previewDisplayState) {
    previewDisplayState = {
      ...state.display,
      before: state.before,
      batchCount: 0
    };
  }
  previewDisplayState.batchCount += 1;
}

export async function beginTrackedEdit() {
  assertNativeRevisionSupport();
  const desktopViewSupported = supportsDesktopRevisionView();

  return Word.run(async (context) => {
    const doc = context.document;
    const changes = doc.body.getTrackedChanges();
    doc.load('changeTrackingMode');
    loadChanges(changes);

    let view = null;
    let filter = null;
    if (desktopViewSupported) {
      view = doc.activeWindow.view;
      filter = view.revisionsFilter;
      view.load('areFormatChangesDisplayed,areInsertionsAndDeletionsDisplayed');
      filter.load('markup,view');
    }
    await context.sync();

    const state = {
      previousMode: doc.changeTrackingMode,
      before: snapshotChanges(changes.items),
      finished: false,
      display: {
        desktopViewSupported,
        areFormatChangesDisplayed: view?.areFormatChangesDisplayed,
        areInsertionsAndDeletionsDisplayed: view?.areInsertionsAndDeletionsDisplayed,
        markup: filter?.markup,
        revisionsView: filter?.view
      }
    };

    try {
      doc.changeTrackingMode = 'TrackAll';
      configureNativeRevisionView(view, filter);
      await context.sync();
      return state;
    } catch (error) {
      try {
        doc.changeTrackingMode = state.previousMode;
        restoreNativeRevisionView(view, filter, state.display);
        await context.sync();
      } catch (restoreError) {
        console.warn('[revisionPreview] 开启原生修订失败后恢复设置失败:', restoreError);
      }
      throw error;
    }
  });
}

export async function abortTrackedEdit(state) {
  if (!state || state.finished) {
    return;
  }
  state.finished = true;
  await Word.run(async (context) => {
    context.document.changeTrackingMode = state.previousMode;
    if (!previewDisplayState && state.display.desktopViewSupported) {
      const view = context.document.activeWindow.view;
      restoreNativeRevisionView(view, view.revisionsFilter, state.display);
    }
    await context.sync();
  });
}

export async function finishTrackedEdit(state, kind) {
  if (!state || state.finished) {
    return { batchId: null, revisionCount: 0 };
  }
  try {
    const result = await Word.run(async (context) => {
      const doc = context.document;
      const changes = doc.body.getTrackedChanges();
      doc.changeTrackingMode = state.previousMode;
      loadChanges(changes);
      await context.sync();

      const created = subtractExistingChanges(state.before, changes.items);
      const selected = selectBatchChanges(created, kind);
      if (selected.length === 0) {
        if (!previewDisplayState && state.display.desktopViewSupported) {
          const view = doc.activeWindow.view;
          restoreNativeRevisionView(view, view.revisionsFilter, state.display);
          await context.sync();
        }
        return { batchId: null, revisionCount: 0 };
      }

      acquirePreviewDisplay(state);
      const batchId = `word-revision-${Date.now()}-${nextBatchId++}`;
      revisionBatches.set(batchId, {
        kind,
        // 保存普通数据；不把旧 RequestContext 的代理对象带到下一次确认。
        changes: snapshotChanges(selected)
      });
      return { batchId, revisionCount: selected.length };
    });
    state.finished = true;
    return result;
  } catch (error) {
    // finish 阶段失败时也必须关闭本轮临时 Track Changes，不能污染用户文档状态。
    try {
      await Word.run(async (context) => {
        context.document.changeTrackingMode = state.previousMode;
        if (!previewDisplayState && state.display.desktopViewSupported) {
          const view = context.document.activeWindow.view;
          restoreNativeRevisionView(view, view.revisionsFilter, state.display);
        }
        await context.sync();
      });
    } catch (restoreError) {
      console.warn('[revisionPreview] 读取修订失败后恢复设置失败:', restoreError);
    }
    state.finished = true;
    throw error;
  }
}

function matchingChanges(current, snapshots) {
  // 原有修订先从候选集合排除，即使其位置变化也不会被本轮接管。
  const candidates = subtractExistingChanges(previewDisplayState?.before || [], current);
  const counts = new Map();
  for (const item of snapshots) {
    const signature = changeSignature(item);
    counts.set(signature, (counts.get(signature) || 0) + 1);
  }
  return candidates.filter((item) => {
    const signature = changeSignature(item);
    const count = counts.get(signature) || 0;
    if (count === 0) return false;
    counts.set(signature, count - 1);
    return true;
  });
}

export async function settleRevisionBatches(batchIds, action) {
  if (action !== 'accept' && action !== 'reject') {
    return { success: false, handled: 0, settledBatchIds: [], error: 'action 必须是 accept 或 reject' };
  }
  const ids = [...new Set(Array.isArray(batchIds) ? batchIds.filter(Boolean) : [])];
  if (ids.length === 0) {
    return { success: false, handled: 0, settledBatchIds: [], error: '修订批次不存在或已处理' };
  }
  const batches = ids.map((id) => revisionBatches.get(id));
  if (batches.some((batch) => !batch)) {
    return { success: false, handled: 0, settledBatchIds: [], error: '修订批次不存在或已处理' };
  }
  const startedAt = performance.now();
  const timings = { readMs: 0, nativeMs: 0, totalMs: 0, syncCount: 0 };
  try {
    return await Word.run(async (context) => {
      const doc = context.document;
      const collection = doc.body.getTrackedChanges();
      loadChanges(collection);
      await context.sync();
      timings.syncCount += 1;
      timings.readMs = performance.now() - startedAt;
      const selected = matchingChanges(collection.items, batches.flatMap((batch) => batch.changes));
      const method = action === 'accept' ? 'acceptAll' : 'rejectAll';
      const bulk = selected.length > 0 && selected.length === collection.items.length && typeof collection[method] === 'function';
      const nativeStartedAt = performance.now();
      if (bulk) {
        // 当前正文的修订全部属于这些批次时，调用 Word 原生集合接口。
        collection[method]();
      } else {
        // 存在用户原有修订/其它批次时只处理本轮，所有批次共用一次 sync。
        // 格式优先，文字倒序，防止拒绝新增后格式范围失效。
        const ordered = [...selected].reverse().sort((left, right) => (
          Number(normalizeType(right.type) === FORMATTED_TYPE) - Number(normalizeType(left.type) === FORMATTED_TYPE)
        ));
        for (const change of ordered) {
          if (action === 'accept') change.accept();
          else change.reject();
        }
      }
      const remaining = doc.body.getTrackedChanges();
      loadChanges(remaining);
      const display = previewDisplayState;
      const restoreDisplay = ids.length === revisionBatches.size && display?.desktopViewSupported;
      if (restoreDisplay) {
        const view = doc.activeWindow.view;
        restoreNativeRevisionView(view, view.revisionsFilter, display);
      }
      await context.sync();
      timings.syncCount += 1;
      timings.nativeMs = performance.now() - nativeStartedAt;

      if (bulk && remaining.items.length > 0) {
        // 集合接口部分成功后，重建的格式修订仍属于本轮，保留以便重试。
        for (const batch of batches) batch.changes = snapshotChanges(remaining.items);
      }
      const settledBatchIds = ids.filter((id, index) => matchingChanges(remaining.items, batches[index].changes).length === 0);
      const handled = Math.max(0, selected.length - matchingChanges(remaining.items, batches.flatMap((batch) => batch.changes)).length);
      for (const id of settledBatchIds) revisionBatches.delete(id);
      if (previewDisplayState) {
        previewDisplayState.batchCount = Math.max(0, previewDisplayState.batchCount - settledBatchIds.length);
        if (previewDisplayState.batchCount === 0) previewDisplayState = null;
      }
      const success = settledBatchIds.length === ids.length;
      if (!success && restoreDisplay) {
        const view = doc.activeWindow.view;
        configureNativeRevisionView(view, view.revisionsFilter);
        await context.sync();
        timings.syncCount += 1;
      }
      return {
        success,
        handled,
        settledBatchIds,
        bulk,
        timings,
        ...(!success ? { error: 'Word 未完整处理本轮修订，请重试' } : {})
      };
    });
  } catch (error) {
    console.warn(`[revisionPreview] ${action === 'accept' ? '接受' : '拒绝'}修订失败:`, error);
    return { success: false, handled: 0, settledBatchIds: [], error: error?.message || String(error), timings };
  } finally {
    timings.totalMs = performance.now() - startedAt;
  }
}

export async function settleRevisionBatch(batchId, action) {
  return settleRevisionBatches([batchId], action);
}

export async function undoLastDocumentAction(times = 1) {
  if (!supportsDesktopRevisionView()) {
    return false;
  }
  return Word.run(async (context) => {
    const result = context.document.undo(Math.max(1, Number(times) || 1));
    await context.sync();
    return Boolean(result.value);
  });
}

export function hasRevisionBatch(batchId) {
  return Boolean(batchId && revisionBatches.has(batchId));
}

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

async function restorePreviewDisplayIfIdle() {
  if (!previewDisplayState || previewDisplayState.batchCount > 0) {
    return;
  }
  const display = previewDisplayState;
  previewDisplayState = null;
  if (!display.desktopViewSupported) {
    return;
  }
  try {
    await Word.run(async (context) => {
      const view = context.document.activeWindow.view;
      const filter = view.revisionsFilter;
      restoreNativeRevisionView(view, filter, display);
      await context.sync();
    });
  } catch (error) {
    console.warn('[revisionPreview] 恢复修订显示设置失败:', error);
  }
}

function acquirePreviewDisplay(state) {
  if (!previewDisplayState) {
    previewDisplayState = {
      ...state.display,
      batchCount: 0
    };
  }
  previewDisplayState.batchCount += 1;
}

async function releasePreviewDisplay() {
  if (!previewDisplayState) {
    return;
  }
  previewDisplayState.batchCount = Math.max(0, previewDisplayState.batchCount - 1);
  await restorePreviewDisplayIfIdle();
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

      changes.track();
      for (const change of selected) {
        change.track();
      }
      await context.sync();

      acquirePreviewDisplay(state);
      const batchId = `word-revision-${Date.now()}-${nextBatchId++}`;
      revisionBatches.set(batchId, {
        kind,
        collection: changes,
        changes: selected.map((change) => ({
          change,
          type: normalizeType(change.type)
        }))
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

async function settleTrackedRevisionBatch(batchId, action) {
  if (action !== 'accept' && action !== 'reject') {
    return { success: false, handled: 0, settledBatchIds: [], error: 'action 必须是 accept 或 reject' };
  }
  const batch = revisionBatches.get(batchId);
  if (!batch) {
    return { success: false, handled: 0, settledBatchIds: [], error: '修订批次不存在或已处理' };
  }

  // 先处理格式修订，再处理文字增删。取消插入时，文字被拒绝后其格式
  // Range 可能立即失效，因此不能把格式修订留到最后。
  const ordered = [...batch.changes].sort((a, b) => {
    const aFormat = a.type === FORMATTED_TYPE ? 0 : 1;
    const bFormat = b.type === FORMATTED_TYPE ? 0 : 1;
    return aFormat - bFormat;
  });
  const proxies = [
    ...new Set([
      batch.collection,
      ...ordered.map((item) => item.change),
    ].filter(Boolean)),
  ];
  let handled = 0;

  try {
    await Word.run(proxies, async (context) => {
      for (const item of ordered) {
        if (action === 'accept') {
          item.change.accept();
        } else {
          item.change.reject();
        }
        item.change.untrack();
        handled += 1;
      }
      batch.collection?.untrack();
      await context.sync();
    });
    revisionBatches.delete(batchId);
    await releasePreviewDisplay();
    return {
      success: true,
      handled,
      settledBatchIds: [batchId],
    };
  } catch (error) {
    console.warn(`[revisionPreview] ${action === 'accept' ? '接受' : '拒绝'}修订失败:`, error);
    return {
      success: false,
      handled: 0,
      settledBatchIds: [],
      error: error?.message || String(error),
    };
  }
}

export async function settleRevisionBatches(batchIds, action) {
  if (action !== 'accept' && action !== 'reject') {
    return { success: false, handled: 0, settledBatchIds: [], error: 'action 必须是 accept 或 reject' };
  }
  const ids = [...new Set(Array.isArray(batchIds) ? batchIds.filter(Boolean) : [])];
  if (ids.length === 0) {
    return { success: false, handled: 0, settledBatchIds: [], error: '修订批次不存在或已处理' };
  }

  let handled = 0;
  const settledBatchIds = [];
  for (const batchId of ids) {
    const result = await settleTrackedRevisionBatch(batchId, action);
    if (!result.success) {
      return {
        success: false,
        handled,
        settledBatchIds,
        error: result.error,
      };
    }
    handled += result.handled;
    settledBatchIds.push(batchId);
  }
  return { success: true, handled, settledBatchIds };
}

export async function settleRevisionBatch(batchId, action) {
  return settleTrackedRevisionBatch(batchId, action);
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

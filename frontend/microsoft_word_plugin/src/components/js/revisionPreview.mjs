/* global Office, Word */

const revisionBatches = new Map();
const previewDisplayStates = new Map();
const loadedDocumentScopes = new Set();
const REVISION_STATE_KEY = 'wence.aiRevisionBatches';
let nextBatchId = 1;

export const AI_REVISION_AUTHOR = '文策AI';

// Office.js 的 RequestContext 绑定加载项所属文档，不使用 WPS 的全局活动文档。
// 保留该对象身份，禁止把一个文档的修订批次交给另一个加载项文档处理。
function documentScope() {
  const scope = Office?.context?.document;
  if (!scope) throw new Error('无法确定 Microsoft Word 加载项所属文档');
  return scope;
}

function assertDocumentScope(expected) {
  if (documentScope() !== expected) throw new Error('修订所属文档已变化，请返回原文档处理');
}

export function assertRevisionDocumentTarget(docId = 0) {
  if (docId != null && Number(docId) !== 0) {
    throw new Error('Microsoft Word 仅支持 docId=0（当前加载项所属文档）');
  }
}

function loadStoredBatches(doc, scope) {
  if (loadedDocumentScopes.has(scope) || !doc.settings) return null;
  const setting = doc.settings.getItemOrNullObject(REVISION_STATE_KEY);
  setting.load('value');
  return setting;
}

function restoreStoredBatches(setting, scope) {
  if (loadedDocumentScopes.has(scope)) return;
  if (setting && !setting.isNullObject) {
    const saved = JSON.parse(setting.value);
    for (const batch of saved.batches) {
      revisionBatches.set(batch.id, { scope, kind: batch.kind, changes: batch.changes });
    }
    if (saved.display) previewDisplayStates.set(scope, {
      ...saved.display,
      desktopViewSupported: saved.display.desktopViewSupported && supportsDesktopRevisionView(),
      batchCount: saved.batches.length
    });
  }
  loadedDocumentScopes.add(scope);
}

async function saveStoredBatches(context, scope) {
  if (!context.document.settings) return false;
  const batches = [...revisionBatches].filter(([, batch]) => batch.scope === scope)
    .map(([id, batch]) => ({ id, kind: batch.kind, changes: batch.changes }));
  try {
    // Word 文档内的加载项元数据，随文档保存；刷新聊天面板仍可找回本插件的批次。
    context.document.settings.add(REVISION_STATE_KEY, JSON.stringify({
      batches, display: previewDisplayStates.get(scope) || null
    }));
    await context.sync();
  } catch (error) {
    console.warn('[revisionPreview] 保存修订批次信息失败:', error);
  }
  return true;
}

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
  if (!previewDisplayStates.has(state.scope)) {
    previewDisplayStates.set(state.scope, {
      ...state.display,
      before: state.before,
      batchCount: 0
    });
  }
  previewDisplayStates.get(state.scope).batchCount += 1;
}

export async function beginTrackedEdit(docId = 0) {
  assertRevisionDocumentTarget(docId);
  assertNativeRevisionSupport();
  const scope = documentScope();
  const desktopViewSupported = supportsDesktopRevisionView();

  return Word.run(async (context) => {
    const doc = context.document;
    const stored = loadStoredBatches(doc, scope);
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
    restoreStoredBatches(stored, scope);

    const state = {
      scope,
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
  assertDocumentScope(state.scope);
  state.finished = true;
  await Word.run(async (context) => {
    context.document.changeTrackingMode = state.previousMode;
    if (!previewDisplayStates.has(state.scope) && state.display.desktopViewSupported) {
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
  assertDocumentScope(state.scope);
  try {
    const result = await Word.run(async (context) => {
      const doc = context.document;
      const changes = doc.body.getTrackedChanges();
      doc.changeTrackingMode = state.previousMode;
      loadChanges(changes);
      await context.sync();

      const created = subtractExistingChanges(state.before, changes.items);
      const selected = selectBatchChanges(created, kind);
      // Office.js 无法设置修订用户名。如果写入期间出现多个作者，不能猜测归属。
      if (new Set(selected.map(change => change.author)).size > 1) {
        throw new Error('写入期间出现多个修订作者，无法确定本轮归属，请在 Word 审阅栏核实');
      }
      if (selected.length === 0) {
        if (!previewDisplayStates.has(state.scope) && state.display.desktopViewSupported) {
          const view = doc.activeWindow.view;
          restoreNativeRevisionView(view, view.revisionsFilter, state.display);
          await context.sync();
        }
        return { batchId: null, revisionCount: 0 };
      }

      acquirePreviewDisplay(state);
      const batchId = `word-revision-${Date.now()}-${nextBatchId++}`;
      revisionBatches.set(batchId, {
        scope: state.scope,
        kind,
        // 保存普通数据；不把旧 RequestContext 的代理对象带到下一次确认。
        changes: snapshotChanges(selected)
      });
      await saveStoredBatches(context, state.scope);
      return { batchId, revisionCount: selected.length };
    });
    state.finished = true;
    return result;
  } catch (error) {
    // finish 阶段失败时也必须关闭本轮临时 Track Changes，不能污染用户文档状态。
    try {
      await Word.run(async (context) => {
        context.document.changeTrackingMode = state.previousMode;
        if (!previewDisplayStates.has(state.scope) && state.display.desktopViewSupported) {
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

function matchingChanges(current, snapshots, scope) {
  // 原有修订先从候选集合排除，即使其位置变化也不会被本轮接管。
  const candidates = subtractExistingChanges(previewDisplayStates.get(scope)?.before || [], current);
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

export async function settleRevisionBatches(batchIds, action, includeAIAuthors = false) {
  if (action !== 'accept' && action !== 'reject') {
    return { success: false, handled: 0, settledBatchIds: [], error: 'action 必须是 accept 或 reject' };
  }
  const ids = [...new Set(Array.isArray(batchIds) ? batchIds.filter(Boolean) : [])];
  if (ids.length === 0 && !includeAIAuthors) {
    return { success: false, handled: 0, settledBatchIds: [], error: '修订批次不存在或已处理' };
  }
  const batches = ids.map((id) => revisionBatches.get(id));
  if (batches.some((batch) => !batch)) {
    return { success: false, handled: 0, settledBatchIds: [], error: '修订批次不存在或已处理' };
  }
  const startedAt = performance.now();
  const timings = { readMs: 0, nativeMs: 0, totalMs: 0, syncCount: 0 };
  try {
    const scope = documentScope();
    for (const batch of batches) assertDocumentScope(batch.scope);
    return await Word.run(async (context) => {
      const doc = context.document;
      const collection = doc.body.getTrackedChanges();
      loadChanges(collection);
      await context.sync();
      timings.syncCount += 1;
      timings.readMs = performance.now() - startedAt;
      const select = (items, snapshots) => [...new Set([
        ...matchingChanges(items, snapshots, scope),
        ...(includeAIAuthors ? items.filter(item => item.author?.trim() === AI_REVISION_AUTHOR) : [])
      ])];
      const selected = select(collection.items, batches.flatMap((batch) => batch.changes));
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
      const display = previewDisplayStates.get(scope);
      const scopeBatchCount = [...revisionBatches.values()].filter(batch => batch.scope === scope).length;
      const restoreDisplay = ids.length === scopeBatchCount && display?.desktopViewSupported;
      if (restoreDisplay) {
        const view = doc.activeWindow.view;
        restoreNativeRevisionView(view, view.revisionsFilter, display);
      }
      await context.sync();
      timings.syncCount += 1;
      timings.nativeMs = performance.now() - nativeStartedAt;

      if (bulk && remaining.items.length > 0) {
        // 集合接口部分成功后，重建的格式修订仍属于本轮，保留以便重试。
        const authors = new Set(selected.map(change => change.author));
        const owned = remaining.items.filter(change => authors.has(change.author));
        for (const batch of batches) batch.changes = snapshotChanges(owned);
      }
      const settledBatchIds = ids.filter((id, index) => matchingChanges(remaining.items, batches[index].changes, scope).length === 0);
      const remainingCount = select(remaining.items, batches.flatMap((batch) => batch.changes)).length;
      const handled = Math.max(0, selected.length - remainingCount);
      for (const id of settledBatchIds) revisionBatches.delete(id);
      if (display) {
        display.batchCount = Math.max(0, display.batchCount - settledBatchIds.length);
        if (display.batchCount === 0) previewDisplayStates.delete(scope);
      }
      const success = settledBatchIds.length === ids.length && remainingCount === 0;
      if (!success && restoreDisplay) {
        const view = doc.activeWindow.view;
        configureNativeRevisionView(view, view.revisionsFilter);
        await context.sync();
        timings.syncCount += 1;
      }
      if (await saveStoredBatches(context, scope)) timings.syncCount += 1;
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

export async function getPendingRevisionCount() {
  if (!isRequirementSupported('WordApi', '1.6')) return 0;
  const scope = documentScope();
  return Word.run(async (context) => {
    const stored = loadStoredBatches(context.document, scope);
    const collection = context.document.body.getTrackedChanges();
    loadChanges(collection);
    await context.sync();
    restoreStoredBatches(stored, scope);
    let pruned = false;
    for (const [id, batch] of revisionBatches) {
      if (batch.scope === scope && matchingChanges(collection.items, batch.changes, scope).length === 0) {
        revisionBatches.delete(id);
        pruned = true;
      }
    }
    const display = previewDisplayStates.get(scope);
    if (display) {
      display.batchCount = [...revisionBatches.values()].filter(batch => batch.scope === scope).length;
      if (display.batchCount === 0) {
        if (display.desktopViewSupported) {
          const view = context.document.activeWindow.view;
          restoreNativeRevisionView(view, view.revisionsFilter, display);
          await context.sync();
        }
        previewDisplayStates.delete(scope);
      }
    }
    if (pruned) await saveStoredBatches(context, scope);
    const snapshots = [...revisionBatches.values()].filter(batch => batch.scope === scope).flatMap(batch => batch.changes);
    return new Set([
      ...matchingChanges(collection.items, snapshots, scope),
      ...collection.items.filter(item => item.author?.trim() === AI_REVISION_AUTHOR)
    ]).size;
  });
}

export async function settleDocumentRevisions(action) {
  const scope = documentScope();
  if (!loadedDocumentScopes.has(scope)) await getPendingRevisionCount();
  const ids = [...revisionBatches].filter(([, batch]) => batch.scope === scope).map(([id]) => id);
  return settleRevisionBatches(ids, action, true);
}

export function hasRevisionBatch(batchId) {
  return Boolean(batchId && revisionBatches.get(batchId)?.scope === documentScope());
}

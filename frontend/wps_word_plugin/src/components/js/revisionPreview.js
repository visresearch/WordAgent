const revisionBatches = new Map();
const documentPreviewStates = new Map();
let nextBatchId = 1;

const INSERT_REVISION_TYPES = new Set([1, 9, 15, 16, 18, 19, 20]);
const DELETE_REVISION_TYPES = new Set([2, 9, 14, 17, 21]);
const FORMAT_REVISION_TYPES = new Set([3, 4, 5, 8, 10, 11, 12, 13]);

function safeRead(read, fallback = null) {
  try {
    const value = read();
    return value === undefined ? fallback : value;
  } catch (error) {
    return fallback;
  }
}

function now() {
  return typeof performance !== 'undefined' ? performance.now() : Date.now();
}

function suspendScreenUpdating(doc) {
  const application = safeRead(() => doc.Application) || safeRead(() => window.Application);
  // 尊重外层操作已经关闭屏幕更新的状态；不支持此属性的版本照常处理。
  if (safeRead(() => application.ScreenUpdating) !== true) {
    return () => {};
  }
  try {
    application.ScreenUpdating = false;
  } catch (error) {
    return () => {};
  }
  return () => {
    application.ScreenUpdating = true;
  };
}

function listRevisions(revisions) {
  const items = [];
  const count = Number(safeRead(() => revisions.Count, 0)) || 0;
  for (let index = 1; index <= count; index++) {
    const revision = safeRead(() => revisions.Item(index));
    if (!revision) {
      continue;
    }
    const range = safeRead(() => revision.Range);
    const text = String(safeRead(() => range.Text, '') || '');
    items.push({
      revision,
      type: Number(safeRead(() => revision.Type, 0)) || 0,
      author: String(safeRead(() => revision.Author, '') || ''),
      date: String(safeRead(() => revision.Date, '') || ''),
      start: Number(safeRead(() => range.Start, -1)),
      end: Number(safeRead(() => range.End, -1)),
      text,
      formatDescription: String(safeRead(() => revision.FormatDescription, '') || ''),
      index: Number(safeRead(() => revision.Index, index)) || index
    });
  }
  return items;
}

function revisionSignature(item) {
  return [
    item.type,
    item.author,
    item.date,
    item.text,
    item.formatDescription
  ].join('\u0001');
}

function subtractExistingRevisions(before, after) {
  const existingObjects = new Set(before.map((item) => item.revision));
  const counts = new Map();
  for (const item of before) {
    const signature = revisionSignature(item);
    counts.set(signature, (counts.get(signature) || 0) + 1);
  }

  return after.filter((item) => {
    if (existingObjects.has(item.revision)) {
      return false;
    }
    const signature = revisionSignature(item);
    const count = counts.get(signature) || 0;
    if (count <= 0) {
      return true;
    }
    counts.set(signature, count - 1);
    return false;
  });
}

function overlapsTarget(item, target) {
  if (!target || !Number.isFinite(target.start) || !Number.isFinite(target.end)) {
    return true;
  }
  if (!Number.isFinite(item.start) || !Number.isFinite(item.end)) {
    return false;
  }
  return item.end >= target.start && item.start <= target.end;
}

function expectedType(item, kind) {
  if (kind === 'insert') {
    return INSERT_REVISION_TYPES.has(item.type);
  }
  if (kind === 'delete') {
    return DELETE_REVISION_TYPES.has(item.type);
  }
  return true;
}

// WdRevisionsView.wdRevisionsViewFinal. WPS may keep a document in the
// original-revisions view, where newly inserted text is hidden until Accept().
const WPS_REVISIONS_VIEW_FINAL = 0;

function showFinalRevisionPreview(view) {
  if (!view) {
    return;
  }
  try {
    view.RevisionsView = WPS_REVISIONS_VIEW_FINAL;
  } catch (error) {
    void error;
  }
  try {
    view.ShowInsertionsAndDeletions = true;
  } catch (error) {
    void error;
  }
  try {
    view.ShowFormatChanges = false;
  } catch (error) {
    void error;
  }
}

function restoreRevisionView(state) {
  if (!state?.view) {
    return;
  }
  if (state.previousRevisionsView !== null) {
    try {
      state.view.RevisionsView = state.previousRevisionsView;
    } catch (error) {
      void error;
    }
  }
  if (state.previousShowInsertionsAndDeletions !== null) {
    try {
      state.view.ShowInsertionsAndDeletions = state.previousShowInsertionsAndDeletions;
    } catch (error) {
      void error;
    }
  }
  if (state.previousShowFormatChanges !== null) {
    try {
      state.view.ShowFormatChanges = state.previousShowFormatChanges;
    } catch (error) {
      void error;
    }
  }
}

function acquireDocumentPreviewState(doc, editState) {
  let state = documentPreviewStates.get(doc);
  if (!state) {
    state = {
      previousShowRevisions: Boolean(editState.previousShowRevisions),
      view: editState.view,
      previousRevisionsView: editState.previousRevisionsView,
      previousShowInsertionsAndDeletions: editState.previousShowInsertionsAndDeletions,
      previousShowFormatChanges: editState.previousShowFormatChanges,
      before: editState.before,
      batches: 0
    };
    documentPreviewStates.set(doc, state);
  }
  state.batches += 1;
  doc.ShowRevisions = true;
  showFinalRevisionPreview(state.view);
}

function releaseDocumentPreviewState(doc) {
  const state = documentPreviewStates.get(doc);
  if (!state) {
    return;
  }
  state.batches = Math.max(0, state.batches - 1);
  if (state.batches > 0) {
    return;
  }
  try {
    doc.ShowRevisions = state.previousShowRevisions;
    restoreRevisionView(state);
  } catch (error) {
    console.warn('[revisionPreview] 恢复 ShowRevisions 失败:', error);
  }
  documentPreviewStates.delete(doc);
}

export function beginTrackedEdit(doc) {
  if (!doc) {
    throw new Error('缺少 WPS Document 对象');
  }
  const view = safeRead(() => doc.ActiveWindow.View) || safeRead(() => window.Application.ActiveWindow.View);
  const state = {
    doc,
    previousTrackRevisions: Boolean(safeRead(() => doc.TrackRevisions, false)),
    previousTrackFormatting: safeRead(() => doc.TrackFormatting, null),
    previousShowRevisions: Boolean(safeRead(() => doc.ShowRevisions, false)),
    view,
    previousRevisionsView: view ? safeRead(() => view.RevisionsView, null) : null,
    previousShowInsertionsAndDeletions: view
      ? safeRead(() => view.ShowInsertionsAndDeletions, null)
      : null,
    previousShowFormatChanges: view ? Boolean(safeRead(() => view.ShowFormatChanges, true)) : null,
    before: listRevisions(doc.Revisions),
    finished: false
  };
  try {
    if (state.previousTrackFormatting !== null) {
      doc.TrackFormatting = false;
    }
    doc.TrackRevisions = true;
    doc.ShowRevisions = true;
    showFinalRevisionPreview(view);
  } catch (error) {
    try {
      doc.TrackRevisions = state.previousTrackRevisions;
      if (state.previousTrackFormatting !== null) {
        doc.TrackFormatting = state.previousTrackFormatting;
      }
      doc.ShowRevisions = state.previousShowRevisions;
      restoreRevisionView(state);
    } catch (restoreError) {
      console.warn('[revisionPreview] 开启原生修订失败后恢复文档状态失败:', restoreError);
    }
    throw error;
  }
  return state;
}

export function abortTrackedEdit(state) {
  if (!state || state.finished) {
    return;
  }
  state.finished = true;
  try {
    state.doc.TrackRevisions = state.previousTrackRevisions;
    if (state.previousTrackFormatting !== null) {
      state.doc.TrackFormatting = state.previousTrackFormatting;
    }
  } finally {
    state.doc.ShowRevisions = state.previousShowRevisions;
    restoreRevisionView(state);
  }
}

export function finishTrackedEdit(state, target, kind) {
  if (!state || state.finished) {
    return { batchId: null, revisionCount: 0 };
  }
  state.finished = true;
  const { doc } = state;
  let after;
  try {
    doc.TrackRevisions = state.previousTrackRevisions;
    if (state.previousTrackFormatting !== null) {
      doc.TrackFormatting = state.previousTrackFormatting;
    }
    after = listRevisions(doc.Revisions);
  } catch (error) {
    try {
      doc.ShowRevisions = state.previousShowRevisions;
      restoreRevisionView(state);
    } catch (restoreError) {
      console.warn('[revisionPreview] 读取修订失败后恢复 ShowRevisions 失败:', restoreError);
    }
    throw error;
  }
  // Capture every revision produced by this edit, including table/property
  // and formatting revisions. Confirming a batch must not leave those behind.
  let created = subtractExistingRevisions(state.before, after);

  // Some WPS builds update the positions of existing revisions after an edit.
  // If the signature diff is inconclusive, restrict the fallback to the target
  // range and the revision types produced by this operation.
  if (created.length === 0 && after.length > state.before.length) {
    const addedCount = after.length - state.before.length;
    const targetCandidates = after.filter((item) => overlapsTarget(item, target));
    created = targetCandidates.slice(Math.max(0, targetCandidates.length - addedCount));
  }

  if (kind === 'delete') {
    // WPS may recreate or merge an already-pending insertion Revision when a
    // nearby paragraph is deleted. Such an insertion can look "new" to the
    // before/after snapshot, but it does not belong to the delete batch.
    // Accepting it again after the insertion batch has been settled can make
    // the newly generated paragraph disappear. Keep delete/replace revisions
    // and structural/format revisions, but never adopt a pure insertion here.
    created = created.filter(
      (item) => !INSERT_REVISION_TYPES.has(item.type) || DELETE_REVISION_TYPES.has(item.type)
    );
  }

  if ((kind === 'insert' || kind === 'delete') && !created.some((item) => expectedType(item, kind))) {
    created = [];
  }

  if (created.length === 0) {
    doc.ShowRevisions = state.previousShowRevisions;
    restoreRevisionView(state);
    return { batchId: null, revisionCount: 0 };
  }

  acquireDocumentPreviewState(doc, state);
  const batchId = `wps-revision-${Date.now()}-${nextBatchId++}`;
  revisionBatches.set(batchId, {
    doc,
    kind,
    revisions: created,
    target: target || null
  });
  return { batchId, revisionCount: created.length };
}

export function settleRevisionBatch(batchId, action) {
  const batch = revisionBatches.get(batchId);
  if (!batch) {
    return { success: false, handled: 0, failed: 0, error: '修订批次不存在或已处理' };
  }
  if (action !== 'accept' && action !== 'reject') {
    return { success: false, handled: 0, failed: 0, error: 'action 必须是 accept 或 reject' };
  }
  if (action === 'reject') {
    return rejectRevisionBatches(batch.doc, [batchId]);
  }

  const revisions = [...batch.revisions].sort((a, b) => {
    const aIndex = Number(safeRead(() => a.revision.Index, a.index)) || a.index;
    const bIndex = Number(safeRead(() => b.revision.Index, b.index)) || b.index;
    if (bIndex !== aIndex) {
      return bIndex - aIndex;
    }
    return b.start - a.start;
  });
  let handled = 0;
  let failed = 0;
  const failedRevisions = [];

  for (const item of revisions) {
    try {
      item.revision.Accept();
      handled += 1;
    } catch (error) {
      failed += 1;
      failedRevisions.push(item);
      console.warn('[revisionPreview] Revision.Accept() 失败:', error);
    }
  }

  if (failedRevisions.length > 0) {
    batch.revisions = failedRevisions;
    return { success: false, handled, failed };
  }

  revisionBatches.delete(batchId);
  releaseDocumentPreviewState(batch.doc);
  return { success: true, handled, failed };
}

// 每次处理后重新读取集合，不复用可能已经重排/失效的 COM Revision。
// 签名不包含位置，因为拒绝插入后，已有修订的范围会向前移动。
function matchRevisions(expected, current, exactRange = false) {
  const remaining = [...current];
  const matched = [];
  for (const item of expected) {
    const signature = revisionSignature(item);
    let bestIndex = -1;
    for (let index = 0; index < remaining.length; index++) {
      const candidate = remaining[index];
      if (revisionSignature(candidate) !== signature) {
        continue;
      }
      if (exactRange && (candidate.start !== item.start || candidate.end !== item.end)) {
        continue;
      }
      if (bestIndex < 0 || Math.abs(candidate.start - item.start) < Math.abs(remaining[bestIndex].start - item.start)) {
        bestIndex = index;
      }
    }
    if (bestIndex >= 0) {
      matched.push(remaining.splice(bestIndex, 1)[0]);
    }
  }
  return matched;
}

function readDocumentRevisions(doc) {
  const revisions = doc.Revisions;
  const count = Number(revisions?.Count);
  if (!Number.isInteger(count) || count < 0) {
    throw new Error('无法读取 WPS 修订集合');
  }
  const items = listRevisions(revisions);
  if (items.length !== count) {
    throw new Error('无法完整读取 WPS 修订集合');
  }
  return items;
}

/**
 * 取消一组待确认操作。没有其它修订时使用文档级 RejectAll，与 WPS
 * “拒绝对文档所做的所有修订”一致；否则只拒绝属于这些批次的范围。
 */
export function rejectRevisionBatches(doc, batchIds) {
  const ids = [...new Set(batchIds)];
  const batches = ids.map((id) => revisionBatches.get(id));
  const sameDocument = (other) => other === doc || (
    doc?.DocID !== undefined && doc?.DocID !== null &&
    other?.DocID !== undefined && other?.DocID !== null && Number(other.DocID) === Number(doc.DocID)
  );
  if (!doc || batches.some((batch) => !batch || !sameDocument(batch.doc))) {
    return { success: false, handled: 0, failed: 1, settledBatchIds: [], error: '修订批次不存在或文档不匹配' };
  }
  doc = batches[0]?.doc || doc;
  const expected = batches.flatMap((batch) => batch.revisions);
  const baseline = documentPreviewStates.get(doc)?.before || [];
  const ownedRevisions = (current, snapshots = expected) => {
    const protectedItems = new Set(matchRevisions(baseline, current));
    return matchRevisions(snapshots, current.filter((item) => !protectedItems.has(item)));
  };
  let handled = 0;
  let error = null;
  let current;
  let rejectingWholeDocument = false;
  const retainRemainingRevisions = () => {
    if (rejectingWholeDocument && current?.length > 0) {
      // 原集合全部属于选中的批次，RejectAll 部分成功后新建/重排的标记
      // 仍属于本轮操作。保留新快照，防止签名变化后误报撤销成功。
      expected.splice(0, expected.length, ...current);
      for (const batch of batches) {
        batch.revisions = [...current];
      }
    }
  };
  try {
    current = readDocumentRevisions(doc);
    let owned = ownedRevisions(current);
    while (owned.length > 0) {
      const beforeCount = current.length;
      if (owned.length === current.length) {
        rejectingWholeDocument = true;
        // 包括插入、删除、样式和段落格式，一次交给 WPS 内核处理。
        if (typeof doc.Revisions.RejectAll === 'function') {
          doc.Revisions.RejectAll();
        } else if (typeof doc.RejectAllRevisions === 'function') {
          doc.RejectAllRevisions();
        } else {
          throw new Error('当前 WPS 版本不支持拒绝全部修订');
        }
      } else {
        // 格式必须先处理，避免拒绝文字后其 Range/签名失效。
        owned.sort((left, right) => (
          Number(FORMAT_REVISION_TYPES.has(right.type)) - Number(FORMAT_REVISION_TYPES.has(left.type)) ||
          right.index - left.index
        ));
        const item = owned[0];
        const rangeRevisions = doc.Range?.(item.start, item.end)?.Revisions;
        const inRange = rangeRevisions ? listRevisions(rangeRevisions) : [];
        const rangeOwned = matchRevisions(owned, inRange, true);
        if (inRange.length > 0 && rangeOwned.length === inRange.length && typeof rangeRevisions.RejectAll === 'function') {
          // WPS 的 Revision.Reject() 不支持格式修订，使用范围集合接口。
          rangeRevisions.RejectAll();
        } else if (!FORMAT_REVISION_TYPES.has(item.type)) {
          item.revision.Reject();
        } else {
          throw new Error('无法单独拒绝本轮格式修订，操作保留以便重试');
        }
      }
      current = readDocumentRevisions(doc);
      retainRemainingRevisions();
      if (current.length >= beforeCount) {
        throw new Error('WPS 拒绝修订后仍有标记残留，操作保留以便重试');
      }
      handled += beforeCount - current.length;
      owned = ownedRevisions(current);
    }
  } catch (failure) {
    error = failure?.message || String(failure);
    console.warn('[revisionPreview] 拒绝修订失败:', failure);
    // RejectAll 也可能部分成功，重新读取后只清除已处理的批次。
    try {
      current = readDocumentRevisions(doc);
      retainRemainingRevisions();
    } catch (readError) {
      current = null;
    }
  }
  const settledBatchIds = [];
  if (current) {
    for (let index = 0; index < ids.length; index++) {
      if (ownedRevisions(current, batches[index].revisions).length === 0) {
        revisionBatches.delete(ids[index]);
        releaseDocumentPreviewState(doc);
        settledBatchIds.push(ids[index]);
      }
    }
  }
  const failed = ids.length - settledBatchIds.length;
  return { success: failed === 0, handled, failed, settledBatchIds, ...(error ? { error } : {}) };
}

/**
 * 使用 WPS 集合级原生接口处理全部修订，与“审阅 → 接受/拒绝所有修订”一致。
 * 不能循环处理缓存的 Revision 对象：每次 Accept()/Reject() 后 WPS 都可能
 * 重排或合并集合，使后续批次保存的 COM 对象引用指向错误范围。
 */
export function settleAllDocumentRevisions(doc, action) {
  if (!doc) {
    return { success: false, handled: 0, error: '缺少 WPS Document 对象' };
  }
  if (action !== 'accept' && action !== 'reject') {
    return { success: false, handled: 0, error: 'action 必须是 accept 或 reject' };
  }

  const startedAt = now();
  const timings = { readMs: 0, nativeMs: 0, restoreViewMs: 0, screenUpdateMs: 0, totalMs: 0 };
  let resumeScreenUpdating = () => {};
  try {
    const revisions = doc.Revisions;
    const handled = Number(revisions?.Count);
    if (!Number.isInteger(handled) || handled < 0) {
      throw new Error('无法读取 WPS 文档的 Revisions 集合');
    }
    timings.readMs = now() - startedAt;
    const previewState = documentPreviewStates.get(doc);
    if (handled > 0 || previewState) {
      // 接受修订和恢复显示设置期间暂停重绘，结束后统一刷新。
      const screenStartedAt = now();
      resumeScreenUpdating = suspendScreenUpdating(doc);
      timings.screenUpdateMs = now() - screenStartedAt;
    }
    const nativeStartedAt = now();
    try {
      // 用户已在审阅栏处理完时，无需再让 WPS 扫描整篇文档。
      if (handled > 0) {
        if (action === 'accept') {
          if (typeof revisions.AcceptAll === 'function') {
            revisions.AcceptAll();
          } else if (typeof doc.AcceptAllRevisions === 'function') {
            doc.AcceptAllRevisions();
          } else {
            throw new Error('当前 WPS 版本不支持 Revisions.AcceptAll()');
          }
        } else if (typeof revisions.RejectAll === 'function') {
          revisions.RejectAll();
        } else if (typeof doc.RejectAllRevisions === 'function') {
          doc.RejectAllRevisions();
        } else {
          throw new Error('当前 WPS 版本不支持 Revisions.RejectAll()');
        }
        // 保留未完成的批次，避免接口返回后仍残留标记却丢失确认入口。
        if (Number(doc.Revisions.Count) !== 0) {
          throw new Error('WPS 未完整处理文档修订，请重试');
        }
      }
    } finally {
      timings.nativeMs = now() - nativeStartedAt;
    }

    for (const [batchId, batch] of revisionBatches.entries()) {
      if (batch.doc === doc) {
        revisionBatches.delete(batchId);
      }
    }

    const viewStartedAt = now();
    if (previewState) {
      try {
        doc.ShowRevisions = previewState.previousShowRevisions;
        restoreRevisionView(previewState);
      } catch (error) {
        console.warn('[revisionPreview] 整体处理修订后恢复显示设置失败:', error);
      }
      documentPreviewStates.delete(doc);
    }
    timings.restoreViewMs = now() - viewStartedAt;
    return { success: true, handled, timings };
  } catch (error) {
    return { success: false, handled: 0, error: error?.message || String(error), timings };
  } finally {
    const screenStartedAt = now();
    try {
      resumeScreenUpdating();
    } catch (error) {
      console.warn('[revisionPreview] 恢复屏幕更新失败:', error);
    }
    timings.screenUpdateMs += now() - screenStartedAt;
    timings.totalMs = now() - startedAt;
  }
}

export function hasRevisionBatch(batchId) {
  return Boolean(batchId && revisionBatches.has(batchId));
}

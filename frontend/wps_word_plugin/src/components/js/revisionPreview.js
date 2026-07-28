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
    if (action === 'reject' && FORMAT_REVISION_TYPES.has(item.type)) {
      // WPS 明确不支持 Reject() 格式修订；拒绝对应的文本/结构修订后，
      // 插入内容上的格式修订会随内容一起消失。
      continue;
    }
    try {
      if (action === 'accept') {
        item.revision.Accept();
      } else {
        item.revision.Reject();
      }
      handled += 1;
    } catch (error) {
      failed += 1;
      failedRevisions.push(item);
      console.warn(`[revisionPreview] Revision.${action === 'accept' ? 'Accept' : 'Reject'}() 失败:`, error);
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

  const revisions = safeRead(() => doc.Revisions);
  if (!revisions) {
    return { success: false, handled: 0, error: '当前 WPS 文档不支持 Revisions 集合' };
  }
  const handled = Number(safeRead(() => revisions.Count, 0)) || 0;

  try {
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
  } catch (error) {
    return { success: false, handled: 0, error: error?.message || String(error) };
  }

  for (const [batchId, batch] of revisionBatches.entries()) {
    if (batch.doc === doc) {
      revisionBatches.delete(batchId);
    }
  }

  const previewState = documentPreviewStates.get(doc);
  if (previewState) {
    try {
      doc.ShowRevisions = previewState.previousShowRevisions;
      restoreRevisionView(previewState);
    } catch (error) {
      console.warn('[revisionPreview] 整体处理修订后恢复显示设置失败:', error);
    }
    documentPreviewStates.delete(doc);
  }

  return { success: true, handled };
}

export function hasRevisionBatch(batchId) {
  return Boolean(batchId && revisionBatches.has(batchId));
}

// AI 修订用户名固定为文策AI，与界面语言无关。
export const AI_REVISION_AUTHOR = '文策AI';
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

function isLinuxWPS() {
  return /linux/i.test(String(safeRead(() => navigator.platform || navigator.userAgent, '')));
}

function sameDocument(left, right) {
  if (left === right) {
    return true;
  }
  const leftId = safeRead(() => left.DocID);
  const rightId = safeRead(() => right.DocID);
  return leftId !== null && rightId !== null && Number.isSafeInteger(Number(leftId)) && Number(leftId) === Number(rightId);
}

function documentPreviewEntry(doc) {
  return [...documentPreviewStates.entries()].find(([other]) => sameDocument(doc, other));
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
    try {
      application.ScreenUpdating = true;
    } catch (error) {
      console.warn('[revisionPreview] 恢复屏幕更新失败:', error);
    }
  };
}

function readRevisionCount(revisions) {
  const count = Number(revisions?.Count);
  if (!Number.isInteger(count) || count < 0) {
    throw new Error('无法读取 WPS 修订集合');
  }
  return count;
}

function readRevisions(revisions) {
  const items = [];
  const count = readRevisionCount(revisions);
  for (let index = 1; index <= count; index++) {
    const revision = safeRead(() => revisions.Item(index));
    if (!revision) {
      throw new Error('无法完整读取 WPS 修订集合');
    }
    // 保留所有作者，才能判断集合/范围中的批量操作是否会影响他人。
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

function readDocumentRevisions(doc) {
  return readRevisions(doc.Revisions);
}

export function getAIRevisionCount(doc) {
  const expected = isLinuxWPS()
    ? [...revisionBatches.values()]
      .filter((batch) => sameDocument(batch.doc, doc))
      .flatMap((batch) => batch.revisions)
      .filter((item) => item.author !== AI_REVISION_AUTHOR)
    : [];
  if (expected.length === 0) {
    const revisions = doc.Revisions;
    const count = readRevisionCount(revisions);
    let aiCount = 0;
    for (let index = 1; index <= count; index++) {
      const author = revisions.Item(index)?.Author;
      if (typeof author !== 'string') {
        throw new Error('无法读取 WPS 修订作者');
      }
      if (author === AI_REVISION_AUTHOR) {
        aiCount += 1;
      }
    }
    return aiCount;
  }
  const current = readDocumentRevisions(doc);
  const aiCount = current.filter((item) => item.author === AI_REVISION_AUTHOR).length;
  const baseline = documentPreviewEntry(doc)?.[1].before || [];
  const protectedItems = new Set(matchRevisions(baseline, current));
  const fallback = matchRevisions(expected, current.filter((item) =>
    item.author !== AI_REVISION_AUTHOR && !protectedItems.has(item)
  ));
  return aiCount + fallback.length;
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

function showFinalRevisionPreview(view) {
  if (!view) {
    return;
  }
  const settings = { RevisionsView: 0, ShowInsertionsAndDeletions: true, ShowFormatChanges: false };
  for (const [property, value] of Object.entries(settings)) {
    try {
      view[property] = value;
    } catch (error) {
      void error; // 兼容不支持部分显示属性的 WPS 版本。
    }
  }
}

function restoreRevisionView(state) {
  if (!state?.view) {
    return;
  }
  const settings = {
    RevisionsView: state.previousRevisionsView,
    ShowInsertionsAndDeletions: state.previousShowInsertionsAndDeletions,
    ShowFormatChanges: state.previousShowFormatChanges
  };
  for (const [property, value] of Object.entries(settings)) {
    if (value === null) {
      continue;
    }
    try {
      state.view[property] = value;
    } catch (error) {
      void error;
    }
  }
}

function restoreDocumentPreview(doc, state) {
  try {
    doc.ShowRevisions = state.previousShowRevisions;
  } catch (error) {
    console.warn('[revisionPreview] 恢复修订显示失败:', error);
  }
  restoreRevisionView(state);
}

function restoreEditSettings(state) {
  try {
    state.doc.TrackRevisions = state.previousTrackRevisions;
    if (state.previousTrackFormatting !== null) {
      state.doc.TrackFormatting = state.previousTrackFormatting;
    }
  } finally {
    try {
      if (state.originalUserName !== null) {
        state.application.UserName = state.originalUserName;
      }
    } finally {
      if (state.useLocalUserInfoChanged) {
        state.options.UseLocalUserInfo = state.previousUseLocalUserInfo;
      }
    }
  }
}

function acquireDocumentPreviewState(doc, editState) {
  let state = documentPreviewEntry(doc)?.[1];
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
  const [previewDoc, state] = documentPreviewEntry(doc) || [];
  if (!state) {
    return;
  }
  state.batches = Math.max(0, state.batches - 1);
  if (state.batches > 0) {
    return;
  }
  restoreDocumentPreview(previewDoc, state);
  documentPreviewStates.delete(previewDoc);
}

export function beginTrackedEdit(doc) {
  if (!doc) {
    throw new Error('缺少 WPS Document 对象');
  }
  const application = safeRead(() => doc.Application) || safeRead(() => window.Application);
  const accountUserName = application?.UserName;
  if (typeof accountUserName !== 'string') {
    throw new Error('无法读取 WPS 用户名，未执行 AI 修订');
  }
  const linux = isLinuxWPS();
  const options = linux ? safeRead(() => application.Options) : null;
  const previousUseLocalUserInfo = linux ? safeRead(() => options.UseLocalUserInfo) : null;
  if (linux && typeof previousUseLocalUserInfo !== 'boolean') {
    throw new Error('Linux WPS 无法读取本地用户信息设置，未执行 AI 修订');
  }

  const view = safeRead(() => doc.ActiveWindow.View) || safeRead(() => application.ActiveWindow.View);
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
    before: readDocumentRevisions(doc),
    finished: false,
    application,
    options,
    linux,
    accountUserName,
    originalUserName: null,
    previousUseLocalUserInfo,
    useLocalUserInfoChanged: false,
    resumeScreenUpdating: suspendScreenUpdating(doc)
  };
  try {
    if (linux) {
      // 登录账户模式会忽略 Application.UserName，修订仍署登录用户的名字。
      state.useLocalUserInfoChanged = true;
      options.UseLocalUserInfo = true;
      if (options.UseLocalUserInfo !== true) {
        throw new Error('Linux WPS 无法启用本地用户信息，未执行 AI 修订');
      }
    }
    state.originalUserName = application.UserName;
    if (typeof state.originalUserName !== 'string') {
      throw new Error('无法读取 WPS 本地用户名，未执行 AI 修订');
    }
    application.UserName = AI_REVISION_AUTHOR;
    if (application.UserName !== AI_REVISION_AUTHOR) {
      throw new Error(`无法将修订作者设为${AI_REVISION_AUTHOR}，未执行 AI 修订`);
    }
    if (state.previousTrackFormatting !== null) {
      doc.TrackFormatting = false;
    }
    doc.TrackRevisions = true;
    doc.ShowRevisions = true;
    showFinalRevisionPreview(view);
  } catch (error) {
    try {
      restoreEditSettings(state);
    } catch (restoreError) {
      console.warn('[revisionPreview] 开启原生修订失败后恢复文档状态失败:', restoreError);
    }
    try {
      restoreDocumentPreview(doc, state);
    } finally {
      state.resumeScreenUpdating();
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
    restoreEditSettings(state);
  } finally {
    try {
      restoreDocumentPreview(state.doc, state);
    } finally {
      state.resumeScreenUpdating();
    }
  }
}

export function finishTrackedEdit(state, target, kind) {
  if (!state || state.finished) {
    return { batchId: null, revisionCount: 0 };
  }
  state.finished = true;
  try {
    return completeTrackedEdit(state, target, kind);
  } finally {
    state.resumeScreenUpdating();
  }
}

function completeTrackedEdit(state, target, kind) {
  const { doc } = state;
  let after;
  try {
    if (state.linux) {
      // 在恢复账户身份前读取，促使 Linux WPS 以本地用户身份生成修订。
      try {
        after = readDocumentRevisions(doc);
      } finally {
        restoreEditSettings(state);
      }
    } else {
      restoreEditSettings(state);
      after = readDocumentRevisions(doc);
    }
  } catch (error) {
    restoreDocumentPreview(doc, state);
    throw error;
  }
  // 同时记录文字、格式和结构修订，避免接受后留下附属标记。
  let created = subtractExistingRevisions(state.before, after);

  // WPS 可能重建修订对象；差异不明确时只在目标范围内补充新增标记。
  if (created.length === 0 && after.length > state.before.length) {
    const addedCount = after.length - state.before.length;
    const targetCandidates = after.filter((item) => overlapsTarget(item, target));
    created = targetCandidates.slice(Math.max(0, targetCandidates.length - addedCount));
  }

  created = created.filter((item) => item.author === AI_REVISION_AUTHOR || (
    state.linux && item.author &&
    (item.author === state.accountUserName || item.author === state.originalUserName)
  ));

  if (kind === 'delete') {
    // 邻近删除可能重建已有插入标记；删除批次不能接管纯插入修订。
    created = created.filter(
      (item) => !INSERT_REVISION_TYPES.has(item.type) || DELETE_REVISION_TYPES.has(item.type)
    );
  }

  if ((kind === 'insert' || kind === 'delete') && !created.some((item) => expectedType(item, kind))) {
    created = [];
  }

  if (created.length === 0) {
    restoreDocumentPreview(doc, state);
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
      // WPS 可能重建 COM 对象，每次处理前重新定位并核对作者。
      const current = readDocumentRevisions(batch.doc).filter((candidate) => candidate.author === item.author);
      const matched = matchRevisions([item], current)[0];
      if (!matched) {
        continue; // 已在 WPS 审阅栏手动处理，或已不属于 AI 作者。
      }
      if (safeRead(() => matched.revision.Author) !== item.author) {
        throw new Error('修订作者已变化，未接受该修订');
      }
      matched.revision.Accept();
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

// 只有集合中的每条修订都属于选中的 AI 修订时，才允许集合级操作。
function applyRevisionAction(doc, revisions, current, owned, action, allowedAuthors = new Set([AI_REVISION_AUTHOR])) {
  if (owned.some((item) => !allowedAuthors.has(item.author))) {
    throw new Error(`只能处理${AI_REVISION_AUTHOR}的修订`);
  }
  if (owned.length === current.length) {
    const method = action === 'accept' ? 'AcceptAll' : 'RejectAll';
    const documentMethod = action === 'accept' ? 'AcceptAllRevisions' : 'RejectAllRevisions';
    if (typeof revisions[method] === 'function') {
      revisions[method]();
      return;
    }
    if (doc && typeof doc[documentMethod] === 'function') {
      doc[documentMethod]();
      return;
    }
  }

  owned.sort((left, right) => (
    (action === 'reject'
      ? Number(FORMAT_REVISION_TYPES.has(right.type)) - Number(FORMAT_REVISION_TYPES.has(left.type))
      : 0) || right.index - left.index
  ));
  const item = owned[0];
  if (!allowedAuthors.has(safeRead(() => item.revision.Author))) {
    throw new Error('修订作者已变化，未处理该修订');
  }
  if (action === 'reject') {
    const rangeRevisions = doc?.Range?.(item.start, item.end)?.Revisions;
    const inRange = rangeRevisions ? readRevisions(rangeRevisions) : [];
    const rangeOwned = matchRevisions(owned, inRange, true);
    if (inRange.length > 0 && rangeOwned.length === inRange.length && typeof rangeRevisions.RejectAll === 'function') {
      rangeRevisions.RejectAll();
      return;
    }
    if (FORMAT_REVISION_TYPES.has(item.type)) {
      throw new Error('格式修订范围包含其他修订或不支持单独拒绝，操作保留以便重试');
    }
    item.revision.Reject();
  } else {
    item.revision.Accept();
  }
}

/**
 * 取消一组待确认操作。没有其它修订时使用文档级 RejectAll，与 WPS
 * “拒绝对文档所做的所有修订”一致；否则只拒绝属于这些批次的范围。
 */
export function rejectRevisionBatches(doc, batchIds) {
  const ids = [...new Set(batchIds)];
  const batches = ids.map((id) => revisionBatches.get(id));
  if (!doc || batches.some((batch) => !batch || !sameDocument(doc, batch.doc))) {
    return { success: false, handled: 0, failed: 1, settledBatchIds: [], error: '修订批次不存在或文档不匹配' };
  }
  doc = batches[0]?.doc || doc;
  const expected = batches.flatMap((batch) => batch.revisions);
  const allowedAuthors = new Set(expected.map((item) => item.author));
  const baseline = documentPreviewEntry(doc)?.[1].before || [];
  const ownedRevisions = (current, snapshots = expected) => {
    const protectedItems = new Set(matchRevisions(baseline, current));
    return matchRevisions(snapshots, current.filter((item) => allowedAuthors.has(item.author) && !protectedItems.has(item)));
  };
  let handled = 0;
  let error = null;
  let current;
  let rejectingWholeDocument = false;
  const retainRemainingRevisions = () => {
    if (rejectingWholeDocument && current?.length > 0) {
      // 原集合全部属于选中的批次，RejectAll 部分成功后新建/重排的标记
      // 仍属于本轮操作。保留新快照，防止签名变化后误报撤销成功。
      const remaining = current.filter((item) => allowedAuthors.has(item.author));
      expected.splice(0, expected.length, ...remaining);
      for (const batch of batches) {
        batch.revisions = [...remaining];
      }
    }
  };
  try {
    current = readDocumentRevisions(doc);
    let owned = ownedRevisions(current);
    while (owned.length > 0) {
      const beforeCount = current.length;
      rejectingWholeDocument = owned.length === current.length;
      applyRevisionAction(doc, doc.Revisions, current, owned, 'reject', allowedAuthors);
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

// 每次操作后重新读取，避免 WPS 重排或合并集合后操作到其他作者。
function settleAIRevisions(doc, action) {
  let handled = 0;
  try {
    let current = readDocumentRevisions(doc);
    let owned = current.filter((item) => item.author === AI_REVISION_AUTHOR);
    while (owned.length > 0) {
      const beforeCount = owned.length;
      applyRevisionAction(doc, doc.Revisions, current, owned, action);
      current = readDocumentRevisions(doc);
      owned = current.filter((item) => item.author === AI_REVISION_AUTHOR);
      if (owned.length >= beforeCount) {
        throw new Error(`WPS 未完整处理${AI_REVISION_AUTHOR}的修订，请重试`);
      }
      handled += beforeCount - owned.length;
    }
    return { success: true, handled };
  } catch (error) {
    return { success: false, handled, error: error?.message || String(error) };
  }
}

// Linux WPS 在账户模式下可能把刚生成的修订署为登录用户。
// 仅凭作者名无法区分用户手动修改，因此只处理本次编辑前后差异记录的批次。
function settleAttributedBatchRevisions(doc, action) {
  const batches = [...revisionBatches.values()].filter((batch) => sameDocument(batch.doc, doc));
  const expected = batches.flatMap((batch) => batch.revisions)
    .filter((item) => item.author !== AI_REVISION_AUTHOR);
  if (expected.length === 0) {
    return { success: true, handled: 0 };
  }
  const allowedAuthors = new Set(expected.map((item) => item.author));
  const baseline = documentPreviewEntry(doc)?.[1].before || [];
  const ownedRevisions = (current) => {
    const protectedItems = new Set(matchRevisions(baseline, current));
    return matchRevisions(expected, current.filter((item) =>
      allowedAuthors.has(item.author) && !protectedItems.has(item)
    ));
  };
  let handled = 0;
  try {
    let current = readDocumentRevisions(doc);
    let owned = ownedRevisions(current);
    while (owned.length > 0) {
      const beforeCount = current.length;
      applyRevisionAction(doc, doc.Revisions, current, owned, action, allowedAuthors);
      current = readDocumentRevisions(doc);
      if (current.length >= beforeCount) {
        throw new Error('WPS 未完整处理本轮 AI 修订，请重试');
      }
      handled += beforeCount - current.length;
      owned = ownedRevisions(current);
    }
    const protectedItems = new Set(matchRevisions(baseline, current));
    const unresolved = current.some((item) => !protectedItems.has(item)
      && expected.some((snapshot) => item.author === snapshot.author
        && item.type === snapshot.type
        && item.date === snapshot.date
        && Math.abs(item.start - snapshot.start) <= Math.max(1, snapshot.end - snapshot.start)));
    if (unresolved) {
      throw new Error('WPS 改写了本轮修订标记，无法安全确认；请在 WPS 审阅中核对');
    }
    return { success: true, handled };
  } catch (error) {
    return { success: false, handled, error: error?.message || String(error) };
  }
}

/**
 * 仅处理目标文档中作者为文策AI的修订。若 AI 修订仍有
 * 残留，则保留批次和确认入口。只有全文都是 AI 修订时才使用全文接口。
 */
export function settleAllDocumentRevisions(doc, action, expectedDocId = null) {
  if (!doc) {
    return { success: false, handled: 0, error: '缺少 WPS Document 对象' };
  }
  if (action !== 'accept' && action !== 'reject') {
    return { success: false, handled: 0, error: 'action 必须是 accept 或 reject' };
  }
  if (expectedDocId !== null) {
    try {
      if (!Number.isSafeInteger(expectedDocId) || expectedDocId === 0 || Number(doc.DocID) !== expectedDocId) {
        return { success: false, handled: 0, error: '目标文档 DocID 不匹配' };
      }
    } catch (error) {
      return { success: false, handled: 0, error: '目标文档已经关闭或 DocID 不可读取' };
    }
  }

  const startedAt = now();
  const timings = { readMs: 0, nativeMs: 0, restoreViewMs: 0, screenUpdateMs: 0, totalMs: 0 };
  let resumeScreenUpdating = () => {};
  let handled = 0;
  try {
    const aiCount = getAIRevisionCount(doc);
    const hasAttributedBatch = isLinuxWPS() && [...revisionBatches.values()].some((batch) =>
      sameDocument(batch.doc, doc)
      && batch.revisions.some((item) => item.author !== AI_REVISION_AUTHOR)
    );
    timings.readMs = now() - startedAt;
    const [previewDoc, previewState] = documentPreviewEntry(doc) || [];
    if (aiCount > 0 || hasAttributedBatch || previewState) {
      // 接受修订和恢复显示设置期间暂停重绘，结束后统一刷新。
      const screenStartedAt = now();
      resumeScreenUpdating = suspendScreenUpdating(doc);
      timings.screenUpdateMs = now() - screenStartedAt;
    }
    const nativeStartedAt = now();
    try {
      if (aiCount > 0 || hasAttributedBatch) {
        const result = settleAIRevisions(doc, action);
        handled = result.handled;
        if (!result.success) {
          throw new Error(result.error);
        }
        if (hasAttributedBatch) {
          const attributed = settleAttributedBatchRevisions(doc, action);
          handled += attributed.handled;
          if (!attributed.success) {
            throw new Error(attributed.error);
          }
        }
      }
    } finally {
      timings.nativeMs = now() - nativeStartedAt;
    }
    const batchIdsToDelete = [];
    for (const [batchId, batch] of revisionBatches.entries()) {
      if (sameDocument(batch.doc, doc)) {
        batchIdsToDelete.push(batchId);
      }
    }
    for (const batchId of batchIdsToDelete) {
      revisionBatches.delete(batchId);
    }

    const viewStartedAt = now();
    if (previewState) {
      restoreDocumentPreview(previewDoc, previewState);
      documentPreviewStates.delete(previewDoc);
    }
    timings.restoreViewMs = now() - viewStartedAt;
    return { success: true, handled, timings };
  } catch (error) {
    return { success: false, handled, error: error?.message || String(error), timings };
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

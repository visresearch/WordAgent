import api from './api.js';
import { copyDocxRange } from './docxJsonConverter.js';
import { abortTrackedEdit, beginTrackedEdit, finishTrackedEdit } from './revisionPreview.mjs';

export async function copyDocument(request, isCurrent) {
  if (Number(request.sourceDocID) !== 0 || Number(request.targetDocID) !== 0) {
    throw new Error('Microsoft Word 加载项只能访问当前文档。复制范围时，两个文档 ID 都需要是 0。');
  }
  if (!isCurrent()) return null;

  const tracked = await beginTrackedEdit(0);
  try {
    if (!isCurrent()) return null;
    const copied = await copyDocxRange(request.start_paraID, request.end_paraID, request.insertID, isCurrent);
    if (!copied) return null;
    const revision = await finishTrackedEdit(tracked, 'insert');
    const url = globalThis.Office?.context?.document?.url;
    return {
      documentId: 0,
      documentName: url?.split(/[\\/]/).at(-1)?.split('?')[0],
      revisionCount: revision.revisionCount,
    };
  } finally {
    await abortTrackedEdit(tracked);
    api.wsManager.clearDocumentCache();
  }
}

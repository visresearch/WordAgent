import { uploadDocumentView } from '../../../../shared/documentView.mjs';
import api from './api.js';
import { readOfficeDocumentFile } from './documentFiles.js';
import { assertRevisionDocumentTarget } from './revisionPreview.mjs';

export async function renderDocumentView(request, isCurrent) {
  assertRevisionDocumentTarget(request.docId);
  const office = globalThis.Office;
  if (office?.PlatformType?.OfficeOnline && office.context?.platform === office.PlatformType.OfficeOnline) {
    throw new Error('Word 网页版无法从加载项导出页面，请在桌面 Word 中打开文档后重试。');
  }
  const pdf = await readOfficeDocumentFile(office?.FileType?.Pdf ?? 'pdf');
  if (isCurrent()) await uploadDocumentView(api.getConfig().baseURL, request, pdf);
  const url = office?.context?.document?.url;
  return { documentId: 0, documentName: url?.split(/[\\/]/).at(-1)?.split('?')[0] };
}

import { uploadDocumentView } from '../../../../shared/js/documentView.mjs';
import api from './api.js';
import { findWpsDocument, readWpsBinaryFile } from './documentFiles.js';

const PDF_FORMAT = 17; // wdExportFormatPDF
const REQUEST_ID = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;

export async function renderDocumentView(request, isCurrent) {
  if (!REQUEST_ID.test(request.requestId)) throw new Error('无效的渲染请求 ID。');

  const app = window.Application;
  const document = findWpsDocument(app, request.docId);
  if (!document) {
    throw new Error('找不到要渲染的文档，请确认文档仍然打开。');
  }
  if (typeof document.ExportAsFixedFormat !== 'function' || !app?.Env?.GetTempPath || !app.FileSystem) {
    throw new Error('当前 WPS 不支持导出文档页面。');
  }

  const directory = app.Env.GetTempPath().replace(/[\\/]+$/, '');
  const path = `${directory}/wence-view-${request.requestId}.pdf`;
  let bytes;
  try {
    // Export the live document with native pagination, including unsaved edits.
    document.ExportAsFixedFormat(path, PDF_FORMAT, false);
    bytes = readWpsBinaryFile(app.FileSystem, path);
  } finally {
    try {
      if (typeof app.FileSystem.unlinkSync === 'function') app.FileSystem.unlinkSync(path);
      else app.FileSystem.Remove(path);
    } catch (error) {
      console.warn('[view_document] 无法删除 WPS 临时 PDF:', error);
    }
  }

  if (isCurrent()) await uploadDocumentView(api.getConfig().baseURL, request, bytes);
  return { documentId: document.DocID ?? 0, documentName: document.Name };
}

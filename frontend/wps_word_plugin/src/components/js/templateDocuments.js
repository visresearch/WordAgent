import { archiveDocumentTemplate, templateEndpoint, templateRequest } from '../../../../shared/documentTemplates.mjs';
import api from './api.js';
import { findWpsDocument, readWpsBinaryFile } from './documentFiles.js';
import { parseDocxToJSON } from './docxJsonConverter.js';

export async function saveDocumentTemplate(request, isCurrent) {
  const app = window.Application;
  const document = findWpsDocument(app, request.docId);
  if (!document) throw new Error('未找到指定的模板源文档，请保持文档打开。');

  const path = document.FullName;
  if (!document.Path || document.Saved === false || !/\.docx?$/i.test(path)) {
    throw new Error('请先将模板源文档保存为本地 DOC 或 DOCX 文件，再重试。');
  }
  const file = new Blob([readWpsBinaryFile(app.FileSystem, path)]);
  if (!file.size || file.size > 50 * 1024 * 1024) throw new Error('模板源文件为空或大于 50 MB。');
  const parsed = parseDocxToJSON(document.Content, null, null, document);
  if (!parsed || parsed.error) throw new Error(parsed?.error || '无法解析模板全文。');
  if (!isCurrent()) throw new Error('模板归档已停止。');
  return archiveDocumentTemplate(api.getConfig().baseURL, request, { file, name: document.Name, document: parsed });
}

export async function createDocumentFromTemplate(id) {
  const documents = window.Application?.Documents;
  if (!documents?.Open) throw new Error('当前窗口无法在 WPS 中打开文档。');
  const response = await templateRequest(templateEndpoint(api.getConfig().baseURL, id, 'copy'), { method: 'POST' });
  const { path } = await response.json();
  const copy = documents.Open(path, false, false, false);
  if (!copy) throw new Error('WPS 未返回新建的模板副本。');
}

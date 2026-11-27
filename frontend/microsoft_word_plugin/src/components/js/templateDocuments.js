import { archiveDocumentTemplate, templateEndpoint, templateRequest } from '../../../../shared/documentTemplates.mjs';
import api from './api.js';
import { encodeOfficeDocument, readOfficeDocumentFile } from './documentFiles.js';
import { assertRevisionDocumentTarget } from './revisionPreview.mjs';

export async function saveDocumentTemplate(request, isCurrent) {
  assertRevisionDocumentTarget(request.docId);
  const document = globalThis.Office?.context?.document;
  const url = document?.url || '';
  let title = url.split(/[\\/]/).at(-1)?.split('?')[0] || request.name;
  try { title = decodeURIComponent(title); } catch (error) { /* Use the provided name. */ }
  const name = /\.docx$/i.test(title) ? title : `${title.replace(/\.doc$/i, '')}.docx`;
  const file = await readOfficeDocumentFile(globalThis.Office?.FileType?.Compressed ?? 'compressed');
  const parsed = await api.parseDocumentRange(0, -1, request.docId);
  if (!parsed || parsed.error) throw new Error(parsed?.error || 'Word could not parse the template.');
  if (!isCurrent()) throw new Error('Template archive cancelled.');
  return archiveDocumentTemplate(api.getConfig().baseURL, request, { file, name, document: parsed });
}

export async function createDocumentFromTemplate(id) {
  const response = await templateRequest(templateEndpoint(api.getConfig().baseURL, id, 'file'));
  const result = await api.createDocument(await encodeOfficeDocument(await response.blob()));
  if (!result.success) throw new Error(result.error);
}

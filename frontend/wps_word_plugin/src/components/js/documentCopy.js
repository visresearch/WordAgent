import api from './api.js';
import { findWpsDocument } from './documentFiles.js';
import { getParagraphLocationAtPosition, getParagraphParaID } from './docxJsonConverter.js';
import { abortTrackedEdit, beginTrackedEdit, finishTrackedEdit } from './revisionPreview.js';

function findParagraph(document, paraID) {
  for (let index = 1; index <= document.Paragraphs.Count; index++) {
    const paragraph = document.Paragraphs.Item(index);
    if (getParagraphParaID(paragraph) === Number(paraID)) return paragraph;
  }
  return null;
}

function documentTables(document) {
  const tables = document.Content.Tables || document.Tables;
  return Array.from({ length: tables?.Count || 0 }, (_, index) => tables.Item(index + 1).Range);
}

function tableBoundaryID(range, atEnd) {
  const paragraphs = range.Paragraphs;
  const index = atEnd ? paragraphs?.Count : 1;
  return index && paragraphs?.Count ? getParagraphParaID(paragraphs.Item(index)) : null;
}

function sourceRange(document, startID, endID) {
  const first = findParagraph(document, startID);
  const last = findParagraph(document, endID);
  if (!first || !last) throw new Error('找不到源文档的起止段落，请重新读取段落 ID。');

  let start = first.Range.Start;
  let end = last.Range.End;
  if (start >= end) throw new Error('源范围的结束段落在起始段落之前。');
  const tables = documentTables(document);
  for (const range of tables) {
    if (tableBoundaryID(range, false) === startID) start = Math.min(start, range.Start);
    if (tableBoundaryID(range, true) === endID) end = Math.max(end, range.End);
  }
  if (tables.some(range => start < range.End && end > range.Start && (start > range.Start || end < range.End))) {
    throw new Error('复制范围只覆盖了部分表格，请选择完整表格。');
  }
  return { start, end };
}

function targetPosition(document, insertID) {
  if (insertID === 0) return document.Content.Start;
  const paragraph = findParagraph(document, insertID);
  if (!paragraph) throw new Error('找不到目标文档的插入锚点，请重新读取段落 ID。');
  const { Start: start, End: end } = paragraph.Range;
  let position = end;
  for (const range of documentTables(document)) {
    if (start < range.End && end > range.Start) {
      if (tableBoundaryID(range, true) !== insertID) {
        throw new Error('插入锚点位于表格内部，请使用表格外的段落或完整表格的最后一个段落。');
      }
      position = Math.max(position, range.End);
    }
  }
  return position;
}

export function copyDocument(request, isCurrent) {
  const app = window.Application;
  const source = findWpsDocument(app, request.sourceDocID);
  const target = findWpsDocument(app, request.targetDocID);
  if (!source || !target) throw new Error('找不到源文档或目标文档。');
  if (target.ReadOnly) throw new Error('目标文档为只读。');

  const startID = Number(request.start_paraID);
  const endID = Number(request.end_paraID);
  const insertID = Number(request.insertID);
  const { start, end } = sourceRange(source, startID, endID);
  const position = targetPosition(target, insertID);
  const sameDocument = source === target || (source.DocID != null && target.DocID != null
    && Number(source.DocID) === Number(target.DocID));
  if (sameDocument && start < position && position < end) {
    throw new Error('插入位置不能位于复制范围内部。');
  }
  const from = source.Range(start, end);
  const content = target.Content;
  const before = content.End;
  // Consume the required paragraph mark of a blank document to avoid a trailing empty paragraph.
  const usePlaceholder = insertID === 0 && before - position === 1 && content.Text === '\r' && !target.Shapes?.Count;
  const destination = target.Range(position, usePlaceholder ? before : position);
  let inTable = false;
  try {
    inTable = [true, 1, -1].includes(destination.Information?.(12)); // wdWithInTable
  } catch (error) {
    // The paragraph and table boundaries were already checked above.
  }
  if (inTable) throw new Error('WPS 将插入点定位到了表格内部，请选择表格外的锚点。');
  const formatted = from.FormattedText;
  if (!formatted) throw new Error('当前 WPS 无法读取源范围的原生格式。');
  if (!isCurrent()) return null;

  const tracked = beginTrackedEdit(target);
  try {
    destination.FormattedText = formatted;
    const insertedEnd = position + target.Content.End - before + Number(usePlaceholder);
    if (insertedEnd <= position) throw new Error('无法确认目标文档中的插入范围，请重新读取后检查。');

    const revision = finishTrackedEdit(tracked, { start: position, end: insertedEnd }, 'insert');
    return {
      documentId: target.DocID ?? 0,
      documentName: target.Name,
      revisionCount: revision.revisionCount,
      lastParagraph: getParagraphLocationAtPosition(target, insertedEnd - 1)
    };
  } finally {
    abortTrackedEdit(tracked);
    api.wsManager.clearDocumentCache();
  }
}

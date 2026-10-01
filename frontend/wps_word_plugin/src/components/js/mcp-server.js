/** WPS 页面侧的 MCP 文档工具执行与后端连接。 */
import { createDocument, getDocumentById, parseDocumentRange, wsManager } from './api.js';
import { executeStyleQuery } from './docxQuery.js';
import {
  deleteDocxPara,
  editDocxParagraph,
  generateDocxFromJSON,
  insertBreakAfterParagraph
} from './docxJsonConverter.js';

const BRIDGE_URL = 'ws://127.0.0.1:3880/api/mcp/bridge';
let socket = null;
let reconnectTimer = null;
let stopped = false;
let delay = 1000;
let workQueue = Promise.resolve();

function targetDocument(docId = 0) {
  const doc = getDocumentById(docId);
  if (!doc) throw new Error('没有打开的 WPS 文档');
  // getDocumentById falls back to ActiveDocument. Reject that fallback for a
  // specified ID so an agent never edits a different document by accident.
  if (Number(docId) !== 0 && Number(doc.DocID) !== Number(docId)) {
    throw new Error(`找不到文档 docId=${docId}`);
  }
  return doc;
}

function checked(result, fallback) {
  if (result?.error || result?.success === false) {
    throw new Error(result?.error || result?.message || fallback);
  }
  return result;
}

async function executeTool(tool, args) {
  const docId = args.docId ?? 0;
  switch (tool) {
    case 'read_document': {
      targetDocument(docId);
      const documentJson = checked(await parseDocumentRange(
        args.startParaIndex, args.endParaIndex, docId,
        args.startParaID, args.endParaID, args.mode
      ), '读取文档失败');
      return { documentJson, docId };
    }
    case 'search_document': {
      targetDocument(docId);
      const documentJson = checked(await parseDocumentRange(0, -1, docId), '读取文档失败');
      return { ...executeStyleQuery(documentJson, args.query), docId };
    }
    case 'delete_document': {
      const result = deleteDocxPara(args.paraIDs, targetDocument(docId));
      wsManager.clearDocumentCache();
      return { ...result, docId };
    }
    case 'edit_document': {
      const result = checked(editDocxParagraph(args.paraID, args.runs, targetDocument(docId)), '编辑段落失败');
      wsManager.clearDocumentCache();
      return { ...result, docId };
    }
    case 'create_document':
      return checked(createDocument(), '创建文档失败');
    case 'insert_break': {
      const result = checked(insertBreakAfterParagraph(args.paraID, args.breakType, targetDocument(docId)), '插入分隔符失败');
      wsManager.clearDocumentCache();
      return { ...result, docId };
    }
    case 'generate_document': {
      const result = generateDocxFromJSON(args.document, targetDocument(docId), args.insertParaID);
      wsManager.clearDocumentCache();
      return { ...result, docId };
    }
    default:
      throw new Error(`未知的 MCP 工具：${tool}`);
  }
}

function connect() {
  if (stopped || socket) return;
  const ws = new WebSocket(BRIDGE_URL);
  socket = ws;
  ws.onopen = () => { delay = 1000; };
  ws.onmessage = (event) => {
    let request;
    try {
      request = JSON.parse(event.data);
      if (!request?.requestId || !request?.tool) return;
    } catch (error) {
      console.warn('[WPS MCP] 无法解析工具请求:', error);
      return;
    }
    // Document reads and edits must observe a single ordering across MCP calls.
    workQueue = workQueue.then(async () => {
      if (ws.readyState !== WebSocket.OPEN) return;
      try {
        const result = await executeTool(request.tool, request.arguments || {});
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ requestId: request.requestId, result }));
        }
      } catch (error) {
        console.error('[WPS MCP] 工具调用失败:', error);
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ requestId: request.requestId, error: error?.message || String(error) }));
        }
      }
    });
  };
  ws.onclose = () => {
    if (socket !== ws) return;
    socket = null;
    if (!stopped) {
      reconnectTimer = setTimeout(connect, delay);
      delay = Math.min(delay * 2, 10000);
    }
  };
  ws.onerror = () => ws.close();
}

export function startMcpBridge() {
  stopped = false;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  connect();
}

export function stopMcpBridge() {
  stopped = true;
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = null;
  socket?.close();
  socket = null;
}

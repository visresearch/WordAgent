/** Microsoft Word 页面侧的 MCP 工具执行与后端桥接。 */
import { createDocument, parseDocumentRange, wsManager } from './api.js';
import { executeStyleQuery } from './docxQuery.js';
import {
  deleteDocxPara,
  editDocxParagraph,
  generateDocxFromJSON,
  insertBreakAfterParagraph,
} from './docxJsonConverter.js';

// 与 WPS 共用后端端口、路径；host 只用于识别加载项类型。
const BRIDGE_URL = 'ws://127.0.0.1:3880/api/mcp/bridge?host=word';
let socket = null;
let reconnectTimer = null;
let stopped = true;
let delay = 1000;
let workQueue = Promise.resolve();

function checked(result, fallback) {
  if (!result || result.error || result.success === false) {
    throw new Error(result?.error || result?.message || fallback);
  }
  return result;
}

async function executeTool(tool, args) {
  // Office.js operates on the task pane's document and cannot select a WPS DocID.
  if (args.docId != null && Number(args.docId) !== 0) {
    throw new Error('Microsoft Word 仅支持 docId=0（当前加载项所属文档）');
  }
  switch (tool) {
    case 'read_document': {
      const documentJson = checked(await parseDocumentRange(
        args.startParaIndex ?? 0, args.endParaIndex ?? -1, 0,
        args.startParaID ?? null, args.endParaID ?? null, args.mode ?? 'full'
      ), '读取文档失败');
      return { documentJson, docId: 0 };
    }
    case 'search_document': {
      const documentJson = checked(await parseDocumentRange(0, -1, 0), '读取文档失败');
      return { ...executeStyleQuery(documentJson, args.query || {}), docId: 0 };
    }
    case 'delete_document':
    case 'edit_document':
    case 'insert_break':
    case 'generate_document': {
      // Clear even after a failed operation: Office may have applied part of it.
      try {
        let result;
        if (tool === 'delete_document') result = await deleteDocxPara(args.paraIDs);
        if (tool === 'edit_document') result = await editDocxParagraph(args.paraID, args.runs);
        if (tool === 'insert_break') result = await insertBreakAfterParagraph(args.paraID, args.breakType);
        if (tool === 'generate_document') {
          result = await generateDocxFromJSON(args.document, 'selection', args.insertParaID ?? 0);
        }
        return { ...checked(result, '文档操作失败'), docId: 0 };
      } finally {
        wsManager.clearDocumentCache();
      }
    }
    case 'create_document': {
      const result = checked(await createDocument(), '创建文档失败');
      return {
        ...result,
        message: '新文档已打开。请关闭旧文档的加载项侧栏，并在新文档中打开加载项后再调用文档工具。',
      };
    }
    default:
      throw new Error(`未知的 MCP 工具：${tool}`);
  }
}

function scheduleReconnect() {
  if (stopped || reconnectTimer !== null) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
  delay = Math.min(delay * 2, 10000);
}

function connect() {
  if (stopped || socket) return;
  let ws;
  try {
    ws = new WebSocket(BRIDGE_URL);
  } catch (error) {
    console.warn('[Word MCP] 无法连接后端:', error);
    scheduleReconnect();
    return;
  }
  socket = ws;
  ws.onopen = () => { delay = 1000; };
  ws.onmessage = (event) => {
    if (socket !== ws || stopped) return;
    let request;
    try {
      request = JSON.parse(event.data);
      if (typeof request?.requestId !== 'string' || typeof request?.tool !== 'string') return;
    } catch (error) {
      console.warn('[Word MCP] 无法解析工具请求:', error);
      return;
    }
    // Office.js reads and mutations observe the same ordering across MCP calls.
    workQueue = workQueue.then(async () => {
      if (socket !== ws || stopped || ws.readyState !== WebSocket.OPEN) return;
      let response;
      try {
        const result = await executeTool(request.tool, request.arguments || {});
        response = { requestId: request.requestId, result };
      } catch (error) {
        response = { requestId: request.requestId, error: error?.message || String(error) };
      }
      if (socket === ws && !stopped && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(response));
      }
    }).catch((error) => {
      // A transport failure must not poison subsequent requests in the queue.
      console.warn('[Word MCP] 工具结果回传失败:', error);
    });
  };
  ws.onclose = () => {
    if (socket !== ws) return;
    socket = null;
    scheduleReconnect();
  };
  ws.onerror = () => ws.close();
}

export function startMcpBridge() {
  stopped = false;
  if (reconnectTimer !== null) clearTimeout(reconnectTimer);
  reconnectTimer = null;
  connect();
}

export function stopMcpBridge() {
  stopped = true;
  if (reconnectTimer !== null) clearTimeout(reconnectTimer);
  reconnectTimer = null;
  const previous = socket;
  socket = null;
  previous?.close();
}

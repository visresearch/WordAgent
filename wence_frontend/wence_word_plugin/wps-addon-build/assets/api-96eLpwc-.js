const c = { baseURL:'http://localhost:3880',timeout:3e4,headers:{ 'Content-Type':'application/json' } };async function i(e,t = {}) {
  const o = `${c.baseURL}${e}`,a = { method:t.method || 'GET',headers:{ ...c.headers,...t.headers },...t };t.body && typeof t.body === 'object' && (a.body = JSON.stringify(t.body));try {
    const r = new AbortController,s = setTimeout(() => r.abort(),t.timeout || c.timeout);a.signal = r.signal;const n = await fetch(o,a);clearTimeout(s);const h = n.headers.get('content-type');let u;return h && h.includes('application/json') ? u = await n.json() : u = await n.text(),n.ok ? { success:!0,data:u,status:n.status } : { success:!1,error:u.message || u.error || `HTTP ${n.status}: ${n.statusText}`,status:n.status,data:u };
  } catch (r) {
    return r.name === 'AbortError' ? { success:!1,error:'请求超时，请稍后重试',code:'TIMEOUT' } : { success:!1,error:r.message || '网络请求失败',code:'NETWORK_ERROR' };
  }
} function R(e,t = {}) {
  const { onMessage:o,onError:a,onComplete:r,mode:s = 'agent',model:n = 'auto',documentJson:h = null,history:u = [] } = t,f = new AbortController;return (async() => {
    try {
      const d = await fetch(`${c.baseURL}/api/chat/stream`,{ method:'POST',headers:c.headers,body:JSON.stringify({ message:e.trim(),mode:s,model:n,documentJson:h,history:u,timestamp:Date.now() }),signal:f.signal });if (!d.ok) {
        throw new Error(`HTTP ${d.status}: ${d.statusText}`);
      } const g = d.body.getReader(),w = new TextDecoder;let l = '';for (;;) {
        const { done:T,value:E } = await g.read();if (T) {
          r && r();break;
        }l += w.decode(E,{ stream:!0 });const y = l.split(`
`);l = y.pop() || '';for (const p of y) {
          if (p.startsWith('data: ')) {
            const m = p.slice(6);if (m === '[DONE]') {
              r && r();return;
            } try {
              const b = JSON.parse(m);o && o(b);
            } catch {
              o && o({ content:m });
            }
          }
        }
      }
    } catch (d) {
      d.name !== 'AbortError' && a && a(d);
    }
  })(),{ abort:() => f.abort() };
} async function S() {
  return await i('/api/chat/models',{ method:'GET' });
} async function O(e,t = {}) {
  const { limit:o = 50,offset:a = 0 } = t,r = new URLSearchParams({ limit:String(o),offset:String(a) });return await i(`/api/chat/history/${encodeURIComponent(e)}?${r}`,{ method:'GET' });
} async function U(e) {
  return await i('/api/chat/history/save',{ method:'POST',body:e });
} async function $(e) {
  return await i(`/api/chat/history/${encodeURIComponent(e)}`,{ method:'DELETE' });
} async function L(e = 100) {
  const t = new URLSearchParams({ limit:String(e) });return await i(`/api/chat/documents?${t}`,{ method:'GET' });
} function v(e) {
  e.baseURL && (c.baseURL = e.baseURL),e.timeout && (c.timeout = e.timeout),e.headers && (c.headers = { ...c.headers,...e.headers });
} function P() {
  return { ...c };
} async function x({ baseUrl:e,apiKey:t }) {
  var o,a,r;try {
    const s = await i('/api/chat/providers/models',{ method:'POST',body:{ base_url:e,api_key:t } });if (s.success && ((o = s.data) != null && o.success) && ((a = s.data) != null && a.models)) {
      return { success:!0,models:s.data.models };
    } throw new Error(((r = s.data) == null ? void 0 : r.error) || s.error || '获取模型列表失败');
  } catch (s) {
    throw console.error('获取模型列表失败:',s),new Error(s.message || '获取模型列表失败');
  }
} async function C() {
  try {
    const e = await i('/api/settings',{ method:'GET' });return e.success ? e.data : (console.error('获取设置失败:',e.error),{ providers:[] });
  } catch (e) {
    return console.error('获取设置异常:',e),{ providers:[] };
  }
} async function G(e) {
  try {
    const t = await i('/api/settings',{ method:'POST',body:e });if (!t.success) {
      throw new Error(t.error || '保存设置失败');
    } return t;
  } catch (t) {
    throw console.error('保存设置异常:',t),t;
  }
} const A = { chatStream:R,getModels:S,fetchAvailableModels:x,getChatHistory:O,saveMessage:U,clearChatHistory:$,getDocuments:L,getSettings:C,saveSettings:G,updateConfig:v,getConfig:P,request:i };export { A as a };

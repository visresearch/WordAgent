export function templateEndpoint(baseURL, id = '', action = '') {
  const root = `${baseURL}/api/templates`;
  return id ? `${root}/${encodeURIComponent(id)}${action ? `/${action}` : ''}` : root;
}

export async function templateRequest(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new Error(typeof problem?.detail === 'string' ? problem.detail : `HTTP ${response.status}`);
  }
  return response;
}

export async function archiveDocumentTemplate(baseURL, request, snapshot) {
  const form = new FormData();
  form.append('template_id', request.requestId);
  form.append('name', request.name);
  form.append('instructions', request.instructions);
  form.append('original', snapshot.file, snapshot.name);
  form.append('document_json', new Blob([JSON.stringify(snapshot.document)], { type: 'application/json' }), 'document.json');
  const response = await templateRequest(templateEndpoint(baseURL), { method: 'POST', body: form });
  return response.json();
}

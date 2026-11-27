export async function uploadDocumentView(baseUrl, request, bytes) {
  const params = new URLSearchParams({
    page_start: request.page_start,
    page_end: request.page_end,
    mode: request.mode
  });
  const body = new FormData();
  body.append('file', new Blob([bytes], { type: 'application/pdf' }), 'document.pdf');
  const response = await fetch(`${baseUrl}/api/chat/document-view/${encodeURIComponent(request.requestId)}?${params}`, {
    method: 'POST', body
  });
  if (!response.ok) {
    const result = await response.json().catch(() => null);
    throw new Error(typeof result?.detail === 'string' ? result.detail : `Document render failed (HTTP ${response.status}).`);
  }
}

export function findWpsDocument(app, docId) {
  const id = Number(docId ?? 0);
  if (id === 0) return app?.ActiveDocument;
  const documents = app?.Documents;
  for (let index = 1; index <= (documents?.Count || 0); index++) {
    const document = documents.Item(index);
    if (Number(document.DocID) === id) return document;
  }
  return null;
}

export function readWpsBinaryFile(fileSystem, path) {
  if (typeof fileSystem?.ReadFileAsArrayBuffer === 'function') {
    return fileSystem.ReadFileAsArrayBuffer(path);
  }
  if (typeof fileSystem?.readAsBinaryString === 'function') {
    return Uint8Array.from(fileSystem.readAsBinaryString(path), character => character.charCodeAt(0));
  }
  throw new Error('当前 WPS 无法读取文件。');
}

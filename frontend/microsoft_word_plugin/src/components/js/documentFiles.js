const MAX_FILE_BYTES = 50 * 1024 * 1024;

function officeResult(callback) {
  return new Promise((resolve, reject) => callback(result => {
    if (result.status === (globalThis.Office?.AsyncResultStatus?.Succeeded ?? 'succeeded')) {
      resolve(result.value);
    } else {
      reject(new Error(result.error?.message || 'Word could not export the document file.'));
    }
  }));
}

export async function readOfficeDocumentFile(fileType) {
  const document = globalThis.Office?.context?.document;
  if (!document?.getFileAsync) throw new Error('This Word host cannot export the document file.');
  const file = await officeResult(done => document.getFileAsync(fileType, { sliceSize: 65536 }, done));
  try {
    if (!file.size || file.size > MAX_FILE_BYTES) throw new Error('The document export must be between 1 byte and 50 MB.');
    const slices = [];
    for (let index = 0; index < file.sliceCount; index++) {
      const slice = await officeResult(done => file.getSliceAsync(index, done));
      slices.push(new Uint8Array(slice.data));
    }
    return new Blob(slices);
  } finally {
    file.closeAsync();
  }
}

export async function encodeOfficeDocument(file) {
  const bytes = new Uint8Array(await file.arrayBuffer());
  const parts = [];
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    parts.push(String.fromCharCode(...bytes.subarray(offset, offset + 0x8000)));
  }
  return btoa(parts.join(''));
}

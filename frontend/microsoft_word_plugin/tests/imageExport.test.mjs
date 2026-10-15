import assert from 'node:assert/strict';
import test from 'node:test';
import { exportImageToTemp } from '../src/components/js/docxJsonConverter.js';

const png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l1cAAAAASUVORK5CYII=';
const picture = () => ({
  load() {}, width: 120, height: 80, altTextTitle: 'Document picture',
  getBase64ImageSrc: () => ({ value: png })
});

test('Word exports image bytes only to the local image endpoint and returns a temp path', async t => {
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, 'http://localhost:3880/api/chat/image');
    assert.equal(options.method, 'POST');
    const file = options.body.get('file');
    assert.equal(file.type, 'image/png');
    assert.deepEqual(Buffer.from(await file.arrayBuffer()), Buffer.from(png, 'base64'));
    return { ok: true, json: async () => ({ saved: true, url: 'F:/wence_data/project/temp/image.png' }) };
  });
  const result = await exportImageToTemp(picture(), { sync: async () => {} });
  assert.deepEqual(result, {
    saved: true, url: 'F:/wence_data/project/temp/image.png', width: 120, height: 80, altText: 'Document picture'
  });
  assert.equal(JSON.stringify(result).includes(png), false);
});

for (const response of [
  { ok: false, status: 500 },
  { ok: true, json: async () => ({ saved: true, url: `data:image/png;base64,${png}` }) },
  { ok: true, json: async () => ({ saved: false }) }
]) {
  test('image export failure never falls back to embedding image data', async t => {
    t.mock.method(console, 'warn', () => {});
    t.mock.method(globalThis, 'fetch', async () => response);
    assert.deepEqual(await exportImageToTemp(picture(), { sync: async () => {} }), { saved: false });
  });
}

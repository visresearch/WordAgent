import assert from "node:assert/strict";
import test from "node:test";

import { parseDocxToJSONLightweight } from "../src/components/js/docxJsonConverter.js";
import { parseDocumentRange } from "../src/components/js/api.js";

function mockParagraph(text, bookmarkName) {
  const contentControl = { isNullObject: true, load() {} };
  return {
    text,
    getRange(name) {
      if (name === "Start") {
        return {
          getBookmarks() {
            return { value: [bookmarkName] };
          },
        };
      }
      if (name === "Whole") {
        return {
          parentContentControlOrNullObject: contentControl,
          getBookmarks() {
            return { value: [bookmarkName] };
          },
        };
      }
      throw new Error(`unexpected range: ${name}`);
    },
  };
}

test("轻量读取仅返回段落文本、位置和 paraID", async t => {
  const items = [
    mockParagraph("第一段\r", "_123456789_p"),
    mockParagraph("\r", "_987654321_p"),
  ];
  const context = {
    document: {
      sections: {
        items: [{ pageSetup: { topMargin: 72, bottomMargin: 72, leftMargin: 85.05, rightMargin: 56.7, load() {} } }],
        load() {},
      },
      body: {
        paragraphs: {
          items,
          load() {},
        },
      },
    },
    async sync() {},
  };
  const previous = globalThis.Word;
  globalThis.Word = {
    async run(callback) {
      return callback(context);
    },
  };
  t.after(() => { globalThis.Word = previous; });

  const result = await parseDocxToJSONLightweight(0, -1);

  assert.deepEqual(result, {
    paragraphs: [
      {
        runs: [{ text: "第一段", rStyle: "" }],
        paraIndex: 0,
        paraID: "123456789",
      },
      { runs: [], paraIndex: 1, paraID: "987654321" },
    ],
    _lightweight: true,
  });

  // 0,0 must remain a single-paragraph read, not an alias for the whole document.
  const first = await parseDocxToJSONLightweight(0, 0);
  assert.deepEqual(first.paragraphs, [result.paragraphs[0]]);

  const tail = await parseDocxToJSONLightweight(1, -1);
  assert.deepEqual(tail.paragraphs, [result.paragraphs[1]]);

  const read = await parseDocumentRange(0, -1, 0, null, null, "lightweight");
  assert.deepEqual(read.meta.pageMarginsCm, { top: 2.54, bottom: 2.54, left: 3, right: 2 });
});

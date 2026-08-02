import assert from "node:assert/strict";
import test from "node:test";

import { parseDocxToJSONLightweight } from "../src/components/js/docxJsonConverter.js";

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

test("轻量读取仅返回段落文本、位置和 paraID", async () => {
  const items = [
    mockParagraph("第一段\r", "_123456789_p"),
    mockParagraph("\r", "_987654321_p"),
  ];
  const context = {
    document: {
      body: {
        paragraphs: {
          items,
          load() {},
        },
      },
    },
    async sync() {},
  };
  globalThis.Word = {
    async run(callback) {
      return callback(context);
    },
  };

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
    fields: [],
    _lightweight: true,
  });
});

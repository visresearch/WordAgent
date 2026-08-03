import assert from "node:assert/strict";
import test from "node:test";

import { getLoadedParagraphPageRange } from "../src/components/js/docxJsonConverter.js";

test("reads a paragraph physical page range from loaded Word pages", () => {
  assert.deepEqual(
    getLoadedParagraphPageRange({ items: [{ index: 3 }, { index: 2 }, { index: 3 }] }),
    { pageStart: 2, pageEnd: 3 }
  );
});

test("omits both page fields when Word returns no valid physical page", () => {
  assert.deepEqual(getLoadedParagraphPageRange({ items: [{ index: 0 }, { index: null }] }), {});
});

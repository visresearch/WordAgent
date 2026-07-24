import assert from "node:assert/strict";
import test from "node:test";

import {
  parseParaIDFromContentControlMeta,
  parseParaIDFromContentControlMetadata,
} from "../src/components/js/contentControlMetadata.mjs";

test("reads a legacy paraID from a content control tag", () => {
  assert.equal(
    parseParaIDFromContentControlMetadata({ tag: "wence:paraID=-123456789", title: "" }),
    "-123456789"
  );
});

test("falls back to a legacy content control title", () => {
  assert.equal(
    parseParaIDFromContentControlMetadata({
      tag: "unrelated-control",
      title: '{"wence":{"paragraphId":987654321}}',
    }),
    "987654321"
  );
});

test("accepts a bare legacy ID but ignores unrelated numbers", () => {
  assert.equal(parseParaIDFromContentControlMeta("123456789"), "123456789");
  assert.equal(parseParaIDFromContentControlMeta("Annual report 2026"), null);
  assert.equal(parseParaIDFromContentControlMeta('{"version":2026}'), null);
});

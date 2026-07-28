import assert from "node:assert/strict";
import test from "node:test";

import { expandOrderedDocumentBlocks } from "../src/components/js/docxJsonConverter.js";

test("表格块严格保留在相邻段落之间", () => {
  const before = { pStyle: "pS_1", runs: [{ text: "表格前", rStyle: "rS_1" }] };
  const table = { rows: 1, columns: 1, cells: [[{ text: "值" }]], tStyle: "tS_1" };
  const after = { pStyle: "pS_1", runs: [{ text: "表格后", rStyle: "rS_1" }] };

  const elements = expandOrderedDocumentBlocks([before, { tables: [table] }, after]);

  assert.deepEqual(elements.map((item) => item.type), ["paragraph", "table", "paragraph"]);
  assert.equal(elements[1].data, table);
});

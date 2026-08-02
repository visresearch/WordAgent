import assert from "node:assert/strict";
import test from "node:test";

import { executeQuery, executeStyleQuery } from "../src/components/js/docxQuery.js";

const tableDocument = {
  paragraphs: [
    { paraIndex: 0, paraID: 100, runs: [{ text: "Before table" }] },
    {
      tables: [
        {
          cells: [
            [
              {
                paragraphs: [
                  {
                    paraIndex: 1,
                    paraID: 101,
                    runs: [
                      { text: "Exact table ", rStyle: [] },
                      { text: "target", rStyle: [null, null, true] },
                    ],
                  },
                ],
              },
            ],
          ],
        },
      ],
    },
    { paraIndex: 2, paraID: 102, runs: [{ text: "After table" }] },
  ],
};

test("style query searches table cell paragraphs", () => {
  const result = executeStyleQuery(tableDocument, {
    type: "paragraph",
    filters: { regex: "Exact table target", regexFlags: "i" },
  });

  assert.equal(result.matchCount, 1);
  assert.equal(result.matches[0].paragraphIndex, 1);
  assert.equal(result.matches[0].paragraphId, "101");
});

test("text-only run query matches text split across runs", () => {
  const result = executeStyleQuery(tableDocument, {
    type: "run",
    filters: { regex: "Exact table target", regexFlags: "i" },
  });

  assert.equal(result.matchCount, 1);
  assert.equal(result.matches[0].text, "Exact table target");
});

test("run style query searches table cell paragraphs", () => {
  const result = executeStyleQuery(tableDocument, {
    type: "run",
    filters: { bold: true },
  });

  assert.equal(result.matchCount, 1);
  assert.equal(result.matches[0].text, "target");
  assert.equal(result.matches[0].paragraphIndex, 1);
});

test("query DSL searches table cell paragraphs", () => {
  const result = executeQuery(tableDocument, {
    query: { match: { field: "text", query: "Exact table target" } },
    context: 0,
  });

  assert.equal(result.found, true);
  assert.equal(result.matchedCount, 1);
  assert.equal(result.paragraphs[0].paraID, 101);
});

test("cell.text without cell paragraphs is not searchable", () => {
  const result = executeStyleQuery(
    { paragraphs: [{ tables: [{ cells: [[{ text: "obsolete text" }]] }] }] },
    { type: "run", filters: { regex: "obsolete text", regexFlags: "i" } }
  );

  assert.equal(result.matchCount, 0);
});

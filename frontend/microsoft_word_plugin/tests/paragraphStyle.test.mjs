import assert from "node:assert/strict";
import test from "node:test";

import { applyGeneratedParagraphStyle } from "../src/components/js/docxJsonConverter.js";

test("空段落与普通段落共用完整 pStyle 应用逻辑", () => {
  const paragraph = {};
  const pStyle = ["center", 18, 1, 2, 3, 4, 5, "摘要标题", 1];

  applyGeneratedParagraphStyle(paragraph, pStyle);

  assert.deepEqual(paragraph, {
    style: "摘要标题",
    alignment: "Centered",
    leftIndent: 1,
    rightIndent: 2,
    firstLineIndent: 3,
    spaceBefore: 4,
    spaceAfter: 5,
    lineSpacing: 18,
  });
});

test("pStyle 中的零值会清除插入锚点继承的段落间距", () => {
  const paragraph = {
    leftIndent: 12,
    rightIndent: 12,
    firstLineIndent: 12,
    spaceBefore: 12,
    spaceAfter: 12,
  };

  applyGeneratedParagraphStyle(paragraph, ["left", 0, 0, 0, 0, 0, 0, "", 1]);

  assert.equal(paragraph.leftIndent, 0);
  assert.equal(paragraph.rightIndent, 0);
  assert.equal(paragraph.firstLineIndent, 0);
  assert.equal(paragraph.spaceBefore, 0);
  assert.equal(paragraph.spaceAfter, 0);
});

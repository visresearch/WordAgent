import assert from "node:assert/strict";
import test from "node:test";

import { applyGeneratedParagraphStyle, generateDocxFromJSON } from "../src/components/js/docxJsonConverter.js";

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

test("生成正文和空段落时只格式化新段落，保留锚点及相邻标题", async (t) => {
  const previousWord = globalThis.Word;
  t.after(() => { globalThis.Word = previousWord; });
  const items = [];
  function paragraph(text, id, style = "原段落") {
    return {
      text, style, font: {}, firstLineIndent: 12,
      bookmarks: id ? [`_${id}_p`] : [],
      getRange() {
        return {
          parentContentControlOrNullObject: { isNullObject: true, load() {} },
          getBookmarks: () => ({ value: this.bookmarks }),
          insertBookmark: (name) => this.bookmarks.push(name),
          insertText: (value) => { this.text += value; }
        };
      },
      insertParagraph(value, location) {
        assert.equal(location, "After");
        const inserted = paragraph(value, null, this.style);
        items.splice(items.indexOf(this) + 1, 0, inserted);
        return inserted;
      },
      search() { return { items: [{ font: {} }], load() {} }; }
    };
  }
  const anchor = paragraph("（3）原有实习目的", "111111111");
  const heading = paragraph("1.2 个人目标", "222222222", "标题 2");
  items.push(anchor, heading);
  globalThis.Word = {
    InsertLocation: { after: "After", end: "End" },
    run: (callback) => callback({
      document: { body: { paragraphs: { items, load() {} } } },
      async sync() {}
    })
  };
  const bodyStyle = ["left", 18, 0, 0, 0, 0, 0, "正文缩进段落", 1];
  const result = await generateDocxFromJSON({ paragraphs: [
    { pStyle: bodyStyle, runs: [{ text: "（4）新增实习目的" }] },
    { pStyle: bodyStyle, runs: [] }
  ] }, "selection", "111111111");
  assert.equal(result.success, true, result.error);
  assert.equal(result.insertedParaIDs.length, 2);
  assert.deepEqual(items.map((item) => item.text), [anchor.text, "（4）新增实习目的", "", heading.text]);
  assert.deepEqual(items.map((item) => item.style), ["原段落", "正文缩进段落", "正文缩进段落", "标题 2"]);
  assert.equal(anchor.firstLineIndent, 12);
  assert.equal(heading.firstLineIndent, 12);
  assert.equal(items[1].firstLineIndent, 0);
  assert.equal(items[2].firstLineIndent, 0);
});

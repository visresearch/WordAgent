import assert from "node:assert/strict";
import test from "node:test";

import {
  getFontReadProperties,
  getLoadedUnderlineColor,
} from "../src/components/js/docxJsonConverter.js";

test("不支持 WordApiDesktop 时不请求 underlineColor", () => {
  const properties = getFontReadProperties(false);
  assert.equal(properties.includes("underlineColor"), false);

  const font = {};
  Object.defineProperty(font, "underlineColor", {
    get() {
      throw new Error("PropertyNotLoaded");
    },
  });
  assert.equal(getLoadedUnderlineColor(font, false), "#000000");
});

test("支持 WordApiDesktop 时保留下划线颜色", () => {
  assert.equal(getFontReadProperties(true).includes("underlineColor"), true);
  assert.equal(getLoadedUnderlineColor({ underlineColor: "#FF0000" }, true), "#FF0000");
});

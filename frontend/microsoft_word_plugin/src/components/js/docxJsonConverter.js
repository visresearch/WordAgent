/**
 * Microsoft Office Word 文档与 JSON 双向转换工具
 *
 * 基于 Office.js Word API 实现，功能对标 WPS 版本：
 * 1. parseDocxToJSON - 将 Word 文档内容解析为 JSON 格式
 * 2. generateDocxFromJSON - 从 JSON 数据生成 Word 文档
 *
 * JSON schema 数据结构（精简版）：
 * {
 *   paragraphs: [{             // 段落数组
 *     pStyle: [                // 段落样式数组（按顺序）
 *       alignment,             // [0] 对齐: left/center/right/justify
 *       lineSpacing,           // [1] 行间距
 *       indentLeft,            // [2] 左缩进
 *       indentRight,           // [3] 右缩进
 *       indentFirstLine,       // [4] 首行缩进
 *       spaceBefore,           // [5] 段前间距
 *       spaceAfter,            // [6] 段后间距
 *       styleName              // [7] 样式名称
 *     ],
 *     runs: [{                 // 格式块数组
 *       text: string,          // 文字内容
 *       rStyle: [              // 字符样式数组（按顺序）
 *         fontName,            // [0] 字体名称
 *         fontSize,            // [1] 字号
 *         bold,                // [2] 加粗
 *         italic,              // [3] 斜体
 *         underline,           // [4] 下划线: 0=无、1=单线
 *         underlineColor,      // [5] 下划线颜色: #RRGGBB
 *         color,               // [6] 字体颜色: #RRGGBB
 *         highlight,           // [7] 高亮色: 0=无
 *         strikethrough,       // [8] 删除线
 *         superscript,         // [9] 上标
 *         subscript            // [10] 下标
 *       ]
 *     }]
 *   }],
 *   tables: [{                 // 表格数组
 *     rows: number,
 *     columns: number,
 *     tStyle: [tableAlignment],// 表格样式数组
 *     cells: [[{               // 单元格二维数组
 *       text: string,
 *       cStyle: [              // 单元格样式数组
 *         rowSpan,             // [0] 跨行数
 *         colSpan,             // [1] 跨列数
 *         alignment,           // [2] 水平对齐
 *         verticalAlignment    // [3] 垂直对齐
 *       ]
 *     }]]
 *   }],
 *   images: [{...}],          // 图片数组
 *   fields: [],               // 域代码数组
 *   hasTOC: boolean,          // 是否包含目录
 *   styles: {                 // 样式字典（去重）
 *     pS_1: [...],            // 段落样式，键名 pS_N
 *     rS_1: [...],            // 字符样式，键名 rS_N
 *     cS_1: [...],            // 单元格样式，键名 cS_N
 *     tS_1: [...]             // 表格样式，键名 tS_N
 *   }
 * }
 */

/* global Word */

// ============== 样式数组索引常量 ==============

const PSTYLE = {
  ALIGNMENT: 0,
  LINE_SPACING: 1,
  INDENT_LEFT: 2,
  INDENT_RIGHT: 3,
  INDENT_FIRST_LINE: 4,
  SPACE_BEFORE: 5,
  SPACE_AFTER: 6,
  STYLE_NAME: 7,
  LINE_SPACING_RULE: 8,
};

const RSTYLE = {
  FONT_NAME: 0,
  FONT_SIZE: 1,
  BOLD: 2,
  ITALIC: 3,
  UNDERLINE: 4,
  UNDERLINE_COLOR: 5,
  COLOR: 6,
  HIGHLIGHT: 7,
  STRIKETHROUGH: 8,
  SUPERSCRIPT: 9,
  SUBSCRIPT: 10,
};

const CSTYLE = {
  ROW_SPAN: 0,
  COL_SPAN: 1,
  ALIGNMENT: 2,
  VERTICAL_ALIGNMENT: 3,
};

// 默认样式值
const DEFAULT_PSTYLE = ["left", 0, 0, 0, 0, 0, 0, "", 0];
const DEFAULT_RSTYLE = ["", 12, false, false, 0, "#000000", "#000000", 0, false, false, false];
const DEFAULT_CSTYLE = [1, 1, "left", "center"];

// ============== 样式去重与解析 ==============

function createStyleRegistry() {
  return {
    _maps: { p: new Map(), r: new Map(), c: new Map(), t: new Map() },
    _counts: { p: 0, r: 0, c: 0, t: 0 },
    _prefixes: { p: "pS_", r: "rS_", c: "cS_", t: "tS_" },
    styles: {},
  };
}

function registerStyle(registry, type, styleArray) {
  const key = JSON.stringify(styleArray);
  const map = registry._maps[type];
  if (map.has(key)) {
    return map.get(key);
  }
  registry._counts[type]++;
  const id = registry._prefixes[type] + registry._counts[type];
  map.set(key, id);
  registry.styles[id] = styleArray;
  return id;
}

function resolveStyle(styles, ref, defaultStyle) {
  if (!ref) return defaultStyle;
  if (Array.isArray(ref)) return ref;
  if (typeof ref === "string" && styles && styles[ref]) return styles[ref];
  return defaultStyle;
}

function deduplicateStyles(result) {
  const registry = createStyleRegistry();

  if (result.paragraphs) {
    for (const para of result.paragraphs) {
      if (para.pStyle && Array.isArray(para.pStyle)) {
        para.pStyle = registerStyle(registry, "p", para.pStyle);
      }
      if (para.runs) {
        for (const run of para.runs) {
          if (run.rStyle && Array.isArray(run.rStyle)) {
            run.rStyle = registerStyle(registry, "r", run.rStyle);
          }
        }
      }
    }
  }

  if (result.tables) {
    for (const table of result.tables) {
      if (table.tStyle && Array.isArray(table.tStyle)) {
        table.tStyle = registerStyle(registry, "t", table.tStyle);
      }
      if (table.cells) {
        for (const row of table.cells) {
          for (const cell of row) {
            if (cell.cStyle && Array.isArray(cell.cStyle)) {
              cell.cStyle = registerStyle(registry, "c", cell.cStyle);
            }
            if (cell.rStyle && Array.isArray(cell.rStyle)) {
              cell.rStyle = registerStyle(registry, "r", cell.rStyle);
            }
            if (cell.paragraphs) {
              for (const para of cell.paragraphs) {
                if (para.pStyle && Array.isArray(para.pStyle)) {
                  para.pStyle = registerStyle(registry, "p", para.pStyle);
                }
                if (para.runs) {
                  for (const run of para.runs) {
                    if (run.rStyle && Array.isArray(run.rStyle)) {
                      run.rStyle = registerStyle(registry, "r", run.rStyle);
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  result.styles = registry.styles;
  return result;
}

// ============== 格式转换辅助函数 ==============

function makePStyle(
  alignment,
  lineSpacing,
  indentLeft,
  indentRight,
  indentFirstLine,
  spaceBefore,
  spaceAfter,
  styleName
) {
  return [
    alignment,
    lineSpacing,
    indentLeft,
    indentRight,
    indentFirstLine,
    spaceBefore,
    spaceAfter,
    styleName,
  ];
}

function makeRStyle(
  fontName,
  fontSize,
  bold,
  italic,
  underline,
  underlineColor,
  color,
  highlight,
  strikethrough,
  superscript,
  subscript
) {
  return [
    fontName,
    fontSize,
    bold,
    italic,
    underline,
    underlineColor,
    color,
    highlight,
    strikethrough,
    superscript,
    subscript,
  ];
}

function makeCStyle(rowSpan, colSpan, alignment, verticalAlignment) {
  return [rowSpan, colSpan, alignment, verticalAlignment];
}

/**
 * Office.js 对齐枚举 -> 名称
 */
function getAlignmentName(alignment) {
  if (typeof alignment === "string") {
    const lower = alignment.toLowerCase();
    if (["left", "center", "right", "justify", "distributed"].includes(lower)) {
      return lower === "distributed" ? "distribute" : lower;
    }
  }
  const map = {
    Left: "left",
    Center: "center",
    Right: "right",
    Justified: "justify",
    Distributed: "distribute",
    0: "left",
    1: "center",
    2: "right",
    3: "justify",
    4: "distribute",
  };
  return map[alignment] || "left";
}

function getAlignmentValue(alignment) {
  const map = {
    left: "Left",
    center: "Center",
    right: "Right",
    justify: "Justified",
    distribute: "Distributed",
  };
  return map[alignment] || "Left";
}

function getVerticalAlignmentName(alignment) {
  if (typeof alignment === "string") {
    const lower = alignment.toLowerCase();
    if (["top", "center", "bottom"].includes(lower)) return lower;
  }
  const map = { Top: "top", Center: "center", Bottom: "bottom" };
  return map[alignment] || "center";
}

function getVerticalAlignmentValue(alignment) {
  const map = { top: "Top", center: "Center", bottom: "Bottom" };
  return map[alignment] || "Center";
}

/**
 * Office.js 下划线枚举 -> 数值
 */
function getUnderlineValue(underlineType) {
  if (typeof underlineType === "number") return underlineType;
  const map = {
    None: 0,
    Single: 1,
    Double: 3,
    Dotted: 4,
    Thick: 6,
    DottedHeavy: 7,
    Wave: 11,
    WavyHeavy: 27,
  };
  return map[underlineType] || 0;
}

function getUnderlineType(value) {
  if (typeof value === "string") return value;
  const map = {
    0: "None",
    1: "Single",
    3: "Double",
    4: "Dotted",
    6: "Thick",
    7: "DottedHeavy",
    11: "Wave",
    27: "WavyHeavy",
  };
  return map[value] || "None";
}

/**
 * Office.js 高亮颜色枚举 -> 数值
 */
function getHighlightValue(highlightColor) {
  if (typeof highlightColor === "number") return highlightColor;
  const map = {
    NoHighlight: 0,
    Black: 1,
    Blue: 2,
    Turquoise: 3,
    BrightGreen: 4,
    Pink: 5,
    Red: 6,
    Yellow: 7,
    DarkBlue: 9,
    Teal: 10,
    Green: 11,
    Violet: 12,
    DarkRed: 13,
    DarkYellow: 14,
    Gray50: 15,
    Gray25: 16,
  };
  return map[highlightColor] || 0;
}

function getHighlightColor(value) {
  if (typeof value === "string") return value;
  const map = {
    0: null,
    1: "Black",
    2: "Blue",
    3: "Turquoise",
    4: "BrightGreen",
    5: "Pink",
    6: "Red",
    7: "Yellow",
    9: "DarkBlue",
    10: "Teal",
    11: "Green",
    12: "Violet",
    13: "DarkRed",
    14: "DarkYellow",
    15: "Gray50",
    16: "Gray25",
  };
  return map[value] || null;
}

function isEmptyParagraph(para) {
  return !!(para && Array.isArray(para.runs) && para.runs.length === 0);
}

function cleanText(text) {
  if (!text) return "";
  return text
    .replace(/\u0007/g, "")
    .replace(/\f/g, "")
    .replace(/\r$/, "");
}

function cleanCellText(text) {
  if (!text) return "";
  return text.replace(/[\r\n\u0007\u0001]+$/g, "");
}

const MATH_FONT_KEYWORDS = ["cambria math", "dejavu math", "tex gyre", "stix", "latin modern math"];

const MATH_SYMBOL_TO_LATEX = {
  "\u221e": "\\infty",
  "\u2211": "\\sum",
  "\u220f": "\\prod",
  "\u222b": "\\int",
  "\u221a": "\\sqrt",
  "\u00d7": "\\times",
  "\u00f7": "\\div",
  "\u00b1": "\\pm",
  "\u2213": "\\mp",
  "\u2264": "\\le",
  "\u2265": "\\ge",
  "\u2260": "\\ne",
  "\u2248": "\\approx",
  "\u2261": "\\equiv",
  "\u00b7": "\\cdot",
  "\u22c5": "\\cdot",
  "\u03b1": "\\alpha",
  "\u03b2": "\\beta",
  "\u03b3": "\\gamma",
  "\u03b4": "\\delta",
  "\u03b5": "\\epsilon",
  "\u03b8": "\\theta",
  "\u03bb": "\\lambda",
  "\u03bc": "\\mu",
  "\u03c0": "\\pi",
  "\u03c1": "\\rho",
  "\u03c3": "\\sigma",
  "\u03c6": "\\phi",
  "\u03c9": "\\omega",
  "\u0393": "\\Gamma",
  "\u0394": "\\Delta",
  "\u0398": "\\Theta",
  "\u039b": "\\Lambda",
  "\u03a0": "\\Pi",
  "\u03a3": "\\Sigma",
  "\u03a6": "\\Phi",
  "\u03a9": "\\Omega",
  "\u2212": "-",
};

const SUPERSCRIPT_CHAR_MAP = {
  "\u2070": "0", "\u00b9": "1", "\u00b2": "2", "\u00b3": "3", "\u2074": "4",
  "\u2075": "5", "\u2076": "6", "\u2077": "7", "\u2078": "8", "\u2079": "9",
  "\u207a": "+", "\u207b": "-", "\u207c": "=", "\u207d": "(", "\u207e": ")",
  "\u207f": "n", "\u1d43": "a", "\u1d47": "b", "\u1d9c": "c", "\u1d48": "d",
  "\u1d49": "e", "\u1da0": "f", "\u1d4d": "g", "\u02b0": "h", "\u2071": "i",
  "\u02b2": "j", "\u1d4f": "k", "\u02e1": "l", "\u1d50": "m",
  "\u1d52": "o", "\u1d56": "p", "\u02b3": "r", "\u02e2": "s", "\u1d57": "t",
  "\u1d58": "u", "\u1d5b": "v", "\u02b7": "w", "\u02e3": "x", "\u02b8": "y",
  "\u1dbb": "z",
};

const SUBSCRIPT_CHAR_MAP = {
  "\u2080": "0", "\u2081": "1", "\u2082": "2", "\u2083": "3", "\u2084": "4",
  "\u2085": "5", "\u2086": "6", "\u2087": "7", "\u2088": "8", "\u2089": "9",
  "\u208a": "+", "\u208b": "-", "\u208c": "=", "\u208d": "(", "\u208e": ")",
  "\u2090": "a", "\u2091": "e", "\u2092": "o", "\u2093": "x", "\u2094": "schwa",
  "\u2095": "h", "\u2096": "k", "\u2097": "l", "\u2098": "m", "\u2099": "n",
  "\u209a": "p", "\u209b": "s", "\u209c": "t",
};

function isMathFont(fontName) {
  if (!fontName) {
    return false;
  }
  const normalized = String(fontName).toLowerCase();
  return MATH_FONT_KEYWORDS.some((keyword) => normalized.includes(keyword));
}

function containsMathUnicode(text) {
  if (!text) {
    return false;
  }
  return /[\u2200-\u22ff\u27c0-\u27ef\u2980-\u29ff\u2a00-\u2aff\u2070-\u209f]|[\ud835\udc00-\ud835\udfff]/u.test(text);
}

function stripMathDelimiters(text) {
  let value = (text || "").trim();
  if (!value) {
    return "";
  }
  if (value.startsWith("$$") && value.endsWith("$$") && value.length > 4) {
    value = value.slice(2, -2).trim();
  } else if (value.startsWith("$") && value.endsWith("$") && value.length > 2) {
    value = value.slice(1, -1).trim();
  } else if (value.startsWith("\\(") && value.endsWith("\\)") && value.length > 4) {
    value = value.slice(2, -2).trim();
  } else if (value.startsWith("\\[") && value.endsWith("\\]") && value.length > 4) {
    value = value.slice(2, -2).trim();
  }
  return value;
}

function convertScriptCharsToLatex(text, scriptMap, marker) {
  let result = "";
  let buffer = "";

  for (const ch of text) {
    const mapped = scriptMap[ch];
    if (mapped) {
      buffer += mapped;
      continue;
    }

    if (buffer) {
      result += `${marker}{${buffer}}`;
      buffer = "";
    }
    result += ch;
  }

  if (buffer) {
    result += `${marker}{${buffer}}`;
  }

  return result;
}

function replaceMathSymbolsWithLatex(text) {
  let value = text;
  for (const [symbol, latex] of Object.entries(MATH_SYMBOL_TO_LATEX)) {
    value = value.split(symbol).join(latex);
  }
  return value;
}

function repairCommonFormulaPatterns(text) {
  let value = text;

  value = value
    .replace(/\s*\(\s*/g, "(")
    .replace(/\s*\)\s*/g, ")")
    .replace(/\s*\-\s*/g, "-")
    .replace(/\s*=\s*/g, "=")
    .replace(/\s+!/g, "!")
    .replace(/\s*\^\s*/g, "^")
    .replace(/\s*_\s*/g, "_");

  value = value.replace(/([A-Za-z])\(n\)\(([A-Za-z])\)/g, "$1^{(n)}($2)");
  value = value.replace(/\(x-a\)\s*n\b/g, "(x-a)^n");

  if (!/\\sum/.test(value)) {
    value = value.replace(/n=0\s*\\infty/g, "\\sum_{n=0}^{\\infty}");
    value = value.replace(/\bn=0\s*\\infty/g, "\\sum_{n=0}^{\\infty}");
  }

  value = value.replace(/\\sum\s*\{?\s*n\s*=\s*0\s*\}?\s*\^?\s*\\infty/g, "\\sum_{n=0}^{\\infty}");

  if (/f\^\{\(n\)\}\(a\)/.test(value) && /n!/.test(value) && !/\\frac\{/.test(value)) {
    value = value.replace(/f\^\{\(n\)\}\(a\)\s*n!/g, "\\frac{f^{(n)}(a)}{n!}");
  }

  value = value
    .replace(/\(\s*x\s*\)/g, "(x)")
    .replace(/\(\s*a\s*\)/g, "(a)")
    .replace(/\(\s*n\s*\)/g, "(n)")
    .replace(/\s+/g, " ")
    .trim();

  return value;
}

function normalizeFormulaTextToLatex(text) {
  let value = stripMathDelimiters((text || "").replace(/[\r\n\f]+/g, " ").trim());
  if (!value) {
    return "";
  }

  value = value.normalize("NFKD");
  value = replaceMathSymbolsWithLatex(value);
  value = convertScriptCharsToLatex(value, SUPERSCRIPT_CHAR_MAP, "^");
  value = convertScriptCharsToLatex(value, SUBSCRIPT_CHAR_MAP, "_");
  value = repairCommonFormulaPatterns(value);
  value = value.replace(/\s+/g, " ").trim();

  value = value.replace(/\\sum\s*([a-zA-Z]\s*=\s*[^\\\s]+)\s*\\infty/g, "\\sum_{$1}^{\\infty}");
  value = value.replace(/\\sum_\{\s*([a-zA-Z])\s*=\s*([^}]+)\s*\}\^\{\s*\\infty\s*\}/g, "\\sum_{$1=$2}^{\\infty}");

  return value;
}

function normalizeParsedRun(run) {
  if (!run || !run.text) {
    return run;
  }

  const text = run.text;
  const rStyle = run.rStyle || DEFAULT_RSTYLE;
  const fontName = rStyle[RSTYLE.FONT_NAME] || "";
  const hasLatexSyntax = /\\[a-zA-Z]+/.test(text) || /[_^]\{?[^\s]/.test(text) || /^\$\$?[\s\S]+\$\$?$/.test(text.trim());

  if (!hasLatexSyntax && !isMathFont(fontName) && !containsMathUnicode(text)) {
    return run;
  }

  const latexText = normalizeFormulaTextToLatex(text);
  if (!latexText) {
    return run;
  }

  return {
    ...run,
    text: latexText,
    isFormula: true,
    formulaFormat: "latex",
  };
}

// ============== OOXML 解析辅助函数 ==============

const NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
const NS_M = "http://schemas.openxmlformats.org/officeDocument/2006/math";

/**
 * 判断字符是否为 CJK（中日韩）字符
 */
function isCJK(ch) {
  const code = ch.codePointAt(0);
  return (
    (code >= 0x4e00 && code <= 0x9fff) || // CJK 统一汉字
    (code >= 0x3400 && code <= 0x4dbf) || // CJK 扩展A
    (code >= 0x20000 && code <= 0x2a6df) || // CJK 扩展B
    (code >= 0x2a700 && code <= 0x2b73f) || // CJK 扩展C
    (code >= 0x2b740 && code <= 0x2b81f) || // CJK 扩展D
    (code >= 0xf900 && code <= 0xfaff) || // CJK 兼容汉字
    (code >= 0x3000 && code <= 0x303f) || // CJK 符号和标点
    (code >= 0xff00 && code <= 0xffef) || // 全角字符
    (code >= 0x3040 && code <= 0x309f) || // 平假名
    (code >= 0x30a0 && code <= 0x30ff) || // 片假名
    (code >= 0xac00 && code <= 0xd7af) // 韩文音节
  );
}

/**
 * 将混合脚本文本按 CJK / Latin 拆分为多个段，每段使用对应字体
 * 空格和标点跟随相邻的主要脚本
 *
 * @param {string} text - 文本
 * @param {string} fontAscii - 拉丁字符字体
 * @param {string} fontEastAsia - CJK 字符字体
 * @returns {Array<{text: string, font: string}>}
 */
function splitByScript(text, fontAscii, fontEastAsia) {
  if (!text) return [];

  const segments = [];
  let currentText = "";
  let currentIsCJK = null; // null = undetermined (for leading spaces/punctuation)

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];

    if (isCJK(ch)) {
      // CJK character
      if (currentIsCJK === false && currentText) {
        segments.push({ text: currentText, font: fontAscii });
        currentText = "";
      }
      currentIsCJK = true;
      currentText += ch;
    } else if (/[a-zA-Z0-9]/.test(ch)) {
      // Latin alphanumeric
      if (currentIsCJK === true && currentText) {
        segments.push({ text: currentText, font: fontEastAsia });
        currentText = "";
      }
      currentIsCJK = false;
      currentText += ch;
    } else {
      // Space, punctuation, etc. - attach to current segment
      currentText += ch;
    }
  }

  if (currentText) {
    const font =
      currentIsCJK === false ? fontAscii : currentIsCJK === true ? fontEastAsia : fontAscii;
    segments.push({ text: currentText, font });
  }

  return segments;
}

/**
 * 从 OOXML 元素上获取 w: 命名空间属性值
 */
function getWAttr(element, attrName) {
  return element.getAttributeNS(NS_W, attrName) || element.getAttribute("w:" + attrName) || "";
}

/**
 * 从段落 OOXML 中解析 runs（精确获取 Word 内部的格式化文本块边界）
 * 用于解决 getTextRanges 无法按格式拆分文本的问题
 *
 * @param {string} ooxmlString - paragraph.getOoxml() 返回的 OOXML 字符串
 * @returns {Array|null} - runs 数组（含 text 和 rStyle），解析失败时返回 null
 */
function parseRunsFromOoxml(ooxmlString) {
  try {
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(ooxmlString, "application/xml");

    // DEBUG: 输出原始 OOXML 便于排查
    console.log("  OOXML 原始内容（前2000字符）:", ooxmlString.substring(0, 2000));

    // 找到 <w:p> 段落元素
    const pElements = xmlDoc.getElementsByTagNameNS(NS_W, "p");
    if (pElements.length === 0) return null;
    const paragraphEl = pElements[0];

    // === 解析主题字体映射 ===
    const NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main";
    const themeFonts = { majorLatin: "", majorEastAsia: "", minorLatin: "", minorEastAsia: "" };
    try {
      const themeElements = xmlDoc.getElementsByTagNameNS(NS_A, "theme");
      if (themeElements.length > 0) {
        const fontScheme = themeElements[0].getElementsByTagNameNS(NS_A, "fontScheme")[0];
        if (fontScheme) {
          const majorFont = fontScheme.getElementsByTagNameNS(NS_A, "majorFont")[0];
          if (majorFont) {
            const latin = majorFont.getElementsByTagNameNS(NS_A, "latin")[0];
            if (latin) themeFonts.majorLatin = latin.getAttribute("typeface") || "";
            const ea = majorFont.getElementsByTagNameNS(NS_A, "ea")[0];
            if (ea) themeFonts.majorEastAsia = ea.getAttribute("typeface") || "";
          }
          const minorFont = fontScheme.getElementsByTagNameNS(NS_A, "minorFont")[0];
          if (minorFont) {
            const latin = minorFont.getElementsByTagNameNS(NS_A, "latin")[0];
            if (latin) themeFonts.minorLatin = latin.getAttribute("typeface") || "";
            const ea = minorFont.getElementsByTagNameNS(NS_A, "ea")[0];
            if (ea) themeFonts.minorEastAsia = ea.getAttribute("typeface") || "";
          }
        }
      }
    } catch (e) {}
    console.log("  主题字体:", JSON.stringify(themeFonts));

    /**
     * 解析主题字体引用为具体字体名
     */
    function resolveThemeFont(themeRef) {
      if (!themeRef) return "";
      const map = {
        majorHAnsi: themeFonts.majorLatin,
        majorAscii: themeFonts.majorLatin,
        majorEastAsia: themeFonts.majorEastAsia,
        minorHAnsi: themeFonts.minorLatin,
        minorAscii: themeFonts.minorLatin,
        minorEastAsia: themeFonts.minorEastAsia,
      };
      return map[themeRef] || "";
    }

    // === 构建样式继承链：docDefaults → 段落样式的 rPr → run 自身 rPr ===

    /**
     * 从 rPr 元素提取格式属性为对象
     * 同时处理直接字体名和主题字体引用
     */
    function extractRprProps(rPr) {
      if (!rPr) return {};
      const props = {};

      const rFonts = rPr.getElementsByTagNameNS(NS_W, "rFonts")[0];
      if (rFonts) {
        // 直接字体名
        const directAscii = getWAttr(rFonts, "ascii");
        const directEastAsia = getWAttr(rFonts, "eastAsia");
        const directHAnsi = getWAttr(rFonts, "hAnsi");

        // 主题字体引用
        const themeAscii = getWAttr(rFonts, "asciiTheme");
        const themeEastAsia = getWAttr(rFonts, "eastAsiaTheme");
        const themeHAnsi = getWAttr(rFonts, "hAnsiTheme");

        // 直接字体名优先，否则从主题解析
        props.fontAscii = directAscii || resolveThemeFont(themeAscii) || "";
        props.fontEastAsia = directEastAsia || resolveThemeFont(themeEastAsia) || "";
        props.fontHAnsi = directHAnsi || resolveThemeFont(themeHAnsi) || "";
      }

      const sz = rPr.getElementsByTagNameNS(NS_W, "sz")[0];
      if (sz) {
        const val = getWAttr(sz, "val");
        if (val) props.fontSize = parseInt(val, 10) / 2;
      }
      if (!props.fontSize) {
        const szCs = rPr.getElementsByTagNameNS(NS_W, "szCs")[0];
        if (szCs) {
          const val = getWAttr(szCs, "val");
          if (val) props.fontSize = parseInt(val, 10) / 2;
        }
      }

      const bEl = rPr.getElementsByTagNameNS(NS_W, "b")[0];
      if (bEl) {
        const val = getWAttr(bEl, "val");
        props.bold = val !== "0" && val !== "false";
      }

      const iEl = rPr.getElementsByTagNameNS(NS_W, "i")[0];
      if (iEl) {
        const val = getWAttr(iEl, "val");
        props.italic = val !== "0" && val !== "false";
      }

      const uEl = rPr.getElementsByTagNameNS(NS_W, "u")[0];
      if (uEl) {
        const uVal = getWAttr(uEl, "val");
        const uMap = {
          single: 1,
          double: 3,
          dotted: 4,
          thick: 6,
          dottedHeavy: 7,
          wave: 11,
          wavyHeavy: 27,
        };
        props.underline = uMap[uVal] || (uVal && uVal !== "none" ? 1 : 0);
        const uColor = getWAttr(uEl, "color");
        if (uColor && uColor !== "auto") props.underlineColor = "#" + uColor;
      }

      const colorEl = rPr.getElementsByTagNameNS(NS_W, "color")[0];
      if (colorEl) {
        const colorVal = getWAttr(colorEl, "val");
        if (colorVal && colorVal !== "auto") props.color = "#" + colorVal;
      }

      const hlEl = rPr.getElementsByTagNameNS(NS_W, "highlight")[0];
      if (hlEl) {
        const hlVal = getWAttr(hlEl, "val");
        const hlMap = {
          black: 1,
          blue: 2,
          cyan: 3,
          green: 4,
          magenta: 5,
          red: 6,
          yellow: 7,
          darkBlue: 9,
          teal: 10,
          darkGreen: 11,
          darkMagenta: 12,
          darkRed: 13,
          darkYellow: 14,
          darkGray: 15,
          lightGray: 16,
        };
        props.highlight = hlMap[hlVal] || 0;
      }

      const strikeEl = rPr.getElementsByTagNameNS(NS_W, "strike")[0];
      if (strikeEl) {
        const val = getWAttr(strikeEl, "val");
        props.strikethrough = val !== "0" && val !== "false";
      }

      const vertAlignEl = rPr.getElementsByTagNameNS(NS_W, "vertAlign")[0];
      if (vertAlignEl) {
        const val = getWAttr(vertAlignEl, "val");
        if (val === "superscript") props.superscript = true;
        if (val === "subscript") props.subscript = true;
      }

      return props;
    }

    // 1. 从 <w:docDefaults> 提取默认 run 属性
    let defaultProps = {};
    try {
      const docDefaults = xmlDoc.getElementsByTagNameNS(NS_W, "docDefaults")[0];
      if (docDefaults) {
        const rPrDefault = docDefaults.getElementsByTagNameNS(NS_W, "rPrDefault")[0];
        if (rPrDefault) {
          const rPr = rPrDefault.getElementsByTagNameNS(NS_W, "rPr")[0];
          defaultProps = extractRprProps(rPr);
        }
      }
    } catch (e) {}

    // 2. 获取段落应用的样式名，从 <w:styles> 中找到该样式的 rPr
    let styleProps = {};
    try {
      const pPr = paragraphEl.getElementsByTagNameNS(NS_W, "pPr")[0];
      if (pPr) {
        // 段落样式名
        const pStyleEl = pPr.getElementsByTagNameNS(NS_W, "pStyle")[0];
        const paraStyleId = pStyleEl ? getWAttr(pStyleEl, "val") : "";

        // 段落自身 pPr 里的 rPr（段落级默认 run 格式）
        const pPrRpr = pPr.getElementsByTagNameNS(NS_W, "rPr")[0];
        if (pPrRpr) {
          styleProps = { ...styleProps, ...extractRprProps(pPrRpr) };
        }

        // 从 <w:styles> 中查找样式定义
        if (paraStyleId) {
          const stylesEl = xmlDoc.getElementsByTagNameNS(NS_W, "styles")[0];
          if (stylesEl) {
            const styleEls = stylesEl.getElementsByTagNameNS(NS_W, "style");
            for (let s = 0; s < styleEls.length; s++) {
              const sId = getWAttr(styleEls[s], "styleId");
              if (sId === paraStyleId) {
                // 样式中的 rPr
                const sRpr = styleEls[s].getElementsByTagNameNS(NS_W, "rPr")[0];
                if (sRpr) {
                  // 样式定义的优先级低于段落 pPr 中的 rPr，先设置样式，再覆盖
                  const sProps = extractRprProps(sRpr);
                  styleProps = { ...sProps, ...styleProps };
                }

                // 如果样式有 basedOn，递归查找父样式
                const basedOnEl = styleEls[s].getElementsByTagNameNS(NS_W, "basedOn")[0];
                if (basedOnEl) {
                  const baseId = getWAttr(basedOnEl, "val");
                  if (baseId) {
                    for (let b = 0; b < styleEls.length; b++) {
                      if (getWAttr(styleEls[b], "styleId") === baseId) {
                        const baseRpr = styleEls[b].getElementsByTagNameNS(NS_W, "rPr")[0];
                        if (baseRpr) {
                          const baseProps = extractRprProps(baseRpr);
                          // 父样式优先级最低
                          styleProps = { ...baseProps, ...styleProps };
                        }
                        break;
                      }
                    }
                  }
                }
                break;
              }
            }
          }
        }
      }
    } catch (e) {}

    // 3. 合并继承链：docDefaults → 样式 → (run自身在processRunElement中覆盖)
    const inheritedProps = { ...defaultProps, ...styleProps };
    console.log("  OOXML 继承属性:", JSON.stringify(inheritedProps));

    const runs = [];

    function pushNormalizedRun(run) {
      const normalized = normalizeParsedRun(run);
      if (!normalized || !normalized.text) {
        return;
      }
      runs.push(normalized);
    }

    function processMathElement(mathElement) {
      if (!mathElement) return;
      const mTextElements = mathElement.getElementsByTagNameNS(NS_M, "t");
      let rawMathText = "";
      for (let i = 0; i < mTextElements.length; i++) {
        rawMathText += mTextElements[i].textContent || "";
      }
      rawMathText = cleanCellText(rawMathText);
      if (!rawMathText) return;

      const latexText = normalizeFormulaTextToLatex(rawMathText) || rawMathText;
      pushNormalizedRun({
        text: latexText,
        rStyle: makeRStyle(
          "Cambria Math",
          12,
          false,
          true,
          0,
          "#000000",
          "#000000",
          0,
          false,
          false,
          false
        ),
        isFormula: true,
        formulaFormat: "latex",
      });
    }

    // 遍历段落的子节点，处理 w:r 和 w:hyperlink 中的 w:r
    function processRunElement(wRun) {
      let text = "";
      // 收集 <w:t> 文本
      const tElements = wRun.getElementsByTagNameNS(NS_W, "t");
      for (let j = 0; j < tElements.length; j++) {
        text += tElements[j].textContent || "";
      }
      // 收集 <m:t> 文本（公式 OMML）
      const mTextElements = wRun.getElementsByTagNameNS(NS_M, "t");
      for (let j = 0; j < mTextElements.length; j++) {
        text += mTextElements[j].textContent || "";
      }
      // 收集 <w:tab> 制表符
      const tabElements = wRun.getElementsByTagNameNS(NS_W, "tab");
      if (tabElements.length > 0) {
        text += "\t";
      }

      // 清理文本
      text = text.replace(/[\r\n\f\u0007]+$/g, "");
      if (!text) return;

      // 读取 run 自身格式属性
      const rPr = wRun.getElementsByTagNameNS(NS_W, "rPr")[0];
      const runProps = extractRprProps(rPr);

      // 合并：继承属性 → run 自身属性（run 自身优先）
      const merged = { ...inheritedProps, ...runProps };

      // 获取不同脚本的字体
      const fontAscii = merged.fontAscii || merged.fontHAnsi || "";
      const fontEastAsia = merged.fontEastAsia || "";
      const baseFontProps = {
        fontSize: merged.fontSize || 12,
        bold: !!merged.bold,
        italic: !!merged.italic,
        underline: merged.underline || 0,
        underlineColor: merged.underlineColor || "#000000",
        color: merged.color || "#000000",
        highlight: merged.highlight || 0,
        strikethrough: !!merged.strikethrough,
        superscript: !!merged.superscript,
        subscript: !!merged.subscript,
      };

      // 如果中英文字体不同且文本包含混合脚本，按脚本拆分 run
      if (fontAscii && fontEastAsia && fontAscii !== fontEastAsia) {
        const segments = splitByScript(text, fontAscii, fontEastAsia);
        for (const seg of segments) {
          pushNormalizedRun({
            text: seg.text,
            rStyle: makeRStyle(
              seg.font,
              baseFontProps.fontSize,
              baseFontProps.bold,
              baseFontProps.italic,
              baseFontProps.underline,
              baseFontProps.underlineColor,
              baseFontProps.color,
              baseFontProps.highlight,
              baseFontProps.strikethrough,
              baseFontProps.superscript,
              baseFontProps.subscript
            ),
          });
        }
      } else {
        // 字体相同或只有一种，直接使用
        const fontName = fontAscii || fontEastAsia || "";
        pushNormalizedRun({
          text,
          rStyle: makeRStyle(
            fontName,
            baseFontProps.fontSize,
            baseFontProps.bold,
            baseFontProps.italic,
            baseFontProps.underline,
            baseFontProps.underlineColor,
            baseFontProps.color,
            baseFontProps.highlight,
            baseFontProps.strikethrough,
            baseFontProps.superscript,
            baseFontProps.subscript
          ),
        });
      }
    }

    // 遍历段落子节点
    for (let i = 0; i < paragraphEl.childNodes.length; i++) {
      const child = paragraphEl.childNodes[i];
      if (!child.localName) continue;

      if (child.localName === "r" && child.namespaceURI === NS_W) {
        processRunElement(child);
      } else if ((child.localName === "oMath" || child.localName === "oMathPara") && child.namespaceURI === NS_M) {
        processMathElement(child);
      } else if (child.localName === "hyperlink") {
        // 超链接内也包含 w:r
        const innerRuns = child.getElementsByTagNameNS(NS_W, "r");
        for (let j = 0; j < innerRuns.length; j++) {
          processRunElement(innerRuns[j]);
        }
      }
    }

    // 合并相邻相同格式的 runs
    if (runs.length > 1) {
      const merged = [runs[0]];
      for (let i = 1; i < runs.length; i++) {
        const prev = merged[merged.length - 1];
        const curr = runs[i];
        if (
          JSON.stringify(prev.rStyle) === JSON.stringify(curr.rStyle) &&
          prev.isFormula === curr.isFormula &&
          prev.formulaFormat === curr.formulaFormat
        ) {
          prev.text += curr.text;
        } else {
          merged.push(curr);
        }
      }
      return merged.length > 0 ? merged : null;
    }

    return runs.length > 0 ? runs : null;
  } catch (e) {
    console.log("OOXML runs 解析失败:", e);
    return null;
  }
}

// ============== 解析函数 ==============

/**
 * 解析 Word 文档内容为 JSON（异步，基于 Office.js API）
 *
 * @param {string} scope - 'selection' 解析选区, 'body' 解析全文
 * @param {number} [startParaIndex] - 可选，起始全文段落索引（0-based），
 *   传入后走快速路径：O(1) 定位仅解析指定范围段落，忽略 scope 参数
 * @param {number} [endParaIndex] - 可选，结束全文段落索引（0-based，含），
 *   省略时默认等于 startParaIndex（即只解析单段）；-1 表示解析到文档末尾
 * @returns {Promise<Object>} - JSON 数据或错误对象
 */
async function parseDocxToJSON(scope = "selection", startParaIndex, endParaIndex) {
  try {
    return await Word.run(async (context) => {
      // ========== 快速路径：按 paraIndex 范围解析 ==========
      if (startParaIndex !== undefined && startParaIndex !== null) {
        // endParaIndex 省略时默认等于 startParaIndex（单段）
        if (endParaIndex === undefined || endParaIndex === null) {
          endParaIndex = startParaIndex;
        }

        const allParas = context.document.body.paragraphs;
        allParas.load("items");
        await context.sync();

        // endParaIndex === -1 表示解析到文档末尾
        if (endParaIndex === -1) {
          endParaIndex = allParas.items.length - 1;
        }

        // 超过文档总段落数时，自动截断到最后一个段落
        if (endParaIndex >= allParas.items.length) {
          endParaIndex = allParas.items.length - 1;
        }

        if (startParaIndex < 0 || startParaIndex >= allParas.items.length) {
          return {
            error: `startParaIndex ${startParaIndex} 超出范围，文档共 ${allParas.items.length} 段`,
          };
        }
        if (endParaIndex < startParaIndex) {
          return {
            error: `endParaIndex ${endParaIndex} 无效（startParaIndex=${startParaIndex}，文档共 ${allParas.items.length} 段）`,
          };
        }

        // 批量 load 范围内所有段落（完整属性）
        for (let idx = startParaIndex; idx <= endParaIndex; idx++) {
          allParas.items[idx].load(
            "text,alignment,lineSpacing,firstLineIndent,leftIndent,rightIndent,spaceBefore,spaceAfter,style,isListItem,tableNestingLevel,lineUnitBefore,lineUnitAfter,outlineLevel"
          );
        }
        // 范围外段落只需加载 tableNestingLevel（用于全文表格映射）
        for (let idx = 0; idx < allParas.items.length; idx++) {
          if (idx < startParaIndex || idx > endParaIndex) {
            allParas.items[idx].load("tableNestingLevel");
          }
        }
        await context.sync();

        const rangeResult = { paragraphs: [], tables: [], images: [], fields: [] };

        // 检测范围内的表格段落范围（连续 tableNestingLevel > 0 的段落组）
        const tableParagraphRanges = [];
        {
          let currentTableRange = null;
          for (let idx = startParaIndex; idx <= endParaIndex; idx++) {
            if (allParas.items[idx].tableNestingLevel > 0) {
              if (!currentTableRange) {
                currentTableRange = { start: idx, end: idx };
              } else {
                currentTableRange.end = idx;
              }
            } else {
              if (currentTableRange) {
                tableParagraphRanges.push(currentTableRange);
                currentTableRange = null;
              }
            }
          }
          if (currentTableRange) tableParagraphRanges.push(currentTableRange);
        }

        // 如果范围内包含表格，加载 body.tables 并解析
        if (tableParagraphRanges.length > 0) {
          // 确定全文所有表格段落范围，用于与 body.tables 建立顺序对应
          const allTableParaRanges = [];
          {
            let cur = null;
            for (let i = 0; i < allParas.items.length; i++) {
              if (allParas.items[i].tableNestingLevel > 0) {
                if (!cur) { cur = { start: i, end: i }; } else { cur.end = i; }
              } else {
                if (cur) { allTableParaRanges.push(cur); cur = null; }
              }
            }
            if (cur) allTableParaRanges.push(cur);
          }

          const bodyTables = context.document.body.tables;
          bodyTables.load("items");
          await context.sync();

          // 解析范围内命中的表格
          for (const tpr of tableParagraphRanges) {
            // 找到此表格段落范围对应的 body.tables 索引
            const tableIdx = allTableParaRanges.findIndex(r => r.start === tpr.start && r.end === tpr.end);
            if (tableIdx < 0 || tableIdx >= bodyTables.items.length) continue;

            const table = bodyTables.items[tableIdx];
            table.load("rowCount,values,alignment");
            table.rows.load("items");
            await context.sync();

            const tableData = {
              rows: table.rowCount,
              columns: 0,
              cells: [],
              tStyle: [getAlignmentName(table.alignment)],
              paraIndex: tpr.start,
              endParaIndex: tpr.end,
            };

            const tableRows = table.rows;

            // 捕获行高
            const rowHeights = [];
            for (const row of tableRows.items) {
              row.load("cellCount,preferredHeight");
              row.cells.load("items");
              const h = row.preferredHeight || 0;
              rowHeights.push([h, h > 0 ? 1 : 0]);
            }
            await context.sync();
            if (rowHeights.some(h => h[0] > 0)) {
              tableData.rowHeights = rowHeights;
            }

            // 加载单元格属性
            for (const row of tableRows.items) {
              for (const cell of row.cells.items) {
                cell.load("columnWidth,rowIndex,cellIndex,verticalAlignment,width");
                cell.body.load("text");
                cell.body.paragraphs.load("items");
              }
            }
            await context.sync();

            // 捕获列宽
            try {
              const firstRow = tableRows.items[0];
              if (firstRow && firstRow.cells.items.length > 0) {
                const columnWidths = firstRow.cells.items.map(c => c.columnWidth || c.width || 0);
                if (columnWidths.some(w => w > 0)) {
                  tableData.columnWidths = columnWidths;
                }
              }
            } catch (e) {}

            // 加载段落详情
            for (const row of tableRows.items) {
              for (const cell of row.cells.items) {
                for (const para of cell.body.paragraphs.items) {
                  para.load("text,alignment,lineSpacing,firstLineIndent,leftIndent,rightIndent,spaceBefore,spaceAfter");
                }
              }
            }
            await context.sync();

            // 解析单元格
            for (const row of tableRows.items) {
              const rowData = [];
              if (row.cells.items.length > tableData.columns) {
                tableData.columns = row.cells.items.length;
              }

              for (const cell of row.cells.items) {
                const cellText = cleanText(cell.body.text || "");
                const cellParas = cell.body.paragraphs;

                const paragraphsData = [];
                for (const para of cellParas.items) {
                  const paraText = cleanText(para.text || "");
                  if (!paraText) continue;

                  const inlineRanges = para.getTextRanges(["\t", "\n"], true);
                  inlineRanges.load("items");
                  await context.sync();

                  for (const ir of inlineRanges.items) {
                    ir.load("text");
                    ir.font.load("name,size,bold,italic,underline,color,highlightColor,strikeThrough,superscript,subscript");
                  }
                  await context.sync();

                  const cellRuns = [];
                  let lastFmtKey = null;
                  let curRun = null;
                  for (const ir of inlineRanges.items) {
                    const t = ir.text || "";
                    if (!t || t.match(/^[\r\n\u0007]$/)) continue;
                    const font = ir.font;
                    const fmtKey = `${font.name}_${font.size}_${font.bold}_${font.italic}_${font.color}_${font.highlightColor}`;
                    if (fmtKey === lastFmtKey && curRun) {
                      curRun.text += t;
                    } else {
                      if (curRun && curRun.text) {
                        const normalizedRun = normalizeParsedRun(curRun);
                        if (normalizedRun && normalizedRun.text) {
                          cellRuns.push(normalizedRun);
                        }
                      }
                      curRun = {
                        text: t,
                        rStyle: makeRStyle(
                          font.name || "", font.size || 12,
                          font.bold === true, font.italic === true,
                          getUnderlineValue(font.underline), "#000000",
                          font.color || "#000000", getHighlightValue(font.highlightColor),
                          font.strikeThrough === true, font.superscript === true, font.subscript === true
                        ),
                      };
                      lastFmtKey = fmtKey;
                    }
                  }
                  if (curRun && curRun.text) {
                    const normalizedRun = normalizeParsedRun(curRun);
                    if (normalizedRun && normalizedRun.text) {
                      cellRuns.push(normalizedRun);
                    }
                  }

                  if (cellRuns.length > 0) {
                    paragraphsData.push({
                      text: paraText,
                      pStyle: makePStyle(
                        getAlignmentName(para.alignment), para.lineSpacing || 0,
                        para.leftIndent || 0, para.rightIndent || 0,
                        para.firstLineIndent || 0, para.spaceBefore || 0,
                        para.spaceAfter || 0, ""
                      ),
                      runs: cellRuns,
                    });
                  }
                }

                // 获取 cell rStyle
                let cellRStyle = undefined;
                try {
                  if (cellParas.items.length > 0) {
                    const pFont = cellParas.items[0].font;
                    pFont.load("name,size,bold,italic,underline,color,highlightColor,strikeThrough,superscript,subscript");
                    await context.sync();
                    cellRStyle = makeRStyle(
                      pFont.name || "", pFont.size || 12,
                      pFont.bold === true, pFont.italic === true,
                      getUnderlineValue(pFont.underline), "#000000",
                      pFont.color || "#000000", getHighlightValue(pFont.highlightColor),
                      pFont.strikeThrough === true, pFont.superscript === true, pFont.subscript === true
                    );
                  }
                } catch (e) {}

                rowData.push({
                  text: cellText,
                  paragraphs: paragraphsData.length > 0 ? paragraphsData : undefined,
                  rStyle: cellRStyle,
                  cStyle: makeCStyle(
                    1, 1,
                    getAlignmentName(cellParas.items.length > 0 ? cellParas.items[0].alignment : "Left"),
                    getVerticalAlignmentName(cell.verticalAlignment)
                  ),
                });
              }
              tableData.cells.push(rowData);
            }

            rangeResult.tables.push(tableData);
          }
        }

        for (let idx = startParaIndex; idx <= endParaIndex; idx++) {
          const para = allParas.items[idx];

          // 表格内段落
          if (para.tableNestingLevel > 0) {
            rangeResult.paragraphs.push({ pStyle: "", runs: [], paraIndex: idx, inTable: true });
            continue;
          }

          const paraText = cleanText(para.text || "");

          // 空段落
          if (!paraText || paraText.match(/^[\r\n\f\u0007]*$/)) {
            rangeResult.paragraphs.push({ pStyle: "", runs: [], paraIndex: idx });
            continue;
          }

          let styleName = "";
          try {
            styleName = para.style || "";
          } catch (e) {}

          // 解析 runs（OOXML 优先）
          let runs = null;
          try {
            const ooxmlResult = para.getOoxml();
            await context.sync();
            runs = parseRunsFromOoxml(ooxmlResult.value);
          } catch (e) {}

          if (!runs) {
            runs = [];
            const inlineRanges = para.getTextRanges(["\t", "\n"], true);
            inlineRanges.load("items");
            await context.sync();
            for (const ir of inlineRanges.items) {
              ir.load("text");
              ir.font.load(
                "name,size,bold,italic,underline,underlineColor,color,highlightColor,strikeThrough,superscript,subscript"
              );
            }
            await context.sync();
            let lastFormatKey = null;
            let currentRun = null;
            for (const ir of inlineRanges.items) {
              const t = ir.text || "";
              if (!t || t.match(/^[\r\n\f\u0007]+$/)) continue;
              const font = ir.font;
              const formatKey = [
                font.name,
                font.size,
                font.bold,
                font.italic,
                font.underline,
                font.color,
                font.highlightColor,
                font.strikeThrough,
                font.superscript,
                font.subscript,
              ].join("|");
              if (formatKey === lastFormatKey && currentRun) {
                currentRun.text += t;
              } else {
                if (currentRun && currentRun.text) {
                  const normalizedRun = normalizeParsedRun(currentRun);
                  if (normalizedRun && normalizedRun.text) {
                    runs.push(normalizedRun);
                  }
                }
                currentRun = {
                  text: t,
                  rStyle: makeRStyle(
                    font.name || "",
                    font.size || 12,
                    font.bold === true,
                    font.italic === true,
                    getUnderlineValue(font.underline),
                    font.underlineColor || "#000000",
                    font.color || "#000000",
                    getHighlightValue(font.highlightColor),
                    font.strikeThrough === true,
                    font.superscript === true,
                    font.subscript === true
                  ),
                };
                lastFormatKey = formatKey;
              }
            }
            if (currentRun && currentRun.text) {
              const normalizedRun = normalizeParsedRun(currentRun);
              if (normalizedRun && normalizedRun.text) {
                runs.push(normalizedRun);
              }
            }
          }

          if (!runs || runs.length === 0) {
            runs = [];
          }

          rangeResult.paragraphs.push({
            pStyle: makePStyle(
              getAlignmentName(para.alignment),
              para.lineSpacing || 0,
              para.leftIndent || 0,
              para.rightIndent || 0,
              para.firstLineIndent || 0,
              para.spaceBefore || 0,
              para.spaceAfter || 0,
              styleName
            ),
            runs: runs,
            paraIndex: idx,
          });
        }

        return deduplicateStyles(rangeResult);
      }

      // ========== 常规路径：解析选区或全文 ==========
      const range = scope === "body" ? context.document.body : context.document.getSelection();

      // 加载段落和表格
      const paragraphs = range.paragraphs;
      paragraphs.load("items");
      const tables = range.tables;
      tables.load("items");
      const inlinePictures = range.inlinePictures;
      inlinePictures.load("items");
      const fields = range.fields;
      fields.load("items");

      await context.sync();

      const result = {
        paragraphs: [],
        tables: [],
        images: [],
        fields: [],
      };

      // === 解析域代码 ===
      try {
        if (fields.items && fields.items.length > 0) {
          for (const field of fields.items) {
            field.load("type,code");
            field.result.load("text");
          }
          await context.sync();

          for (const field of fields.items) {
            const fieldCode = field.code || "";
            result.fields.push({
              type: field.type,
              code: fieldCode.trim(),
            });
            if (fieldCode.toUpperCase().includes("TOC")) {
              result.hasTOC = true;
              result.tocFieldCode = fieldCode.trim();
            }
          }
        }
      } catch (e) {
        // fields API 可能不可用
      }

      // === 收集表格范围用于段落排除 ===
      const tableRangesInfo = [];
      if (tables.items && tables.items.length > 0) {
        for (const table of tables.items) {
          table.load("rowCount,values,alignment");
          table.rows.load("items");
        }
        await context.sync();

        for (const table of tables.items) {
          const tableRows = table.rows;
          for (const row of tableRows.items) {
            row.load("cellCount,preferredHeight");
            row.cells.load("items");
          }
        }
        await context.sync();

        // 解析每个表格
        for (const table of tables.items) {
          const tableData = {
            rows: table.rowCount,
            columns: 0,
            cells: [],
            tStyle: [getAlignmentName(table.alignment)],
          };

          // 捕获行高
          const rowHeights = [];
          for (const row of table.rows.items) {
            const h = row.preferredHeight || 0;
            rowHeights.push([h, h > 0 ? 1 : 0]);
          }
          if (rowHeights.some(h => h[0] > 0)) {
            tableData.rowHeights = rowHeights;
          }

          const tableRows = table.rows;
          for (const row of tableRows.items) {
            for (const cell of row.cells.items) {
              cell.load("columnWidth,rowIndex,cellIndex,verticalAlignment,width");
              cell.body.load("text");
              const cellParas = cell.body.paragraphs;
              cellParas.load("items");
            }
          }
          await context.sync();

          // 加载每个单元格中段落的详细信息
          for (const row of tableRows.items) {
            for (const cell of row.cells.items) {
              const cellParas = cell.body.paragraphs;
              for (const para of cellParas.items) {
                para.load(
                  "text,alignment,lineSpacing,firstLineIndent,leftIndent,rightIndent,spaceBefore,spaceAfter,style,lineUnitBefore,lineUnitAfter"
                );
                const runs = para.getTextRanges([" "], false);
                runs.load("items");
              }
            }
          }
          await context.sync();

          // 捕获列宽（从第一行的单元格获取）
          try {
            const firstRow = tableRows.items[0];
            if (firstRow && firstRow.cells.items.length > 0) {
              const columnWidths = firstRow.cells.items.map(c => c.columnWidth || c.width || 0);
              if (columnWidths.some(w => w > 0)) {
                tableData.columnWidths = columnWidths;
              }
            }
          } catch (e) {}

          for (const row of tableRows.items) {
            const rowData = [];
            if (row.cells.items.length > tableData.columns) {
              tableData.columns = row.cells.items.length;
            }

            for (const cell of row.cells.items) {
              const cellText = cleanText(cell.body.text || "");
              const cellParas = cell.body.paragraphs;

              // 解析单元格段落和 runs
              const paragraphsData = [];
              for (const para of cellParas.items) {
                const paraText = cleanText(para.text || "");
                if (!paraText) continue;

                // 加载 runs
                const inlineRanges = para.getTextRanges(["\t", "\n"], true);
                inlineRanges.load("items");
                await context.sync();

                for (const ir of inlineRanges.items) {
                  ir.load("text");
                  ir.font.load(
                    "name,size,bold,italic,underline,color,highlightColor,strikeThrough,superscript,subscript"
                  );
                }
                await context.sync();

                const runs = [];
                let lastFormatKey = null;
                let currentRun = null;

                for (const ir of inlineRanges.items) {
                  const t = ir.text || "";
                  if (!t || t.match(/^[\r\n\u0007]$/)) continue;

                  const font = ir.font;
                  const formatKey = `${font.name}_${font.size}_${font.bold}_${font.italic}_${font.color}_${font.highlightColor}`;

                  if (formatKey === lastFormatKey && currentRun) {
                    currentRun.text += t;
                  } else {
                    if (currentRun && currentRun.text) {
                      const normalizedRun = normalizeParsedRun(currentRun);
                      if (normalizedRun && normalizedRun.text) {
                        runs.push(normalizedRun);
                      }
                    }
                    currentRun = {
                      text: t,
                      rStyle: makeRStyle(
                        font.name || "",
                        font.size || 12,
                        font.bold === true,
                        font.italic === true,
                        getUnderlineValue(font.underline),
                        "#000000",
                        font.color || "#000000",
                        getHighlightValue(font.highlightColor),
                        font.strikeThrough === true,
                        font.superscript === true,
                        font.subscript === true
                      ),
                    };
                    lastFormatKey = formatKey;
                  }
                }
                if (currentRun && currentRun.text) {
                  const normalizedRun = normalizeParsedRun(currentRun);
                  if (normalizedRun && normalizedRun.text) {
                    runs.push(normalizedRun);
                  }
                }

                if (runs.length > 0) {
                  paragraphsData.push({
                    text: paraText,
                    pStyle: makePStyle(
                      getAlignmentName(para.alignment),
                      para.lineSpacing || 0,
                      para.leftIndent || 0,
                      para.rightIndent || 0,
                      para.firstLineIndent || 0,
                      para.spaceBefore || 0,
                      para.spaceAfter || 0,
                      ""
                    ),
                    runs: runs,
                  });
                }
              }

              // 获取单元格级别字体信息作为 rStyle（取第一个段落的字体）
              let cellRStyle = undefined;
              try {
                if (cellParas.items.length > 0) {
                  const firstPara = cellParas.items[0];
                  const pFont = firstPara.font;
                  pFont.load("name,size,bold,italic,underline,color,highlightColor,strikeThrough,superscript,subscript");
                  await context.sync();
                  cellRStyle = makeRStyle(
                    pFont.name || "",
                    pFont.size || 12,
                    pFont.bold === true,
                    pFont.italic === true,
                    getUnderlineValue(pFont.underline),
                    "#000000",
                    pFont.color || "#000000",
                    getHighlightValue(pFont.highlightColor),
                    pFont.strikeThrough === true,
                    pFont.superscript === true,
                    pFont.subscript === true
                  );
                }
              } catch (e) {}

              rowData.push({
                text: cellText,
                paragraphs: paragraphsData.length > 0 ? paragraphsData : undefined,
                rStyle: cellRStyle,
                cStyle: makeCStyle(
                  1,
                  1,
                  getAlignmentName(
                    cellParas.items.length > 0 ? cellParas.items[0].alignment : "Left"
                  ),
                  getVerticalAlignmentName(cell.verticalAlignment)
                ),
              });
            }
            tableData.cells.push(rowData);
          }

          result.tables.push(tableData);
          tableRangesInfo.push(table);
        }
      }

      // === 解析图片 ===
      try {
        if (inlinePictures.items && inlinePictures.items.length > 0) {
          for (const pic of inlinePictures.items) {
            pic.load("width,height,altTextTitle,altTextDescription");
          }
          await context.sync();

          for (const pic of inlinePictures.items) {
            result.images.push({
              type: "inline",
              width: pic.width || 100,
              height: pic.height || 100,
              altText: pic.altTextTitle || pic.altTextDescription || "",
              placeholder: "[图片]",
            });
          }
        }
      } catch (e) {
        // inlinePictures API 可能不可用
      }

      // === 解析段落 ===
      // 始终从 body.paragraphs 获取段落，数组下标即全文索引
      const bodyParas = context.document.body.paragraphs;
      bodyParas.load("items");
      await context.sync();

      if (bodyParas.items && bodyParas.items.length > 0) {
        // 选区模式：确定哪些 body 段落在选区内
        let inSelectionSet = null; // null 表示全选（body 模式）
        if (scope !== "body") {
          const selRange = context.document.getSelection();
          const comparisons = bodyParas.items.map((bp) =>
            bp.getRange("Whole").compareLocationWith(selRange)
          );
          await context.sync();
          inSelectionSet = new Set();
          for (let i = 0; i < comparisons.length; i++) {
            const v = comparisons[i].value;
            // Inside / Equal / InsideStart / InsideEnd = 段落落在选区内
            if (v === "Inside" || v === "Equal" || v === "InsideStart" || v === "InsideEnd") {
              inSelectionSet.add(i);
            }
          }
        }

        for (const para of bodyParas.items) {
          para.load(
            "text,alignment,lineSpacing,firstLineIndent,leftIndent,rightIndent,spaceBefore,spaceAfter,style,isListItem,tableNestingLevel,lineUnitBefore,lineUnitAfter,outlineLevel"
          );
        }
        await context.sync();

        // 额外加载 listItem、font、range 等调试属性
        for (const para of bodyParas.items) {
          try {
            if (para.isListItem) {
              para.listItem.load("level,listString,siblingIndex");
            }
          } catch (e) {}
          try {
            para.font.load("name,size,bold,italic,underline,color,highlightColor");
          } catch (e) {}
        }
        try {
          await context.sync();
        } catch (e) {}

        // === 计算表格 paraIndex / endParaIndex ===
        // 通过 tableNestingLevel 找到连续的表格段落范围，按顺序映射到 result.tables
        if (result.tables.length > 0) {
          const tableParagraphRanges = [];
          let currentTableRange = null;
          for (let i = 0; i < bodyParas.items.length; i++) {
            if (bodyParas.items[i].tableNestingLevel > 0) {
              if (!currentTableRange) {
                currentTableRange = { start: i, end: i };
              } else {
                currentTableRange.end = i;
              }
            } else {
              if (currentTableRange) {
                tableParagraphRanges.push(currentTableRange);
                currentTableRange = null;
              }
            }
          }
          if (currentTableRange) tableParagraphRanges.push(currentTableRange);

          for (let ti = 0; ti < result.tables.length && ti < tableParagraphRanges.length; ti++) {
            result.tables[ti].paraIndex = tableParagraphRanges[ti].start;
            result.tables[ti].endParaIndex = tableParagraphRanges[ti].end;
          }
        }

        for (let _paraIdx = 0; _paraIdx < bodyParas.items.length; _paraIdx++) {
          // 选区模式：跳过不在选区内的段落
          if (inSelectionSet && !inSelectionSet.has(_paraIdx)) continue;

          const para = bodyParas.items[_paraIdx];

          // ====== DEBUG: 输出段落的各种 Office.js API 属性 ======
          try {
            console.log(`===== 段落 [第${_paraIdx + 1}个] =====`);
            console.log(
              `  文本预览: "${(para.text || "").substring(0, 80).replace(/[\r\n]/g, "\\n")}"`
            );
            console.log(`  Style: "${para.style || ""}"`);
            console.log(`  Alignment: ${para.alignment}`);
            console.log(`  LineSpacing: ${para.lineSpacing}`);
            console.log(
              `  LeftIndent: ${para.leftIndent}, RightIndent: ${para.rightIndent}, FirstLineIndent: ${para.firstLineIndent}`
            );
            console.log(`  SpaceBefore: ${para.spaceBefore}, SpaceAfter: ${para.spaceAfter}`);
            console.log(
              `  LineUnitBefore: ${para.lineUnitBefore}, LineUnitAfter: ${para.lineUnitAfter}`
            );
            try {
              console.log(`  OutlineLevel: ${para.outlineLevel}`);
            } catch (e) {}
            console.log(
              `  IsListItem: ${para.isListItem}, TableNestingLevel: ${para.tableNestingLevel}`
            );

            // 列表项属性
            try {
              if (para.isListItem) {
                console.log(`  ListItem.Level: ${para.listItem.level}`);
                console.log(`  ListItem.ListString: "${para.listItem.listString}"`);
                console.log(`  ListItem.SiblingIndex: ${para.listItem.siblingIndex}`);
              }
            } catch (e) {
              console.log(`  [ListItem 属性获取失败]: ${e.message}`);
            }

            // 段落级字体属性
            try {
              const pFont = para.font;
              console.log(`  Font.Name: "${pFont.name}", Font.Size: ${pFont.size}`);
              console.log(`  Font.Bold: ${pFont.bold}, Font.Italic: ${pFont.italic}`);
              console.log(`  Font.Underline: ${pFont.underline}, Font.Color: ${pFont.color}`);
              console.log(`  Font.HighlightColor: ${pFont.highlightColor}`);
            } catch (e) {
              console.log(`  [Font 属性获取失败]: ${e.message}`);
            }

            console.log(`  ---- END 段落 ${_paraIdx + 1} ----`);
          } catch (debugErr) {
            console.log(`  [DEBUG ERROR] 段落 ${_paraIdx + 1}: ${debugErr.message}`);
          }
          // ====== END DEBUG ======

          // 跳过表格内段落
          if (para.tableNestingLevel > 0) continue;

          const paraText = cleanText(para.text || "");

          // 空段落
          if (!paraText || paraText.match(/^[\r\n\f\u0007]*$/)) {
            result.paragraphs.push({ pStyle: "", runs: [], paraIndex: _paraIdx });
            continue;
          }

          let styleName = "";
          try {
            styleName = para.style || "";
          } catch (e) {}

          // === 优先使用 OOXML 解析 runs（精确获取 Word 内部 run 边界）===
          let runs = null;
          try {
            const ooxmlResult = para.getOoxml();
            await context.sync();
            const ooxmlRuns = parseRunsFromOoxml(ooxmlResult.value);
            if (ooxmlRuns && ooxmlRuns.length > 0) {
              runs = ooxmlRuns;
              console.log(`  段落 ${_paraIdx + 1}: OOXML 解析成功，获取 ${runs.length} 个 runs`);

              // 如果仍有 run 字体为空，用 Office.js API 按字符偏移获取实际字体
              const hasEmptyFont = runs.some((r) => !r.rStyle[RSTYLE.FONT_NAME]);
              if (hasEmptyFont) {
                console.log(`  段落 ${_paraIdx + 1}: 部分 run 字体为空，使用 Office.js API 补充`);
                try {
                  // 获取段落中每个 run 对应的文本范围及其字体
                  const paraRange = para.getRange("Whole");
                  // 用每个 run 的文本去 search 定位
                  let charOffset = 0;
                  for (const run of runs) {
                    if (run.rStyle[RSTYLE.FONT_NAME]) {
                      charOffset += run.text.length;
                      continue;
                    }
                    // 尝试通过 search 找到文本并读取字体
                    try {
                      const searchResults = para.search(run.text, {
                        matchCase: true,
                        matchWholeWord: false,
                      });
                      searchResults.load("items");
                      await context.sync();
                      if (searchResults.items.length > 0) {
                        const matchItem = searchResults.items[0];
                        matchItem.font.load("name");
                        await context.sync();
                        if (matchItem.font.name) {
                          run.rStyle[RSTYLE.FONT_NAME] = matchItem.font.name;
                          console.log(
                            `    补充字体: "${run.text.substring(0, 20)}..." → "${matchItem.font.name}"`
                          );
                        }
                      }
                    } catch (searchErr) {
                      // search 失败，尝试用段落级字体
                    }
                    charOffset += run.text.length;
                  }

                  // 仍然有空字体的 run，最后用段落级字体兜底
                  const stillEmpty = runs.filter((r) => !r.rStyle[RSTYLE.FONT_NAME]);
                  if (stillEmpty.length > 0) {
                    const paraFont = para.font;
                    paraFont.load("name");
                    await context.sync();
                    if (paraFont.name) {
                      for (const run of stillEmpty) {
                        run.rStyle[RSTYLE.FONT_NAME] = paraFont.name;
                        console.log(
                          `    段落级字体兜底: "${run.text.substring(0, 20)}..." → "${paraFont.name}"`
                        );
                      }
                    }
                  }
                } catch (fontFallbackErr) {
                  console.log(`    字体补充失败:`, fontFallbackErr.message);
                }
              }
            }
          } catch (e) {
            console.log(`  段落 ${_paraIdx + 1}: OOXML 解析失败，降级到 getTextRanges:`, e.message);
          }

          // === 降级方案：使用 getTextRanges 拆分 ===
          if (!runs) {
            runs = [];
            const inlineRanges = para.getTextRanges(["\t", "\n"], true);
            inlineRanges.load("items");
            await context.sync();

            for (const ir of inlineRanges.items) {
              ir.load("text");
              ir.font.load(
                "name,size,bold,italic,underline,underlineColor,color,highlightColor,strikeThrough,superscript,subscript"
              );
            }
            await context.sync();

            let lastFormatKey = null;
            let currentRun = null;

            for (const ir of inlineRanges.items) {
              const t = ir.text || "";
              if (!t || t.match(/^[\r\n\f\u0007]+$/)) continue;

              const font = ir.font;
              const formatKey = [
                font.name,
                font.size,
                font.bold,
                font.italic,
                font.underline,
                font.color,
                font.highlightColor,
                font.strikeThrough,
                font.superscript,
                font.subscript,
              ].join("|");

              if (formatKey === lastFormatKey && currentRun) {
                currentRun.text += t;
              } else {
                if (currentRun && currentRun.text) {
                  const normalizedRun = normalizeParsedRun(currentRun);
                  if (normalizedRun && normalizedRun.text) {
                    runs.push(normalizedRun);
                  }
                }
                currentRun = {
                  text: t,
                  rStyle: makeRStyle(
                    font.name || "",
                    font.size || 12,
                    font.bold === true,
                    font.italic === true,
                    getUnderlineValue(font.underline),
                    font.underlineColor || "#000000",
                    font.color || "#000000",
                    getHighlightValue(font.highlightColor),
                    font.strikeThrough === true,
                    font.superscript === true,
                    font.subscript === true
                  ),
                };
                lastFormatKey = formatKey;
              }
            }
            if (currentRun && currentRun.text) {
              const normalizedRun = normalizeParsedRun(currentRun);
              if (normalizedRun && normalizedRun.text) {
                runs.push(normalizedRun);
              }
            }

            // 最终降级：整段作为一个 run
            if (runs.length === 0 && paraText) {
              const font = para.getRange().font;
              font.load(
                "name,size,bold,italic,underline,underlineColor,color,highlightColor,strikeThrough,superscript,subscript"
              );
              await context.sync();

              const fallbackRun = normalizeParsedRun({
                text: paraText,
                rStyle: makeRStyle(
                  font.name || "",
                  font.size || 12,
                  font.bold === true,
                  font.italic === true,
                  getUnderlineValue(font.underline),
                  font.underlineColor || "#000000",
                  font.color || "#000000",
                  getHighlightValue(font.highlightColor),
                  font.strikeThrough === true,
                  font.superscript === true,
                  font.subscript === true
                ),
              });
              if (fallbackRun && fallbackRun.text) {
                runs.push(fallbackRun);
              }
            }
          }

          const paragraphData = {
            pStyle: makePStyle(
              getAlignmentName(para.alignment),
              para.lineSpacing || 0,
              para.leftIndent || 0,
              para.rightIndent || 0,
              para.firstLineIndent || 0,
              para.spaceBefore || 0,
              para.spaceAfter || 0,
              styleName
            ),
            runs: runs,
            paraIndex: _paraIdx,
          };

          if (paragraphData.runs.length > 0) {
            result.paragraphs.push(paragraphData);
          }
        }
      }

      return deduplicateStyles(result);
    });
  } catch (error) {
    return { error: "解析失败: " + error.message };
  }
}

// ============== 生成函数 ==============

/**
 * 从 JSON 数据生成 Word 文档（异步，基于 Office.js API）
 *
 * @param {Object} jsonData - JSON 数据
 * @param {string} insertLocation - 插入位置:
 *   'end'       - 文档末尾追加
 *   'selection' - 当前选区之后
 *   'replace'   - 替换当前选区
 *   'before'    - 在 jsonData.paraIndex 指定的段落之前插入（O(1) 定位）
 * @returns {Promise<Object>} - 成功返回 {success: true}，失败返回 {error: string}
 */
async function generateDocxFromJSON(jsonData, insertLocation = "selection") {
  try {
    if (!jsonData || (!jsonData.paragraphs && !jsonData.tables)) {
      return { error: "JSON数据格式不正确" };
    }

    const styles = jsonData.styles || {};

    return await Word.run(async (context) => {
      let targetRange;
      let insertBeforeMode = false;

      if (insertLocation === "before") {
        // 'before' 模式：通过 paraIndex 直接 O(1) 定位到目标段落
        const paraIndex = jsonData.paraIndex;
        if (paraIndex === undefined || paraIndex === null || paraIndex < 0) {
          return { error: "before 模式需要 jsonData.paraIndex（0-based 段落索引）" };
        }
        const allParagraphs = context.document.body.paragraphs;
        allParagraphs.load("items");
        await context.sync();
        if (paraIndex >= allParagraphs.items.length) {
          return {
            error: `paraIndex ${paraIndex} 超出范围，文档共 ${allParagraphs.items.length} 段`,
          };
        }
        targetRange = allParagraphs.items[paraIndex];
        insertBeforeMode = true;

        // 防御：如果目标段落在表格内部，跳转到表格之后的首个段落
        // 避免新内容（尤其是新表格）被嵌套到旧表格单元格内
        try {
          allParagraphs.items[paraIndex].load("tableNestingLevel");
          await context.sync();
          if (allParagraphs.items[paraIndex].tableNestingLevel > 0) {
            console.log(`[generateDocxFromJSON] 插入位置(paraIndex=${paraIndex})在表格内部，寻找表格后安全位置`);
            let safeIdx = -1;
            for (let pi = paraIndex + 1; pi < allParagraphs.items.length; pi++) {
              allParagraphs.items[pi].load("tableNestingLevel");
              await context.sync();
              if (allParagraphs.items[pi].tableNestingLevel === 0) {
                safeIdx = pi;
                break;
              }
            }
            if (safeIdx >= 0) {
              targetRange = allParagraphs.items[safeIdx];
              console.log(`[generateDocxFromJSON] 调整到表格后方: paraIndex=${safeIdx}`);
            }
          }
        } catch (e) {
          console.warn('[generateDocxFromJSON] 表格位置检测失败:', e);
        }
      } else if (insertLocation === "end") {
        targetRange = context.document.body;
      } else {
        targetRange = context.document.getSelection();
      }

      // 合并段落和表格，按位置排序
      const elements = [];

      if (jsonData.paragraphs) {
        jsonData.paragraphs.forEach((para, index) => {
          elements.push({ type: "paragraph", data: para, position: para.position || index * 1000 });
        });
      }

      if (jsonData.tables) {
        jsonData.tables.forEach((table, index) => {
          elements.push({
            type: "table",
            data: table,
            position: table.position || (index + 0.5) * 10000,
          });
        });
      }

      elements.sort((a, b) => a.position - b.position);

      // 预处理：合并连续空段落
      const processedElements = [];
      let consecutiveEmptyCount = 0;
      for (const element of elements) {
        if (element.type === "paragraph" && isEmptyParagraph(element.data)) {
          consecutiveEmptyCount++;
          if (consecutiveEmptyCount <= 2) processedElements.push(element);
        } else {
          consecutiveEmptyCount = 0;
          processedElements.push(element);
        }
      }

      // 插入内容
      const insertLoc = insertBeforeMode
        ? Word.InsertLocation.before
        : insertLocation === "end"
          ? Word.InsertLocation.end
          : Word.InsertLocation.after;

      for (let i = 0; i < processedElements.length; i++) {
        const element = processedElements[i];

        if (element.type === "paragraph") {
          const para = element.data;
          const pStyle = resolveStyle(styles, para.pStyle, DEFAULT_PSTYLE);
          const alignment = pStyle[PSTYLE.ALIGNMENT] || "left";
          const lineSpacing = pStyle[PSTYLE.LINE_SPACING] || 0;
          const indentLeft = pStyle[PSTYLE.INDENT_LEFT] || 0;
          const indentRight = pStyle[PSTYLE.INDENT_RIGHT] || 0;
          const indentFirstLine = pStyle[PSTYLE.INDENT_FIRST_LINE] || 0;
          const spaceBefore = pStyle[PSTYLE.SPACE_BEFORE] || 0;
          const spaceAfter = pStyle[PSTYLE.SPACE_AFTER] || 0;
          const styleName = pStyle[PSTYLE.STYLE_NAME] || "";

          // 空段落
          if (isEmptyParagraph(para)) {
            if (insertBeforeMode) {
              targetRange.insertParagraph("", Word.InsertLocation.before);
            } else if (insertLocation === "end") {
              targetRange.insertParagraph("", Word.InsertLocation.end);
            } else {
              targetRange.insertParagraph("", insertLoc);
            }
            continue;
          }

          // 拼接段落文本
          const fullText = (para.runs || []).map((r) => r.text || "").join("");
          if (!fullText) continue;

          // 插入段落
          let newParagraph;
          if (insertBeforeMode) {
            newParagraph = targetRange.insertParagraph(fullText, Word.InsertLocation.before);
          } else if (insertLocation === "end") {
            newParagraph = targetRange.insertParagraph(fullText, Word.InsertLocation.end);
          } else {
            newParagraph = targetRange.insertParagraph(fullText, insertLoc);
          }

          // 应用段落样式名
          if (styleName) {
            try {
              newParagraph.style = styleName;
            } catch (e) {}
          }

          // 段落格式
          newParagraph.alignment = getAlignmentValue(alignment);
          if (indentLeft) newParagraph.leftIndent = indentLeft;
          if (indentRight) newParagraph.rightIndent = indentRight;
          if (indentFirstLine) newParagraph.firstLineIndent = indentFirstLine;
          if (spaceBefore) newParagraph.spaceBefore = spaceBefore;
          if (spaceAfter) newParagraph.spaceAfter = spaceAfter;
          if (lineSpacing) newParagraph.lineSpacing = lineSpacing;

          // 应用 runs 字符格式
          if (para.runs && para.runs.length > 0) {
            let charOffset = 0;
            for (const run of para.runs) {
              let runText = run.text || "";
              if (!runText) continue;

              const rStyle = resolveStyle(styles, run.rStyle, DEFAULT_RSTYLE);
              const isExplicitLatexRun = run.isFormula === true && run.formulaFormat === "latex";
              if (isExplicitLatexRun) {
                runText = run.text || normalizeFormulaTextToLatex(run.text);
              }

              try {
                // 使用 getRange 获取段落中的子范围
                const runRange = newParagraph.getRange().getRange("Whole");
                // Office.js 不支持直接按字符偏移设置格式，
                // 使用 search 方式定位文本
                const searchResults = newParagraph.search(runText, {
                  matchCase: true,
                  matchWholeWord: false,
                });
                searchResults.load("items");
                await context.sync();

                // 取匹配结果，应用字符格式
                if (searchResults.items.length > 0) {
                  const targetItem =
                    searchResults.items[
                      searchResults.items.length > 1
                        ? findClosestMatch(searchResults.items, charOffset)
                        : 0
                    ];
                  applyRunStyle(targetItem.font, rStyle);
                }
              } catch (e) {
                // 降级处理：给整个段落设置最后一个 run 的格式
              }

              charOffset += runText.length;
            }

            // 如果只有一个 run，直接给整段设格式（更可靠）
            if (para.runs.length === 1) {
              const rStyle = resolveStyle(styles, para.runs[0].rStyle, DEFAULT_RSTYLE);
              applyRunStyle(newParagraph.font, rStyle);
            }
          }

          // 更新 targetRange 引用（before 模式不需要更新，始终在同一段落前插入）
          if (!insertBeforeMode && insertLocation !== "end") {
            targetRange = newParagraph;
          }
        } else if (element.type === "table") {
          const tableData = element.data;
          const tStyle = resolveStyle(styles, tableData.tStyle, ["center"]);

          // 构建表格数据值数组
          const values = [];
          for (let row = 0; row < tableData.rows; row++) {
            const rowValues = [];
            if (tableData.cells && tableData.cells[row]) {
              for (let col = 0; col < tableData.columns; col++) {
                const cellData = tableData.cells[row][col];
                if (cellData) {
                  let cellText = cellData.text || "";
                  if (!cellText && cellData.paragraphs) {
                    cellText = cellData.paragraphs
                      .map((p) => {
                        if (p.runs) return p.runs.map((r) => r.text || "").join("");
                        return p.text || "";
                      })
                      .join("\n");
                  }
                  rowValues.push(cleanText(cellText));
                } else {
                  rowValues.push("");
                }
              }
            }
            // 补齐列数
            while (rowValues.length < tableData.columns) {
              rowValues.push("");
            }
            values.push(rowValues);
          }

          // 插入表格
          let newTable;
          if (insertLocation === "end") {
            newTable = targetRange.insertTable(
              tableData.rows,
              tableData.columns,
              Word.InsertLocation.end,
              values
            );
          } else {
            // 在选区后插入一个段落，再在该段落后插入表格
            const tempPara = targetRange.insertParagraph("", Word.InsertLocation.after);
            newTable = tempPara.insertTable(
              tableData.rows,
              tableData.columns,
              Word.InsertLocation.after,
              values
            );
            tempPara.delete();
          }

          // 设置表格对齐
          newTable.alignment = getAlignmentValue(tStyle[0] || "center");

          // 应用单元格格式
          newTable.load("rows");
          await context.sync();

          // 设置列宽
          if (tableData.columnWidths && tableData.columnWidths.length === tableData.columns) {
            for (let row = 0; row < tableData.cells.length; row++) {
              for (let col = 0; col < tableData.columns; col++) {
                if (tableData.columnWidths[col] > 0) {
                  try {
                    const cell = newTable.getCell(row, col);
                    cell.columnWidth = tableData.columnWidths[col];
                  } catch (e) {}
                }
              }
            }
            await context.sync();
          }

          // 设置行高
          if (tableData.rowHeights && tableData.rowHeights.length === tableData.rows) {
            const rows = newTable.rows;
            rows.load("items");
            await context.sync();
            for (let r = 0; r < tableData.rows; r++) {
              try {
                const [height] = tableData.rowHeights[r];
                if (height > 0) {
                  rows.items[r].preferredHeight = height;
                }
              } catch (e) {}
            }
            await context.sync();
          }

          for (let row = 0; row < tableData.cells.length; row++) {
            for (let col = 0; col < tableData.cells[row].length; col++) {
              const cellData = tableData.cells[row][col];
              if (!cellData) continue;

              const cStyle = resolveStyle(styles, cellData.cStyle, DEFAULT_CSTYLE);

              try {
                const cell = newTable.getCell(row, col);
                cell.verticalAlignment = getVerticalAlignmentValue(
                  cStyle[CSTYLE.VERTICAL_ALIGNMENT] || "center"
                );

                // 设置单元格段落格式
                const cellBody = cell.body;
                cellBody.paragraphs.load("items");
                await context.sync();

                if (cellData.paragraphs && cellData.paragraphs.length > 0) {
                  // 有多段落数据时，逐段设置段落格式和 run 字符格式
                  for (let pi = 0; pi < cellData.paragraphs.length && pi < cellBody.paragraphs.items.length; pi++) {
                    const paraData = cellData.paragraphs[pi];
                    const cellPara = cellBody.paragraphs.items[pi];
                    const pStyle = resolveStyle(styles, paraData.pStyle, DEFAULT_PSTYLE);

                    cellPara.alignment = getAlignmentValue(pStyle[PSTYLE.ALIGNMENT] || "center");
                    if (pStyle[PSTYLE.INDENT_LEFT]) cellPara.leftIndent = pStyle[PSTYLE.INDENT_LEFT];
                    if (pStyle[PSTYLE.INDENT_RIGHT]) cellPara.rightIndent = pStyle[PSTYLE.INDENT_RIGHT];
                    cellPara.firstLineIndent = pStyle[PSTYLE.INDENT_FIRST_LINE] || 0;
                    if (pStyle[PSTYLE.SPACE_BEFORE]) cellPara.spaceBefore = pStyle[PSTYLE.SPACE_BEFORE];
                    if (pStyle[PSTYLE.SPACE_AFTER]) cellPara.spaceAfter = pStyle[PSTYLE.SPACE_AFTER];
                    if (pStyle[PSTYLE.LINE_SPACING]) cellPara.lineSpacing = pStyle[PSTYLE.LINE_SPACING];

                    // 应用 run 字符格式
                    if (paraData.runs && paraData.runs.length > 0) {
                      if (paraData.runs.length === 1) {
                        // 单 run：直接设置段落字体
                        const rStyle = resolveStyle(styles, paraData.runs[0].rStyle, DEFAULT_RSTYLE);
                        applyRunStyle(cellPara.font, rStyle);
                      } else {
                        // 多 run：通过 search 定位设置
                        for (const run of paraData.runs) {
                          const runText = run.text || "";
                          if (!runText) continue;
                          const rStyle = resolveStyle(styles, run.rStyle, DEFAULT_RSTYLE);
                          try {
                            const searchResults = cellPara.search(runText, { matchCase: true, matchWholeWord: false });
                            searchResults.load("items");
                            await context.sync();
                            if (searchResults.items.length > 0) {
                              applyRunStyle(searchResults.items[0].font, rStyle);
                            }
                          } catch (e) {}
                        }
                      }
                    }
                  }
                } else {
                  // 无多段落数据时，使用 cStyle 对齐和 rStyle 字体
                  for (const cellPara of cellBody.paragraphs.items) {
                    cellPara.alignment = getAlignmentValue(cStyle[CSTYLE.ALIGNMENT] || "left");
                    cellPara.firstLineIndent = 0;

                    if (cellData.rStyle) {
                      const rStyle = resolveStyle(styles, cellData.rStyle, DEFAULT_RSTYLE);
                      applyRunStyle(cellPara.font, rStyle);
                    }
                  }
                }
              } catch (e) {
                // 单元格操作可能因合并等原因失败
              }
            }
          }

          // 处理合并单元格
          for (let row = 0; row < tableData.cells.length; row++) {
            for (let col = 0; col < tableData.cells[row].length; col++) {
              const cellData = tableData.cells[row][col];
              if (!cellData || !cellData.cStyle) continue;

              const cStyle = resolveStyle(styles, cellData.cStyle, DEFAULT_CSTYLE);
              const rowSpan = cStyle[CSTYLE.ROW_SPAN] || 1;
              const colSpan = cStyle[CSTYLE.COL_SPAN] || 1;

              // Office.js Word API 不直接支持 cell merge，
              // 需要通过 OOXML 或其他方式实现
              // 这里记录合并信息但跳过合并操作
              if (rowSpan > 1 || colSpan > 1) {
                // TODO: Office.js 对合并操作支持有限
              }
            }
          }

          if (!insertBeforeMode && insertLocation !== "end") {
            targetRange = newTable.getRange("After");
          }
        }
      }

      await context.sync();

      const paraCount = jsonData.paragraphs?.length || 0;
      const tableCount = jsonData.tables?.length || 0;
      return { success: true, message: `文档生成成功！${paraCount} 段落 / ${tableCount} 表格` };
    });
  } catch (error) {
    return { error: "生成文档失败: " + error.message };
  }
}

/**
 * 应用 run 样式到字体对象
 */
function applyRunStyle(font, rStyle) {
  if (rStyle[RSTYLE.FONT_NAME]) font.name = rStyle[RSTYLE.FONT_NAME];
  if (rStyle[RSTYLE.FONT_SIZE]) font.size = rStyle[RSTYLE.FONT_SIZE];
  font.bold = !!rStyle[RSTYLE.BOLD];
  font.italic = !!rStyle[RSTYLE.ITALIC];
  font.strikeThrough = !!rStyle[RSTYLE.STRIKETHROUGH];
  font.superscript = !!rStyle[RSTYLE.SUPERSCRIPT];
  font.subscript = !!rStyle[RSTYLE.SUBSCRIPT];

  // 下划线
  const underlineType = getUnderlineType(rStyle[RSTYLE.UNDERLINE]);
  font.underline = underlineType;

  // 颜色
  if (rStyle[RSTYLE.COLOR] && rStyle[RSTYLE.COLOR] !== "#000000") {
    font.color = rStyle[RSTYLE.COLOR];
  } else {
    font.color = "#000000";
  }

  // 高亮
  const highlightColor = getHighlightColor(rStyle[RSTYLE.HIGHLIGHT]);
  if (highlightColor) {
    font.highlightColor = highlightColor;
  }
}

function findClosestMatch(items, offset) {
  return 0; // 简化实现，返回第一个匹配
}

/**
 * 删除指定范围的段落（Office.js 版本）
 * @param {number} startParaIndex - 起始段落索引（0-based）
 * @param {number} [endParaIndex] - 结束段落索引（0-based，含），-1 表示删除到文档末尾
 * @returns {Promise<{ success: boolean, deletedCount: number, message: string }>}
 */
async function deleteDocxPara(startParaIndex, endParaIndex) {
  if (startParaIndex === undefined || startParaIndex === null) {
    return { success: false, deletedCount: 0, message: "未提供有效的 startParaIndex" };
  }
  if (endParaIndex === undefined || endParaIndex === null) {
    endParaIndex = startParaIndex;
  }

  try {
    return await Word.run(async (context) => {
      const allParas = context.document.body.paragraphs;
      allParas.load("items");
      await context.sync();

      const totalParas = allParas.items.length;
      if (totalParas === 0) {
        return { success: false, deletedCount: 0, message: "文档中没有段落" };
      }

      if (endParaIndex === -1) {
        endParaIndex = totalParas - 1;
      }

      if (startParaIndex < 0 || startParaIndex >= totalParas) {
        return {
          success: false,
          deletedCount: 0,
          message: `startParaIndex ${startParaIndex} 超出范围，文档共 ${totalParas} 段`,
        };
      }
      if (endParaIndex < startParaIndex || endParaIndex >= totalParas) {
        return { success: false, deletedCount: 0, message: `endParaIndex ${endParaIndex} 无效` };
      }

      // 从后往前删除，避免索引偏移
      let deletedCount = 0;
      for (let idx = endParaIndex; idx >= startParaIndex; idx--) {
        const para = allParas.items[idx];
        para.delete();
        deletedCount++;
      }
      await context.sync();

      return { success: true, deletedCount, message: `成功删除 ${deletedCount} 个段落` };
    });
  } catch (e) {
    return { success: false, deletedCount: 0, message: `删除失败: ${e.message}` };
  }
}

/**
 * 为指定范围的段落添加批注（Office.js 版本）
 * @param {number} startParaIndex - 起始段落索引（0-based）
 * @param {number} endParaIndex - 结束段落索引（0-based，含），-1 表示到文档末尾
 * @param {string} text - 批注文本
 * @returns {Promise<{ success: boolean, rangeStart: number, rangeEnd: number }>}
 */
async function addCommentToParas(startParaIndex, endParaIndex, text) {
  try {
    return await Word.run(async (context) => {
      const allParas = context.document.body.paragraphs;
      allParas.load("items");
      await context.sync();

      const totalParas = allParas.items.length;
      if (endParaIndex === -1) endParaIndex = totalParas - 1;

      const startPara = allParas.items[startParaIndex];
      const endPara = allParas.items[endParaIndex];

      // 获取起止段落的 range 然后合并
      const startRange = startPara.getRange("Start");
      const endRange = endPara.getRange("End");
      const fullRange = startRange.expandTo(endRange);

      // 插入批注
      fullRange.insertComment(text);
      await context.sync();

      return { success: true };
    });
  } catch (e) {
    console.error("添加批注失败:", e);
    return { success: false, error: e.message };
  }
}

// ============== 导出 ==============

export default {
  parseDocxToJSON,
  generateDocxFromJSON,
  deleteDocxPara,
  addCommentToParas,
  cleanText,
  deduplicateStyles,
  resolveStyle,
  PSTYLE,
  RSTYLE,
  CSTYLE,
  makePStyle,
  makeRStyle,
  makeCStyle,
  getAlignmentName,
  getAlignmentValue,
  getVerticalAlignmentName,
  getVerticalAlignmentValue,
  getUnderlineValue,
  getUnderlineType,
  getHighlightValue,
  getHighlightColor,
};

export {
  parseDocxToJSON,
  generateDocxFromJSON,
  deleteDocxPara,
  addCommentToParas,
  cleanText,
  deduplicateStyles,
  resolveStyle,
  PSTYLE,
  RSTYLE,
  CSTYLE,
  makePStyle,
  makeRStyle,
  makeCStyle,
  getAlignmentName,
  getAlignmentValue,
  getVerticalAlignmentName,
  getVerticalAlignmentValue,
  getUnderlineValue,
  getUnderlineType,
  getHighlightValue,
  getHighlightColor,
};

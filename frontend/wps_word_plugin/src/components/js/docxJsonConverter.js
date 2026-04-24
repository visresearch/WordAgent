/**
 * WPS Word 文档与 JSON 双向转换工具
 *
 * 功能：
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
 *     runs: [{                 // 格式块数组（文本或图片）
 *       // 文本 run:
 *       text: string,          // 文字内容
 *       rStyle: [              // 字符样式数组（按顺序）
 *         fontName,            // [0] 字体名称
 *         fontSize,            // [1] 字号
 *         bold,                // [2] 加粗
 *         italic,              // [3] 斜体
 *         underline,           // [4] 下划线: 0=无、1=单线、3=双线、4=虚线、6=粗线、7=粗虚线、11=波浪线、27=粗波浪线
 *         underlineColor,      // [5] 下划线颜色: #RRGGBB
 *         color,               // [6] 字体颜色: #RRGGBB
 *         highlight,           // [7] 高亮色: 0=无, 1-16=黑、蓝、青绿、鲜绿、粉红、红、黄、未知、深蓝、青、绿、紫罗兰、深红、深黄、深灰、浅灰
 *         strikethrough,       // [8] 删除线
 *         superscript,         // [9] 上标
 *         subscript            // [10] 下标
 *       ]
 *       // 或图片 run（没有 text 字段）:
 *       // url/tempPath/sourcePath: 图片路径（三选一）
 *       // width/height: 图片尺寸
 *       // left/top/wrapType: 浮动图片属性
 *       // altText: 替代文本
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
 *   fields: [],               // 域代码数组
 *   hasTOC: boolean,          // 是否包含目录
 *   styles: {                 // 样式字典（去重）
 *     pS_1: [...],            // 段落样式，键名 pS_N
 *     rS_1: [...],            // 字符样式，键名 rS_N
 *     cS_1: [...],            // 单元格样式，键名 cS_N
 *     tS_1: [...]             // 表格样式，键名 tS_N
 *   }
 * }
 *
 * 图片现在作为 inline runs 嵌入段落中，没有独立的 images 数组。
 * 文本 run 有 text 字段，图片 run 没有 text 字段但有 url/tempPath 等。
 *
 * 段落/run/单元格中的 pStyle/rStyle/cStyle/tStyle 为字符串引用（如 "pS_1"），
 * 指向 styles 字典中的完整样式数组，以去重节约 token。
 */

// ============== 格式转换辅助函数 ==============

// 样式数组索引常量
const PSTYLE = {
  ALIGNMENT: 0,
  LINE_SPACING: 1,
  INDENT_LEFT: 2,
  INDENT_RIGHT: 3,
  INDENT_FIRST_LINE: 4,
  SPACE_BEFORE: 5,
  SPACE_AFTER: 6,
  STYLE_NAME: 7,
  LINE_SPACING_RULE: 8
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
  SUBSCRIPT: 10
};

const CSTYLE = {
  ROW_SPAN: 0,
  COL_SPAN: 1,
  ALIGNMENT: 2,
  VERTICAL_ALIGNMENT: 3
};

// 默认样式值
const DEFAULT_PSTYLE = ['left', 0, 0, 0, 0, 0, 0, '', 0];
const DEFAULT_RSTYLE = ['', 12, false, false, 0, '#000000', '#000000', 0, false, false, false];
const DEFAULT_CSTYLE = [1, 1, 'left', 'center'];
const DEFAULT_IMAGE_PSTYLE = ['center', 0, 0, 0, 0, 0, 0, '', 0];

function isEmptyParagraph(para) {
  return !!(para && Array.isArray(para.runs) && para.runs.length === 0);
}

// ============== 样式去重与解析 ==============

/**
 * 创建样式注册表
 */
function createStyleRegistry() {
  return {
    _maps: { p: new Map(), r: new Map(), c: new Map(), t: new Map() },
    _counts: { p: 0, r: 0, c: 0, t: 0 },
    _prefixes: { p: 'pS_', r: 'rS_', c: 'cS_', t: 'tS_' },
    styles: {}
  };
}

/**
 * 注册样式并返回引用ID，相同样式返回同一ID
 */
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

/**
 * 解析样式引用：字符串则查字典，数组则直接使用（向后兼容）
 */
function resolveStyle(styles, ref, defaultStyle) {
  if (!ref) {
    return defaultStyle;
  }
  if (Array.isArray(ref)) {
    return ref;
  }
  if (typeof ref === 'string' && styles && styles[ref]) {
    return styles[ref];
  }
  return defaultStyle;
}

/**
 * 对 parseDocxToJSON 的结果进行样式去重
 */
function deduplicateStyles(result) {
  const registry = createStyleRegistry();

  if (result.paragraphs) {
    for (const para of result.paragraphs) {
      if (para.pStyle && Array.isArray(para.pStyle)) {
        para.pStyle = registerStyle(registry, 'p', para.pStyle);
      }
      if (para.runs) {
        for (const run of para.runs) {
          if (run.rStyle && Array.isArray(run.rStyle)) {
            run.rStyle = registerStyle(registry, 'r', run.rStyle);
          }
        }
      }
    }
  }

  if (result.tables) {
    for (const table of result.tables) {
      if (table.tStyle && Array.isArray(table.tStyle)) {
        table.tStyle = registerStyle(registry, 't', table.tStyle);
      }
      if (table.cells) {
        for (const row of table.cells) {
          for (const cell of row) {
            if (cell.cStyle && Array.isArray(cell.cStyle)) {
              cell.cStyle = registerStyle(registry, 'c', cell.cStyle);
            }
            if (cell.rStyle && Array.isArray(cell.rStyle)) {
              cell.rStyle = registerStyle(registry, 'r', cell.rStyle);
            }
            if (cell.paragraphs) {
              for (const para of cell.paragraphs) {
                if (para.pStyle && Array.isArray(para.pStyle)) {
                  para.pStyle = registerStyle(registry, 'p', para.pStyle);
                }
                if (para.runs) {
                  for (const run of para.runs) {
                    if (run.rStyle && Array.isArray(run.rStyle)) {
                      run.rStyle = registerStyle(registry, 'r', run.rStyle);
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

/**
 * 创建段落样式数组
 */
function makePStyle(alignment, lineSpacing, indentLeft, indentRight, indentFirstLine, spaceBefore, spaceAfter, styleName) {
  return [alignment, lineSpacing, indentLeft, indentRight, indentFirstLine, spaceBefore, spaceAfter, styleName];
}

/**
 * 创建字符样式数组
 */
function makeRStyle(fontName, fontSize, bold, italic, underline, underlineColor, color, highlight, strikethrough, superscript, subscript) {
  return [fontName, fontSize, bold, italic, underline, underlineColor, color, highlight, strikethrough, superscript, subscript];
}

/**
 * 创建单元格样式数组
 */
function makeCStyle(rowSpan, colSpan, alignment, verticalAlignment) {
  return [rowSpan, colSpan, alignment, verticalAlignment];
}

/**
 * 对齐方式：值 -> 名称
 */
function getAlignmentName(alignment) {
  const map = { 0: 'left', 1: 'center', 2: 'right', 3: 'justify', 4: 'distribute' };
  return map[alignment] || 'left';
}

/**
 * 对齐方式：名称 -> 值
 */
function getAlignmentValue(alignment) {
  const map = { left: 0, center: 1, right: 2, justify: 3, distribute: 4 };
  return map[alignment] || 0;
}

/**
 * 表格对齐方式：值 -> 名称
 */
function getTableAlignmentName(alignment) {
  const map = { 0: 'left', 1: 'center', 2: 'right' };
  return map[alignment] || 'center';
}

/**
 * 表格对齐方式：名称 -> 值
 */
function getTableAlignmentValue(alignment) {
  const map = { left: 0, center: 1, right: 2 };
  return map[alignment] || 1;
}

/**
 * 单元格垂直对齐：值 -> 名称
 */
function getCellVerticalAlignmentName(alignment) {
  const map = { 0: 'top', 1: 'center', 2: 'bottom' };
  return map[alignment] || 'center';
}

/**
 * 单元格垂直对齐：名称 -> 值
 */
function getCellVerticalAlignmentValue(alignment) {
  const map = { top: 0, center: 1, bottom: 2 };
  return map[alignment] || 1;
}

/**
 * 图片环绕方式：值 -> 名称
 */
function getWrapTypeName(wrapType) {
  const map = {
    0: 'inline',
    1: 'topBottom',
    2: 'square',
    3: 'none',
    4: 'tight',
    5: 'through',
    6: 'behindText',
    7: 'inFrontOfText'
  };
  return map[wrapType] || 'square';
}

/**
 * 图片环绕方式：名称 -> 值
 */
function getWrapTypeValue(wrapType) {
  const map = {
    inline: 0,
    topBottom: 1,
    square: 2,
    none: 3,
    tight: 4,
    through: 5,
    behindText: 6,
    inFrontOfText: 7
  };
  return map[wrapType] || 2;
}

/**
 * 制表位对齐：值 -> 名称
 */
function getTabAlignmentName(alignment) {
  const map = { 0: 'left', 1: 'center', 2: 'right', 3: 'decimal', 4: 'bar', 5: 'list' };
  return map[alignment] || 'left';
}

/**
 * 制表位对齐：名称 -> 值
 */
function getTabAlignmentValue(alignment) {
  const map = { left: 0, center: 1, right: 2, decimal: 3, bar: 4, list: 5 };
  return map[alignment] || 0;
}

/**
 * 制表位前导符：值 -> 名称
 */
function getTabLeaderName(leader) {
  const map = { 0: 'none', 1: 'dots', 2: 'dashes', 3: 'lines', 4: 'heavy', 5: 'middleDot' };
  return map[leader] || 'none';
}

/**
 * 制表位前导符：名称 -> 值
 */
function getTabLeaderValue(leader) {
  const map = { none: 0, dots: 1, dashes: 2, lines: 3, heavy: 4, middleDot: 5 };
  return map[leader] || 0;
}

/**
 * 颜色值 -> RGB 字符串
 */
function getRGBColor(colorValue) {
  if (!colorValue || colorValue === 0) {
    return '#000000';
  }
  try {
    const r = colorValue & 0xff;
    const g = (colorValue >> 8) & 0xff;
    const b = (colorValue >> 16) & 0xff;
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  } catch (e) {
    return '#000000';
  }
}

/**
 * RGB 字符串 -> 颜色值
 */
function parseRGBColor(colorStr) {
  if (!colorStr || colorStr === '#000000') {
    return 0;
  }
  try {
    const hex = colorStr.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return r + (g << 8) + (b << 16);
  } catch (e) {
    return 0;
  }
}

/**
 * 清理文本中的特殊字符
 * - \u0007: 表格单元格结束符
 * - \u0001: 域占位符
 * - \f: 分页符
 * - \r: 末尾回车
 */
function cleanText(text) {
  if (!text) {
    return '';
  }
  return text
    .replace(/\u0007/g, '')
    .replace(/\f/g, '')
    .replace(/\r$/, '');
}

/**
 * 清理单元格文本末尾的特殊字符
 */
function cleanCellText(text) {
  if (!text) {
    return '';
  }
  return text.replace(/[\r\n\u0007\u0001]+$/g, '');
}

function getDocumentUsableWidth(doc) {
  let pageWidth = 425;
  try {
    const pageSetup = doc && doc.PageSetup;
    if (pageSetup) {
      const rawPageWidth = Number(pageSetup.PageWidth) || 0;
      const leftMargin = Number(pageSetup.LeftMargin) || 0;
      const rightMargin = Number(pageSetup.RightMargin) || 0;
      const usableWidth = rawPageWidth - leftMargin - rightMargin;
      if (usableWidth > 0) {
        pageWidth = usableWidth;
      }
    }
  } catch (e) {}
  return pageWidth;
}

function normalizeImageSizeByMaxWidth(img, maxWidth) {
  const normalized = {};
  const width = Number(img && img.width);
  const height = Number(img && img.height);
  const hasWidth = Number.isFinite(width) && width > 0;
  const hasHeight = Number.isFinite(height) && height > 0;
  const safeMaxWidth = Number.isFinite(maxWidth) && maxWidth > 0 ? maxWidth : 425;

  if (!hasWidth && !hasHeight) {
    return normalized;
  }

  if (hasWidth && width > safeMaxWidth) {
    const ratio = safeMaxWidth / width;
    normalized.width = safeMaxWidth;
    if (hasHeight) {
      normalized.height = Math.max(1, Math.round(height * ratio));
    }
    return normalized;
  }

  if (hasWidth) {
    normalized.width = width;
  }
  if (hasHeight) {
    normalized.height = height;
  }

  return normalized;
}

function getImageParagraphStyle(img, styles) {
  const pStyle = resolveStyle(styles, img && img.pStyle, DEFAULT_IMAGE_PSTYLE);
  const normalized = Array.isArray(pStyle) ? [...pStyle] : [...DEFAULT_IMAGE_PSTYLE];

  normalized[PSTYLE.ALIGNMENT] = normalized[PSTYLE.ALIGNMENT] || 'center';
  normalized[PSTYLE.INDENT_LEFT] = Number(normalized[PSTYLE.INDENT_LEFT]) || 0;
  normalized[PSTYLE.INDENT_RIGHT] = Number(normalized[PSTYLE.INDENT_RIGHT]) || 0;
  normalized[PSTYLE.INDENT_FIRST_LINE] = Number(normalized[PSTYLE.INDENT_FIRST_LINE]) || 0;
  normalized[PSTYLE.SPACE_BEFORE] = Number(normalized[PSTYLE.SPACE_BEFORE]) || 0;
  normalized[PSTYLE.SPACE_AFTER] = Number(normalized[PSTYLE.SPACE_AFTER]) || 0;

  return normalized;
}

const MATH_FONT_KEYWORDS = ['cambria math', 'dejavu math', 'tex gyre', 'stix', 'latin modern math'];

const MATH_SYMBOL_TO_LATEX = {
  '\u221e': '\\infty',
  '\u2211': '\\sum',
  '\u220f': '\\prod',
  '\u222b': '\\int',
  '\u221a': '\\sqrt',
  '\u00d7': '\\times',
  '\u00f7': '\\div',
  '\u00b1': '\\pm',
  '\u2213': '\\mp',
  '\u2264': '\\le',
  '\u2265': '\\ge',
  '\u2260': '\\ne',
  '\u2248': '\\approx',
  '\u2261': '\\equiv',
  '\u00b7': '\\cdot',
  '\u22c5': '\\cdot',
  '\u03b1': '\\alpha',
  '\u03b2': '\\beta',
  '\u03b3': '\\gamma',
  '\u03b4': '\\delta',
  '\u03b5': '\\epsilon',
  '\u03b8': '\\theta',
  '\u03bb': '\\lambda',
  '\u03bc': '\\mu',
  '\u03c0': '\\pi',
  '\u03c1': '\\rho',
  '\u03c3': '\\sigma',
  '\u03c6': '\\phi',
  '\u03c9': '\\omega',
  '\u0393': '\\Gamma',
  '\u0394': '\\Delta',
  '\u0398': '\\Theta',
  '\u039b': '\\Lambda',
  '\u03a0': '\\Pi',
  '\u03a3': '\\Sigma',
  '\u03a6': '\\Phi',
  '\u03a9': '\\Omega',
  '\u2212': '-'
};

const SUPERSCRIPT_CHAR_MAP = {
  '\u2070': '0', '\u00b9': '1', '\u00b2': '2', '\u00b3': '3', '\u2074': '4',
  '\u2075': '5', '\u2076': '6', '\u2077': '7', '\u2078': '8', '\u2079': '9',
  '\u207a': '+', '\u207b': '-', '\u207c': '=', '\u207d': '(', '\u207e': ')',
  '\u207f': 'n', '\u1d43': 'a', '\u1d47': 'b', '\u1d9c': 'c', '\u1d48': 'd',
  '\u1d49': 'e', '\u1da0': 'f', '\u1d4d': 'g', '\u02b0': 'h', '\u2071': 'i',
  '\u02b2': 'j', '\u1d4f': 'k', '\u02e1': 'l', '\u1d50': 'm',
  '\u1d52': 'o', '\u1d56': 'p', '\u02b3': 'r', '\u02e2': 's', '\u1d57': 't',
  '\u1d58': 'u', '\u1d5b': 'v', '\u02b7': 'w', '\u02e3': 'x', '\u02b8': 'y',
  '\u1dbb': 'z'
};

const SUBSCRIPT_CHAR_MAP = {
  '\u2080': '0', '\u2081': '1', '\u2082': '2', '\u2083': '3', '\u2084': '4',
  '\u2085': '5', '\u2086': '6', '\u2087': '7', '\u2088': '8', '\u2089': '9',
  '\u208a': '+', '\u208b': '-', '\u208c': '=', '\u208d': '(', '\u208e': ')',
  '\u2090': 'a', '\u2091': 'e', '\u2092': 'o', '\u2093': 'x', '\u2094': 'schwa',
  '\u2095': 'h', '\u2096': 'k', '\u2097': 'l', '\u2098': 'm', '\u2099': 'n',
  '\u209a': 'p', '\u209b': 's', '\u209c': 't'
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
  let value = (text || '').trim();
  if (!value) {
    return '';
  }
  if (value.startsWith('$$') && value.endsWith('$$') && value.length > 4) {
    value = value.slice(2, -2).trim();
  } else if (value.startsWith('$') && value.endsWith('$') && value.length > 2) {
    value = value.slice(1, -1).trim();
  } else if (value.startsWith('\\(') && value.endsWith('\\)') && value.length > 4) {
    value = value.slice(2, -2).trim();
  } else if (value.startsWith('\\[') && value.endsWith('\\]') && value.length > 4) {
    value = value.slice(2, -2).trim();
  }
  return value;
}

function convertScriptCharsToLatex(text, scriptMap, marker) {
  let result = '';
  let buffer = '';

  for (const ch of text) {
    const mapped = scriptMap[ch];
    if (mapped) {
      buffer += mapped;
      continue;
    }

    if (buffer) {
      result += `${marker}{${buffer}}`;
      buffer = '';
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
    .replace(/\s*\(\s*/g, '(')
    .replace(/\s*\)\s*/g, ')')
    .replace(/\s*\-\s*/g, '-')
    .replace(/\s*=\s*/g, '=')
    .replace(/\s+!/g, '!')
    .replace(/\s*\^\s*/g, '^')
    .replace(/\s*_\s*/g, '_');

  value = value.replace(/([A-Za-z])\(n\)\(([A-Za-z])\)/g, '$1^{(n)}($2)');
  value = value.replace(/\(x-a\)\s*n\b/g, '(x-a)^n');

  if (!/\\sum/.test(value)) {
    value = value.replace(/n=0\s*\\infty/g, '\\sum_{n=0}^{\\infty}');
    value = value.replace(/\bn=0\s*\\infty/g, '\\sum_{n=0}^{\\infty}');
  }

  value = value.replace(/\\sum\s*\{?\s*n\s*=\s*0\s*\}?\s*\^?\s*\\infty/g, '\\sum_{n=0}^{\\infty}');

  if (/f\^\{\(n\)\}\(a\)/.test(value) && /n!/.test(value) && !/\\frac\{/.test(value)) {
    value = value.replace(/f\^\{\(n\)\}\(a\)\s*n!/g, '\\frac{f^{(n)}(a)}{n!}');
  }

  value = value
    .replace(/\(\s*x\s*\)/g, '(x)')
    .replace(/\(\s*a\s*\)/g, '(a)')
    .replace(/\(\s*n\s*\)/g, '(n)')
    .replace(/\s+/g, ' ')
    .trim();

  return value;
}

function scoreLatexCandidate(text) {
  if (!text) {
    return -100;
  }

  let score = 0;
  if (/\\sum/.test(text)) {
    score += 4;
  }
  if (/\\sum_\{[^}]+\}\^\{[^}]+\}/.test(text)) {
    score += 4;
  }
  if (/\\frac\{[^}]+\}\{[^}]+\}/.test(text)) {
    score += 4;
  }
  if (/\\infty/.test(text)) {
    score += 2;
  }
  if (/\^[{(]?[A-Za-z0-9]+/.test(text)) {
    score += 2;
  }
  if (/_\{[^}]+\}/.test(text)) {
    score += 2;
  }
  if (/[A-Za-z]\^\{\(n\)\}/.test(text)) {
    score += 2;
  }
  if (/\(x-a\)\^n/.test(text)) {
    score += 2;
  }
  if (/n\s*=\s*0\s*\\infty/.test(text)) {
    score -= 4;
  }
  if (/\\sum\s+n\s*=/.test(text)) {
    score -= 3;
  }
  if (/\s{2,}/.test(text)) {
    score -= 1;
  }

  return score;
}

function normalizeFormulaTextToLatex(text) {
  let value = stripMathDelimiters((text || '').replace(/[\r\n\f]+/g, ' ').trim());
  if (!value) {
    return '';
  }

  value = value.normalize('NFKD');
  value = replaceMathSymbolsWithLatex(value);
  value = convertScriptCharsToLatex(value, SUPERSCRIPT_CHAR_MAP, '^');
  value = convertScriptCharsToLatex(value, SUBSCRIPT_CHAR_MAP, '_');
  value = repairCommonFormulaPatterns(value);
  value = value.replace(/\s+/g, ' ').trim();

  value = value.replace(/\\sum\s*([a-zA-Z]\s*=\s*[^\\\s]+)\s*\\infty/g, '\\sum_{$1}^{\\infty}');
  value = value.replace(/\\sum_\{\s*([a-zA-Z])\s*=\s*([^}]+)\s*\}\^\{\s*\\infty\s*\}/g, '\\sum_{$1=$2}^{\\infty}');

  if (/\\sum_\{n=0\}\^\{\\infty\}/.test(value) && /f\^\{\(n\)\}\(a\)/.test(value) && /\(x-a\)\^n/.test(value) && !/\\frac\{/.test(value)) {
    value = value.replace(/f\^\{\(n\)\}\(a\)\s*n!/g, '\\frac{f^{(n)}(a)}{n!}');
  }

  return value;
}

function normalizeParsedRun(run) {
  if (!run || !run.text) {
    return run;
  }

  const text = run.text;
  const rStyle = run.rStyle || DEFAULT_RSTYLE;
  const fontName = rStyle[RSTYLE.FONT_NAME] || '';
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
    formulaFormat: 'latex'
  };
}

function extractFormulaRunsFromRange(paraRange) {
  const formulaRuns = [];
  if (!paraRange) {
    return formulaRuns;
  }

  try {
    const oMaths = paraRange.OMaths;
    if (!oMaths || oMaths.Count <= 0) {
      return formulaRuns;
    }

    for (let i = 1; i <= oMaths.Count; i++) {
      try {
        const oMath = oMaths.Item(i);
        const formulaRange = oMath.Range;
        if (!formulaRange) {
          continue;
        }

        let originalFormulaText = '';
        try {
          originalFormulaText = cleanText(formulaRange.Text || '');
        } catch (e) {}

        let linearFormulaText = '';
        try {
          oMath.Linearize();
          const linearText = cleanText(formulaRange.Text || '');
          if (linearText) {
            linearFormulaText = linearText;
          }
        } catch (e) {}

        try {
          oMath.BuildUp();
        } catch (e) {}

        const originalLatex = normalizeFormulaTextToLatex(originalFormulaText);
        const linearLatex = normalizeFormulaTextToLatex(linearFormulaText);

        let latexText = originalLatex;
        if (scoreLatexCandidate(linearLatex) > scoreLatexCandidate(originalLatex)) {
          latexText = linearLatex;
        }

        if (!latexText) {
          continue;
        }

        const font = formulaRange.Font || {};
        formulaRuns.push({
          start: formulaRange.Start,
          end: formulaRange.End,
          text: latexText,
          rStyle: makeRStyle(
            font.Name || 'Cambria Math',
            font.Size || 12,
            false,
            true,
            0,
            '#000000',
            getRGBColor(font.Color),
            0,
            false,
            false,
            false
          ),
          isFormula: true,
          formulaFormat: 'latex'
        });
      } catch (e) {}
    }
  } catch (e) {}

  formulaRuns.sort((a, b) => a.start - b.start);
  return formulaRuns;
}

// ============== 图片处理 ==============

function getImageExportTempDir() {
  let dir = '';

  try {
    if (typeof window.__WENCE_TEMP_DIR__ === 'string' && window.__WENCE_TEMP_DIR__.trim()) {
      dir = window.__WENCE_TEMP_DIR__.trim();
    }
  } catch (e) {}

  if (!dir) {
    try {
      const cached = localStorage.getItem('wence_temp_dir');
      if (cached && cached.trim()) {
        dir = cached.trim();
      }
    } catch (e) {}
  }

  if (!dir) {
    dir = window.Application.Options.DefaultFilePath(2) || '/tmp';
  }

  return dir.replace(/\\/g, '/').replace(/[\/]+$/, '');
}

/**
 * 导出图片到临时文件
 * @param {Object} shape - InlineShape 或 Shape 对象
 * @returns {Object} - {tempPath, saved} 或 {sourcePath, saved}
 */
function exportImageToTemp(shape) {
  try {
    shape.Select();
    window.Application.Selection.Copy();

    const tempDir = getImageExportTempDir();
    const timestamp = Date.now();
    const tempPath = `${tempDir}/wps_img_${timestamp}.png`;

    try {
      if (shape.SaveAsPicture) {
        shape.SaveAsPicture(tempPath);
        return { tempPath: tempPath, saved: true };
      }
    } catch (e) {
      console.log('SaveAsPicture 不可用:', e);
    }

    try {
      if (shape.LinkFormat && shape.LinkFormat.SourceFullName) {
        return { sourcePath: shape.LinkFormat.SourceFullName, saved: false };
      }
    } catch (e) {}

    return { saved: false };
  } catch (e) {
    console.log('导出图片出错:', e);
    return { saved: false };
  }
}

// ============== 解析函数 ==============

/**
 * 解析表格单元格内的复杂段落格式
 * @param {Object} cellRange - 单元格 Range 对象
 * @param {Object} doc - 文档对象
 * @returns {Array} - 段落数组
 */
function parseCellParagraphs(cellRange, doc) {
  const paragraphs = [];
  try {
    const cellParas = cellRange.Paragraphs;
    if (cellParas && cellParas.Count > 0) {
      for (let p = 1; p <= cellParas.Count; p++) {
        const para = cellParas.Item(p);
        const paraRange = para.Range;
        const paraText = cleanText(paraRange.Text);

        if (!paraText || paraText.match(/^[\r\n]*$/)) {
          continue;
        }

        const paraData = {
          text: paraText,
          pStyle: [
            getAlignmentName(para.Format.Alignment),
            para.Format.LineSpacing || 0,
            para.Format.LeftIndent || 0,
            para.Format.RightIndent || 0,
            para.Format.FirstLineIndent || 0,
            para.Format.SpaceBefore || 0,
            para.Format.SpaceAfter || 0,
            '',
            para.Format.LineSpacingRule || 0
          ],
          runs: []
        };

        // 解析 runs
        try {
          const chars = paraRange.Characters;
          if (chars && chars.Count > 0) {
            const formulaRuns = extractFormulaRunsFromRange(paraRange);
            let formulaRunIndex = 0;
            let activeFormulaEnd = -1;
            let lastFormat = null;
            let currentRun = null;

            for (let c = 1; c <= chars.Count; c++) {
              const char = chars.Item(c);
              const charText = char.Text;

              if (!charText || charText.match(/^[\r\n\u0007]$/)) {
                continue;
              }

              const charStart = typeof char.Start === 'number' ? char.Start : null;
              if (charStart !== null && formulaRuns.length > 0) {
                while (formulaRunIndex < formulaRuns.length && charStart >= formulaRuns[formulaRunIndex].end) {
                  formulaRunIndex++;
                }

                const currentFormula = formulaRuns[formulaRunIndex];
                if (currentFormula && charStart >= currentFormula.start && charStart < currentFormula.end) {
                  if (currentRun && currentRun.text) {
                    currentRun.text = cleanCellText(currentRun.text);
                    if (currentRun.text) {
                      paraData.runs.push(normalizeParsedRun(currentRun));
                    }
                  }

                  if (activeFormulaEnd !== currentFormula.end) {
                    const formulaRunData = { ...currentFormula };
                    delete formulaRunData.start;
                    delete formulaRunData.end;
                    paraData.runs.push(formulaRunData);
                    activeFormulaEnd = currentFormula.end;
                  }

                  currentRun = null;
                  lastFormat = null;
                  continue;
                }
              }

              const font = char.Font;
              const formatKey = `${font.Name}_${font.Size}_${font.Bold}_${font.Italic}_${font.Color}`;

              if (formatKey !== lastFormat) {
                if (currentRun && currentRun.text) {
                  currentRun.text = cleanCellText(currentRun.text);
                  if (currentRun.text) {
                    paraData.runs.push(normalizeParsedRun(currentRun));
                  }
                }
                currentRun = {
                  text: charText,
                  rStyle: makeRStyle(
                    font.Name || '',
                    font.Size || 12,
                    font.Bold === -1 || font.Bold === true,
                    font.Italic === -1 || font.Italic === true,
                    font.Underline || 0,
                    getRGBColor(font.UnderlineColor),
                    getRGBColor(font.Color),
                    0,
                    false,
                    false,
                    false
                  )
                };
                lastFormat = formatKey;
              } else if (currentRun) {
                currentRun.text += charText;
              }
            }

            if (currentRun && currentRun.text) {
              currentRun.text = cleanCellText(currentRun.text);
              if (currentRun.text) {
                paraData.runs.push(normalizeParsedRun(currentRun));
              }
            }
          }
        } catch (e) {
          const font = paraRange.Font;
          paraData.runs.push(normalizeParsedRun({
            text: paraText,
            rStyle: makeRStyle(
              font.Name || '',
              font.Size || 12,
              font.Bold === -1 || font.Bold === true,
              font.Italic === -1 || font.Italic === true,
              'none',
              '#000000',
              'none',
              false,
              false,
              false
            )
          }));
        }

        if (paraData.runs.length > 0) {
          paragraphs.push(paraData);
        }
      }
    }
  } catch (e) {
    console.log('解析单元格段落出错:', e);
  }
  return paragraphs;
}

/**
 * 解析表格（含合并单元格检测）
 * @param {Object} table - WPS Table 对象
 * @returns {Object} - 表格数据
 */
function parseTable(table) {
  const tableRange = table.Range;
  const tableData = {
    rows: table.Rows.Count,
    columns: table.Columns.Count,
    cells: [],
    tStyle: [getTableAlignmentName(table.Rows.Alignment)]  // 表格样式数组
  };

  // 捕获列宽
  try {
    const columnWidths = [];
    for (let c = 1; c <= table.Columns.Count; c++) {
      try {
        columnWidths.push(table.Columns.Item(c).Width);
      } catch (e) {
        columnWidths.push(0);
      }
    }
    if (columnWidths.some(w => w > 0)) {
      tableData.columnWidths = columnWidths;
    }
  } catch (e) {}

  // 捕获行高
  try {
    const rowHeights = [];
    for (let r = 1; r <= table.Rows.Count; r++) {
      try {
        const row = table.Rows.Item(r);
        rowHeights.push([row.Height || 0, row.HeightRule || 0]);
      } catch (e) {
        rowHeights.push([0, 0]);
      }
    }
    if (rowHeights.some(h => h[0] > 0 && h[1] > 0)) {
      tableData.rowHeights = rowHeights;
    }
  } catch (e) {}

  // 第一阶段：收集原始单元格
  const rawCells = [];
  for (let row = 1; row <= table.Rows.Count; row++) {
    const rowData = [];
    for (let col = 1; col <= table.Columns.Count; col++) {
      try {
        const cell = table.Cell(row, col);
        const cellRange = cell.Range;
        const cellText = cleanText(cellRange.Text);
        const paragraphs = parseCellParagraphs(cellRange, null);
        const cellFont = cellRange.Font;

        rowData.push({
          text: cellText,
          paragraphs: paragraphs.length > 0 ? paragraphs : undefined,
          rStyle: makeRStyle(
            cellFont.Name || '',
            cellFont.Size || 12,
            cellFont.Bold === -1 || cellFont.Bold === true,
            cellFont.Italic === -1 || cellFont.Italic === true,
            0, '#000000', '#000000', 0, false, false, false
          ),
          cStyle: makeCStyle(
            1, 1,
            getAlignmentName(cellRange.ParagraphFormat.Alignment),
            getCellVerticalAlignmentName(cell.VerticalAlignment)
          ),
          exists: true
        });
      } catch (e) {
        rowData.push({ exists: false });
      }
    }
    rawCells.push(rowData);
  }

  // 第二阶段：分析合并，计算 rowSpan 和 colSpan
  for (let row = 0; row < rawCells.length; row++) {
    const rowData = [];
    for (let col = 0; col < rawCells[row].length; col++) {
      const rawCell = rawCells[row][col];

      if (!rawCell.exists) {
        rowData.push({ text: '', rowSpan: 0, colSpan: 0 });
        continue;
      }

      // 计算 colSpan
      let colSpan = 1;
      for (let c = col + 1; c < rawCells[row].length; c++) {
        if (!rawCells[row][c].exists) {
          colSpan++;
        } else {
          break;
        }
      }

      // 计算 rowSpan
      let rowSpan = 1;
      for (let r = row + 1; r < rawCells.length; r++) {
        let allNotExist = true;
        for (let c = col; c < col + colSpan && c < rawCells[r].length; c++) {
          if (rawCells[r][c].exists) {
            allNotExist = false;
            break;
          }
        }
        if (allNotExist && !rawCells[r][col].exists) {
          rowSpan++;
        } else {
          break;
        }
      }

      const cStyle = rawCell.cStyle || DEFAULT_CSTYLE;
      rowData.push({
        text: rawCell.text,
        paragraphs: rawCell.paragraphs,
        rStyle: rawCell.rStyle,
        cStyle: makeCStyle(
          rowSpan,
          colSpan,
          cStyle[CSTYLE.ALIGNMENT] || 'left',
          cStyle[CSTYLE.VERTICAL_ALIGNMENT] || 'center'
        )
      });
    }
    tableData.cells.push(rowData);
  }

  return tableData;
}

/**
 * 通过二分查找确定表格 endParaIndex：
 * 在排序数组 paraStartsSorted 中，找到第一个 >= tableRangeEnd 的段落索引 - 1
 * @param {number[]} paraStartsSorted - 所有段落 Range.Start 的排序数组
 * @param {number} tableRangeEnd - 表格 Range.End
 * @param {number} totalParaCount - 文档总段落数
 * @returns {number} - 表格占用的最后一个段落索引（0-based）
 */
function _findEndParaIndex(paraStartsSorted, tableRangeEnd, totalParaCount) {
  let lo = 0, hi = paraStartsSorted.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (paraStartsSorted[mid] < tableRangeEnd) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  // lo 是第一个 >= tableRangeEnd 的索引，表格最后一个段落是 lo - 1
  return lo > 0 ? lo - 1 : 0;
}

/**
 * 解析 Word 文档内容为 JSON
 * @param {Object} [range] - WPS Range 对象，省略时使用当前选区
 * @param {number} [startParaIndex] - 可选，起始全文段落索引（0-based），
 *   传入后走快速路径：O(k) 仅解析指定范围段落，忽略 range 参数
 * @param {number} [endParaIndex] - 可选，结束全文段落索引（0-based，含），
 *   省略时默认等于 startParaIndex（即只解析单段）；-1 表示解析到文档末尾
 * @returns {Object} - JSON 数据或错误对象
 */
function parseDocxToJSON(range, startParaIndex, endParaIndex) {
  try {
    // ========== 快速路径：按 paraIndex 范围解析 ==========
    if (startParaIndex !== undefined && startParaIndex !== null) {
      if (endParaIndex === undefined || endParaIndex === null) {
        endParaIndex = startParaIndex;
      }

      const doc = window.Application?.ActiveDocument;
      if (!doc) {
        return { error: '没有打开的文档' };
      }

      const totalParas = doc.Paragraphs.Count;

      // endParaIndex === -1 表示解析到文档末尾
      if (endParaIndex === -1) {
        endParaIndex = totalParas - 1;
      }

      // 超过文档总段落数时，自动截断到最后一个段落
      if (endParaIndex >= totalParas) {
        endParaIndex = totalParas - 1;
      }

      if (startParaIndex < 0 || startParaIndex >= totalParas) {
        return { error: `startParaIndex ${startParaIndex} 超出范围，文档共 ${totalParas} 段` };
      }
      if (endParaIndex < startParaIndex) {
        return { error: `endParaIndex ${endParaIndex} 无效（startParaIndex=${startParaIndex}，文档共 ${totalParas} 段）` };
      }

      // 收集表格范围用于排除表格内段落，并记录表格对象以便后续解析
      const tableRanges = [];
      const tableObjects = [];  // 保存需要解析的表格对象
      try {
        const tables = doc.Content.Tables;
        if (tables && tables.Count > 0) {
          for (let t = 1; t <= tables.Count; t++) {
            const tableObj = tables.Item(t);
            const tr = tableObj.Range;
            tableRanges.push({ start: tr.Start, end: tr.End });
            tableObjects.push({ table: tableObj, rangeStart: tr.Start, rangeEnd: tr.End });
          }
        }
      } catch (e) {}

      // 构建 paraStart → 全文段落索引 的映射（用于表格 paraIndex / endParaIndex）
      const paraStartToIndex = new Map();
      const paraStartsSorted = []; // 排序数组用于二分查找 endParaIndex
      const allParas = doc.Paragraphs;
      for (let pi = 1; pi <= allParas.Count; pi++) {
        const ps = allParas.Item(pi).Range.Start;
        paraStartToIndex.set(ps, pi - 1);
        paraStartsSorted.push(ps);
      }

      const result = { paragraphs: [], tables: [], fields: [] };

      // 解析范围内的段落起止位置
      const rangeStart = doc.Paragraphs.Item(startParaIndex + 1).Range.Start;
      const rangeEnd = doc.Paragraphs.Item(endParaIndex + 1).Range.End;
      const requestedRange = doc.Range(rangeStart, rangeEnd);

      // 解析范围内的表格（表格起始位置落在请求范围内）
      const parsedTableRanges = new Set();
      for (const tObj of tableObjects) {
        if (tObj.rangeStart >= rangeStart && tObj.rangeStart < rangeEnd) {
          try {
            const tableData = parseTable(tObj.table);
            tableData.paraIndex = paraStartToIndex.get(tObj.rangeStart) ?? -1;
            // 计算 endParaIndex：找到表格 Range.End 之后第一个段落的索引 - 1
            tableData.endParaIndex = _findEndParaIndex(paraStartsSorted, tObj.rangeEnd, allParas.Count);
            result.tables.push(tableData);
            parsedTableRanges.add(tObj.rangeStart);
          } catch (e) {}
        }
      }

      // 解析段落范围内的嵌入式图片
      function getInlineShapesInRange(paraRange) {
        const shapes = [];
        try {
          const inlineShapes = paraRange.InlineShapes;
          if (inlineShapes && inlineShapes.Count > 0) {
            for (let i = 1; i <= inlineShapes.Count; i++) {
              try {
                const shape = inlineShapes.Item(i);
                if (shape.Type === 3 || shape.Type === 1) {
                  shapes.push(shape);
                }
              } catch (e) {}
            }
          }
        } catch (e) {}
        return shapes;
      }

      // 解析段落范围内的浮动图片
      function getFloatingShapesInRange(paraRange) {
        const shapes = [];
        try {
          const shapes2 = paraRange.ShapeRange;
          if (shapes2 && shapes2.Count > 0) {
            for (let i = 1; i <= shapes2.Count; i++) {
              try {
                const shape = shapes2.Item(i);
                if ([13, 75, 3, 1].includes(shape.Type)) {
                  shapes.push(shape);
                }
              } catch (e) {}
            }
          }
        } catch (e) {}
        return shapes;
      }

      // 解析范围内的图片并收集到临时数组
      const inlineImages = [];
      const floatingImages = [];
      try {
        const allInlineShapes = requestedRange.InlineShapes;
        if (allInlineShapes && allInlineShapes.Count > 0) {
          for (let i = 1; i <= allInlineShapes.Count; i++) {
            try {
              const shape = allInlineShapes.Item(i);
              if (shape.Type === 3 || shape.Type === 1) {
                const imageInfo = exportImageToTemp(shape);
                inlineImages.push({
                  shape,
                  width: shape.Width || 100,
                  height: shape.Height || 100,
                  altText: shape.AlternativeText || '',
                  rangeStart: shape.Range ? shape.Range.Start : 0,
                  rangeEnd: shape.Range ? shape.Range.End : 0,
                  ...imageInfo
                });
              }
            } catch (e) {}
          }
        }
      } catch (e) {}
      try {
        const allShapes = requestedRange.ShapeRange;
        if (allShapes && allShapes.Count > 0) {
          for (let i = 1; i <= allShapes.Count; i++) {
            try {
              const shape = allShapes.Item(i);
              if ([13, 75, 3, 1].includes(shape.Type)) {
                const imageInfo = exportImageToTemp(shape);
                let anchorStart = 0;
                try {
                  anchorStart = shape.Anchor ? shape.Anchor.Start : 0;
                } catch (e) {
                  anchorStart = shape.Range ? shape.Range.Start : 0;
                }
                floatingImages.push({
                  shape,
                  type: 'floating',
                  width: shape.Width || 100,
                  height: shape.Height || 100,
                  left: shape.Left || 0,
                  top: shape.Top || 0,
                  wrapType: getWrapTypeName(shape.WrapFormat ? shape.WrapFormat.Type : 0),
                  altText: shape.AlternativeText || '',
                  anchorStart,
                  ...imageInfo
                });
              }
            } catch (e) {}
          }
        }
      } catch (e) {}

      for (let idx = startParaIndex; idx <= endParaIndex; idx++) {
        const para = doc.Paragraphs.Item(idx + 1); // WPS 1-based
        const paraRange = para.Range;
        const paraStart = paraRange.Start;
        const paraEnd = paraRange.End;

        // 跳过表格内段落
        let inTable = false;
        for (const tr of tableRanges) {
          if (paraStart >= tr.start && paraEnd <= tr.end) {
            inTable = true;
            break;
          }
        }
        if (inTable) {
          continue;
        }

        // 收集落在此段落范围内的图片
        const paraInlineImages = [];
        for (let i = inlineImages.length - 1; i >= 0; i--) {
          const img = inlineImages[i];
          if (img.rangeStart >= paraStart && img.rangeEnd <= paraEnd) {
            paraInlineImages.push(inlineImages.splice(i, 1)[0]);
          }
        }
        const paraFloatingImages = [];
        for (let i = floatingImages.length - 1; i >= 0; i--) {
          const img = floatingImages[i];
          if (img.anchorStart >= paraStart && img.anchorStart < paraEnd) {
            paraFloatingImages.push(floatingImages.splice(i, 1)[0]);
          }
        }

        const paraText = cleanText(paraRange.Text || '');

        // 空段落但有图片
        if ((!paraText || paraText.match(/^[\r\n\f\u0007]*$/)) && (paraInlineImages.length > 0 || paraFloatingImages.length > 0)) {
          result.paragraphs.push({ pStyle: DEFAULT_IMAGE_PSTYLE, runs: [], paraIndex: idx });
        }

        // 如果是空段落且没有图片
        if (!paraText || paraText.match(/^[\r\n\f\u0007]*$/)) {
          if (paraInlineImages.length === 0 && paraFloatingImages.length === 0) {
            result.paragraphs.push({ pStyle: '', runs: [], paraIndex: idx });
          }
          continue;
        }

        const paraFormat = para.Format;
        let styleName = '';
        try {
          styleName = para.Style.NameLocal || para.Style.Name || ''; 
        } catch (e) {}

        const paragraphData = {
          pStyle: [
            getAlignmentName(paraFormat.Alignment),
            paraFormat.LineSpacing || 0,
            paraFormat.LeftIndent || 0,
            paraFormat.RightIndent || 0,
            paraFormat.FirstLineIndent || 0,
            paraFormat.SpaceBefore || 0,
            paraFormat.SpaceAfter || 0,
            styleName,
            paraFormat.LineSpacingRule || 0
          ],
          runs: [],
          paraIndex: idx
        };

        // 解析 runs
        const chars = paraRange.Characters;
        if (chars && chars.Count > 0) {
          const formulaRuns = extractFormulaRunsFromRange(paraRange);
          let formulaRunIndex = 0;
          let activeFormulaEnd = -1;
          let lastFormat = null;
          let currentRun = null;

          for (let j = 1; j <= chars.Count; j++) {
            const char = chars.Item(j);
            const font = char.Font;
            const charText = char.Text || '';

            if (charText.match(/^[\r\n\f\u0007]+$/)) {
              continue;
            }

            const charStart = typeof char.Start === 'number' ? char.Start : null;
            if (charStart !== null && formulaRuns.length > 0) {
              while (formulaRunIndex < formulaRuns.length && charStart >= formulaRuns[formulaRunIndex].end) {
                formulaRunIndex++;
              }

              const currentFormula = formulaRuns[formulaRunIndex];
              if (currentFormula && charStart >= currentFormula.start && charStart < currentFormula.end) {
                if (currentRun && currentRun.text) {
                  paragraphData.runs.push(normalizeParsedRun(currentRun));
                }

                if (activeFormulaEnd !== currentFormula.end) {
                  const formulaRunData = { ...currentFormula };
                  delete formulaRunData.start;
                  delete formulaRunData.end;
                  paragraphData.runs.push(formulaRunData);
                  activeFormulaEnd = currentFormula.end;
                }

                currentRun = null;
                lastFormat = null;
                continue;
              }
            }

            let highlightIndex = 0;
            try {
              highlightIndex = char.HighlightColorIndex || 0; 
            } catch (e) {
              try {
                highlightIndex = font.HighlightColorIndex || 0; 
              } catch (e2) {}
            }

            const formatKey = [
              font.Name, font.Size, font.Bold, font.Italic,
              font.Underline, font.Color, highlightIndex,
              font.StrikeThrough, font.Superscript, font.Subscript
            ].join('|');

            if (formatKey === lastFormat && currentRun) {
              currentRun.text += charText;
            } else {
              if (currentRun && currentRun.text) {
                paragraphData.runs.push(normalizeParsedRun(currentRun));
              }
              currentRun = {
                text: charText,
                rStyle: makeRStyle(
                  font.Name || '', font.Size || 12,
                  font.Bold === -1 || font.Bold === true,
                  font.Italic === -1 || font.Italic === true,
                  font.Underline || 0,
                  getRGBColor(font.UnderlineColor),
                  getRGBColor(font.Color),
                  highlightIndex,
                  font.StrikeThrough === -1 || font.StrikeThrough === true,
                  font.Superscript === -1 || font.Superscript === true,
                  font.Subscript === -1 || font.Subscript === true
                )
              };
              lastFormat = formatKey;
            }
          }
          if (currentRun && currentRun.text) {
            paragraphData.runs.push(normalizeParsedRun(currentRun));
          }
        }

        // 在段落末尾添加 inline 图片 runs
        for (const img of paraInlineImages) {
          paragraphData.runs.push({
            width: img.width,
            height: img.height,
            altText: img.altText,
            tempPath: img.tempPath,
            sourcePath: img.sourcePath
          });
        }
        for (const img of paraFloatingImages) {
          paragraphData.runs.push({
            type: img.type,
            width: img.width,
            height: img.height,
            left: img.left,
            top: img.top,
            wrapType: img.wrapType,
            altText: img.altText,
            tempPath: img.tempPath,
            sourcePath: img.sourcePath
          });
        }

        if (paragraphData.runs.length > 0) {
          result.paragraphs.push(paragraphData);
        }
      }

      // 将剩余未分配的图片作为独立段落添加（理论上不应该发生）
      for (const img of inlineImages) {
        result.paragraphs.push({
          pStyle: DEFAULT_IMAGE_PSTYLE,
          runs: [{
            width: img.width,
            height: img.height,
            altText: img.altText,
            tempPath: img.tempPath,
            sourcePath: img.sourcePath
          }],
          paraIndex: -1
        });
      }
      for (const img of floatingImages) {
        result.paragraphs.push({
          pStyle: DEFAULT_IMAGE_PSTYLE,
          runs: [{
            type: img.type,
            width: img.width,
            height: img.height,
            left: img.left,
            top: img.top,
            wrapType: img.wrapType,
            altText: img.altText,
            tempPath: img.tempPath,
            sourcePath: img.sourcePath
          }],
          paraIndex: -1
        });
      }

      return deduplicateStyles(result);
    }

    // ========== 常规路径：解析 Range 或选区 ==========
    if (!range) {
      const selection = window.Application.Selection;
      if (!selection) {
        return { error: '没有选中内容' };
      }
      range = selection.Range;
      if (!range) {
        return { error: '无法获取选中范围' };
      }
    }

    const result = {
      paragraphs: [],
      tables: [],
      fields: []
    };

    // 解析域代码（检测目录等）
    try {
      const fields = range.Fields;
      if (fields && fields.Count > 0) {
        for (let i = 1; i <= fields.Count; i++) {
          const field = fields.Item(i);
          const fieldCode = field.Code.Text || '';
          const fieldType = field.Type;

          result.fields.push({
            type: fieldType,
            code: fieldCode.trim(),
            start: field.Code.Start,
            end: field.Result ? field.Result.End : field.Code.End
          });

          if (fieldType === 13 || fieldCode.toUpperCase().includes('TOC')) {
            result.hasTOC = true;
            result.tocFieldCode = fieldCode.trim();
          }
        }
      }
    } catch (e) {}

    // 构建 paraStart → 全文段落索引 的映射（O(n) 一次构建，后续 O(1) 查找）
    const doc = window.Application?.ActiveDocument;
    const paraStartToIndex = new Map();
    const paraStartsSorted = []; // 排序数组用于二分查找 endParaIndex
    let totalParaCount = 0;
    if (doc) {
      const allParas = doc.Paragraphs;
      totalParaCount = allParas.Count;
      for (let pi = 1; pi <= totalParaCount; pi++) {
        const ps = allParas.Item(pi).Range.Start;
        paraStartToIndex.set(ps, pi - 1); // 0-based
        paraStartsSorted.push(ps);
      }
    }

    // 解析表格，记录位置范围
    const tables = range.Tables;
    const tableRanges = [];
    if (tables && tables.Count > 0) {
      for (let i = 1; i <= tables.Count; i++) {
        const table = tables.Item(i);
        const tableRange = table.Range;
        tableRanges.push({ start: tableRange.Start, end: tableRange.End });
        const tableData = parseTable(table);
        tableData.paraIndex = paraStartToIndex.get(tableRange.Start) ?? -1;
        tableData.endParaIndex = _findEndParaIndex(paraStartsSorted, tableRange.End, totalParaCount);
        result.tables.push(tableData);
      }
    }

    // 收集所有图片到临时数组
    const inlineImages = [];
    const floatingImages = [];
    try {
      const inlineShapes = range.InlineShapes;
      if (inlineShapes && inlineShapes.Count > 0) {
        for (let i = 1; i <= inlineShapes.Count; i++) {
          try {
            const shape = inlineShapes.Item(i);
            if (shape.Type === 3 || shape.Type === 1) {
              const imageInfo = exportImageToTemp(shape);
              inlineImages.push({
                shape,
                width: shape.Width || 100,
                height: shape.Height || 100,
                altText: shape.AlternativeText || '',
                rangeStart: shape.Range ? shape.Range.Start : 0,
                rangeEnd: shape.Range ? shape.Range.End : 0,
                ...imageInfo
              });
            }
          } catch (e) {}
        }
      }
    } catch (e) {}
    try {
      const shapes = range.ShapeRange;
      if (shapes && shapes.Count > 0) {
        for (let i = 1; i <= shapes.Count; i++) {
          try {
            const shape = shapes.Item(i);
            if ([13, 75, 3, 1].includes(shape.Type)) {
              const imageInfo = exportImageToTemp(shape);
              let anchorStart = 0;
              try {
                anchorStart = shape.Anchor ? shape.Anchor.Start : 0;
              } catch (e) {
                anchorStart = shape.Range ? shape.Range.Start : 0;
              }
              floatingImages.push({
                shape,
                type: 'floating',
                width: shape.Width || 100,
                height: shape.Height || 100,
                left: shape.Left || 0,
                top: shape.Top || 0,
                wrapType: getWrapTypeName(shape.WrapFormat ? shape.WrapFormat.Type : 0),
                altText: shape.AlternativeText || '',
                anchorStart,
                ...imageInfo
              });
            }
          } catch (e) {}
        }
      }
    } catch (e) {}

    // 解析段落（排除表格内的）
    const paragraphs = range.Paragraphs;
    if (paragraphs && paragraphs.Count > 0) {

      for (let i = 1; i <= paragraphs.Count; i++) {
        const para = paragraphs.Item(i);
        const paraRange = para.Range;
        const paraStart = paraRange.Start;
        const paraEnd = paraRange.End;

        // // ====== DEBUG: 输出段落的各种属性 ======
        // try {
        //   const paraFormat = para.Format;
        //   let styleName = '', styleNameLocal = '', styleType = '';
        //   try {
        //     styleName = para.Style?.Name || '';
        //     styleNameLocal = para.Style?.NameLocal || '';
        //     styleType = para.Style?.Type;
        //   } catch (e) {}

        //   const globalParagraphIndex = paraStartToIndex.has(paraStart) ? paraStartToIndex.get(paraStart) : '未找到';

        //   console.log(`===== 段落 [范围内第${i}个] =====`);
        //   console.log(`  全文段落索引: ${globalParagraphIndex}`);
        //   console.log(`  Range.Start: ${paraStart}, Range.End: ${paraEnd}, 长度: ${paraEnd - paraStart}`);
        //   console.log(`  文本预览: "${(para.Range.Text || '').substring(0, 80).replace(/[\r\n]/g, '\\n')}"`);
        //   console.log(`  Style.Name: "${styleName}", Style.NameLocal: "${styleNameLocal}", Style.Type: ${styleType}`);
        //   console.log(`  Format.Alignment: ${paraFormat.Alignment}`);
        //   console.log(`  Format.LineSpacing: ${paraFormat.LineSpacing}, LineSpacingRule: ${paraFormat.LineSpacingRule}`);
        //   console.log(`  Format.LeftIndent: ${paraFormat.LeftIndent}, RightIndent: ${paraFormat.RightIndent}, FirstLineIndent: ${paraFormat.FirstLineIndent}`);
        //   console.log(`  Format.SpaceBefore: ${paraFormat.SpaceBefore}, SpaceAfter: ${paraFormat.SpaceAfter}`);
        //   console.log(`  Format.OutlineLevel: ${paraFormat.OutlineLevel}`);

        //   // 尝试探测更多属性
        //   try { console.log(`  Format.KeepTogether: ${paraFormat.KeepTogether}`); } catch (e) {}
        //   try { console.log(`  Format.KeepWithNext: ${paraFormat.KeepWithNext}`); } catch (e) {}
        //   try { console.log(`  Format.PageBreakBefore: ${paraFormat.PageBreakBefore}`); } catch (e) {}
        //   try { console.log(`  Format.WidowControl: ${paraFormat.WidowControl}`); } catch (e) {}
        //   try { console.log(`  Format.CharacterUnitFirstLineIndent: ${paraFormat.CharacterUnitFirstLineIndent}`); } catch (e) {}
        //   try { console.log(`  Format.CharacterUnitLeftIndent: ${paraFormat.CharacterUnitLeftIndent}`); } catch (e) {}
        //   try { console.log(`  Format.CharacterUnitRightIndent: ${paraFormat.CharacterUnitRightIndent}`); } catch (e) {}
        //   try { console.log(`  Format.LineUnitBefore: ${paraFormat.LineUnitBefore}`); } catch (e) {}
        //   try { console.log(`  Format.LineUnitAfter: ${paraFormat.LineUnitAfter}`); } catch (e) {}
        //   try { console.log(`  Format.Borders: ${paraFormat.Borders}`); } catch (e) {}
        //   try { console.log(`  Format.Shading.BackgroundPatternColor: ${paraFormat.Shading?.BackgroundPatternColor}`); } catch (e) {}
        //   try { console.log(`  Format.TabStops.Count: ${paraFormat.TabStops?.Count}`); } catch (e) {}

        //   // 段落级别额外属性
        //   try { console.log(`  para.ID: ${para.ID}`); } catch (e) {}
        //   try { console.log(`  para.ParaID: ${para.ParaID}`); } catch (e) {}

        //   // Range 上的额外属性
        //   try { console.log(`  Range.ListFormat.ListType: ${paraRange.ListFormat?.ListType}`); } catch (e) {}
        //   try { console.log(`  Range.ListFormat.ListLevelNumber: ${paraRange.ListFormat?.ListLevelNumber}`); } catch (e) {}
        //   try { console.log(`  Range.ListFormat.ListString: "${paraRange.ListFormat?.ListString}"`); } catch (e) {}
        //   try { console.log(`  Range.ListFormat.ListValue: ${paraRange.ListFormat?.ListValue}`); } catch (e) {}
        //   try { console.log(`  Range.LanguageID: ${paraRange.LanguageID}`); } catch (e) {}
        //   try { console.log(`  Range.Characters.Count: ${paraRange.Characters?.Count}`); } catch (e) {}
        //   try { console.log(`  Range.Words.Count: ${paraRange.Words?.Count}`); } catch (e) {}
        //   try { console.log(`  Range.Sentences.Count: ${paraRange.Sentences?.Count}`); } catch (e) {}
        //   try { console.log(`  Range.BookmarkID: ${paraRange.BookmarkID}`); } catch (e) {}
        //   try { console.log(`  Range.SectionNumber: ${paraRange.Information(10)}`); } catch (e) {} // wdActiveEndSectionNumber
        //   try { console.log(`  Range.PageNumber: ${paraRange.Information(3)}`); } catch (e) {}  // wdActiveEndPageNumber
        //   try { console.log(`  Range.LineNumber: ${paraRange.Information(5)}`); } catch (e) {}  // wdFirstCharacterLineNumber

        //   console.log(`  ---- END 段落 ${i} ----`);
        // } catch (debugErr) {
        //   console.log(`  [DEBUG ERROR] 段落 ${i}: ${debugErr.message}`);
        // }
        // // ====== END DEBUG ======

        // 跳过表格内段落
        let inTable = false;
        for (const tr of tableRanges) {
          if (paraStart >= tr.start && paraEnd <= tr.end) {
            inTable = true;
            break;
          }
        }
        if (inTable) {
          continue;
        }

        // 收集落在此段落范围内的图片
        const paraInlineImages = [];
        for (let i = inlineImages.length - 1; i >= 0; i--) {
          const img = inlineImages[i];
          if (img.rangeStart >= paraStart && img.rangeEnd <= paraEnd) {
            paraInlineImages.push(inlineImages.splice(i, 1)[0]);
          }
        }
        const paraFloatingImages = [];
        for (let i = floatingImages.length - 1; i >= 0; i--) {
          const img = floatingImages[i];
          if (img.anchorStart >= paraStart && img.anchorStart < paraEnd) {
            paraFloatingImages.push(floatingImages.splice(i, 1)[0]);
          }
        }

        const paraText = para.Range.Text || '';

        // 空段落但有图片
        if ((!paraText || paraText.match(/^[\r\n\f\u0007]*$/)) && (paraInlineImages.length > 0 || paraFloatingImages.length > 0)) {
          result.paragraphs.push({ pStyle: DEFAULT_IMAGE_PSTYLE, runs: [], paraIndex: paraStartToIndex.get(paraStart) ?? -1 });
        }

        // 空段落且没有图片
        if (paraText.match(/^[\r\n\f\u0007]*$/)) {
          if (paraInlineImages.length === 0 && paraFloatingImages.length === 0) {
            result.paragraphs.push({
              pStyle: '',
              runs: [],
              paraIndex: paraStartToIndex.get(paraStart) ?? -1
            });
          }
          continue;
        }

        const paraFormat = para.Format;
        let styleName = '';
        try {
          styleName = para.Style.NameLocal || para.Style.Name || '';
        } catch (e) {}

        const paragraphData = {
          // text: cleanText(paraText),
          pStyle: [
            getAlignmentName(paraFormat.Alignment),
            paraFormat.LineSpacing || 0,
            paraFormat.LeftIndent || 0,
            paraFormat.RightIndent || 0,
            paraFormat.FirstLineIndent || 0,
            paraFormat.SpaceBefore || 0,
            paraFormat.SpaceAfter || 0,
            styleName,
            paraFormat.LineSpacingRule || 0
          ],
          runs: [],
          paraIndex: paraStartToIndex.get(paraStart) ?? -1
        };

        // 解析 runs - 使用Characters确保捕获Tab等特殊字符
        const chars = paraRange.Characters;
        if (chars && chars.Count > 0) {
          const formulaRuns = extractFormulaRunsFromRange(paraRange);
          let formulaRunIndex = 0;
          let activeFormulaEnd = -1;
          let lastFormat = null;
          let currentRun = null;

          for (let j = 1; j <= chars.Count; j++) {
            const char = chars.Item(j);
            const font = char.Font;
            const charText = char.Text || '';

            // 跳过段落结束符等，但保留Tab
            if (charText.match(/^[\r\n\f\u0007]+$/)) {
              continue;
            }

            const charStart = typeof char.Start === 'number' ? char.Start : null;
            if (charStart !== null && formulaRuns.length > 0) {
              while (formulaRunIndex < formulaRuns.length && charStart >= formulaRuns[formulaRunIndex].end) {
                formulaRunIndex++;
              }

              const currentFormula = formulaRuns[formulaRunIndex];
              if (currentFormula && charStart >= currentFormula.start && charStart < currentFormula.end) {
                if (currentRun && currentRun.text) {
                  paragraphData.runs.push(normalizeParsedRun(currentRun));
                }

                if (activeFormulaEnd !== currentFormula.end) {
                  const formulaRunData = { ...currentFormula };
                  delete formulaRunData.start;
                  delete formulaRunData.end;
                  paragraphData.runs.push(formulaRunData);
                  activeFormulaEnd = currentFormula.end;
                }

                currentRun = null;
                lastFormat = null;
                continue;
              }
            }

            // 获取高亮颜色（使用 Range 的 HighlightColorIndex）
            let highlightIndex = 0;
            try {
              const charRange = char;
              highlightIndex = charRange.HighlightColorIndex || 0;
            } catch (e) {
              // 如果失败，尝试从 Font 获取
              try {
                highlightIndex = font.HighlightColorIndex || 0;
              } catch (e2) {}
            }

            const formatKey = [
              font.Name,
              font.Size,
              font.Bold,
              font.Italic,
              font.Underline,
              font.Color,
              highlightIndex,
              font.StrikeThrough,
              font.Superscript,
              font.Subscript
            ].join('|');

            if (formatKey === lastFormat && currentRun) {
              currentRun.text += charText;
            } else {
              if (currentRun && currentRun.text) {
                paragraphData.runs.push(normalizeParsedRun(currentRun));
              }
              currentRun = {
                text: charText,
                rStyle: makeRStyle(
                  font.Name || '',
                  font.Size || 12,
                  font.Bold === -1 || font.Bold === true,
                  font.Italic === -1 || font.Italic === true,
                  font.Underline || 0,
                  getRGBColor(font.UnderlineColor),
                  getRGBColor(font.Color),
                  highlightIndex,
                  font.StrikeThrough === -1 || font.StrikeThrough === true,
                  font.Superscript === -1 || font.Superscript === true,
                  font.Subscript === -1 || font.Subscript === true
                )
              };
              lastFormat = formatKey;
            }
          }
          if (currentRun && currentRun.text) {
            paragraphData.runs.push(normalizeParsedRun(currentRun));
          }
        }

        // 在段落末尾添加 inline 图片 runs
        for (const img of paraInlineImages) {
          paragraphData.runs.push({
            width: img.width,
            height: img.height,
            altText: img.altText,
            tempPath: img.tempPath,
            sourcePath: img.sourcePath
          });
        }
        for (const img of paraFloatingImages) {
          paragraphData.runs.push({
            type: img.type,
            width: img.width,
            height: img.height,
            left: img.left,
            top: img.top,
            wrapType: img.wrapType,
            altText: img.altText,
            tempPath: img.tempPath,
            sourcePath: img.sourcePath
          });
        }

        if (paragraphData.runs.length > 0) {
          result.paragraphs.push(paragraphData);
        }
      }
    }

    // 将剩余未分配的图片作为独立段落添加
    for (const img of inlineImages) {
      result.paragraphs.push({
        pStyle: DEFAULT_IMAGE_PSTYLE,
        runs: [{
          width: img.width,
          height: img.height,
          altText: img.altText,
          tempPath: img.tempPath,
          sourcePath: img.sourcePath
        }],
        paraIndex: -1
      });
    }
    for (const img of floatingImages) {
      result.paragraphs.push({
        pStyle: DEFAULT_IMAGE_PSTYLE,
        runs: [{
          type: img.type,
          width: img.width,
          height: img.height,
          left: img.left,
          top: img.top,
          wrapType: img.wrapType,
          altText: img.altText,
          tempPath: img.tempPath,
          sourcePath: img.sourcePath
        }],
        paraIndex: -1
      });
    }

    return deduplicateStyles(result);
  } catch (error) {
    return { error: '解析失败: ' + error.message };
  }
}

// ============== 生成函数 ==============

/**
 * 在指定位置插入图片
 * @param {Object} doc - 文档对象
 * @param {Object} img - 图片数据
 * @param {number} insertPos - 插入位置
 * @returns {number} - 插入后增加的字符数
 */
function insertImage(doc, img, insertPos, maxWidth) {
  try {
    const imagePath = img.tempPath || img.sourcePath || img.url;
    if (!imagePath) {
      return 0;
    }

    const insertRange = doc.Range(insertPos, insertPos);
    const constrainedSize = normalizeImageSizeByMaxWidth(img, maxWidth);

    if (img.type === 'inline') {
      try {
        const inlineShape = doc.InlineShapes.AddPicture(imagePath, false, true, insertRange);
        if (constrainedSize.width) {
          inlineShape.Width = constrainedSize.width;
        }
        if (constrainedSize.height) {
          inlineShape.Height = constrainedSize.height;
        }
        if (img.altText) {
          inlineShape.AlternativeText = img.altText;
        }
        return 1;
      } catch (e) {
        console.log('插入嵌入式图片失败:', e);
        return 0;
      }
    } else if (img.type === 'floating') {
      try {
        const inlineShape = doc.InlineShapes.AddPicture(imagePath, false, true, insertRange);
        const shape = inlineShape.ConvertToShape();
        if (constrainedSize.width) {
          shape.Width = constrainedSize.width;
        }
        if (constrainedSize.height) {
          shape.Height = constrainedSize.height;
        }
        if (img.left !== undefined) {
          shape.Left = img.left;
        }
        if (img.top !== undefined) {
          shape.Top = img.top;
        }
        if (img.altText) {
          shape.AlternativeText = img.altText;
        }
        if (img.wrapType && shape.WrapFormat) {
          shape.WrapFormat.Type = getWrapTypeValue(img.wrapType);
        }
        return 1;
      } catch (e) {
        console.log('插入浮动图片失败:', e);
        return 0;
      }
    }
    return 0;
  } catch (e) {
    return 0;
  }
}

/**
 * 生成表格
 * @param {Object} doc - 文档对象
 * @param {Object} tableData - 表格数据
 * @param {number} currentPos - 当前位置
 * @returns {number} - 新的位置
 */
function generateTable(doc, tableData, currentPos, styles) {
  // 在表格前添加换行
  if (currentPos > 0) {
    const range = doc.Range(currentPos, currentPos);
    range.Text = '\r';
    currentPos += 1;
  }

  const tableRange = doc.Range(currentPos, currentPos);
  const table = doc.Tables.Add(tableRange, tableData.rows, tableData.columns);

  try {
    table.Borders.Enable = true;
  } catch (e) {}

  // 设置表格宽度
  try {
    let pageWidth = 425;
    try {
      const pageSetup = doc.PageSetup;
      pageWidth = pageSetup.PageWidth - pageSetup.LeftMargin - pageSetup.RightMargin;
    } catch (e) {}

    table.AutoFitBehavior(0);
    try {
      table.PreferredWidthType = 3;
      table.PreferredWidth = pageWidth;
    } catch (e) {}

    // 使用原始列宽（如果有），否则平均分配
    if (tableData.columnWidths && tableData.columnWidths.length === tableData.columns) {
      for (let c = 0; c < tableData.columns; c++) {
        try {
          if (tableData.columnWidths[c] > 0) {
            const column = table.Columns.Item(c + 1);
            column.PreferredWidthType = 3;
            column.PreferredWidth = tableData.columnWidths[c];
            column.Width = tableData.columnWidths[c];
          }
        } catch (e) {}
      }
    } else {
      const avgWidth = pageWidth / tableData.columns;
      for (let c = 0; c < tableData.columns; c++) {
        try {
          const column = table.Columns.Item(c + 1);
          column.PreferredWidthType = 3;
          column.PreferredWidth = avgWidth;
          column.Width = avgWidth;
        } catch (e) {}
      }
    }

    // 表格对齐
    const tStyle = resolveStyle(styles, tableData.tStyle, ['center']);
    table.Rows.Alignment = getTableAlignmentValue(tStyle[0] || 'center');
  } catch (e) {}

  // 还原行高
  if (tableData.rowHeights && tableData.rowHeights.length === tableData.rows) {
    for (let r = 0; r < tableData.rows; r++) {
      try {
        const [height, heightRule] = tableData.rowHeights[r];
        if (height > 0 && heightRule > 0) {
          const tableRow = table.Rows.Item(r + 1);
          tableRow.HeightRule = heightRule;
          tableRow.Height = height;
        }
      } catch (e) {}
    }
  }

  // 填充内容
  for (let row = 0; row < tableData.cells.length; row++) {
    for (let col = 0; col < tableData.cells[row].length; col++) {
      try {
        const cellData = tableData.cells[row][col];
        const cStyle = resolveStyle(styles, cellData.cStyle, DEFAULT_CSTYLE);
        const rowSpan = cStyle[CSTYLE.ROW_SPAN] || 1;
        const colSpan = cStyle[CSTYLE.COL_SPAN] || 1;
        
        if (!cellData || rowSpan === 0 || colSpan === 0) {
          continue;
        }

        const cell = table.Cell(row + 1, col + 1);
        const cellRange = cell.Range;

        if (cellData.paragraphs && cellData.paragraphs.length > 0) {
          // 阶段1：构建完整文本并记录每个run的偏移量
          let fullText = '';
          const runMetadata = [];  // [{offset, length, rStyle}]
          const paraMetadata = []; // [{pStyle}]

          for (let pi = 0; pi < cellData.paragraphs.length; pi++) {
            const para = cellData.paragraphs[pi];
            if (pi > 0) {
              fullText += '\r';
            } // 段落分隔符

            paraMetadata.push({ pStyle: para.pStyle });

            for (const run of para.runs) {
              const runText = cleanCellText(run.text || '');
              if (!runText) {
                continue;
              }
              runMetadata.push({
                offset: fullText.length,
                length: runText.length,
                rStyle: run.rStyle
              });
              fullText += runText;
            }
          }

          // 阶段2：一次性设置单元格文本（避免默认 \r\u0007 导致多余空段落）
          if (fullText) {
            cellRange.Text = fullText;
            const basePos = cellRange.Start;

            // 阶段3：按偏移量逐个设置run字符格式
            for (const rm of runMetadata) {
              try {
                const formatRange = doc.Range(basePos + rm.offset, basePos + rm.offset + rm.length);
                const font = formatRange.Font;
                font.Reset();
                const rStyle = resolveStyle(styles, rm.rStyle, DEFAULT_RSTYLE);
                if (rStyle[RSTYLE.FONT_NAME]) {
                  font.Name = rStyle[RSTYLE.FONT_NAME];
                }
                if (rStyle[RSTYLE.FONT_SIZE]) {
                  font.Size = rStyle[RSTYLE.FONT_SIZE];
                }
                font.Bold = rStyle[RSTYLE.BOLD] ? -1 : 0;
                font.Italic = rStyle[RSTYLE.ITALIC] ? -1 : 0;
                if (rStyle[RSTYLE.UNDERLINE]) {
                  font.Underline = rStyle[RSTYLE.UNDERLINE];
                  if (rStyle[RSTYLE.UNDERLINE_COLOR] && rStyle[RSTYLE.UNDERLINE_COLOR] !== '#000000') {
                    font.UnderlineColor = parseRGBColor(rStyle[RSTYLE.UNDERLINE_COLOR]);
                  }
                } else {
                  font.Underline = 0;
                }
                if (rStyle[RSTYLE.COLOR] && rStyle[RSTYLE.COLOR] !== '#000000') {
                  font.Color = parseRGBColor(rStyle[RSTYLE.COLOR]);
                } else {
                  font.Color = 0;
                }
                if (rStyle[RSTYLE.HIGHLIGHT]) {
                  try {
                    formatRange.HighlightColorIndex = rStyle[RSTYLE.HIGHLIGHT];
                  } catch (e) {
                    try {
                      font.HighlightColorIndex = rStyle[RSTYLE.HIGHLIGHT]; 
                    } catch (e2) {}
                  }
                }
                font.StrikeThrough = rStyle[RSTYLE.STRIKETHROUGH] ? -1 : 0;
                font.Superscript = rStyle[RSTYLE.SUPERSCRIPT] ? -1 : 0;
                font.Subscript = rStyle[RSTYLE.SUBSCRIPT] ? -1 : 0;
              } catch (e) {}
            }

            // 阶段4：逐段设置段落格式（通过 Paragraphs 集合精确定位）
            try {
              const cellParas = cellRange.Paragraphs;
              for (let pi = 0; pi < paraMetadata.length && pi < cellParas.Count; pi++) {
                const pStyle = resolveStyle(styles, paraMetadata[pi].pStyle, DEFAULT_PSTYLE);
                const pf = cellParas.Item(pi + 1).Format;
                pf.Alignment = getAlignmentValue(pStyle[PSTYLE.ALIGNMENT] || 'left');
                pf.LeftIndent = pStyle[PSTYLE.INDENT_LEFT] || 0;
                pf.RightIndent = pStyle[PSTYLE.INDENT_RIGHT] || 0;
                pf.FirstLineIndent = pStyle[PSTYLE.INDENT_FIRST_LINE] || 0;
                pf.SpaceBefore = pStyle[PSTYLE.SPACE_BEFORE] || 0;
                pf.SpaceAfter = pStyle[PSTYLE.SPACE_AFTER] || 0;

                const lineSpacing = pStyle[PSTYLE.LINE_SPACING] || 0;
                const lineSpacingRule = pStyle[PSTYLE.LINE_SPACING_RULE] || 0;
                if (lineSpacingRule >= 3 && lineSpacing > 0) {
                  pf.LineSpacing = lineSpacing;
                  pf.LineSpacingRule = lineSpacingRule;
                } else if (lineSpacingRule > 0) {
                  pf.LineSpacingRule = lineSpacingRule;
                }
              }
            } catch (e) {}
          }
        } else {
          if (cellData.text) {
            const cleanedText = cleanCellText(cellData.text);
            if (cleanedText) {
              cellRange.Text = cleanedText;
            }
          }

          // 设置字体格式
          const rStyle = resolveStyle(styles, cellData.rStyle, DEFAULT_RSTYLE);
          const font = cellRange.Font;
          font.Reset();
          if (rStyle[RSTYLE.FONT_NAME]) {
            font.Name = rStyle[RSTYLE.FONT_NAME];
          }
          if (rStyle[RSTYLE.FONT_SIZE]) {
            font.Size = rStyle[RSTYLE.FONT_SIZE];
          }
          font.Bold = rStyle[RSTYLE.BOLD] ? -1 : 0;
          font.Italic = rStyle[RSTYLE.ITALIC] ? -1 : 0;

          // 设置段落格式（对齐、行距、缩进、段间距）
          try {
            const pf = cellRange.ParagraphFormat;
            pf.Alignment = getAlignmentValue(cStyle[CSTYLE.ALIGNMENT] || 'center');
            pf.LeftIndent = 0;
            pf.RightIndent = 0;
            pf.FirstLineIndent = 0;
            pf.SpaceBefore = 0;
            pf.SpaceAfter = 0;
          } catch (e) {}
        }

        cell.VerticalAlignment = getCellVerticalAlignmentValue(cStyle[CSTYLE.VERTICAL_ALIGNMENT] || 'center');
      } catch (e) {}
    }
  }

  // 收集并执行合并
  const mergeTasks = [];
  for (let row = 0; row < tableData.cells.length; row++) {
    for (let col = 0; col < tableData.cells[row].length; col++) {
      const cellData = tableData.cells[row][col];
      if (cellData && cellData.cStyle) {
        const mergedCStyle = resolveStyle(styles, cellData.cStyle, DEFAULT_CSTYLE);
        const rowSpan = mergedCStyle[CSTYLE.ROW_SPAN] || 1;
        const colSpan = mergedCStyle[CSTYLE.COL_SPAN] || 1;
        if (rowSpan > 1 || colSpan > 1) {
          mergeTasks.push({
            startRow: row + 1,
            startCol: col + 1,
            endRow: Math.min(row + rowSpan, tableData.rows),
            endCol: Math.min(col + colSpan, tableData.columns)
          });
        }
      }
    }
  }

  // 从右下到左上排序
  mergeTasks.sort((a, b) =>
    b.startRow !== a.startRow ? b.startRow - a.startRow : b.startCol - a.startCol
  );

  for (const task of mergeTasks) {
    try {
      table.Cell(task.startRow, task.startCol).Merge(table.Cell(task.endRow, task.endCol));
    } catch (e) {}
  }

  // 返回表格末尾位置（而非 doc.Content.End），避免在文档中间插入表格时
  // currentPos 跳到文档末尾，导致 endPos 覆盖原有内容、撤回时误删后续段落
  return table.Range.End;
}

/**
 * 从 JSON 数据生成 Word 文档
 * @param {Object} jsonData - JSON 数据
 * @param {Object} doc - 已存在的文档对象（可选，默认创建新文档）
 * @param {number} [insertParaIndex] - 可选，在指定段落索引（0-based）之前插入。
 *   省略时在当前选区位置插入。
 * @returns {Object} - 成功返回 {success: true, doc, startPos, endPos}，失败返回 {error: string}
 */
function generateDocxFromJSON(jsonData, doc, insertParaIndex) {
  try {
    if (!jsonData || (!jsonData.paragraphs && !jsonData.tables)) {
      return { error: 'JSON数据格式不正确' };
    }

    // 提取样式字典
    const styles = jsonData.styles || {};

    if (!doc) {
      doc = window.Application.Documents.Add();
      if (!doc) {
        return { error: '无法创建新文档' };
      }
    }

    // 合并段落和表格，按位置排序
    const elements = [];

    if (jsonData.paragraphs) {
      jsonData.paragraphs.forEach((para, index) => {
        elements.push({ type: 'paragraph', data: para, position: para.paraIndex ?? (index * 1000) });
      });
    }

    if (jsonData.tables) {
      jsonData.tables.forEach((table, index) => {
        elements.push({
          type: 'table',
          data: table,
          position: table.paraIndex ?? ((index + 0.5) * 10000)
        });
      });
    }

    elements.sort((a, b) => a.position - b.position);

    // 预处理：合并连续空段落
    const processedElements = [];
    let consecutiveEmptyCount = 0;

    for (const element of elements) {
      if (element.type === 'paragraph' && isEmptyParagraph(element.data)) {
        if (processedElements.length === 0) {
          continue;
        }
        consecutiveEmptyCount++;
        if (consecutiveEmptyCount <= 1) {
          processedElements.push(element);
        }
      } else {
        consecutiveEmptyCount = 0;
        processedElements.push(element);
      }
    }

    // 确定插入起始位置
    let currentPos;
    if (insertParaIndex === -1) {
      // -1: 在文档末尾插入
      currentPos = doc.Content.End - 1;
    } else if (insertParaIndex !== undefined && insertParaIndex !== null) {
      // 通过段落索引定位插入位置（在指定段落之前插入）
      const totalParas = doc.Paragraphs.Count;
      if (insertParaIndex < 0 || insertParaIndex >= totalParas) {
        return { error: `insertParaIndex ${insertParaIndex} 超出范围，文档共 ${totalParas} 段` };
      }
      currentPos = doc.Paragraphs.Item(insertParaIndex + 1).Range.Start; // WPS 1-based
    } else {
      // 默认使用当前选区位置
      const selection = window.Application.Selection;
      currentPos = selection ? selection.Range.Start : 0;
    }

    // 防御：如果插入位置在表格内部，跳转到该表格之后的首个段落
    // 避免新内容（尤其是新表格）被嵌套到旧表格单元格内
    // 注意：不能直接用 tblRange.End 作为插入点，WPS 中在该位置插入文本仍可能落入表格
    try {
      const docTables = doc.Content.Tables;
      if (docTables && docTables.Count > 0) {
        for (let ti = 1; ti <= docTables.Count; ti++) {
          const tbl = docTables.Item(ti);
          const tblRange = tbl.Range;
          if (currentPos >= tblRange.Start && currentPos <= tblRange.End) {
            console.log(`[generateDocxFromJSON] 插入位置(${currentPos})在表格内部(${tblRange.Start}-${tblRange.End})，寻找表格后安全位置`);
            // 从 insertParaIndex 附近开始扫描，找到第一个在表格后面的段落
            const totalP = doc.Paragraphs.Count;
            let safePos = doc.Content.End - 1; // fallback: 文档末尾
            const scanStart = (insertParaIndex != null && insertParaIndex >= 0)
              ? insertParaIndex + 1  // WPS 1-based
              : 1;
            for (let pi = scanStart; pi <= totalP; pi++) {
              const pStart = doc.Paragraphs.Item(pi).Range.Start;
              if (pStart >= tblRange.End) {
                safePos = pStart;
                break;
              }
            }
            console.log(`[generateDocxFromJSON] 调整到表格后方: ${safePos}`);
            currentPos = safePos;
            break;
          }
        }
      }
    } catch (e) {
      console.warn('[generateDocxFromJSON] 表格位置检测失败:', e);
    }

    const insertStartPos = currentPos;  // 记录插入起始位置
    let paraIndex = 0;
    const docUsableWidth = getDocumentUsableWidth(doc);

    for (let i = 0; i < processedElements.length; i++) {
      const element = processedElements[i];

      if (element.type === 'paragraph') {
        const para = element.data;

        // 获取段落样式
        const pStyle = resolveStyle(styles, para.pStyle, DEFAULT_PSTYLE);
        const alignment = pStyle[PSTYLE.ALIGNMENT] || 'left';
        const lineSpacing = pStyle[PSTYLE.LINE_SPACING] || 0;
        const lineSpacingRule = pStyle[PSTYLE.LINE_SPACING_RULE] || 0;
        const indentLeft = pStyle[PSTYLE.INDENT_LEFT] || 0;
        const indentRight = pStyle[PSTYLE.INDENT_RIGHT] || 0;
        const indentFirstLine = pStyle[PSTYLE.INDENT_FIRST_LINE] || 0;
        const spaceBefore = pStyle[PSTYLE.SPACE_BEFORE] || 0;
        const spaceAfter = pStyle[PSTYLE.SPACE_AFTER] || 0;
        const styleName = pStyle[PSTYLE.STYLE_NAME] || '';

        // 处理空段落
        if (isEmptyParagraph(para)) {
          const prevElement = i > 0 ? processedElements[i - 1] : null;
          const nextElement = i < processedElements.length - 1 ? processedElements[i + 1] : null;

          const prevHasContent =
            prevElement &&
            (prevElement.type === 'table' ||
              (prevElement.type === 'paragraph' &&
                !isEmptyParagraph(prevElement.data) &&
                prevElement.data.runs &&
                prevElement.data.runs.length > 0));
          const nextHasContent =
            nextElement &&
            (nextElement.type === 'table' ||
              (nextElement.type === 'paragraph' &&
                !isEmptyParagraph(nextElement.data) &&
                nextElement.data.runs &&
                nextElement.data.runs.length > 0));

          if (prevHasContent || nextHasContent) {
            const range = doc.Range(currentPos, currentPos);
            range.Text = '\r';
            currentPos += 1;
            paraIndex++;
          }
          continue;
        }

        // 处理普通段落
        const paraStartPos = currentPos;

        if (para.runs && para.runs.length > 0) {
          for (const run of para.runs) {
            // 检查是否是图片 run（没有 text 字段）
            const isImageRun = !run.text && (run.url || run.tempPath || run.sourcePath);
            if (isImageRun) {
              const imageMaxWidth = Math.max(120, docUsableWidth - indentLeft - indentRight);
              const charAdded = insertImage(doc, run, currentPos, imageMaxWidth);
              if (charAdded > 0) {
                currentPos += charAdded;
              }
              continue;
            }

            // 文本 run
            let runText = run.text || '';
            if (!runText) {
              continue;
            }

            const rStyle = resolveStyle(styles, run.rStyle, DEFAULT_RSTYLE);
            const isExplicitLatexRun = run.isFormula === true && run.formulaFormat === 'latex';
            if (isExplicitLatexRun) {
              runText = run.text || normalizeFormulaTextToLatex(run.text);
            }

            const range = doc.Range(currentPos, currentPos);
            range.Text = runText;

            const insertedRange = doc.Range(currentPos, currentPos + runText.length);
            const font = insertedRange.Font;

            // 应用字符样式（直接使用JSON中的值）
            // 字体和字号
            if (rStyle[RSTYLE.FONT_NAME]) {
              font.Name = rStyle[RSTYLE.FONT_NAME];
            }
            if (rStyle[RSTYLE.FONT_SIZE]) {
              font.Size = rStyle[RSTYLE.FONT_SIZE];
            }

            // 字体样式 - 直接设置，不做条件判断
            font.Bold = rStyle[RSTYLE.BOLD] ? -1 : 0;
            font.Italic = rStyle[RSTYLE.ITALIC] ? -1 : 0;
            font.StrikeThrough = rStyle[RSTYLE.STRIKETHROUGH] ? -1 : 0;
            font.Superscript = rStyle[RSTYLE.SUPERSCRIPT] ? -1 : 0;
            font.Subscript = rStyle[RSTYLE.SUBSCRIPT] ? -1 : 0;

            // 下划线
            if (rStyle[RSTYLE.UNDERLINE]) {
              font.Underline = rStyle[RSTYLE.UNDERLINE];
              if (rStyle[RSTYLE.UNDERLINE_COLOR] && rStyle[RSTYLE.UNDERLINE_COLOR] !== '#000000') {
                font.UnderlineColor = parseRGBColor(rStyle[RSTYLE.UNDERLINE_COLOR]);
              }
            } else {
              font.Underline = 0;
            }

            // 颜色
            if (rStyle[RSTYLE.COLOR] && rStyle[RSTYLE.COLOR] !== '#000000') {
              font.Color = parseRGBColor(rStyle[RSTYLE.COLOR]);
            } else {
              font.Color = 0;
            }

            // 高亮（使用 Range 的 HighlightColorIndex）
            if (rStyle[RSTYLE.HIGHLIGHT]) {
              try {
                insertedRange.HighlightColorIndex = rStyle[RSTYLE.HIGHLIGHT];
              } catch (e) {
                // 如果 Range.HighlightColorIndex 不可用，尝试 Font
                try {
                  font.HighlightColorIndex = rStyle[RSTYLE.HIGHLIGHT];
                } catch (e2) {}
              }
            } else {
              try {
                insertedRange.HighlightColorIndex = 0;
              } catch (e) {
                try {
                  font.HighlightColorIndex = 0;
                } catch (e2) {}
              }
            }

            currentPos += runText.length;
          }
        }

        // 先设置段落格式 - 使用 Range 来精确定位刚插入的段落
        // 必须在添加段落结束符（\r）之前设置格式
        try {
          const insertedParaRange = doc.Range(paraStartPos, currentPos);
          const insertedPara = insertedParaRange.Paragraphs.Item(1);
          if (insertedPara) {
            const paraFormat = insertedPara.Format;

            // 如果有样式名称，先应用样式
            if (styleName) {
              try {
                insertedPara.Style = styleName;
              } catch (e) {
                console.warn('应用样式失败:', e);
              }
            }

            // 强制应用 JSON 中的所有段落格式（覆盖继承的格式和样式）
            // 不使用条件判断，直接设置所有属性
            paraFormat.Alignment = getAlignmentValue(alignment);
            paraFormat.LeftIndent = indentLeft;
            paraFormat.RightIndent = indentRight;
            paraFormat.FirstLineIndent = indentFirstLine;
            paraFormat.SpaceBefore = spaceBefore;
            paraFormat.SpaceAfter = spaceAfter;

            // 设置行距
            // 预设档位 (0=单倍, 1=1.5倍, 2=双倍): WPS 自动计算行距，只需设置 Rule
            // 显式档位 (3=至少, 4=固定值, 5=多倍): 需要先设磅值再设 Rule
            try {
              if (lineSpacingRule >= 3 && lineSpacing && lineSpacing > 0) {
                paraFormat.LineSpacing = lineSpacing;
                paraFormat.LineSpacingRule = lineSpacingRule;
              } else if (lineSpacingRule > 0) {
                paraFormat.LineSpacingRule = lineSpacingRule;
              }
            } catch (e) {
              console.warn('设置行距失败:', e);
            }
          }
          paraIndex++;
        } catch (e) {
          console.warn('设置段落格式失败:', e);
        }

        // 段落格式设置完成后，再添加段落结束符
        if (i < processedElements.length - 1) {
          const nextElement = processedElements[i + 1];
          if (nextElement && nextElement.type !== 'table') {
            const range = doc.Range(currentPos, currentPos);
            range.Text = '\r';
            currentPos += 1;
          }
        }
      } else if (element.type === 'table') {
        currentPos = generateTable(doc, element.data, currentPos, styles);
        paraIndex = doc.Paragraphs.Count;

        // 表格后换行
        if (i < processedElements.length - 1) {
          let hasContentAfter = false;
          for (let j = i + 1; j < processedElements.length; j++) {
            const nextEl = processedElements[j];
            if (
              nextEl.type === 'table' ||
              (nextEl.type === 'paragraph' &&
                !isEmptyParagraph(nextEl.data) &&
                nextEl.data.runs &&
                nextEl.data.runs.length > 0)
            ) {
              hasContentAfter = true;
              break;
            }
          }
          if (hasContentAfter) {
            const range = doc.Range(currentPos, currentPos);
            range.Text = '\r';
            currentPos += 1;
          }
        }
      }
    }

    // 在AI生成内容末尾追加段落分隔符，防止原文档内容黏连到AI最后一段
    if (processedElements.length > 0) {
      const trailingRange = doc.Range(currentPos, currentPos);
      trailingRange.Text = '\r';
      currentPos += 1;
    }

    // 触发重绘
    const rgSel = window.Application.Selection.Range;
    if (rgSel) {
      rgSel.Select();
    }

    return { success: true, message: '文档生成成功！', doc, startPos: insertStartPos, endPos: currentPos };
  } catch (error) {
    return { error: '生成文档失败: ' + error.message };
  }
}

// ============== 段落删除 ==============

/**
 * 根据段落索引范围批量删除文档中的段落
 * 
 * @param {number} startParaIndex - 起始段落索引（0-based）
 * @param {number} [endParaIndex] - 结束段落索引（0-based，含），省略时默认等于 startParaIndex；-1 表示删除到文档末尾
 * @returns {{ success: boolean, deletedCount: number, message: string }}
 */
function deleteDocxPara(startParaIndex, endParaIndex) {
  if (startParaIndex === undefined || startParaIndex === null) {
    return { success: false, deletedCount: 0, message: '未提供有效的 startParaIndex' };
  }
  if (endParaIndex === undefined || endParaIndex === null) {
    endParaIndex = startParaIndex;
  }

  const doc = window.Application?.ActiveDocument;
  if (!doc) {
    return { success: false, deletedCount: 0, message: '没有打开的文档' };
  }

  const totalParas = doc.Paragraphs.Count;
  if (totalParas === 0) {
    return { success: false, deletedCount: 0, message: '文档中没有段落' };
  }

  // endParaIndex === -1 表示删除到文档末尾
  if (endParaIndex === -1) {
    endParaIndex = totalParas - 1;
  }

  if (startParaIndex < 0 || startParaIndex >= totalParas) {
    return { success: false, deletedCount: 0, message: `startParaIndex ${startParaIndex} 超出范围，文档共 ${totalParas} 段` };
  }
  if (endParaIndex < startParaIndex || endParaIndex >= totalParas) {
    return { success: false, deletedCount: 0, message: `endParaIndex ${endParaIndex} 无效（startParaIndex=${startParaIndex}，文档共 ${totalParas} 段）` };
  }

  // 一次性计算整个删除范围，然后一次删除（避免逐段删除的索引偏移和残留问题）
  let deletedCount = endParaIndex - startParaIndex + 1;
  try {
    const firstPara = doc.Paragraphs.Item(startParaIndex + 1); // WPS 1-based
    const lastPara = doc.Paragraphs.Item(endParaIndex + 1);
    let delStart = firstPara.Range.Start;
    let delEnd = lastPara.Range.End;

    // 如果删除范围到文档末尾且前面还有段落，向前扩展 1 字符吃掉前段的 \r
    // 否则如果后面还有内容，段落 Range.End 已包含 \r，直接删即可
    if (delEnd >= doc.Content.End && delStart > 0) {
      delStart -= 1;
    }

    if (startParaIndex === 0 && endParaIndex >= totalParas - 1) {
      // 删除全部段落：只清空内容，Word 要求至少保留一个空段落
      doc.Content.Text = '';
    } else {
      doc.Range(delStart, delEnd).Delete();
    }
  } catch (e) {
    console.log('删除段落范围失败:', e.message);
    deletedCount = 0;
  }

  return { success: true, deletedCount, message: `成功删除 ${deletedCount} 个段落` };
}

// ============== 导出 ==============

export default {
  // 主要函数
  parseDocxToJSON,
  generateDocxFromJSON,
  deleteDocxPara,

  // 辅助函数（供外部使用）
  cleanText,
  cleanCellText,
  exportImageToTemp,
  deduplicateStyles,
  resolveStyle,

  // 样式数组常量
  PSTYLE,
  RSTYLE,
  CSTYLE,

  // 样式数组创建函数
  makePStyle,
  makeRStyle,
  makeCStyle,

  // 格式转换函数
  getAlignmentName,
  getAlignmentValue,
  getTableAlignmentName,
  getTableAlignmentValue,
  getCellVerticalAlignmentName,
  getCellVerticalAlignmentValue,
  getWrapTypeName,
  getWrapTypeValue,
  getTabAlignmentName,
  getTabAlignmentValue,
  getTabLeaderName,
  getTabLeaderValue,
  getRGBColor,
  parseRGBColor
};

// 也支持命名导出
export {
  parseDocxToJSON,
  generateDocxFromJSON,
  deleteDocxPara,
  cleanText,
  cleanCellText,
  exportImageToTemp,
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
  getTableAlignmentName,
  getTableAlignmentValue,
  getCellVerticalAlignmentName,
  getCellVerticalAlignmentValue,
  getWrapTypeName,
  getWrapTypeValue,
  getTabAlignmentName,
  getTabAlignmentValue,
  getTabLeaderName,
  getTabLeaderValue,
  getRGBColor,
  parseRGBColor
};

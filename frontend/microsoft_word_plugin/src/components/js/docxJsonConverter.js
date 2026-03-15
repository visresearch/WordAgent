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

// ============== 样式去重与解析 ==============

function createStyleRegistry() {
  return {
    _maps: { p: new Map(), r: new Map(), c: new Map(), t: new Map() },
    _counts: { p: 0, r: 0, c: 0, t: 0 },
    _prefixes: { p: 'pS_', r: 'rS_', c: 'cS_', t: 'tS_' },
    styles: {}
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
  if (typeof ref === 'string' && styles && styles[ref]) return styles[ref];
  return defaultStyle;
}

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

// ============== 格式转换辅助函数 ==============

function makePStyle(alignment, lineSpacing, indentLeft, indentRight, indentFirstLine, spaceBefore, spaceAfter, styleName) {
  return [alignment, lineSpacing, indentLeft, indentRight, indentFirstLine, spaceBefore, spaceAfter, styleName];
}

function makeRStyle(fontName, fontSize, bold, italic, underline, underlineColor, color, highlight, strikethrough, superscript, subscript) {
  return [fontName, fontSize, bold, italic, underline, underlineColor, color, highlight, strikethrough, superscript, subscript];
}

function makeCStyle(rowSpan, colSpan, alignment, verticalAlignment) {
  return [rowSpan, colSpan, alignment, verticalAlignment];
}

/**
 * Office.js 对齐枚举 -> 名称
 */
function getAlignmentName(alignment) {
  if (typeof alignment === 'string') {
    const lower = alignment.toLowerCase();
    if (['left', 'center', 'right', 'justify', 'distributed'].includes(lower)) {
      return lower === 'distributed' ? 'distribute' : lower;
    }
  }
  const map = {
    'Left': 'left', 'Center': 'center', 'Right': 'right',
    'Justified': 'justify', 'Distributed': 'distribute',
    0: 'left', 1: 'center', 2: 'right', 3: 'justify', 4: 'distribute'
  };
  return map[alignment] || 'left';
}

function getAlignmentValue(alignment) {
  const map = { left: 'Left', center: 'Center', right: 'Right', justify: 'Justified', distribute: 'Distributed' };
  return map[alignment] || 'Left';
}

function getVerticalAlignmentName(alignment) {
  if (typeof alignment === 'string') {
    const lower = alignment.toLowerCase();
    if (['top', 'center', 'bottom'].includes(lower)) return lower;
  }
  const map = { 'Top': 'top', 'Center': 'center', 'Bottom': 'bottom' };
  return map[alignment] || 'center';
}

function getVerticalAlignmentValue(alignment) {
  const map = { top: 'Top', center: 'Center', bottom: 'Bottom' };
  return map[alignment] || 'Center';
}

/**
 * Office.js 下划线枚举 -> 数值
 */
function getUnderlineValue(underlineType) {
  if (typeof underlineType === 'number') return underlineType;
  const map = {
    'None': 0, 'Single': 1, 'Double': 3, 'Dotted': 4,
    'Thick': 6, 'DottedHeavy': 7, 'Wave': 11, 'WavyHeavy': 27
  };
  return map[underlineType] || 0;
}

function getUnderlineType(value) {
  if (typeof value === 'string') return value;
  const map = { 0: 'None', 1: 'Single', 3: 'Double', 4: 'Dotted', 6: 'Thick', 7: 'DottedHeavy', 11: 'Wave', 27: 'WavyHeavy' };
  return map[value] || 'None';
}

/**
 * Office.js 高亮颜色枚举 -> 数值
 */
function getHighlightValue(highlightColor) {
  if (typeof highlightColor === 'number') return highlightColor;
  const map = {
    'NoHighlight': 0, 'Black': 1, 'Blue': 2, 'Turquoise': 3,
    'BrightGreen': 4, 'Pink': 5, 'Red': 6, 'Yellow': 7,
    'DarkBlue': 9, 'Teal': 10, 'Green': 11, 'Violet': 12,
    'DarkRed': 13, 'DarkYellow': 14, 'Gray50': 15, 'Gray25': 16
  };
  return map[highlightColor] || 0;
}

function getHighlightColor(value) {
  if (typeof value === 'string') return value;
  const map = {
    0: null, 1: 'Black', 2: 'Blue', 3: 'Turquoise',
    4: 'BrightGreen', 5: 'Pink', 6: 'Red', 7: 'Yellow',
    9: 'DarkBlue', 10: 'Teal', 11: 'Green', 12: 'Violet',
    13: 'DarkRed', 14: 'DarkYellow', 15: 'Gray50', 16: 'Gray25'
  };
  return map[value] || null;
}

function isEmptyParagraph(para) {
  return !!(para && Array.isArray(para.runs) && para.runs.length === 0);
}

function cleanText(text) {
  if (!text) return '';
  return text.replace(/\u0007/g, '').replace(/\f/g, '').replace(/\r$/, '');
}

// ============== 解析函数 ==============

/**
 * 解析 Word 文档内容为 JSON（异步，基于 Office.js API）
 *
 * @param {string} scope - 'selection' 解析选区, 'body' 解析全文
 * @returns {Promise<Object>} - JSON 数据或错误对象
 */
async function parseDocxToJSON(scope = 'selection') {
  try {
    return await Word.run(async (context) => {
      const range = scope === 'body'
        ? context.document.body
        : context.document.getSelection();

      // 加载段落和表格
      const paragraphs = range.paragraphs;
      paragraphs.load('items');
      const tables = range.tables;
      tables.load('items');
      const inlinePictures = range.inlinePictures;
      inlinePictures.load('items');
      const fields = range.fields;
      fields.load('items');

      await context.sync();

      const result = {
        paragraphs: [],
        tables: [],
        images: [],
        fields: []
      };

      // === 解析域代码 ===
      try {
        if (fields.items && fields.items.length > 0) {
          for (const field of fields.items) {
            field.load('type,code');
            field.result.load('text');
          }
          await context.sync();

          for (const field of fields.items) {
            const fieldCode = field.code || '';
            result.fields.push({
              type: field.type,
              code: fieldCode.trim()
            });
            if (fieldCode.toUpperCase().includes('TOC')) {
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
          table.load('rowCount,values,alignment');
          table.rows.load('items');
        }
        await context.sync();

        for (const table of tables.items) {
          const tableRows = table.rows;
          for (const row of tableRows.items) {
            row.load('cellCount,preferredHeight');
            row.cells.load('items');
          }
        }
        await context.sync();

        // 解析每个表格
        for (const table of tables.items) {
          const tableData = {
            rows: table.rowCount,
            columns: 0,
            cells: [],
            tStyle: [getAlignmentName(table.alignment)]
          };

          const tableRows = table.rows;
          for (const row of tableRows.items) {
            for (const cell of row.cells.items) {
              cell.load('columnWidth,rowIndex,cellIndex,verticalAlignment,width');
              cell.body.load('text');
              const cellParas = cell.body.paragraphs;
              cellParas.load('items');
            }
          }
          await context.sync();

          // 加载每个单元格中段落的详细信息
          for (const row of tableRows.items) {
            for (const cell of row.cells.items) {
              const cellParas = cell.body.paragraphs;
              for (const para of cellParas.items) {
                para.load('text,alignment,lineSpacing,firstLineIndent,leftIndent,rightIndent,spaceBefore,spaceAfter,style,lineUnitBefore,lineUnitAfter');
                const runs = para.getTextRanges([' '], false);
                runs.load('items');
              }
            }
          }
          await context.sync();

          for (const row of tableRows.items) {
            const rowData = [];
            if (row.cells.items.length > tableData.columns) {
              tableData.columns = row.cells.items.length;
            }

            for (const cell of row.cells.items) {
              const cellText = cleanText(cell.body.text || '');
              const cellParas = cell.body.paragraphs;

              // 解析单元格段落和 runs
              const paragraphsData = [];
              for (const para of cellParas.items) {
                const paraText = cleanText(para.text || '');
                if (!paraText) continue;

                // 加载 runs
                const inlineRanges = para.getTextRanges(['\t', '\n'], true);
                inlineRanges.load('items');
                await context.sync();

                for (const ir of inlineRanges.items) {
                  ir.load('text');
                  ir.font.load('name,size,bold,italic,underline,color,highlightColor,strikeThrough,superscript,subscript');
                }
                await context.sync();

                const runs = [];
                let lastFormatKey = null;
                let currentRun = null;

                for (const ir of inlineRanges.items) {
                  const t = ir.text || '';
                  if (!t || t.match(/^[\r\n\u0007]$/)) continue;

                  const font = ir.font;
                  const formatKey = `${font.name}_${font.size}_${font.bold}_${font.italic}_${font.color}_${font.highlightColor}`;

                  if (formatKey === lastFormatKey && currentRun) {
                    currentRun.text += t;
                  } else {
                    if (currentRun && currentRun.text) runs.push(currentRun);
                    currentRun = {
                      text: t,
                      rStyle: makeRStyle(
                        font.name || '', font.size || 12,
                        font.bold === true, font.italic === true,
                        getUnderlineValue(font.underline),
                        '#000000',
                        font.color || '#000000',
                        getHighlightValue(font.highlightColor),
                        font.strikeThrough === true,
                        font.superscript === true,
                        font.subscript === true
                      )
                    };
                    lastFormatKey = formatKey;
                  }
                }
                if (currentRun && currentRun.text) runs.push(currentRun);

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
                      ''
                    ),
                    runs: runs
                  });
                }
              }

              rowData.push({
                text: cellText,
                paragraphs: paragraphsData.length > 0 ? paragraphsData : undefined,
                cStyle: makeCStyle(
                  1, 1,
                  getAlignmentName(cellParas.items.length > 0 ? cellParas.items[0].alignment : 'Left'),
                  getVerticalAlignmentName(cell.verticalAlignment)
                )
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
            pic.load('width,height,altTextTitle,altTextDescription');
          }
          await context.sync();

          for (const pic of inlinePictures.items) {
            result.images.push({
              type: 'inline',
              width: pic.width || 100,
              height: pic.height || 100,
              altText: pic.altTextTitle || pic.altTextDescription || '',
              placeholder: '[图片]'
            });
          }
        }
      } catch (e) {
        // inlinePictures API 可能不可用
      }

      // === 解析段落 ===
      if (paragraphs.items && paragraphs.items.length > 0) {
        for (const para of paragraphs.items) {
          para.load('text,alignment,lineSpacing,firstLineIndent,leftIndent,rightIndent,spaceBefore,spaceAfter,style,isListItem,tableNestingLevel,lineUnitBefore,lineUnitAfter');
        }
        await context.sync();

        for (const para of paragraphs.items) {
          // 跳过表格内段落
          if (para.tableNestingLevel > 0) continue;

          const paraText = cleanText(para.text || '');

          // 空段落
          if (!paraText || paraText.match(/^[\r\n\f\u0007]*$/)) {
            result.paragraphs.push({ pStyle: '', runs: [] });
            continue;
          }

          let styleName = '';
          try {
            styleName = para.style || '';
          } catch (e) {}

          // 加载 runs（使用分隔符拆分文本范围）
          const inlineRanges = para.getTextRanges(['\t', '\n'], true);
          inlineRanges.load('items');
          await context.sync();

          for (const ir of inlineRanges.items) {
            ir.load('text');
            ir.font.load('name,size,bold,italic,underline,underlineColor,color,highlightColor,strikeThrough,superscript,subscript');
          }
          await context.sync();

          const runs = [];
          let lastFormatKey = null;
          let currentRun = null;

          for (const ir of inlineRanges.items) {
            const t = ir.text || '';
            if (!t || t.match(/^[\r\n\f\u0007]+$/)) continue;

            const font = ir.font;
            const formatKey = [
              font.name, font.size, font.bold, font.italic,
              font.underline, font.color, font.highlightColor,
              font.strikeThrough, font.superscript, font.subscript
            ].join('|');

            if (formatKey === lastFormatKey && currentRun) {
              currentRun.text += t;
            } else {
              if (currentRun && currentRun.text) runs.push(currentRun);
              currentRun = {
                text: t,
                rStyle: makeRStyle(
                  font.name || '', font.size || 12,
                  font.bold === true, font.italic === true,
                  getUnderlineValue(font.underline),
                  font.underlineColor || '#000000',
                  font.color || '#000000',
                  getHighlightValue(font.highlightColor),
                  font.strikeThrough === true,
                  font.superscript === true,
                  font.subscript === true
                )
              };
              lastFormatKey = formatKey;
            }
          }
          if (currentRun && currentRun.text) runs.push(currentRun);

          // 如果无法通过 getTextRanges 获取 runs，降级为整段
          if (runs.length === 0 && paraText) {
            const font = para.getRange().font;
            font.load('name,size,bold,italic,underline,underlineColor,color,highlightColor,strikeThrough,superscript,subscript');
            await context.sync();

            runs.push({
              text: paraText,
              rStyle: makeRStyle(
                font.name || '', font.size || 12,
                font.bold === true, font.italic === true,
                getUnderlineValue(font.underline),
                font.underlineColor || '#000000',
                font.color || '#000000',
                getHighlightValue(font.highlightColor),
                font.strikeThrough === true,
                font.superscript === true,
                font.subscript === true
              )
            });
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
            runs: runs
          };

          if (paragraphData.runs.length > 0) {
            result.paragraphs.push(paragraphData);
          }
        }
      }

      return deduplicateStyles(result);
    });
  } catch (error) {
    return { error: '解析失败: ' + error.message };
  }
}

// ============== 生成函数 ==============

/**
 * 从 JSON 数据生成 Word 文档（异步，基于 Office.js API）
 *
 * @param {Object} jsonData - JSON 数据
 * @param {string} insertLocation - 插入位置: 'end'(末尾), 'selection'(当前选区), 'replace'(替换选区)
 * @returns {Promise<Object>} - 成功返回 {success: true}，失败返回 {error: string}
 */
async function generateDocxFromJSON(jsonData, insertLocation = 'selection') {
  try {
    if (!jsonData || (!jsonData.paragraphs && !jsonData.tables)) {
      return { error: 'JSON数据格式不正确' };
    }

    const styles = jsonData.styles || {};

    return await Word.run(async (context) => {
      let targetRange;
      if (insertLocation === 'end') {
        targetRange = context.document.body;
      } else {
        targetRange = context.document.getSelection();
      }

      // 合并段落和表格，按位置排序
      const elements = [];

      if (jsonData.paragraphs) {
        jsonData.paragraphs.forEach((para, index) => {
          elements.push({ type: 'paragraph', data: para, position: para.position || index * 1000 });
        });
      }

      if (jsonData.tables) {
        jsonData.tables.forEach((table, index) => {
          elements.push({ type: 'table', data: table, position: table.position || (index + 0.5) * 10000 });
        });
      }

      elements.sort((a, b) => a.position - b.position);

      // 预处理：合并连续空段落
      const processedElements = [];
      let consecutiveEmptyCount = 0;
      for (const element of elements) {
        if (element.type === 'paragraph' && isEmptyParagraph(element.data)) {
          consecutiveEmptyCount++;
          if (consecutiveEmptyCount <= 2) processedElements.push(element);
        } else {
          consecutiveEmptyCount = 0;
          processedElements.push(element);
        }
      }

      // 插入内容
      const insertLoc = insertLocation === 'end' ? Word.InsertLocation.end : Word.InsertLocation.after;

      for (let i = 0; i < processedElements.length; i++) {
        const element = processedElements[i];

        if (element.type === 'paragraph') {
          const para = element.data;
          const pStyle = resolveStyle(styles, para.pStyle, DEFAULT_PSTYLE);
          const alignment = pStyle[PSTYLE.ALIGNMENT] || 'left';
          const lineSpacing = pStyle[PSTYLE.LINE_SPACING] || 0;
          const indentLeft = pStyle[PSTYLE.INDENT_LEFT] || 0;
          const indentRight = pStyle[PSTYLE.INDENT_RIGHT] || 0;
          const indentFirstLine = pStyle[PSTYLE.INDENT_FIRST_LINE] || 0;
          const spaceBefore = pStyle[PSTYLE.SPACE_BEFORE] || 0;
          const spaceAfter = pStyle[PSTYLE.SPACE_AFTER] || 0;
          const styleName = pStyle[PSTYLE.STYLE_NAME] || '';

          // 空段落
          if (isEmptyParagraph(para)) {
            if (insertLocation === 'end') {
              targetRange.insertParagraph('', Word.InsertLocation.end);
            } else {
              targetRange.insertParagraph('', insertLoc);
            }
            continue;
          }

          // 拼接段落文本
          const fullText = (para.runs || []).map(r => r.text || '').join('');
          if (!fullText) continue;

          // 插入段落
          let newParagraph;
          if (insertLocation === 'end') {
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
              const runText = run.text || '';
              if (!runText) continue;

              const rStyle = resolveStyle(styles, run.rStyle, DEFAULT_RSTYLE);

              try {
                // 使用 getRange 获取段落中的子范围
                const runRange = newParagraph.getRange().getRange('Whole');
                // Office.js 不支持直接按字符偏移设置格式，
                // 使用 search 方式定位文本
                const searchResults = newParagraph.search(runText, { matchCase: true, matchWholeWord: false });
                searchResults.load('items');
                await context.sync();

                // 取匹配结果，应用字符格式
                if (searchResults.items.length > 0) {
                  const targetItem = searchResults.items[searchResults.items.length > 1 ? findClosestMatch(searchResults.items, charOffset) : 0];
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

          // 更新 targetRange 引用
          if (insertLocation !== 'end') {
            targetRange = newParagraph;
          }

        } else if (element.type === 'table') {
          const tableData = element.data;
          const tStyle = resolveStyle(styles, tableData.tStyle, ['center']);

          // 构建表格数据值数组
          const values = [];
          for (let row = 0; row < tableData.rows; row++) {
            const rowValues = [];
            if (tableData.cells && tableData.cells[row]) {
              for (let col = 0; col < tableData.columns; col++) {
                const cellData = tableData.cells[row][col];
                if (cellData) {
                  let cellText = cellData.text || '';
                  if (!cellText && cellData.paragraphs) {
                    cellText = cellData.paragraphs.map(p => {
                      if (p.runs) return p.runs.map(r => r.text || '').join('');
                      return p.text || '';
                    }).join('\n');
                  }
                  rowValues.push(cleanText(cellText));
                } else {
                  rowValues.push('');
                }
              }
            }
            // 补齐列数
            while (rowValues.length < tableData.columns) {
              rowValues.push('');
            }
            values.push(rowValues);
          }

          // 插入表格
          let newTable;
          if (insertLocation === 'end') {
            newTable = targetRange.insertTable(tableData.rows, tableData.columns, Word.InsertLocation.end, values);
          } else {
            // 在选区后插入一个段落，再在该段落后插入表格
            const tempPara = targetRange.insertParagraph('', Word.InsertLocation.after);
            newTable = tempPara.insertTable(tableData.rows, tableData.columns, Word.InsertLocation.after, values);
            tempPara.delete();
          }

          // 设置表格对齐
          newTable.alignment = getAlignmentValue(tStyle[0] || 'center');

          // 应用单元格格式
          newTable.load('rows');
          await context.sync();

          for (let row = 0; row < tableData.cells.length; row++) {
            for (let col = 0; col < tableData.cells[row].length; col++) {
              const cellData = tableData.cells[row][col];
              if (!cellData) continue;

              const cStyle = resolveStyle(styles, cellData.cStyle, DEFAULT_CSTYLE);

              try {
                const cell = newTable.getCell(row, col);
                cell.verticalAlignment = getVerticalAlignmentValue(cStyle[CSTYLE.VERTICAL_ALIGNMENT] || 'center');

                // 设置单元格段落对齐
                const cellBody = cell.body;
                cellBody.paragraphs.load('items');
                await context.sync();

                for (const cellPara of cellBody.paragraphs.items) {
                  cellPara.alignment = getAlignmentValue(cStyle[CSTYLE.ALIGNMENT] || 'left');

                  // 如果有 runs 格式，应用字体
                  if (cellData.rStyle) {
                    const rStyle = resolveStyle(styles, cellData.rStyle, DEFAULT_RSTYLE);
                    applyRunStyle(cellPara.font, rStyle);
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

          if (insertLocation !== 'end') {
            targetRange = newTable.getRange('After');
          }
        }
      }

      await context.sync();

      const paraCount = jsonData.paragraphs?.length || 0;
      const tableCount = jsonData.tables?.length || 0;
      return { success: true, message: `文档生成成功！${paraCount} 段落 / ${tableCount} 表格` };
    });
  } catch (error) {
    return { error: '生成文档失败: ' + error.message };
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
  if (rStyle[RSTYLE.COLOR] && rStyle[RSTYLE.COLOR] !== '#000000') {
    font.color = rStyle[RSTYLE.COLOR];
  } else {
    font.color = '#000000';
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

// ============== 导出 ==============

export default {
  parseDocxToJSON,
  generateDocxFromJSON,
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
  getHighlightColor
};

export {
  parseDocxToJSON,
  generateDocxFromJSON,
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
  getHighlightColor
};

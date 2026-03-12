/**
 * WPS Word 文档与 JSON 双向转换工具
 *
 * 功能：
 * 1. parseDocxToJSON - 将 Word 文档内容解析为 JSON 格式
 * 2. generateDocxFromJSON - 从 JSON 数据生成 Word 文档
 *
 * JSON 数据结构（精简版）：
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
 *         underline,           // [4] 下划线: 0=无、1=单线、3=双线、4=虚线、6=粗线、7=粗虚线、11=波浪线、27=粗波浪线
 *         underlineColor,      // [5] 下划线颜色: #RRGGBB
 *         color,               // [6] 字体颜色: #RRGGBB
 *         highlight,           // [7] 高亮色: 0=无, 1-16=黑、蓝、青绿、鲜绿、粉红、红、黄、未知、深蓝、青、绿、紫罗兰、深红、深黄、深灰、浅灰
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
 *   images: [{...}],          // 图片数组（保持不变）
 *   fields: [],               // 域代码数组
 *   hasTOC: boolean           // 是否包含目录
 * }
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

// ============== 图片处理 ==============

/**
 * 导出图片到临时文件
 * @param {Object} shape - InlineShape 或 Shape 对象
 * @returns {Object} - {tempPath, saved} 或 {sourcePath, saved}
 */
function exportImageToTemp(shape) {
  try {
    shape.Select();
    window.Application.Selection.Copy();

    const tempDir = window.Application.Options.DefaultFilePath(2) || '/tmp';
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
            let lastFormat = null;
            let currentRun = null;

            for (let c = 1; c <= chars.Count; c++) {
              const char = chars.Item(c);
              const charText = char.Text;

              if (!charText || charText.match(/^[\r\n\u0007]$/)) {
                continue;
              }

              const font = char.Font;
              const formatKey = `${font.Name}_${font.Size}_${font.Bold}_${font.Italic}_${font.Color}`;

              if (formatKey !== lastFormat) {
                if (currentRun && currentRun.text) {
                  currentRun.text = cleanCellText(currentRun.text);
                  if (currentRun.text) {
                    paraData.runs.push(currentRun);
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
                paraData.runs.push(currentRun);
              }
            }
          }
        } catch (e) {
          const font = paraRange.Font;
          paraData.runs.push({
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
          });
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
    position: tableRange.Start,
    tStyle: [getTableAlignmentName(table.Rows.Alignment)]  // 表格样式数组
  };

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
 * 解析 Word 文档内容为 JSON
 * @param {Object|number} rangeOrStart - WPS Range 对象，或起始位置（数字）
 * @param {number} [end] - 结束位置（仅当第一个参数为数字时使用）
 * @returns {Object} - JSON 数据或错误对象
 */
function parseDocxToJSON(rangeOrStart, end) {
  try {
    let range;

    if (typeof rangeOrStart === 'number') {
      // 传入的是起始和结束位置
      const doc = window.Application?.ActiveDocument;
      if (!doc) {
        return { error: '没有打开的文档' };
      }
      const endPos = (typeof end === 'number') ? end : doc.Content.End;
      range = doc.Range(rangeOrStart, endPos);
      if (!range) {
        return { error: '无法创建指定范围' };
      }
    } else if (rangeOrStart) {
      // 传入的是 Range 对象
      range = rangeOrStart;
    } else {
      // 无参数，使用当前选区
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
      fields: [],
      images: []
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

    // 解析表格，记录位置范围
    const tables = range.Tables;
    const tableRanges = [];
    if (tables && tables.Count > 0) {
      for (let i = 1; i <= tables.Count; i++) {
        const table = tables.Item(i);
        const tableRange = table.Range;
        tableRanges.push({ start: tableRange.Start, end: tableRange.End });
        result.tables.push(parseTable(table));
      }
    }

    // 解析嵌入式图片
    try {
      const inlineShapes = range.InlineShapes;
      if (inlineShapes && inlineShapes.Count > 0) {
        for (let i = 1; i <= inlineShapes.Count; i++) {
          try {
            const shape = inlineShapes.Item(i);
            if (shape.Type === 3 || shape.Type === 1) {
              const imageInfo = exportImageToTemp(shape);
              result.images.push({
                type: 'inline',
                width: shape.Width || 100,
                height: shape.Height || 100,
                position: shape.Range ? shape.Range.Start : 0,
                altText: shape.AlternativeText || '',
                ...imageInfo,
                placeholder: '[图片]'
              });
            }
          } catch (e) {}
        }
      }
    } catch (e) {}

    // 解析浮动图片
    try {
      const shapes = range.ShapeRange;
      if (shapes && shapes.Count > 0) {
        for (let i = 1; i <= shapes.Count; i++) {
          try {
            const shape = shapes.Item(i);
            if ([13, 75, 3, 1].includes(shape.Type)) {
              const imageInfo = exportImageToTemp(shape);
              result.images.push({
                type: 'floating',
                width: shape.Width || 100,
                height: shape.Height || 100,
                left: shape.Left || 0,
                top: shape.Top || 0,
                wrapType: getWrapTypeName(shape.WrapFormat ? shape.WrapFormat.Type : 0),
                altText: shape.AlternativeText || '',
                ...imageInfo,
                placeholder: '[图片]'
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

        const paraText = para.Range.Text || '';

        // 空段落
        if (paraText.match(/^[\r\n\f\u0007]*$/)) {
          result.paragraphs.push({
            isParaEmpty: true,
            position: paraStart
          });
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
          position: paraStart
        };

        // 解析 runs - 使用Characters确保捕获Tab等特殊字符
        const chars = paraRange.Characters;
        if (chars && chars.Count > 0) {
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
                paragraphData.runs.push(currentRun);
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
            paragraphData.runs.push(currentRun);
          }
        }

        if (paragraphData.runs.length > 0 || paragraphData.text) {
          result.paragraphs.push(paragraphData);
        }
      }
    }

    return result;
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
function insertImage(doc, img, insertPos) {
  try {
    const imagePath = img.tempPath || img.sourcePath;
    if (!imagePath) {
      return 0;
    }

    const insertRange = doc.Range(insertPos, insertPos);

    if (img.type === 'inline') {
      try {
        const inlineShape = doc.InlineShapes.AddPicture(imagePath, false, true, insertRange);
        if (img.width) {
          inlineShape.Width = img.width;
        }
        if (img.height) {
          inlineShape.Height = img.height;
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
        if (img.width) {
          shape.Width = img.width;
        }
        if (img.height) {
          shape.Height = img.height;
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
function generateTable(doc, tableData, currentPos) {
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

    // 平均分配列宽
    const avgWidth = pageWidth / tableData.columns;
    
    table.AutoFitBehavior(0);
    try {
      table.PreferredWidthType = 3;
      table.PreferredWidth = pageWidth;
    } catch (e) {}

    for (let c = 0; c < tableData.columns; c++) {
      try {
        const column = table.Columns.Item(c + 1);
        column.PreferredWidthType = 3;
        column.PreferredWidth = avgWidth;
        column.Width = avgWidth;
      } catch (e) {}
    }

    // 表格对齐
    const tStyle = tableData.tStyle || ['center'];
    table.Rows.Alignment = getTableAlignmentValue(tStyle[0] || 'center');
  } catch (e) {}

  // 填充内容
  for (let row = 0; row < tableData.cells.length; row++) {
    for (let col = 0; col < tableData.cells[row].length; col++) {
      try {
        const cellData = tableData.cells[row][col];
        const cStyle = cellData.cStyle || DEFAULT_CSTYLE;
        const rowSpan = cStyle[CSTYLE.ROW_SPAN] || 1;
        const colSpan = cStyle[CSTYLE.COL_SPAN] || 1;
        
        if (!cellData || rowSpan === 0 || colSpan === 0) {
          continue;
        }

        const cell = table.Cell(row + 1, col + 1);
        const cellRange = cell.Range;

        if (cellData.paragraphs && cellData.paragraphs.length > 0) {
          let isFirstPara = true;
          for (const para of cellData.paragraphs) {
            if (!isFirstPara) {
              const endPos = cellRange.End - 1;
              doc.Range(endPos, endPos).InsertAfter('\r');
            }

            for (const run of para.runs) {
              const runText = cleanCellText(run.text || '');
              if (!runText) {
                continue;
              }

              const endPos = cellRange.End - 1;
              const insertRange = doc.Range(endPos, endPos);
              insertRange.InsertAfter(runText);

              const formatRange = doc.Range(endPos, endPos + runText.length);
              const font = formatRange.Font;
              
              try {
                font.Reset();  // 重置格式避免继承
                const rStyle = run.rStyle || DEFAULT_RSTYLE;
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
                }
                if (rStyle[RSTYLE.COLOR] && rStyle[RSTYLE.COLOR] !== '#000000') {
                  font.Color = parseRGBColor(rStyle[RSTYLE.COLOR]);
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
              } catch (e) {}
            }

            // 设置段落对齐
            const pStyle = para.pStyle || DEFAULT_PSTYLE;
            try {
              cellRange.ParagraphFormat.Alignment = getAlignmentValue(pStyle[PSTYLE.ALIGNMENT] || 'left');
            } catch (e) {}

            isFirstPara = false;
          }
        } else {
          if (cellData.text) {
            const cleanedText = cleanCellText(cellData.text);
            if (cleanedText) {
              cellRange.Text = cleanedText;
            }
          }

          // 设置字体格式
          const rStyle = cellData.rStyle || DEFAULT_RSTYLE;
          const font = cellRange.Font;
          font.Reset();  // 重置格式避免继承
          if (rStyle[RSTYLE.FONT_NAME]) {
            font.Name = rStyle[RSTYLE.FONT_NAME];
          }
          if (rStyle[RSTYLE.FONT_SIZE]) {
            font.Size = rStyle[RSTYLE.FONT_SIZE];
          }
          font.Bold = rStyle[RSTYLE.BOLD] ? -1 : 0;
          font.Italic = rStyle[RSTYLE.ITALIC] ? -1 : 0;

          // 设置对齐（使用循环开头的 cStyle）
          cellRange.ParagraphFormat.Alignment = getAlignmentValue(cStyle[CSTYLE.ALIGNMENT] || 'center');
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
        const rowSpan = cellData.cStyle[CSTYLE.ROW_SPAN] || 1;
        const colSpan = cellData.cStyle[CSTYLE.COL_SPAN] || 1;
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

  return doc.Content.End - 1;
}

/**
 * 从 JSON 数据生成 Word 文档
 * @param {Object} jsonData - JSON 数据
 * @param {Object} doc - 已存在的文档对象（可选，默认创建新文档）
 * @param {number} startPosition - 插入起始位置（可选，默认为当前选区位置）
 * @returns {Object} - 成功返回 {success: true, doc, startPos, endPos}，失败返回 {error: string}
 */
function generateDocxFromJSON(jsonData, doc, startPosition = null) {
  try {
    if (!jsonData || (!jsonData.paragraphs && !jsonData.tables)) {
      return { error: 'JSON数据格式不正确' };
    }

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
        elements.push({ type: 'paragraph', data: para, position: para.position || index * 1000 });
      });
    }

    if (jsonData.tables) {
      jsonData.tables.forEach((table, index) => {
        elements.push({
          type: 'table',
          data: table,
          position: table.position || (index + 0.5) * 10000
        });
      });
    }

    elements.sort((a, b) => a.position - b.position);

    // 预处理：合并连续空段落
    const processedElements = [];
    let consecutiveEmptyCount = 0;

    for (const element of elements) {
      if (element.type === 'paragraph' && element.data.isEmpty) {
        consecutiveEmptyCount++;
        if (consecutiveEmptyCount <= 2) {
          processedElements.push(element);
        }
      } else {
        consecutiveEmptyCount = 0;
        processedElements.push(element);
      }
    }

    // 确定插入起始位置
    let currentPos;
    if (startPosition !== null && startPosition !== undefined) {
      currentPos = startPosition;
    } else {
      // 默认使用当前选区位置
      const selection = window.Application.Selection;
      currentPos = selection ? selection.Range.Start : 0;
    }
    const insertStartPos = currentPos;  // 记录插入起始位置
    let paraIndex = 0;

    // 图片位置映射
    const imagesByPosition = new Map();
    if (jsonData.images && jsonData.images.length > 0) {
      for (const img of jsonData.images) {
        if (img.position) {
          imagesByPosition.set(img.position, img);
        }
      }
    }

    const findImageForParagraph = (paraPosition) => {
      for (const [pos, img] of imagesByPosition) {
        if (Math.abs(pos - paraPosition) <= 5) {
          imagesByPosition.delete(pos);
          return img;
        }
      }
      return null;
    };

    for (let i = 0; i < processedElements.length; i++) {
      const element = processedElements[i];

      if (element.type === 'paragraph') {
        const para = element.data;
        // 如果没有 text 字段，从 runs 拼接
        const paraText = para.text ? para.text.trim() : (para.runs || []).map(r => r.text || '').join('').trim();
        const isImagePlaceholder = paraText === '/' || paraText === '[图片]';

        // 获取段落样式
        const pStyle = para.pStyle || DEFAULT_PSTYLE;
        const alignment = pStyle[PSTYLE.ALIGNMENT] || 'left';
        const lineSpacing = pStyle[PSTYLE.LINE_SPACING] || 0;
        const lineSpacingRule = pStyle[PSTYLE.LINE_SPACING_RULE] || 0;
        const indentLeft = pStyle[PSTYLE.INDENT_LEFT] || 0;
        const indentRight = pStyle[PSTYLE.INDENT_RIGHT] || 0;
        const indentFirstLine = pStyle[PSTYLE.INDENT_FIRST_LINE] || 0;
        const spaceBefore = pStyle[PSTYLE.SPACE_BEFORE] || 0;
        const spaceAfter = pStyle[PSTYLE.SPACE_AFTER] || 0;
        const styleName = pStyle[PSTYLE.STYLE_NAME] || '';

        // 处理图片占位符
        if (isImagePlaceholder && para.position) {
          const img = findImageForParagraph(para.position);
          if (img) {
            const paraStartPos = currentPos;
            const charAdded = insertImage(doc, img, currentPos);
            currentPos += charAdded;

            const range = doc.Range(currentPos, currentPos);
            range.Text = '\r';
            currentPos += 1;

            try {
              const imgRange = doc.Range(paraStartPos, paraStartPos + 1);
              const imgPara = imgRange.Paragraphs.Item(1);
              if (imgPara && imgPara.Format) {
                imgPara.Format.Alignment = getAlignmentValue(alignment || 'center');
              }
            } catch (e) {}

            paraIndex++;
            continue;
          }
        }

        // 处理空段落
        if (para.isEmpty) {
          const prevElement = i > 0 ? processedElements[i - 1] : null;
          const nextElement = i < processedElements.length - 1 ? processedElements[i + 1] : null;

          const prevHasContent =
            prevElement &&
            (prevElement.type === 'table' ||
              (prevElement.type === 'paragraph' &&
                !prevElement.data.isEmpty &&
                prevElement.data.runs &&
                prevElement.data.runs.length > 0));
          const nextHasContent =
            nextElement &&
            (nextElement.type === 'table' ||
              (nextElement.type === 'paragraph' &&
                !nextElement.data.isEmpty &&
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
        const paraStartPos = currentPos;  // 记录段落开始位置（移到外面避免未定义）

        if (para.runs && para.runs.length > 0) {
          for (const run of para.runs) {
            const runText = run.text || '';
            if (!runText) {
              continue;
            }

            const range = doc.Range(currentPos, currentPos);
            range.Text = runText;

            const insertedRange = doc.Range(currentPos, currentPos + runText.length);
            const font = insertedRange.Font;

            // 应用字符样式（直接使用JSON中的值）
            const rStyle = run.rStyle || DEFAULT_RSTYLE;

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

            // 设置行距（先设磅值，再设规则，确保规则最终生效）
            if (lineSpacing && lineSpacing > 0) {
              try {
                paraFormat.LineSpacing = lineSpacing;
                paraFormat.LineSpacingRule = lineSpacingRule;
              } catch (e) {
                console.warn('设置行距失败:', e);
              }
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
        currentPos = generateTable(doc, element.data, currentPos);
        paraIndex = doc.Paragraphs.Count;

        // 表格后换行
        if (i < processedElements.length - 1) {
          let hasContentAfter = false;
          for (let j = i + 1; j < processedElements.length; j++) {
            const nextEl = processedElements[j];
            if (
              nextEl.type === 'table' ||
              (nextEl.type === 'paragraph' &&
                !nextEl.data.isEmpty &&
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

// ============== 导出 ==============

export default {
  // 主要函数
  parseDocxToJSON,
  generateDocxFromJSON,

  // 辅助函数（供外部使用）
  cleanText,
  cleanCellText,
  exportImageToTemp,

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
  cleanText,
  cleanCellText,
  exportImageToTemp,
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

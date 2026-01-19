/**
 * WPS Word 文档与 JSON 双向转换工具
 *
 * 功能：
 * 1. parseDocxToJSON - 将 Word 文档内容解析为 JSON 格式
 * 2. generateDocxFromJSON - 从 JSON 数据生成 Word 文档
 *
 * JSON 数据结构：
 * {
 *   text: string,              // 纯文本内容
 *   paragraphs: [{             // 段落数组
 *     text: string,            // 段落文本
 *     alignment: string,       // 对齐: left/center/right/justify
 *     lineSpacing: number,     // 行间距
 *     indentLeft: number,      // 左缩进
 *     indentRight: number,     // 右缩进
 *     indentFirstLine: number, // 首行缩进
 *     spaceBefore: number,     // 段前间距
 *     spaceAfter: number,      // 段后间距
 *     styleName: string,       // 样式名称
 *     position: number,        // 文档中位置
 *     tabStops: [{position, alignment, leader}],
 *     runs: [{                 // 格式块数组
 *       text: string,
 *       fontName: string,
 *       fontSize: number,
 *       bold: boolean,
 *       italic: boolean,
 *       underline: string,
 *       color: string,
 *       highlight: string,
 *       strikethrough: boolean,
 *       superscript: boolean,
 *       subscript: boolean
 *     }]
 *   }],
 *   tables: [{                 // 表格数组
 *     rows: number,
 *     columns: number,
 *     tableAlignment: string,
 *     columnWidths: number[],
 *     position: number,
 *     cells: [[{               // 单元格二维数组
 *       text: string,
 *       rowSpan: number,
 *       colSpan: number,
 *       paragraphs: [{...}],   // 复杂格式时的段落数组
 *       alignment: string,
 *       verticalAlignment: string
 *     }]]
 *   }],
 *   images: [{                 // 图片数组
 *     type: string,            // inline/floating
 *     width: number,
 *     height: number,
 *     position: number,
 *     tempPath: string,
 *     altText: string,
 *     wrapType: string         // 浮动图片环绕方式
 *   }],
 *   fields: [],                // 域代码数组
 *   hasTOC: boolean            // 是否包含目录
 * }
 */

// ============== 格式转换辅助函数 ==============

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
 * 下划线：值 -> 名称
 */
function getUnderlineName(underline) {
  if (underline === 0) {
    return 'none';
  }
  if (underline === 1) {
    return 'single';
  }
  if (underline === 2) {
    return 'double';
  }
  if (underline === 3) {
    return 'thick';
  }
  return 'none';
}

/**
 * 下划线：名称 -> 值
 */
function getUnderlineValue(underline) {
  const map = { none: 0, single: 1, double: 2, thick: 3 };
  return map[underline] || 0;
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
 * 高亮色：索引 -> 名称
 */
function getHighlightName(highlightIndex) {
  const map = {
    0: 'none',
    1: 'black',
    2: 'blue',
    3: 'cyan',
    4: 'green',
    5: 'magenta',
    6: 'red',
    7: 'yellow',
    8: 'white',
    9: 'darkBlue',
    10: 'darkCyan',
    11: 'darkGreen',
    12: 'darkMagenta',
    13: 'darkRed',
    14: 'darkYellow',
    15: 'darkGray',
    16: 'lightGray'
  };
  return map[highlightIndex] || 'none';
}

/**
 * 高亮色：名称 -> 索引
 */
function getHighlightValue(highlight) {
  const map = {
    none: 0,
    black: 1,
    blue: 2,
    cyan: 3,
    green: 4,
    magenta: 5,
    red: 6,
    yellow: 7,
    white: 8,
    darkBlue: 9,
    darkCyan: 10,
    darkGreen: 11,
    darkMagenta: 12,
    darkRed: 13,
    darkYellow: 14,
    darkGray: 15,
    lightGray: 16
  };
  return map[highlight] || 0;
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
          alignment: getAlignmentName(para.Format.Alignment),
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
                  fontName: font.Name || '',
                  fontSize: font.Size || 12,
                  bold: font.Bold === -1 || font.Bold === true,
                  italic: font.Italic === -1 || font.Italic === true,
                  underline: getUnderlineName(font.Underline),
                  color: getRGBColor(font.Color)
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
            fontName: font.Name || '',
            fontSize: font.Size || 12,
            bold: font.Bold === -1 || font.Bold === true,
            italic: font.Italic === -1 || font.Italic === true
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
    tableWidth: table.PreferredWidth || 0,
    tableWidthType: table.PreferredWidthType || 0,
    tableAlignment: getTableAlignmentName(table.Rows.Alignment),
    columnWidths: []
  };

  // 获取列宽
  try {
    for (let c = 1; c <= table.Columns.Count; c++) {
      tableData.columnWidths.push(table.Columns.Item(c).Width || 0);
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
          fontName: cellFont.Name || '',
          fontSize: cellFont.Size || 12,
          bold: cellFont.Bold === -1 || cellFont.Bold === true,
          italic: cellFont.Italic === -1 || cellFont.Italic === true,
          alignment: getAlignmentName(cellRange.ParagraphFormat.Alignment),
          verticalAlignment: getCellVerticalAlignmentName(cell.VerticalAlignment),
          width: cell.Width || 0,
          height: cell.Height || 0,
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

      rowData.push({
        text: rawCell.text,
        paragraphs: rawCell.paragraphs,
        rowSpan,
        colSpan,
        fontName: rawCell.fontName,
        fontSize: rawCell.fontSize,
        bold: rawCell.bold,
        italic: rawCell.italic,
        alignment: rawCell.alignment,
        verticalAlignment: rawCell.verticalAlignment,
        width: rawCell.width,
        height: rawCell.height
      });
    }
    tableData.cells.push(rowData);
  }

  return tableData;
}

/**
 * 解析 Word 文档选中内容为 JSON
 * @param {Object} range - WPS Range 对象（可选，默认使用当前选中）
 * @returns {Object} - JSON 数据或错误对象
 */
function parseDocxToJSON(range) {
  try {
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
      text: cleanText(range.Text),
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
            text: '',
            alignment: getAlignmentName(para.Format.Alignment),
            lineSpacing: para.Format.LineSpacing || 0,
            indentLeft: para.Format.LeftIndent || 0,
            indentRight: para.Format.RightIndent || 0,
            indentFirstLine: para.Format.FirstLineIndent || 0,
            spaceBefore: para.Format.SpaceBefore || 0,
            spaceAfter: para.Format.SpaceAfter || 0,
            runs: [],
            isEmpty: true,
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
          text: cleanText(paraText),
          alignment: getAlignmentName(paraFormat.Alignment),
          lineSpacing: paraFormat.LineSpacing || 0,
          indentLeft: paraFormat.LeftIndent || 0,
          indentRight: paraFormat.RightIndent || 0,
          indentFirstLine: paraFormat.FirstLineIndent || 0,
          spaceBefore: paraFormat.SpaceBefore || 0,
          spaceAfter: paraFormat.SpaceAfter || 0,
          runs: [],
          tabStops: [],
          position: paraStart,
          styleName
        };

        // 解析制表位
        try {
          const tabStops = paraFormat.TabStops;
          if (tabStops && tabStops.Count > 0) {
            for (let t = 1; t <= tabStops.Count; t++) {
              const tab = tabStops.Item(t);
              paragraphData.tabStops.push({
                position: tab.Position || 0,
                alignment: getTabAlignmentName(tab.Alignment),
                leader: getTabLeaderName(tab.Leader)
              });
            }
          }
        } catch (e) {}

        // 解析 runs
        const words = paraRange.Words;
        if (words && words.Count > 0) {
          let lastFormat = null;
          let currentRun = null;

          for (let j = 1; j <= words.Count; j++) {
            const word = words.Item(j);
            const font = word.Font;
            const wordText = word.Text || '';

            if (wordText.match(/^[\r\n\f\u0007]+$/)) {
              continue;
            }

            const formatKey = [
              font.Name,
              font.Size,
              font.Bold,
              font.Italic,
              font.Underline,
              font.Color,
              font.HighlightColorIndex,
              font.StrikeThrough,
              font.Superscript,
              font.Subscript
            ].join('|');

            if (formatKey === lastFormat && currentRun) {
              currentRun.text += cleanText(wordText);
            } else {
              if (currentRun && currentRun.text) {
                paragraphData.runs.push(currentRun);
              }
              currentRun = {
                text: cleanText(wordText),
                fontName: font.Name || '',
                fontSize: font.Size || 0,
                bold: font.Bold === -1 || font.Bold === true,
                italic: font.Italic === -1 || font.Italic === true,
                underline: getUnderlineName(font.Underline),
                color: getRGBColor(font.Color),
                highlight: getHighlightName(font.HighlightColorIndex),
                strikethrough: font.StrikeThrough === -1 || font.StrikeThrough === true,
                superscript: font.Superscript === -1 || font.Superscript === true,
                subscript: font.Subscript === -1 || font.Subscript === true
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

    const columnWidths = new Array(tableData.columns).fill(0);
    let hasValidWidths = false;

    for (const row of tableData.cells) {
      let colIndex = 0;
      for (const cell of row) {
        if (cell && cell.rowSpan > 0 && cell.colSpan === 1) {
          if (cell.width > 0 && cell.width < 9999999) {
            if (columnWidths[colIndex] === 0) {
              columnWidths[colIndex] = cell.width;
              hasValidWidths = true;
            }
          }
        }
        colIndex += cell && cell.colSpan > 0 ? cell.colSpan : 1;
      }
    }

    let totalWidth = columnWidths.reduce((sum, w) => sum + w, 0);

    if (!hasValidWidths || totalWidth === 0) {
      totalWidth = pageWidth;
      const avgWidth = pageWidth / tableData.columns;
      for (let i = 0; i < tableData.columns; i++) {
        columnWidths[i] = avgWidth;
      }
    } else {
      const validWidths = columnWidths.filter((w) => w > 0);
      const avgValidWidth =
        validWidths.length > 0
          ? validWidths.reduce((a, b) => a + b, 0) / validWidths.length
          : pageWidth / tableData.columns;
      for (let i = 0; i < columnWidths.length; i++) {
        if (columnWidths[i] === 0) {
          columnWidths[i] = avgValidWidth;
          totalWidth += avgValidWidth;
        }
      }
    }

    // 限制不超过页面宽度
    if (totalWidth > pageWidth) {
      const scale = pageWidth / totalWidth;
      for (let i = 0; i < columnWidths.length; i++) {
        columnWidths[i] = Math.floor(columnWidths[i] * scale);
      }
      totalWidth = pageWidth;
    }

    table.AutoFitBehavior(0);
    try {
      table.PreferredWidthType = 3;
      table.PreferredWidth = totalWidth;
    } catch (e) {}

    for (let c = 0; c < columnWidths.length && c < tableData.columns; c++) {
      try {
        const column = table.Columns.Item(c + 1);
        column.PreferredWidthType = 3;
        column.PreferredWidth = columnWidths[c];
        column.Width = columnWidths[c];
      } catch (e) {}
    }

    table.Rows.Alignment = getTableAlignmentValue(tableData.tableAlignment || 'center');
  } catch (e) {}

  // 填充内容
  for (let row = 0; row < tableData.cells.length; row++) {
    for (let col = 0; col < tableData.cells[row].length; col++) {
      try {
        const cellData = tableData.cells[row][col];
        if (!cellData || cellData.rowSpan === 0 || cellData.colSpan === 0) {
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
              try {
                if (run.fontName) {
                  formatRange.Font.Name = run.fontName;
                }
                if (run.fontSize) {
                  formatRange.Font.Size = run.fontSize;
                }
                if (run.bold) {
                  formatRange.Font.Bold = -1;
                }
                if (run.italic) {
                  formatRange.Font.Italic = -1;
                }
                if (run.underline && run.underline !== 'none') {
                  formatRange.Font.Underline = getUnderlineValue(run.underline);
                }
                if (run.color && run.color !== '#000000') {
                  formatRange.Font.Color = parseRGBColor(run.color);
                }
              } catch (e) {}
            }

            try {
              cellRange.ParagraphFormat.Alignment = getAlignmentValue(
                para.alignment || cellData.alignment || 'left'
              );
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

          if (cellData.fontName) {
            cellRange.Font.Name = cellData.fontName;
          }
          if (cellData.fontSize) {
            cellRange.Font.Size = cellData.fontSize;
          }
          if (cellData.bold) {
            cellRange.Font.Bold = -1;
          }
          if (cellData.italic) {
            cellRange.Font.Italic = -1;
          }

          cellRange.ParagraphFormat.Alignment = getAlignmentValue(cellData.alignment || 'center');
        }

        cell.VerticalAlignment = getCellVerticalAlignmentValue(
          cellData.verticalAlignment || 'center'
        );
      } catch (e) {}
    }
  }

  // 收集并执行合并
  const mergeTasks = [];
  for (let row = 0; row < tableData.cells.length; row++) {
    for (let col = 0; col < tableData.cells[row].length; col++) {
      const cellData = tableData.cells[row][col];
      if (cellData) {
        const rowSpan = cellData.rowSpan || 1;
        const colSpan = cellData.colSpan || 1;
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
 * @returns {Object} - 成功返回 {success: true, doc}，失败返回 {error: string}
 */
function generateDocxFromJSON(jsonData, doc) {
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

    let currentPos = 0;
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
        const paraText = (para.text || '').trim();
        const isImagePlaceholder = paraText === '/' || paraText === '[图片]';

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
                imgPara.Format.Alignment = getAlignmentValue(para.alignment || 'center');
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

            if (run.fontName) {
              font.Name = run.fontName;
            }
            if (run.fontSize) {
              font.Size = run.fontSize;
            }
            font.Bold = run.bold ? -1 : 0;
            font.Italic = run.italic ? -1 : 0;
            font.StrikeThrough = run.strikethrough ? -1 : 0;
            font.Superscript = run.superscript ? -1 : 0;
            font.Subscript = run.subscript ? -1 : 0;
            font.Underline = getUnderlineValue(run.underline);

            if (run.color && run.color !== '#000000') {
              font.Color = parseRGBColor(run.color);
            }
            if (run.highlight && run.highlight !== 'none') {
              font.HighlightColorIndex = getHighlightValue(run.highlight);
            }

            currentPos += runText.length;
          }
        }

        // 段落末尾换行
        if (i < processedElements.length - 1) {
          const nextElement = processedElements[i + 1];
          if (nextElement && nextElement.type !== 'table') {
            const range = doc.Range(currentPos, currentPos);
            range.Text = '\r';
            currentPos += 1;
          }
        }

        // 设置段落格式
        try {
          paraIndex++;
          const paraCount = doc.Paragraphs.Count;
          if (paraCount > 0 && paraIndex <= paraCount) {
            const currentPara = doc.Paragraphs.Item(paraIndex);
            const paraFormat = currentPara.Format;

            if (para.styleName) {
              try {
                currentPara.Style = para.styleName;
              } catch (e) {}
            }

            paraFormat.Alignment = getAlignmentValue(para.alignment);
            if (para.lineSpacing && para.lineSpacing > 0) {
              paraFormat.LineSpacing = para.lineSpacing;
            }
            if (para.indentLeft !== undefined) {
              paraFormat.LeftIndent = para.indentLeft;
            }
            if (para.indentRight !== undefined) {
              paraFormat.RightIndent = para.indentRight;
            }
            if (para.indentFirstLine !== undefined) {
              paraFormat.FirstLineIndent = para.indentFirstLine;
            }
            if (para.spaceBefore !== undefined) {
              paraFormat.SpaceBefore = para.spaceBefore;
            }
            if (para.spaceAfter !== undefined) {
              paraFormat.SpaceAfter = para.spaceAfter;
            }

            if (para.tabStops && para.tabStops.length > 0) {
              try {
                paraFormat.TabStops.ClearAll();
              } catch (e) {}
              for (const tab of para.tabStops) {
                try {
                  paraFormat.TabStops.Add(
                    tab.position,
                    getTabAlignmentValue(tab.alignment),
                    getTabLeaderValue(tab.leader)
                  );
                } catch (e) {}
              }
            }
          }
        } catch (e) {}
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

    return { success: true, message: '文档生成成功！', doc };
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
  getUnderlineName,
  getUnderlineValue,
  getRGBColor,
  parseRGBColor,
  getHighlightName,
  getHighlightValue
};

// 也支持命名导出
export {
  parseDocxToJSON,
  generateDocxFromJSON,
  cleanText,
  cleanCellText,
  exportImageToTemp,
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
  getUnderlineName,
  getUnderlineValue,
  getRGBColor,
  parseRGBColor,
  getHighlightName,
  getHighlightValue
};

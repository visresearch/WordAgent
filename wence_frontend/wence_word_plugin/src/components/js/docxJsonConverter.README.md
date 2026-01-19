# docxJsonConverter.js 使用文档

WPS Word 文档与 JSON 双向转换工具，用于 WPS 加载项开发。

## 安装

将 `docxJsonConverter.js` 放入项目中，然后导入：

```javascript
import { parseDocxToJSON, generateDocxFromJSON } from './docxJsonConverter.js'

// 或者
import docxJsonConverter from './docxJsonConverter.js'
```

## 核心 API

### 1. parseDocxToJSON(range?)

将 Word 文档内容解析为 JSON 格式。

**参数：**

- `range` (可选): WPS Range 对象。不传则自动获取当前选中内容。

**返回值：**

- 成功: JSON 数据对象
- 失败: `{ error: '错误信息' }`

**示例：**

```javascript
// 解析当前选中内容
const jsonData = parseDocxToJSON()

// 解析全文
const doc = window.Application.ActiveDocument
const jsonData = parseDocxToJSON(doc.Content)

// 解析指定范围（前1000个字符）
const customRange = doc.Range(0, 1000)
const jsonData = parseDocxToJSON(customRange)

// 检查是否成功
if (jsonData.error) {
  console.error('解析失败:', jsonData.error)
} else {
  console.log('段落数:', jsonData.paragraphs.length)
  console.log('表格数:', jsonData.tables.length)
  console.log('图片数:', jsonData.images.length)
}
```

---

### 2. generateDocxFromJSON(jsonData, doc?)

从 JSON 数据生成 Word 文档。

**参数：**

- `jsonData` (必需): 符合格式的 JSON 数据对象
- `doc` (可选): 已存在的文档对象。不传则创建新文档。

**返回值：**

- 成功: `{ success: true, message: '文档生成成功！', doc: 文档对象 }`
- 失败: `{ error: '错误信息' }`

**示例：**

```javascript
// 从 JSON 创建新文档
const result = generateDocxFromJSON(jsonData)
if (result.success) {
  console.log('生成成功！')
}

// 在指定文档中生成
const existingDoc = window.Application.ActiveDocument
const result = generateDocxFromJSON(jsonData, existingDoc)
```

---

## JSON 数据结构

```javascript
{
  // 纯文本内容
  text: "全文纯文本...",

  // 段落数组
  paragraphs: [
    {
      text: "段落文本",
      alignment: "left",       // left/center/right/justify/distribute
      lineSpacing: 12,         // 行间距（磅）
      indentLeft: 0,           // 左缩进（磅）
      indentRight: 0,          // 右缩进（磅）
      indentFirstLine: 24,     // 首行缩进（磅）
      spaceBefore: 0,          // 段前间距（磅）
      spaceAfter: 0,           // 段后间距（磅）
      styleName: "正文",       // 样式名称
      position: 100,           // 在文档中的位置
      isEmpty: false,          // 是否空段落

      // 制表位
      tabStops: [
        { position: 100, alignment: "left", leader: "none" }
      ],

      // 格式块数组（文本按格式分块）
      runs: [
        {
          text: "这是加粗文本",
          fontName: "宋体",
          fontSize: 12,
          bold: true,
          italic: false,
          underline: "none",    // none/single/double/thick
          color: "#000000",     // RGB颜色
          highlight: "none",    // 高亮色
          strikethrough: false, // 删除线
          superscript: false,   // 上标
          subscript: false      // 下标
        }
      ]
    }
  ],

  // 表格数组
  tables: [
    {
      rows: 3,                  // 行数
      columns: 4,               // 列数
      tableAlignment: "center", // 表格对齐
      columnWidths: [100, 100, 100, 100], // 列宽数组
      position: 500,            // 在文档中的位置

      // 单元格二维数组
      cells: [
        [
          {
            text: "单元格内容",
            rowSpan: 1,         // 行合并数（0表示被合并）
            colSpan: 1,         // 列合并数（0表示被合并）
            alignment: "center",
            verticalAlignment: "center", // top/center/bottom
            fontName: "宋体",
            fontSize: 12,
            bold: false,
            italic: false,
            width: 100,
            height: 30,

            // 复杂格式时的段落数组（可选）
            paragraphs: [
              {
                text: "段落1",
                alignment: "left",
                runs: [...]
              }
            ]
          }
        ]
      ]
    }
  ],

  // 图片数组
  images: [
    {
      type: "inline",          // inline(嵌入式)/floating(浮动)
      width: 200,              // 宽度（磅）
      height: 150,             // 高度（磅）
      position: 300,           // 在文档中的位置
      tempPath: "/tmp/wps_img_xxx.png", // 导出的临时路径
      altText: "图片说明",
      saved: true,             // 是否成功导出

      // 浮动图片特有属性
      left: 100,               // 左边距
      top: 200,                // 上边距
      wrapType: "square"       // 环绕方式
    }
  ],

  // 域代码数组
  fields: [
    { type: 13, code: "TOC ...", start: 0, end: 100 }
  ],

  // 是否包含目录
  hasTOC: false,
  tocFieldCode: ""
}
```

---

## 完整使用示例

### 示例1：复制文档格式

```javascript
import { parseDocxToJSON, generateDocxFromJSON } from './docxJsonConverter.js'

// 1. 选中要复制的内容（或使用全文）
const doc = window.Application.ActiveDocument
const jsonData = parseDocxToJSON(doc.Content)

// 2. 可以修改 JSON 数据
jsonData.paragraphs.forEach((para) => {
  para.runs.forEach((run) => {
    run.fontSize = 14 // 统一改为14号字
  })
})

// 3. 生成新文档
const result = generateDocxFromJSON(jsonData)
if (result.success) {
  alert('文档复制成功！')
}
```

### 示例2：导出为 JSON 文件

```javascript
const jsonData = parseDocxToJSON()

// 下载为文件
const jsonString = JSON.stringify(jsonData, null, 2)
const blob = new Blob([jsonString], { type: 'application/json' })
const url = URL.createObjectURL(blob)
const a = document.createElement('a')
a.href = url
a.download = 'document.json'
a.click()
URL.revokeObjectURL(url)
```

### 示例3：从 JSON 文件导入

```javascript
// 假设已通过 FileReader 读取了 JSON 文件内容
const jsonString = '...' // 文件内容
const jsonData = JSON.parse(jsonString)

const result = generateDocxFromJSON(jsonData)
if (result.error) {
  alert('生成失败: ' + result.error)
}
```

### 示例4：提取文档中的所有表格

```javascript
const jsonData = parseDocxToJSON(doc.Content)

jsonData.tables.forEach((table, index) => {
  console.log(`表格 ${index + 1}: ${table.rows}行 x ${table.columns}列`)

  table.cells.forEach((row, rowIndex) => {
    row.forEach((cell, colIndex) => {
      if (cell.rowSpan > 0 && cell.colSpan > 0) {
        console.log(`  [${rowIndex},${colIndex}]: ${cell.text}`)
      }
    })
  })
})
```

---

## 特殊处理说明

### 1. 表格合并单元格

- **解析时**: 使用两阶段检测，先收集所有单元格，再分析 rowSpan/colSpan
- **生成时**: 先填充内容，再从右下到左上执行合并（避免索引错乱）
- **被合并的单元格**: rowSpan=0 或 colSpan=0

### 2. 表格宽度

- 自动计算页面可用宽度（页宽 - 左右边距）
- 表格总宽度超出时按比例缩放

### 3. 单元格复杂格式

单元格内有多种字体/格式时，使用 `paragraphs` 数组：

```javascript
cell: {
  text: "完整文本",
  paragraphs: [
    {
      text: "第一段",
      runs: [
        { text: "普通", bold: false },
        { text: "加粗", bold: true }
      ]
    },
    {
      text: "第二段",
      runs: [...]
    }
  ]
}
```

### 4. 图片处理

- **解析时**: 使用 `SaveAsPicture` 导出到临时目录
- **生成时**: 根据 position 匹配占位符段落（"/"），在原位插入
- **临时文件**: 位于 WPS 临时目录，需手动清理

清理临时图片：

```bash
# Linux
rm -f ~/.local/share/Kingsoft/office6/templates/wps/zh_CN/wps_img_*.png

# Windows
del /q %APPDATA%\kingsoft\office6\templates\wps\zh_CN\wps_img_*.png
```

### 5. 特殊字符

自动清理以下字符：

- `\u0007` - 表格单元格结束符
- `\u0001` - 域占位符
- `\f` - 分页符
- `\r` - 末尾回车

---

## 辅助函数

如果需要单独使用格式转换：

```javascript
import {
  getAlignmentName, // 对齐值 -> 名称
  getAlignmentValue, // 对齐名称 -> 值
  getRGBColor, // 颜色值 -> #RRGGBB
  parseRGBColor, // #RRGGBB -> 颜色值
  cleanText, // 清理特殊字符
  cleanCellText // 清理单元格文本
} from './docxJsonConverter.js'

// 示例
const alignName = getAlignmentName(1) // "center"
const alignValue = getAlignmentValue('center') // 1
const hexColor = getRGBColor(255) // "#ff0000"
```

---

## 注意事项

1. **仅限 WPS 加载项环境**: 依赖 `window.Application` API
2. **图片需要临时文件**: 图片通过临时文件传递，JSON 中存储路径
3. **样式名称**: 生成时会尝试应用样式，样式不存在则使用手动格式
4. **大文档性能**: 解析大文档可能较慢，建议分段处理

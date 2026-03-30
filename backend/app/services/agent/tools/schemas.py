"""单智能体工具使用的文档与查询 Schema。"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Run(BaseModel):
    """格式块 - 一段具有相同格式的文字"""

    text: str = Field(description="文字内容")
    rStyle: str = Field(description='字符样式引用ID，如 "rS_1"，对应 document.styles["rS_1"]')


class Paragraph(BaseModel):
    """段落 - 每行内容独立为一个段落，禁止在 text 中使用 \\n 换行。runs 为空数组时表示空段落"""

    pStyle: str = Field(
        description='段落样式引用ID，如 "pS_1"，对应 document.styles["pS_1"]。空段落时可省略', default=""
    )
    runs: list[Run] = Field(
        description="格式块数组。一个段落可包含多个 run（不同格式的文字拆为不同 run）。"
        "禁止在 text 中使用 \\n 换行，换行必须新建段落。空段落时为空数组。",
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_empty_paragraph_shape(self):
        """runs 为空时视为空段落，空段落要求 pStyle 为空字符串。"""
        if not self.runs and self.pStyle != "":
            raise ValueError("空段落（runs 为空数组）要求 pStyle 为空字符串")
        return self


class CellParagraph(BaseModel):
    """单元格内段落 - 一个单元格可包含多个段落，每个段落有独立的样式和格式块"""

    text: str = Field(description="段落文本（可选，所有 runs 的文本拼接）", default="")
    pStyle: str = Field(description='段落样式引用ID，如 "pS_1"。控制对齐、行距等段落格式', default="")
    runs: list[Run] = Field(
        description="格式块数组。单元格内一个段落可包含多个不同格式的 run",
        default_factory=list,
    )


class Cell(BaseModel):
    """表格单元格。支持两种模式：
    1. 简单模式：只填 text + cStyle（单段落纯文本，字体由 rStyle 控制）
    2. 多段落模式：填 paragraphs + cStyle（单元格内多段落，每段有独立格式）
    优先使用 paragraphs 模式以获得精确的格式还原。"""

    text: str = Field(description="单元格文本（简单模式必填；多段落模式下可为空字符串）", default="")
    paragraphs: list[CellParagraph] | None = Field(
        default=None,
        description="单元格内段落数组（多段落模式）。每个段落有独立的 pStyle 和 runs。"
        "填写此字段时，text 字段会被忽略，内容以 paragraphs 为准。",
    )
    rStyle: str | None = Field(
        default=None,
        description='单元格整体字符样式引用ID（简单模式使用），如 "rS_1"。'
        "多段落模式下由各 run 的 rStyle 控制，此字段可省略。",
    )
    cStyle: str = Field(description='单元格样式引用ID，如 "cS_1"，对应 document.styles["cS_1"]')


class Table(BaseModel):
    """表格。包含行列数、单元格内容、表格样式，以及可选的列宽和行高控制。"""

    rows: int = Field(description="行数")
    columns: int = Field(description="列数")
    cells: list[list[Cell]] = Field(description="单元格二维数组，cells[row][col]")
    tStyle: str = Field(description='表格样式引用ID，如 "tS_1"，对应 document.styles["tS_1"]')
    columnWidths: list[float] | None = Field(
        default=None,
        description="每列宽度数组（磅值），长度必须等于 columns。"
        "省略时前端自动等分页面宽度。如 [120, 280] 表示第1列120磅、第2列280磅。",
    )
    rowHeights: list[list[int | float]] | None = Field(
        default=None,
        description="每行高度数组，长度必须等于 rows。每项为 [height, heightRule]："
        "height=高度（磅值）；heightRule: 0=自动（文字撑高）、1=最小值（至少这么高）、2=固定值。"
        "省略时行高自动由内容决定。如 [[40, 1], [40, 1]] 表示2行各至少40磅高。",
    )


class DocumentOutput(BaseModel):
    """文档输出结构。paragraphs 和 tables 是两个独立的顶级字段，不要混合。"""

    paragraphs: list[Paragraph] = Field(description="段落数组，每个元素必须是 Paragraph 对象，不要放字符串")
    tables: list[Table] = Field(default_factory=list, description="表格数组，每个元素必须是 Table 对象")
    styles: dict[str, list] = Field(
        description="样式字典（必填）。key 为引用ID（如 pS_1、rS_1、cS_1、tS_1），value 为样式数组。"
        "必须包含所有 pStyle/rStyle/cStyle/tStyle 引用到的样式定义。\n"
        "pStyle 数组格式: [对齐, 行距, 左缩进, 右缩进, 首行缩进, 段前, 段后, 样式名, 行距规则]。"
        "对齐: left/center/right/justify; "
        "行距: 磅值(points)，仅在行距规则=3/4/5时生效(规则0/1/2为预设档位，WPS忽略此字段)，以12pt字号为例：单倍=12,1.5倍=18,双倍=24; "
        "左缩进/右缩进/首行缩进: 磅值，每个中文字符≈12磅，2字符缩进=24，0=无缩进; "
        "段前/段后: 磅值，如12=约1行，0=无间距; "
        "样式名: 如'正文','标题 1','标题 2'等; "
        "行距规则(WPS常量): 0=单倍行距,1=1.5倍行距,2=双倍行距,3=至少,4=固定值,5=多倍行距。"
        "注意：规则0/1/2为预设档位(WPS自动计算行距，忽略行距字段)；规则3/4/5使用行距字段的磅值；普通文档推荐用行距规则=3(至少)配合明确的磅值。\n"
        "rStyle 数组格式: [字体, 字号, 粗体, 斜体, 下划线, 下划线颜色, 颜色, 高亮, 删除线, 上标, 下标]。"
        "字体: 如'宋体','Times New Roman'; 字号: 磅值; 粗体/斜体: bool; "
        "下划线: 0=无,1=单线,3=双线,4=虚线,6=粗线,11=波浪线; "
        "下划线颜色/颜色: #RRGGBB格式; "
        "高亮: 0=无,1=黑,2=蓝,3=青绿,4=鲜绿,5=粉红,6=红,7=黄,9=深蓝,10=青,11=绿,12=紫罗兰,13=深红,14=深黄,15=深灰,16=浅灰; "
        "删除线/上标/下标: bool。\n"
        "cStyle 数组格式: [rowSpan, colSpan, alignment, verticalAlignment]。"
        "rowSpan/colSpan: 合并行/列数; alignment: 同pStyle; verticalAlignment: 0=顶端,1=居中,2=底端。\n"
        "tStyle 数组格式: [tableAlignment]。tableAlignment: 0=左对齐,1=居中,2=右对齐。"
    )
    insertParaIndex: int = Field(
        default=-1,
        description="插入位置（段落索引，0-based），前端会在该段落之前插入生成的内容。"
        "如果用户选中了文档范围，应设为该范围的 startParaIndex；"
        "如果是新建内容无特定位置，设为 -1（文档末尾）或 0（文档开头）。",
    )

    @model_validator(mode="before")
    @classmethod
    def filter_invalid_paragraphs(cls, data):
        """过滤 paragraphs 中的非法项。"""
        if isinstance(data, dict) and "paragraphs" in data:
            cleaned = []
            for p in data["paragraphs"]:
                if isinstance(p, Paragraph):
                    cleaned.append(p)
                elif isinstance(p, dict):
                    # 跳过没有 runs 的非法段落
                    if "runs" not in p:
                        continue
                    cleaned.append(p)
                # 跳过字符串等非法类型
            data["paragraphs"] = cleaned
        return data

    @model_validator(mode="after")
    def validate_style_references(self):
        """校验样式引用必须存在于 styles 字典中。"""
        style_keys = set(self.styles.keys())
        missing: set[str] = set()

        for para in self.paragraphs:
            if not para.runs:
                continue
            if para.pStyle not in style_keys:
                missing.add(para.pStyle)
            for run in para.runs:
                if run.rStyle not in style_keys:
                    missing.add(run.rStyle)

        for table in self.tables:
            if table.tStyle not in style_keys:
                missing.add(table.tStyle)
            for row in table.cells:
                for cell in row:
                    if cell.cStyle not in style_keys:
                        missing.add(cell.cStyle)
                    if cell.rStyle and cell.rStyle not in style_keys:
                        missing.add(cell.rStyle)
                    if cell.paragraphs:
                        for cp in cell.paragraphs:
                            if cp.pStyle and cp.pStyle not in style_keys:
                                missing.add(cp.pStyle)
                            for run in cp.runs:
                                if run.rStyle not in style_keys:
                                    missing.add(run.rStyle)

        if missing:
            refs = ", ".join(sorted(missing))
            raise ValueError(f"styles 缺少引用定义: {refs}")
        return self


class RangeFilter(BaseModel):
    """数值范围筛选，用于 fontSize、lineSpacing 等字段"""

    gt: float | None = Field(default=None, description="大于")
    lt: float | None = Field(default=None, description="小于")
    gte: float | None = Field(default=None, description="大于等于")
    lte: float | None = Field(default=None, description="小于等于")


class QueryFilter(BaseModel):
    """查询筛选条件，所有字段为 AND 关系。只需填写需要筛选的字段，其余留空。"""

    # 文本匹配（统一使用正则）
    regex: str | None = Field(
        default=None,
        description="正则表达式匹配文本（run 级别匹配 run.text；paragraph 级别匹配段落拼接文本）",
    )
    regexFlags: str | None = Field(
        default="i",
        description="正则标志位，如 i(忽略大小写)、m(多行)、s(dotall)。例如 'im'",
    )

    # Run 级别样式（type=run 时直接匹配；type=paragraph 时检查段落中是否存在匹配的 run）
    fontName: str | None = Field(default=None, description="字体名，精确匹配，如 '宋体'、'楷体'、'Times New Roman'")
    fontSize: float | RangeFilter | None = Field(
        default=None, description="字号。精确值如 14；或范围如 {gt: 14}、{gte: 14, lte: 18}"
    )
    bold: bool | None = Field(default=None, description="粗体")
    italic: bool | None = Field(default=None, description="斜体")
    underline: int | None = Field(default=None, description="下划线: 0=无, 1=单线, 3=双线, 4=虚线, 6=粗线, 11=波浪线")
    color: str | None = Field(default=None, description="字体颜色 #RRGGBB 格式，如 '#FF0000' 为红色")
    highlight: int | None = Field(
        default=None, description="高亮色: 0=无, 1=黑, 2=蓝, 3=青绿, 4=鲜绿, 5=粉红, 6=红, 7=黄"
    )
    strikethrough: bool | None = Field(default=None, description="删除线")
    superscript: bool | None = Field(default=None, description="上标")
    subscript: bool | None = Field(default=None, description="下标")

    # Paragraph 级别样式（仅 type=paragraph 时有效）
    alignment: str | None = Field(default=None, description="段落对齐: left/center/right/justify")
    styleName: str | None = Field(
        default=None, description="段落样式名，包含匹配（如 '标题' 可匹配 '标题 1'、'标题 2'）"
    )
    lineSpacing: float | RangeFilter | None = Field(
        default=None, description="行距（磅值）。单倍=12, 1.5倍=18, 双倍=24；精确值如 18；或范围如 {gt: 18}"
    )


class DocumentQuery(BaseModel):
    """文档查询 DSL"""

    type: Literal["run", "paragraph"] = Field(
        default="run",
        description="搜索粒度：run=格式块级别（精确到同一格式的文字片段），paragraph=段落级别",
    )
    filters: QueryFilter = Field(description="筛选条件，所有字段为 AND 关系，只填需要的字段")

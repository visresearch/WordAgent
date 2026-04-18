"""Document and query schemas used by agent tools."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Run(BaseModel):
    """A text run with uniform character formatting."""

    text: str = Field(description="Text content")
    rStyle: str = Field(description='Character style reference ID, e.g. "rS_1", mapped to document.styles["rS_1"]')


class Paragraph(BaseModel):
    """A paragraph. Each line should be a separate paragraph; do not use \\n in run text."""

    pStyle: str = Field(
        description='Paragraph style reference ID, e.g. "pS_1", mapped to document.styles["pS_1"]. Optional for empty paragraphs.',
        default="",
    )
    runs: list[Run] = Field(
        description="Array of runs. A paragraph can contain multiple runs with different formatting."
        " Do not use \\n for line breaks in text; create new paragraphs instead."
        " Use an empty array for blank paragraphs.",
        default_factory=list,
    )
    paraIndex: int | None = Field(
        default=None,
        description="Optional paragraph index used for image placeholder mapping."
        " For generated content, this can be local 0-based index within this payload.",
    )

    @model_validator(mode="after")
    def validate_empty_paragraph_shape(self):
        """If runs is empty, paragraph is considered blank and pStyle must be empty."""
        if not self.runs and self.pStyle != "":
            raise ValueError("Blank paragraph requires empty pStyle when runs is an empty array")
        return self


class CellParagraph(BaseModel):
    """A paragraph inside a table cell."""

    text: str = Field(description="Paragraph text (optional; typically the concatenation of run texts)", default="")
    pStyle: str = Field(description='Paragraph style reference ID, e.g. "pS_1"', default="")
    runs: list[Run] = Field(
        description="Array of runs. A cell paragraph can contain multiple runs with different formatting.",
        default_factory=list,
    )


class Cell(BaseModel):
    """Table cell.

    Two modes are supported:
    1. Simple mode: use text + cStyle (single-paragraph plain text; font via rStyle)
    2. Multi-paragraph mode: use paragraphs + cStyle (multiple styled paragraphs inside one cell)
    Multi-paragraph mode is preferred for precise style preservation.
    """

    text: str = Field(
        description="Cell text (required in simple mode; may be empty in multi-paragraph mode)", default=""
    )
    paragraphs: list[CellParagraph] | None = Field(
        default=None,
        description="Array of paragraphs inside the cell (multi-paragraph mode)."
        " Each paragraph has independent pStyle and runs."
        " If this field is provided, text is ignored.",
    )
    rStyle: str | None = Field(
        default=None,
        description='Cell-level character style reference ID for simple mode, e.g. "rS_1".'
        " In multi-paragraph mode, each run controls style via its own rStyle; this field can be omitted.",
    )
    cStyle: str = Field(description='Cell style reference ID, e.g. "cS_1", mapped to document.styles["cS_1"]')


class Table(BaseModel):
    """Table schema with rows, columns, cells, style, and optional width/height controls."""

    rows: int = Field(description="Number of rows")
    columns: int = Field(description="Number of columns")
    cells: list[list[Cell]] = Field(description="2D cell array, indexed as cells[row][col]")
    tStyle: str = Field(description='Table style reference ID, e.g. "tS_1", mapped to document.styles["tS_1"]')
    columnWidths: list[float] | None = Field(
        default=None,
        description="Column widths in points; length must equal columns."
        " If omitted, frontend auto-distributes width. Example: [120, 280].",
    )
    rowHeights: list[list[int | float]] | None = Field(
        default=None,
        description="Row heights; length must equal rows. Each item is [height, heightRule], where"
        " height is in points and heightRule: 0=auto, 1=at least, 2=exact."
        " If omitted, height is content-driven. Example: [[40, 1], [40, 1]].",
    )


class Image(BaseModel):
    """Image object for document generation."""

    type: Literal["inline", "floating"] = Field(
        default="inline", description="Image layout type: inline or floating"
    )
    paraIndex: int | None = Field(
        default=None,
        description="Optional image anchor paragraph index."
        " For generated content, use local 0-based index matching placeholder paragraph.",
    )
    tempPath: str | None = Field(
        default=None,
        description="Local temp file path exported or downloaded by frontend, preferred for insertion.",
    )
    sourcePath: str | None = Field(
        default=None,
        description="Local source file path fallback for insertion.",
    )
    url: str | None = Field(
        default=None,
        description="Remote image URL. Frontend may download it and convert to tempPath before insertion.",
    )
    width: float | None = Field(default=None, description="Image width in points")
    height: float | None = Field(default=None, description="Image height in points")
    left: float | None = Field(default=None, description="Floating image left position")
    top: float | None = Field(default=None, description="Floating image top position")
    wrapType: str | None = Field(
        default=None,
        description="Floating wrap type: inline/topBottom/square/none/tight/through/behindText/inFrontOfText",
    )
    altText: str | None = Field(default=None, description="Alternative text")
    placeholder: str | None = Field(default="[图片]", description="Placeholder marker")


class DocumentOutput(BaseModel):
    """Document output schema. paragraphs and tables are independent top-level fields."""

    paragraphs: list[Paragraph] = Field(description="Paragraph array; every item must be a Paragraph object")
    tables: list[Table] = Field(default_factory=list, description="Table array; every item must be a Table object")
    images: list[Image] = Field(default_factory=list, description="Image array for insertion into document")
    styles: dict[str, list] = Field(
        description="Style dictionary (required). Key is style ID (e.g. pS_1, rS_1, cS_1, tS_1); value is style array."
        " Must include all styles referenced by pStyle/rStyle/cStyle/tStyle.\n"
        "pStyle format: [alignment, lineSpacing, leftIndent, rightIndent, firstLineIndent, beforeSpacing, afterSpacing, styleName, lineSpacingRule]."
        " alignment: left/center/right/justify. lineSpacing and indents are points.\n"
        "rStyle format: [fontName, fontSize, bold, italic, underline, underlineColor, color, highlight, strikethrough, superscript, subscript]."
        " colors use #RRGGBB.\n"
        "cStyle format: [rowSpan, colSpan, alignment, verticalAlignment], where verticalAlignment: 0=top, 1=center, 2=bottom.\n"
        "tStyle format: [tableAlignment], where tableAlignment: 0=left, 1=center, 2=right."
    )
    insertParaIndex: int = Field(
        default=-1,
        description="Insertion index (0-based). Frontend inserts content before this paragraph."
        " For selected-range edits, use startParaIndex."
        " For new content without a fixed position, use -1 (end) or 0 (beginning).",
    )

    @model_validator(mode="before")
    @classmethod
    def filter_invalid_paragraphs(cls, data):
        """Filter invalid items from paragraphs."""
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
        """Validate that all style references exist in styles dictionary."""
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
            raise ValueError(f"Missing style definitions in styles: {refs}")
        return self

    @model_validator(mode="after")
    def validate_style_value_shapes(self):
        """Validate style values are primitive arrays with expected minimum lengths."""
        primitive_types = (str, int, float, bool)

        for style_id, style_value in self.styles.items():
            if not isinstance(style_value, list):
                raise ValueError(f"styles[{style_id}] must be an array, got {type(style_value).__name__}")

            for idx, item in enumerate(style_value):
                if not isinstance(item, primitive_types):
                    raise ValueError(
                        f"styles[{style_id}][{idx}] must be a primitive (str/int/float/bool), got {type(item).__name__}"
                    )

            if style_id.startswith("pS_") and len(style_value) < 9:
                raise ValueError(f"styles[{style_id}] must contain at least 9 items for paragraph style")
            if style_id.startswith("rS_") and len(style_value) < 11:
                raise ValueError(f"styles[{style_id}] must contain at least 11 items for run style")
            if style_id.startswith("cS_") and len(style_value) < 4:
                raise ValueError(f"styles[{style_id}] must contain at least 4 items for cell style")
            if style_id.startswith("tS_") and len(style_value) < 1:
                raise ValueError(f"styles[{style_id}] must contain at least 1 item for table style")

        return self


class RangeFilter(BaseModel):
    """Numeric range filter, used by fields such as fontSize and lineSpacing."""

    gt: float | None = Field(default=None, description="Greater than")
    lt: float | None = Field(default=None, description="Less than")
    gte: float | None = Field(default=None, description="Greater than or equal to")
    lte: float | None = Field(default=None, description="Less than or equal to")


class QueryFilter(BaseModel):
    """Query filters. All provided fields are combined with AND semantics."""

    # 文本匹配（统一使用正则）
    regex: str | None = Field(
        default=None,
        description="Regex for text matching (run-level matches run.text; paragraph-level matches concatenated paragraph text)",
    )
    regexFlags: str | None = Field(
        default="i",
        description="Regex flags, e.g. i (ignore case), m (multiline), s (dotall). Example: 'im'",
    )

    # Run 级别样式（type=run 时直接匹配；type=paragraph 时检查段落中是否存在匹配的 run）
    fontName: str | None = Field(
        default=None, description="Font name, exact match, e.g. 'SimSun', 'KaiTi', 'Times New Roman'"
    )
    fontSize: float | RangeFilter | None = Field(
        default=None,
        description="Font size. Exact value (e.g. 14) or range (e.g. {gt: 14}, {gte: 14, lte: 18})",
    )
    bold: bool | None = Field(default=None, description="Bold")
    italic: bool | None = Field(default=None, description="Italic")
    underline: int | None = Field(
        default=None, description="Underline: 0=none, 1=single, 3=double, 4=dashed, 6=thick, 11=wave"
    )
    color: str | None = Field(default=None, description="Text color in #RRGGBB format, e.g. '#FF0000'")
    highlight: int | None = Field(
        default=None,
        description="Highlight color index: 0=none, 1=black, 2=blue, 3=cyan-green, 4=bright green, 5=pink, 6=red, 7=yellow",
    )
    strikethrough: bool | None = Field(default=None, description="Strikethrough")
    superscript: bool | None = Field(default=None, description="Superscript")
    subscript: bool | None = Field(default=None, description="Subscript")

    # Paragraph 级别样式（仅 type=paragraph 时有效）
    alignment: str | None = Field(default=None, description="Paragraph alignment: left/center/right/justify")
    styleName: str | None = Field(
        default=None,
        description="Paragraph style name (contains match), e.g. 'Heading' can match 'Heading 1' and 'Heading 2'",
    )
    lineSpacing: float | RangeFilter | None = Field(
        default=None,
        description="Line spacing in points. Single=12, 1.5x=18, double=24. Exact value or range supported.",
    )


class DocumentQuery(BaseModel):
    """Document query DSL."""

    type: Literal["run", "paragraph"] = Field(
        default="run",
        description="Search granularity: run (text run level) or paragraph (paragraph level)",
    )
    filters: QueryFilter = Field(description="Filter set; provided fields are combined with AND semantics")

import unittest

from pydantic import ValidationError

from app.services.tools.schemas import CellParagraph, DocumentOutput, Paragraph


class CellParagraphSchemaTests(unittest.TestCase):
    def test_compact_rstyle_is_preserved(self):
        paragraph = CellParagraph(text="静态计算图", pStyle="pS_5", rStyle="rS_9")
        self.assertEqual(
            paragraph.model_dump(),
            {"text": "静态计算图", "pStyle": "pS_5", "rStyle": "rS_9", "runs": []},
        )

    def test_cell_paragraph_requires_non_empty_pstyle(self):
        with self.assertRaises(ValidationError):
            CellParagraph(text="静态计算图", pStyle="")


class ParagraphSchemaTests(unittest.TestCase):
    def test_blank_paragraph_keeps_defined_pstyle(self):
        paragraph = Paragraph(pStyle="pS_1", runs=[])
        self.assertEqual(paragraph.model_dump()["pStyle"], "pS_1")
        self.assertEqual(paragraph.model_dump()["runs"], [])

    def test_blank_paragraph_rejects_empty_pstyle(self):
        with self.assertRaises(ValidationError):
            Paragraph(pStyle="", runs=[])

    def test_blank_paragraph_rejects_missing_pstyle(self):
        with self.assertRaises(ValidationError):
            Paragraph(runs=[])

    def test_document_accepts_blank_paragraph_with_defined_pstyle(self):
        document = DocumentOutput.model_validate(
            {
                "paragraphs": [{"pStyle": "pS_blank", "runs": []}],
                "styles": {"pS_blank": ["left", 0, 0, 0, 0, 0, 0, "正文", 1]},
            }
        )
        self.assertEqual(document.paragraphs[0].pStyle, "pS_blank")

    def test_document_rejects_blank_paragraph_with_undefined_pstyle(self):
        with self.assertRaises(ValidationError):
            DocumentOutput.model_validate(
                {
                    "paragraphs": [{"pStyle": "pS_missing", "runs": []}],
                    "styles": {},
                }
            )


if __name__ == "__main__":
    unittest.main()

import unittest

from app.services.tools.schemas import CellParagraph


class CellParagraphSchemaTests(unittest.TestCase):
    def test_compact_rstyle_is_preserved(self):
        paragraph = CellParagraph(text="静态计算图", rStyle="rS_9")
        self.assertEqual(
            paragraph.model_dump(),
            {"text": "静态计算图", "pStyle": "", "rStyle": "rS_9", "runs": []},
        )


if __name__ == "__main__":
    unittest.main()

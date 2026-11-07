"""PDF text extraction loaded only by the plugin's Python process."""


class Plugin:
    name = "PDF"
    description = "Extract text from PDF documents for language models."
    capabilities = ("pdf",)

    @staticmethod
    def check() -> None:
        import pymupdf

        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((72, 72), "WordAgent PDF plugin ready")
            if "WordAgent PDF plugin ready" not in page.get_text():
                raise RuntimeError("PDF text extraction self-check failed")

    @staticmethod
    def run(capability: str, payload: dict) -> dict:
        if capability != "pdf":
            raise ValueError(f"Unsupported capability: {capability}")

        import pymupdf

        with pymupdf.open(payload["path"]) as document:
            return {"text": "\n".join(page.get_text() for page in document).strip()}

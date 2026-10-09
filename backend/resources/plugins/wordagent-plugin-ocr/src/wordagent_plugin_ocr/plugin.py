"""RapidOCR implementation loaded only by the plugin's Python process."""


class Plugin:
    name = "OCR"
    description = "Recognize text in image files for text-only language models."
    capabilities = ("ocr",)

    @staticmethod
    def check() -> None:
        from rapidocr_onnxruntime import RapidOCR

        RapidOCR()

    @staticmethod
    def run(capability: str, payload: dict) -> dict:
        if capability != "ocr":
            raise ValueError(f"Unsupported capability: {capability}")
        return {"text": Plugin.recognize_image(payload["path"])}

    @staticmethod
    def recognize_image(path: str) -> str:
        import numpy as np
        from PIL import Image, ImageOps
        from rapidocr_onnxruntime import RapidOCR

        with Image.open(path) as image:
            pixels = np.ascontiguousarray(ImageOps.exif_transpose(image).convert("L"))
        result, _elapsed = RapidOCR()(pixels)
        return "\n".join(
            item[1].strip()
            for item in (result or [])
            if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[1], str) and item[1].strip()
        )

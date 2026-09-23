# wordagent-plugin-ocr

Optional WordAgent OCR plugin. Its wheel includes RapidOCR, OpenCV, ONNX Runtime,
and the model files. Install it from WPS Settings > Plugins. The backend runs it
in a separate uv environment and can remove that environment at any time.

Custom plugins use a Python package named `wordagent-plugin-*` and declare a
`wordagent.plugins` entry point. The loaded class provides `name`,
`description`, `capabilities`, and `run(capability: str, payload: dict) -> dict`.
For OCR, return `{"text": "..."}` for the `ocr` capability with a `path`
in the payload. An optional `check()`
method can validate downloaded assets during installation. Plugin code runs in
its own Python subprocess, outside the backend process.

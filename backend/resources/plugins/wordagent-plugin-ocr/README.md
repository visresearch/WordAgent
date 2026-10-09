# wordagent-plugin-ocr

Optional WordAgent OCR plugin. Installation downloads RapidOCR, OpenCV, ONNX Runtime,
and the model files into the plugin environment. Install it from WPS Settings > Plugins. The backend runs it
in a separate uv environment and can remove that environment at any time.

Install custom plugins with a GitHub repository or folder URL pointing to a Python
project containing `pyproject.toml` and `.py` source files. Declare a
`wordagent.plugins` entry point in `[project.entry-points."wordagent.plugins"]`.
The loaded class (constructed without arguments) or object provides `name`,
`description`, `capabilities`, and `run(capability: str, payload: dict) -> dict`.
For OCR, return `{"text": "..."}` for the `ocr` capability with a `path`
in the payload. The optional `api_version` defaults to `1`; only version `1` is
supported. An optional synchronous `check()` method can validate downloaded assets
during installation; returning `False` or raising an exception fails installation.
Python 3.11 compatibility, source syntax and the plugin interface are checked before
the plugin is enabled. Failed installations are cleaned up. Plugin code runs in
its own Python subprocess, outside the backend process.

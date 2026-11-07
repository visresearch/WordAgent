# wordagent-plugin-pdf

Optional WordAgent PDF text extraction plugin, powered by PyMuPDF.
Install it from Settings > Plugins in the WPS or Microsoft Word add-in.
PyMuPDF is downloaded only when the user installs this plugin and runs in the
plugin's separate Python environment. Removing the plugin removes that environment.

Once installed, the agent's `read_file` tool extracts text from PDF files under
`wence_data/project/`, including uploaded PDF attachments. Without the plugin,
reading a PDF returns an installation prompt. Other file types remain available.
Scanned PDFs without an embedded text layer do not produce readable text;
this plugin does not perform OCR.

The plugin uses the `wordagent.plugins` entry point and declares the `pdf`
capability. Calling `run("pdf", {"path": "/absolute/path/to/document.pdf"})`
returns `{"text": "..."}` with page text joined in document order.
Installation runs a self-check that creates a page and verifies text extraction.

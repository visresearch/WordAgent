Create and open a new blank `.docx` document in the active Word or WPS application.

## Parameters

This tool takes no parameters.

## Use

- Use this when the user explicitly asks to create a new blank Word document.
- The current active document is not modified.
- The frontend creates the document through the native Word/WPS API and opens it immediately.
- After creation, use `generate_document` with `insertParaID: 0` for the first write into the new empty document.

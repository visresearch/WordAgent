Render a document's page layout as PNG images at a fixed 120 DPI. Use this read-only tool to inspect pagination, headers, footers, or the placement of text, tables, and figures.

- `page_start` and `page_end` are inclusive physical page numbers starting at 1. Use the same number for both to view one page.
- `mode="single"` saves one PNG per page. `mode="combine"` stacks the pages vertically in page order into one PNG.
- `docId` selects the document. Omit it or pass 0 for the current document at render time. The result identifies the document actually rendered.
- The result lists the saved paths under `wence_data/project/temp/view_document/`. Models with vision receive the rendered images with their paths.

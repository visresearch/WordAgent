Search document text/styles with `query: DocumentQuery` and required `docId`.

Returns matches with `paragraphIndex` and `paragraphId`. Text matching uses `filters.regex`, with optional `regexFlags`; choose `type="paragraph"` to match whole paragraph text or `type="run"` for individual runs. Supplied filters combine with AND.

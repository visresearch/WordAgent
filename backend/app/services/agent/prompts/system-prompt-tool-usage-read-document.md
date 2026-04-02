Use read_document to read required paragraph ranges.
If reading large scope, split into chunks of at most 50 paragraphs.
Avoid read_document(0, -1) in a single call.

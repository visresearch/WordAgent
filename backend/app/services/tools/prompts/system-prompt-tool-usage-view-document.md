## view_document Usage Policy

- Use `view_document` when the task depends on how pages look or where page breaks fall. Use `read_document` for exact text, structured content, and paragraph IDs.
- Pass physical page positions, counting from 1 regardless of printed page labels. When comparing documents in WPS, pass the source and target IDs in separate tool calls, then check the document identities returned with the images. In Word, render from the add-in attached to each document.
- Use `single` for close inspection of text and layout. Use `combine` for an overview of consecutive pages, such as checking a table across a page break. If a long image lacks detail, render the relevant pages individually.
- Base visual findings on the images you receive. If the tool reports an error or the model receives only file paths, state that the page appearance could not be verified.

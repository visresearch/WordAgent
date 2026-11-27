## copy_document Usage Policy

- Use `copy_document` when an existing editable range should be carried into an open target. Read the source and target to resolve their paragraph IDs. Create a target first if the user needs a new document.
- Include both source endpoints. Use source and target IDs from their respective documents. Use `insertID=0` for insertion at the beginning, including in a nonempty target. Use a target paragraph outside a table, or the final paragraph of a complete table, for insertion after an anchor.
- Keep the target's page setup in mind when verifying layout. A range copy preserves native range content; paper size, margins, and headers/footers are determined by the target and any section boundaries included in the range.
- Check the returned target ID. Read or render the target to verify the result. If insertion is uncertain, check the target before attempting another insertion.

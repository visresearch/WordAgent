Replace one paragraph's content by `paraID` in `docId` (default `0`) under native Track Changes.

`runs` is the complete replacement content; `[]` clears text without deleting the paragraph. Do not include `\n` in run text. Optional `rStyle` references must come from the target document's read result.

In WPS Writer, use a separate `{"formula":"x^{2}"}` run for each editable equation. Preserve any existing formula runs the user wants to keep. A `formulaError` in a read result means the original equation could not be converted. Resolve the formula before replacing its paragraph.

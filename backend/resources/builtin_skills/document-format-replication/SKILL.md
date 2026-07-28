---
name: document-format-replication
description: Replicate formatting from a reference Word document in a target while keeping the new content independent. Trigger for requests to imitate, copy, transcribe, reproduce, match, clone, or strictly follow a document's template, layout, style, or formatting—including Chinese requests containing 模仿、抄写、照抄、仿照、复刻、克隆、模板、模版、按照格式、参考排版、照着样式生成、保持原文格式、严格按模板生成, or “照着这个论文/报告/合同生成”. Use especially for theses, dissertations, academic papers, reports, proposals, contracts, and institutional templates.
---

# Document Format Replication

Use a clone-first workflow. Treat the exact DocxJSON returned by `read_document(mode="full")` as the source of truth. Copy existing paragraph, run, table, image, and style structures directly; do not recreate formatting from a verbal summary when an exact exemplar is available.

## Trigger and non-negotiable fidelity

Load this skill before planning or editing whenever the request asks to imitate, copy, transcribe, reproduce, or strictly follow another document's template, layout, style, or formatting. This includes indirect wording such as “参考这个模板/论文/报告”, “按原文排版”, “照着样式生成”, “保持格式一致”, and “把这份内容套到那个文档里”. Treat the reference document as a structural specification, not merely a visual suggestion.

For any strict or template-based replication, preserve every layout-bearing element that appears in the reference. In particular:

- Keep every paragraph in order, including intentional blank paragraphs (空白段落) whose `runs` are empty. Every paragraph must retain a non-empty `pStyle` defined in `styles`; a blank paragraph is `{ "pStyle": "<defined pS_*>", "runs": [] }`, never `{ "pStyle": "", "runs": [] }`. Never delete, merge, or “clean up” blank paragraphs because they appear to contain no text.
- Reproduce page breaks (分页符) and section breaks (分节符) at their original positions. A next-page break, line break, and next-page section break have different semantics; do not represent them as ordinary text or substitute `\\n`. When the API exposes them, use `insert_break` with the exact `breakType` (`wdLineBreak`, `wdPageBreak`, or `wdSectionBreakNextPage`) and the preceding paragraph's `paraID`.
- When no reference break is available, major blocks such as the cover-following content, Chinese/English abstracts, table of contents, references, appendices, and top-level chapters should normally begin on fresh pages. Use `wdPageBreak`, or `wdSectionBreakNextPage` when section settings change; never approximate a page break with extra blank paragraphs.
- Preserve cover images, tables, fixed labels, and spacing, as well as headers, footers, page numbers, margins, paper settings, orientation, and section boundaries. Preserve table merges, row heights, column widths, image dimensions, positions, and wrapping.
- Preserve run boundaries and mixed-language font assignments (body English must remain Times New Roman where required); do not flatten runs into one plain-text run.

Read the reference with `read_document(mode="full")` before generating. Use its paragraph order, break anchors, complete JSON, and (when available) `pageStart`/`pageEnd` only as evidence for validating pagination. Lightweight reads do not provide page numbers and must not be used as the sole basis for strict replication. After generation, read the result in full mode and verify that blank paragraphs, break locations, and section/page-level structures remain present. If a property cannot be represented by the available tool, report it explicitly and perform a visual check in Word or WPS.

## Establish source, target, and fidelity

Identify these before editing:

- **Format reference**: the template whose structure, fixed text, and formatting must be cloned.
- **Content source**: the report, draft, facts, or outline that supplies the new subject matter.
- **Target**: the document that may be modified.
- **Fidelity requirement**: exact template replication or only a selected subset such as headings, tables, or citations.

Use document metadata and the user's wording to resolve identities. Ask one concise question only when the reference or target is genuinely ambiguous. Never modify the reference document.

Do not confuse the format reference with the content source. Copy fixed template material from the format reference verbatim, including institution names, cover labels, declarations, required headings, field labels, punctuation, intentional blank paragraphs, and table shells. Replace only fields that are meant to vary, such as thesis title, author, student number, major, supervisor, date, and body text.

For strict replication, prefer a copy of the format reference as the target. This preserves page size, margins, sections, headers, footers, page numbering, and other page-level settings. A blank target can reproduce the structures supported by `generate_document`, but page-level settings still require a template copy or manual verification.

## 1. Analyze the reference

Resolve document names to exact `docId` values from document metadata. Call `read_document` with `mode="full"` on the format reference. Read the complete cover block first, then other components in ordered chunks of no more than 50 paragraphs. Never use lightweight mode for a block that will be cloned.

For every block, retain the returned objects as direct exemplars:

- preserve paragraph order, blank paragraphs, `pStyle`, and run boundaries
- preserve each run's `rStyle`, image fields, and text unless the text is an approved variable
- preserve table dimensions, cells, merges, column widths, row heights, and table/cell styles
- preserve the exact style-array values referenced by the block
- omit source-only location fields such as `paraID` when constructing generated paragraphs, but do not normalize or redesign the formatting

Use a format specification only as an index to exact exemplars. Record:

- document order and required front/back matter
- paragraph roles and their exact `pStyle` arrays
- run roles and their exact `rStyle` arrays
- fonts, sizes, emphasis, colors, alignment, indentation, spacing, and line-spacing rules
- heading hierarchy and numbering patterns
- table alignment, column widths, row heights, cell alignment, merged cells, and cell text styles
- figure dimensions, wrapping, placement patterns, and caption styles
- blank paragraphs, page-break-like structural anchors, and repeated layout patterns
- observable page, section, header, footer, and numbering requirements that must be preserved or manually checked

Do not average, simplify, or “clean up” differing styles. Choose the exemplar that corresponds to the same semantic role. If the correct role is ambiguous, inspect more of the template or ask instead of inventing a standard.

## 2. Clone exact blocks

Map each target component to an exact reference block before writing. A typical thesis map includes:

| Target role | Reference evidence |
|---|---|
| Cover title and identity fields | Corresponding cover placeholders |
| Chinese and English abstracts | Reference abstract headings and body paragraphs |
| Keywords | Reference keyword label and separator pattern |
| Level 1-3 headings | Matching heading levels and numbering examples |
| Body paragraphs | Repeated normal-text paragraphs |
| Tables and table titles | Representative academic tables |
| Figures and captions | Representative figures and captions |
| Citations and references | Reference citation and bibliography entries |
| Appendices and acknowledgements | Corresponding terminal sections |

Clone each mapped block mechanically:

1. Copy its ordered `paragraphs` stream, including every `{ "tables": [...] }` block, plus all referenced entries from `styles`. Keep every table block at its exact source position; never emit a parallel top-level `tables` array.
2. For fixed template content, keep every `run.text` value unchanged.
3. For a variable field, change only the intended `run.text`; preserve the paragraph object, run count, run order, and all style references.
4. For new prose, duplicate the matching body or heading exemplar for every new paragraph and replace only its text. Preserve distinct runs when the exemplar uses mixed formatting.
5. Include every referenced style ID with the exact source array. Never substitute WordAgent default styles when the template provides an exemplar.

The result should be explainable as “the same JSON structure with approved text substitutions,” not as a newly designed document that merely looks similar.

## 3. Apply the format

Read the target with `mode="full"` before changing it. Apply and validate the cover before drafting the body; do not generate the entire thesis first and inspect the cover afterward.

### Cover-first replication

The cover is a literal-cloning task:

1. Read the complete cover range from the format reference in full mode.
2. Copy every paragraph, blank line, run, image, table, and referenced style in the same order.
3. Keep fixed labels and institutional wording verbatim.
4. Replace only supplied variable fields. If a required field value is missing, keep the template placeholder or ask the user; never delete the field or redesign the cover.
5. Generate the cover as its own block.
6. Re-read the generated cover in full mode and compare its structures and style arrays with the source cover. Repair any mismatch before continuing.

### Template-copy target

Preserve structural content that carries layout, including section boundaries, headers, footers, page-numbering setup, table shells, and intentional blank paragraphs. Replace only identified placeholders or content ranges:

1. Locate the exact target paragraphs with `search_document` and confirm them with `read_document`.
2. Call `delete_document` once for the confirmed paragraph IDs.
3. Insert replacement content with `generate_document` using the `replacementInsertParaID` returned by `delete_document`; never reuse a just-deleted paraID that remains visible as a native revision.
4. Use the cloned reference block as the generated payload and replace only approved text fields.

Check the immediate `delete_document` result before generating replacement content. On partial failure, re-read and retry only IDs that still exist. Do not rebuild an intact template from scratch when targeted replacement preserves more formatting.

### Blank or independent target

Use `insertParaID=0` whenever content must begin at the document start, including in a non-empty document. Use a real nonzero paragraph ID to insert after that paragraph. Generate in stable component order: cover/front matter, main body, then references/back matter. Inside each payload, keep paragraph objects and `{ "tables": [...] }` blocks in exact visual order, including surrounding blank paragraphs. Include complete cloned style definitions and preserve style-reference closure for paragraphs, runs, tables, cells, and cell paragraphs.

Use the content source only for the new thesis subject matter. Fixed text from the format reference is allowed and required; unrelated prose from the format reference must not leak into the new body.

## 4. Validate the result

After each major block, re-read the target with `mode="full"`. Compare returned structures directly with the corresponding reference block, not against visual intuition or a prose style summary.

Check at minimum:

- required sections and their order
- heading levels, numbering, alignment, and spacing
- body font, size, indentation, line spacing, and paragraph spacing
- cover paragraph count and order, including blank paragraphs
- cover fixed text, variable substitutions, run segmentation, and exact style-array equality
- title page and abstract formatting
- table dimensions, alignment, merges, and cell styles
- image sizing, wrapping, and caption formatting
- citation, bibliography, appendix, and acknowledgement formatting
- no accidental reference text, missing target text, duplicate content, or extra blank paragraphs
- page-level settings retained by the template copy, or clearly identified for manual inspection

Fix mismatches through the same locate-read-delete-generate workflow. Finish with a concise validation report containing: replicated rules, deviations or unsupported properties, and items that still require visual inspection in Word or WPS.

## Example: graduation thesis template

For a request such as “Analyze my university graduation thesis template and generate another thesis that follows it strictly”:

1. Treat the university template as the reference and a duplicate of that template as the target.
2. Read and clone the complete cover first. Keep the university name, document labels, field labels, punctuation, blank lines, and styles verbatim; replace only supplied thesis metadata.
3. Re-read the target cover and require exact structural and style equality before proceeding.
4. Read exact exemplars for declarations, Chinese and English abstracts, contents, each heading level, body paragraphs, tables, figures, bibliography, appendices, and acknowledgements.
5. Use the research report as the content source, but construct every new paragraph by cloning the appropriate thesis-template exemplar and replacing only text.
6. Re-read each generated component and compare it with its template exemplar.
7. Report any feature that cannot be verified structurally, such as final pagination, automatic table-of-contents refresh, widow/orphan behavior, or printer-dependent line wrapping.

Never claim strict fidelity before completing the validation pass.

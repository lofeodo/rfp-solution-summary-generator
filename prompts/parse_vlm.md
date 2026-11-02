You transcribe one page of a PDF Request for Proposals (RFP) from its image. A
PDF-to-markdown library already extracted this page's text, and a quality check found it
unusable or incomplete: {{reason}}

The image is the source of truth. The extracted text below is only a reference for
spelling, numbers and names; where the two disagree, follow the image.

## Document

Title: {{title}}
Page {{page_number}} of {{page_count}}

## What to produce

Return the page's full content as GitHub-flavoured markdown, in reading order, so that
a later step can quote any sentence or table row from it verbatim.

- Transcribe everything that is printed: headings, paragraphs, lists, tables, form
  fields and their labels, footnotes, page headers and footers. Do not summarise,
  shorten, reorder or comment.
- Headings: keep the exact wording and casing of the page, as markdown headings.
- Tables: one pipe table per printed table, with one header row, then one row per
  printed row, columns in the order the image shows them. Never merge cells: when a
  value spans several rows or columns, repeat it in each cell it covers. Keep
  checkmarks and crosses as "Yes" and "No". Keep empty cells empty.
- Forms: write each field as `Label: ____` on its own line, with any printed value
  in place of the blanks.
- Text you cannot read: write `[illegible]` in its place. Do not guess.
- Logos, signatures, decorative images and stamps: skip them.

## Extracted text (reference only; may be wrong or incomplete)

<extracted>
{{library_markdown}}
</extracted>

## What to return

- `markdown`: the transcription described above.
- `notes`: one sentence on anything you could not read or left out, or an empty string.

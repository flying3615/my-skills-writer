# WeRead Text Downloader Design

**Problem**

The user wants a new skill and tool inspired by `bunnyburrow-weread`, but narrowed to a simpler outcome: export WeRead book content as chapter-based plain text for AI reading. The user does not want the intermediate `rdata.zip` artifacts or final `epub` generation. The new tool should be CLI-only.

**Approaches**

1. Wrap the original project as-is and stop after download.
   This would preserve unnecessary raw-file handling and does not match the user's preferred output format.

2. Rebuild the minimum browser automation path and write plain-text chapters directly.
   Recommended. The original repository already exposes the right data through the web reader state: book metadata, chapter list, and chapter HTML. This is enough to create a simpler text-first exporter.

3. Download raw data and add a second conversion layer from the original archive format to text.
   This adds extra IO, extra failure points, and does not improve the final result.

**Recommended Design**

Use approach 2.

## Scope

The new tool should:

- open WeRead in a browser
- log in through the web reader
- locate a purchased book by title
- iterate chapters
- extract chapter HTML from the page state
- convert HTML to plain text
- write chapter-based output plus metadata

The new tool should not keep intermediate raw archives.

## Output Contract

Default output:

```text
out/
  <book-slug>/
    metadata.json
    toc.json
    chapters/
      001-<chapter-slug>.txt
      002-<chapter-slug>.txt
```

The output should be optimized for downstream AI reading and further summarization.

## CLI Shape

The tool should expose one primary command:

```bash
python3 weread-text-downloader/scripts/weread_text.py download "Book Name"
```

Optional flags:

- `--out-dir`
- `--headless`
- `--delay`
- `--verbose`

## Implementation Notes

The original upstream code uses `pyppeteer` and the WeRead page's Vue store. Reusing that browser strategy is the simplest path:

- get the bookshelf
- open the selected book
- read `bookInfo` and `chapterInfos`
- switch chapters through the reader store
- read `chapterContentHtml`

The new implementation should convert HTML to readable plain text rather than writing archived HTML.

## Validation

Validation should focus on:

- HTML-to-text conversion
- stable output file names
- metadata and chapter list output
- CLI argument handling

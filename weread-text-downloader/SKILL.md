---
name: weread-text-downloader
description: Use when downloading purchased WeRead books into chapter-based plain text for AI reading, using a CLI workflow that logs into the WeRead web reader and writes metadata, table of contents, and chapter txt files.
---

# WeRead Text Downloader

Use this skill to download a purchased WeRead book and export it as chapter-based plain text.

Default behavior:

- CLI-only workflow
- final output is plain text, not `epub`
- chapter-based output for downstream AI reading
- no intermediate `rdata.zip` is kept

## Dependencies

Required:

- `python3`
- `pyppeteer`

Optional for `--headless` QR display:

- `pillow`
- `pyzbar`
- `qrcode`

Install the minimum dependency set with:

```bash
pip install pyppeteer
```

Install the headless extras only if needed:

```bash
pip install pillow pyzbar qrcode
```

## Command

```bash
python3 weread-text-downloader/scripts/weread_text.py download "Book Name"
```

Optional flags:

- `--out-dir ./out`
- `--headless`
- `--delay 2`
- `--verbose`

Example:

```bash
python3 weread-text-downloader/scripts/weread_text.py download "怦然心动" \
  --out-dir ./out \
  --verbose
```

## Output

The script writes:

```text
out/
  <book-slug>/
    metadata.json
    toc.json
    chapters/
      001-<chapter-slug>.txt
      002-<chapter-slug>.txt
```

Use `metadata.json` and `toc.json` for structure-aware downstream processing. Use `chapters/*.txt` as the primary AI reading input.

## Workflow

1. Start the CLI command.
2. Log in to WeRead through the web reader.
3. Open the target book from the bookshelf.
4. Iterate chapters through the reader state.
5. Convert chapter HTML into plain text.
6. Write the output files.

## Notes

- The book title match is substring-based against the bookshelf text.
- This tool assumes the requested book is already available in the logged-in WeRead account.
- When `--headless` is used, the QR code is printed in the terminal only if the optional QR dependencies are installed.

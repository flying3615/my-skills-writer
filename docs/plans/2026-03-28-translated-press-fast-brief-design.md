# Translated Press Fast Path And Daily Brief Design

**Problem**

The translated-PDF path already has usable text-layer extraction and local article ranking, but it still pays the old OCR/render cost inside `process_paper()`. That makes automation slower without improving the translated summary path. The current outputs also favor `summary.json`, which works, but is heavier than needed for downstream daily automation.

**Approaches**

1. Keep the current mixed path and only add a new output file.
   This is lowest risk, but it leaves the main performance problem untouched.

2. Add a translated fast path and a flat automation brief.
   This skips render/OCR/review work whenever text-layer extraction is available, while preserving existing output contracts and adding a new compact `daily_brief.json`. This is the recommended approach because it directly targets the translated workflow the user wants to automate.

3. Remove the OCR path entirely for translated runs.
   This would be simpler, but it would prematurely cut off fallback behavior for PDFs that still need OCR. It is too aggressive for the current script.

**Recommended Design**

Use approach 2.

- When `text_layer_status == "available"`, build `page_index` from text-layer artifacts and bbox metadata only.
- Skip page rendering, OCR, opinion/topic scan, and second-stage review for that paper.
- Keep the old OCR path intact for papers without usable text layers.
- Continue writing `results.json`, `articles.json`, `summary.json`, and `summary.md`.
- Add `daily_brief.json` as a flatter automation payload that contains the run date plus a compact per-paper list of selected articles.

**Data Flow**

1. Download PDF.
2. Extract text layer and optional bbox blocks.
3. If text layer is available, create page records from text artifacts and stop there for scanning.
4. Build article candidates from those page records.
5. Rank summary articles as before.
6. Write legacy summary outputs plus `daily_brief.json`.

**Error Handling**

- Text-layer extraction failures still record `text_layer_status`, `text_layer_reason`, and fall back to the OCR path.
- `daily_brief.json` generation should be derived from already selected summary articles so it cannot diverge from `summary.json`.

**Testing**

- Verify translated papers with text layer available do not call `render_page()` or OCR helpers.
- Verify page records still include `text_path` and paper metadata in the fast path.
- Verify `daily_brief.json` is written with stable compact fields for automation consumption.

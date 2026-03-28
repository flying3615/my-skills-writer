# Delete Downloaded PDFs Design

**Problem**

The translated press pipeline keeps downloaded PDFs under `out/pdfs/`, but the user wants those files deleted after processing completes. The durable artifacts should be the extracted text and JSON outputs, not the downloaded PDF copy.

**Approaches**

1. Delete PDFs only on success.
   Safer for debugging, but does not match the requested behavior.

2. Delete PDFs after processing regardless of success or failure.
   Recommended because it matches the requested lifecycle exactly.

**Recommended Design**

Use approach 2.

- Treat `out/pdfs/<paper>.pdf` as a temporary working file.
- After `process_paper()` finishes, remove the downloaded copy in a `finally` block.
- Keep `url` in outputs, but set `local_pdf` to `null` because the file no longer exists.
- Do not delete `text/`, `articles.json`, `summary.json`, or `daily_brief.json`.

**Testing**

- Verify `process_paper()` deletes the downloaded PDF after a successful translated/text-layer run.
- Verify `paper.local_pdf` is `None` after cleanup.

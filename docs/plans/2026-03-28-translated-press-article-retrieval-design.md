# Translated Press Article Retrieval Design

**Problem**

The current translated-PDF pipeline can produce ranked summary outputs, but the user’s real workflow is two-stage:

1. Browse a compact list of important articles.
2. Ask the downstream AI to expand a specific article and return cleaned long-form content.

That means the system needs both a lightweight index for browsing and a stable full-text article store for later lookup.

**Approaches**

1. Keep the current outputs and let the downstream AI infer article identity from title text.
   This is low effort, but it is brittle because titles may be noisy or duplicated.

2. Add stable article identity plus a clean split between brief and full article payloads.
   `daily_brief.json` becomes the browse layer, `articles.json` becomes the retrieval layer, and every article gets a stable `article_id`. This is the recommended approach because it matches the intended human-AI interaction pattern.

3. Add a separate lookup CLI immediately.
   This can wait. The data contract should come first so both AI and future CLI helpers can reuse it.

**Recommended Design**

Use approach 2.

- Every article candidate gets a stable `article_id`.
- `articles.json` becomes the source of truth for complete article retrieval.
- `daily_brief.json` keeps only the selected important articles, but now also exposes `article_id`, `byline`, and `priority_score`.
- Article lookup should be possible by:
  - `article_id`
  - `page + title`

**Output Model**

`articles.json` entries should include at least:

- `article_id`
- `source_name`
- `paper_id`
- `page`
- `title`
- `title_normalized`
- `byline`
- `topic_tags`
- `priority_score`
- `body_text`
- `text_path`
- `block_kind`
- `block_index`
- `lookup_keys`

`daily_brief.json` entries should include at least:

- `article_id`
- `page`
- `title`
- `byline`
- `priority_score`
- `summary_text`
- `topic_tags`

**Identity Strategy**

`article_id` should be derived from stable article metadata, not from list position. A good shape is:

`<paper_id>:p<page>:<normalized-title-fragment>:b<block_index>`

This is readable, deterministic, and still stable across repeated runs of the same paper.

**Ranking Strategy**

Promote the existing summary ranking into a first-class `priority_score`.

- `daily_brief.json` sorts by `priority_score`
- `articles.json` stores `priority_score`
- downstream AI can use the score as a hint when deciding what to surface first

**Lookup Semantics**

Downstream AI should be able to:

- read `daily_brief.json`
- choose a specific article using `article_id`
- or resolve by `page + title`
- then fetch the full `body_text` from `articles.json`

**Testing**

- Verify every article candidate gets a stable `article_id`
- Verify `daily_brief.json` exposes `article_id` and `priority_score`
- Verify `articles.json` includes normalized lookup fields
- Verify repeated candidate generation over the same input produces the same `article_id`

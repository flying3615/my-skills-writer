# Article Title Normalization Design

**Problem**

The retrieval workflow now depends on `article_id`, `title_normalized`, and `lookup_keys`, but title normalization only collapses whitespace. That leaves avoidable mismatch risk when the same title appears with different fullwidth/halfwidth characters or different quote, colon, and dash variants.

**Approaches**

1. Keep normalization minimal and rely on looser downstream matching.
   Lowest effort, but keeps the retrieval contract fragile.

2. Add light canonicalization for punctuation and width variants.
   Recommended. Normalize the most common variants without aggressively stripping text.

3. Add fuzzy matching logic now.
   Stronger lookup behavior, but out of scope for this fix.

**Recommended Design**

Use approach 2.

- Keep `title` as the readable original title.
- Make `title_normalized` deterministic and slightly stricter.
- Normalize:
  - fullwidth to halfwidth via Unicode normalization
  - curly and CJK quotes to straight quotes
  - apostrophe variants to `'`
  - CJK/fullwidth colon, comma, semicolon, question/exclamation to ASCII
  - dash variants to `-`
  - ellipsis variants to `...`
- Continue collapsing whitespace at the end.

**Testing**

- Verify `normalize_article_title()` folds punctuation and width variants into one canonical title.
- Verify two otherwise identical article candidates with title punctuation/width variants receive the same `article_id`.

# Scite — tool reference

Vet mode uses exactly one tool: `mcp__claude_ai_Scite__search_literature`. The other Scite tools (evidence databases) require the `evidence:*:mcp` entitlement, which this license does not have — they return a hard error and are out of scope. See `usage_guide.md` for the reasoning behind these constraints.

## `search_literature`

Cross-field search over ~210M papers (title + abstract + full text). All parameters optional; calling with none browses the corpus.

### Parameters used by Vet

| Param | Purpose |
|---|---|
| `term` | Query string. Boolean (`AND`/`OR`/`NOT`), phrase (`"..."`), proximity (`"a b"~5`). |
| `dois` | Restrict to specific DOIs. Without `term` → metadata fetch. Preferred over `titles`. |
| `titles` | Restrict by title when no DOI is available. |
| `has_retraction` | `true` → only retracted papers. |
| `has_correction` | `true` → only papers with corrections. |
| `has_concern` | `true` → only papers with expressions of concern. |
| `has_erratum` | `true` → only papers with errata. |
| `has_tally` | `true` → only papers with ≥1 Smart Citation. |
| `supporting_from` / `supporting_to` | Bound the count of supporting Smart Citations. |
| `contrasting_from` / `contrasting_to` | Bound the count of contrasting Smart Citations. |
| `mentioning_from` / `mentioning_to` | Bound the count of mentioning Smart Citations. |
| `citing_publications_from` / `citing_publications_to` | Bound the traditional citation count. |
| `limit` | Default 10, max 1000. Keep small (10–50). |
| `offset` | Pagination offset. |

Other metadata facets exist (`author`, `affiliation`, `journal`, `publisher`, `topic`, `paper_type`, `year`, `date_from`/`date_to`) — usable but rarely needed for Vet.

### Response shape (this license)

```json
{ "results": [ { "title": "...", "doi": "...", "url": "https://resolver.ebsco.com/..." } ] }
```

Only these three fields per result. `tally`, `citations`, `fulltextExcerpts`, and `retraction_notices` are documented in the schema but **not returned** on this tier. A retraction shows only as a `RETRACTED` / `RETRACTED ARTICLE` prefix in `title`.

### Filter-probe idiom (how Vet reads notice status without the structured field)

Because `retraction_notices` is not returned, determine a paper's status by re-querying its DOI with the notice filter — the filter runs server-side, so:

- non-empty result → the flag is set for that paper
- empty result → it is not

Caveat (verified): under a notice filter, an empty result can carry the message *"not present in Scite's index"* even for a DOI Scite does index. It means "did not match the filter," not "absent" — confirm indexing with a plain `dois` fetch first.

See `usage_guide.md` for the full recipes.

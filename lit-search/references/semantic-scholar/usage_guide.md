# Semantic Scholar — Usage Guide

This page covers neuroscience-tuned defaults, recipe templates, and the gotchas that come up most often. For the full API surface (parameters, filter values, response shapes), see `tool_reference.md`. For the structured endpoint catalog, query `data/endpoints.db`.

## Table of contents

1. Default `fields_of_study` for neuroscience users
2. Default paper / author fields
3. When to deviate from defaults
4. Boolean-search recipe templates
5. Persistent gotchas
6. Known historical bug fixes
7. Notable feature additions
8. Following ongoing changes

---

## 1. Default `fields_of_study` for neuroscience users

The skill defaults to `Biology,Medicine,Psychology` because S2 has no top-level "Neuroscience" bucket. Neuro work splits across these three:

| Bucket | Subdomains it tends to capture |
|---|---|
| Biology | Systems / cellular / molecular / computational neuro, biophysics, genetics |
| Medicine | Clinical neuro, neurology, neuroimaging, psychiatry-as-medicine |
| Psychology | Cognitive psych, behavioral neuro, neuroeconomics, psychophysics |

Stats-heavy methods papers (e.g. inference, hierarchical models) often land under `Mathematics` or `Computer Science` — pass `--fields-of-study ""` (empty) for these to disable the filter, or set explicitly: `--fields-of-study "Mathematics,Computer Science"`.

---

## 2. Default paper / author fields

`s2_client.DEFAULT_PAPER_FIELDS`:

```
paperId,title,authors,year,venue,publicationVenue,publicationTypes,
publicationDate,citationCount,influentialCitationCount,referenceCount,
isOpenAccess,openAccessPdf,externalIds,fieldsOfStudy,s2FieldsOfStudy,
abstract,tldr
```

Trade-off: rich enough to triage papers without follow-up calls, omits heavy fields (`embedding`, `citations`, `references`) that would balloon response size.

`s2_client.LEAN_PAPER_FIELDS` (used by bulk operations):

```
paperId,title,authors,year,venue,citationCount,externalIds,openAccessPdf,tldr
```

Default author fields:

```
authorId,name,aliases,affiliations,homepage,paperCount,citationCount,hIndex,url
```

---

## 3. When to deviate from defaults

| Case | Suggested override |
|---|---|
| Sweeping >1000 results | `--fields paperId,title,year,citationCount,externalIds` |
| Need full-text PDF | add `openAccessPdf,isOpenAccess` |
| Building a citation graph | `--fields paperId,title,citations.paperId,references.paperId` |
| Computing embeddings | `--fields paperId,title,embedding.specter_v2` |
| Pure stats / methods paper | `--fields-of-study "Mathematics,Computer Science"` or empty |
| Clinical-only subset | `--fields-of-study "Medicine" --publication-types "ClinicalTrial,MetaAnalysis,Review"` |

---

## 4. Boolean-search recipe templates

### Topic survey, last 5 years, journal articles, ≥10 citations

```bash
scripts/.venv/bin/python scripts/semantic-scholar/examples/keyword_search.py "hippocampal replay" \
  --bulk --max 500 --year 2020- \
  --publication-types JournalArticle \
  --min-citation-count 10 \
  --sort citationCount:desc
```

### Methods-paper hunt (no field-of-study filter)

```bash
scripts/.venv/bin/python scripts/semantic-scholar/examples/keyword_search.py "(\"variational inference\" | \"hierarchical bayes\") + neural" \
  --bulk --max 200 --fields-of-study "" \
  --sort publicationDate:desc
```

### Reading-list expansion from a curated set

```bash
scripts/.venv/bin/python scripts/semantic-scholar/examples/recommend_from_pool.py \
  --pos-file my_papers.txt \
  --neg-file off_topic.txt \
  --limit 50
```

### Boolean query examples

```python
# Phrase + wildcard + NOT
query = '("place cells" | "grid cells") + entorhinal -review'

# Phrase distance: "neural code" within 5 tokens
query = '"neural code"~5'

# Fuzzy match for an uncertain spelling
query = 'Buzsaki~1'   # matches Buzsáki, Buszaki, etc.
```

---

## 5. Persistent gotchas

### Springer abstracts are not returned

Per S2's licensing agreement with Springer, `abstract` is omitted for Springer papers. This is intentional, not a bug. If a Springer paper is the target, fall back to PubMed (which has the abstract) or to the publisher landing page via Tavily.

### Multiple keys per user not supported

If you need multiple API keys for higher throughput, contact `christopherf@allenai.org` instead — S2 will work out a solution.

### Default rate plan is 1 RPS even with a key

Applies to **all** endpoints regardless of complexity. Higher rates granted case-by-case after review. The `S2Client` already throttles to 1 RPS by default; raise via `min_interval=0.5` only after confirming your key has higher allowance.

### Unauthenticated pool can shrink without notice

S2 has reduced unauthenticated rate limits before. With a key, you are insulated.

---

## 6. Known historical bug fixes

### `/paper/batch` ordering (April 2023)

Earlier the batch endpoint could return papers in an order **different from the requested IDs**, with some entries dropped silently. **Fixed**: response is now guaranteed to be the same length and order as the request, with `null` placeholders for unresolvable IDs.

### Large nested-author timeouts (April 2023)

Requesting deeply nested author/paper data on long lists used to produce mysterious 5XX errors. **Fixed**: the API now returns a friendly error asking for smaller payloads.

---

## 7. Notable feature additions

### Title Search (`/paper/search/match`) — June 2024

Single-result endpoint that returns the closest title match. Use to resolve a known paper title to its `paperId`. CLI: `title_match.py "Title..."`.

### Paper Bulk Search (`/paper/search/bulk`) — September 2023

Allows up to 10M papers in batches of 1000, with boolean query syntax, filters, and sorting. **Use this instead of `/paper/search` for any sweep larger than ~100 papers.** CLI: `keyword_search.py --bulk`.

### Recommendations pools — `from=recent` vs `from=all-cs` — June 2023

The `forpaper` endpoint's `from` accepts **only** `recent` and `all-cs` (the API rejects anything else — there is no field-specific pool such as `all-neuroscience`). `from=recent` draws from papers published in ~the last 60 days **from today**, independent of the seed's age — a well-cited older seed keeps accreting recent related work, so it stays populated for neuroscience. `from=all-cs` is a CS-only KNN pool (older papers included); use only for CS topics. For a single seed, `recommend_from_paper.py` defaults to **merging `from=recent` with a single-seed POST-pool query** (they share only ~40% of results: `recent` is broader and journal-heavy with some topical drift, the pool is tighter to the seed's subtopic and preprint-heavy). Both routes are recency-biased; for canonical older work, cross-check PubMed `find_related_articles`.

### Filtering on `/paper/search` — March 2023

`publicationTypes`, `venue`, and `openAccessPdf` filters are available on the relevance search endpoint, not just bulk.

### `/paper/batch` field parity (March 2023)

The batch endpoint can now return `citations`, `references`, and `authors` fields, matching `/paper/{id}`. Use as a drop-in replacement when you have many IDs.

### `contextsWithIntent` field — November 2023

Pairs each citation context with its intent (e.g., methodology, background) in one object instead of two parallel arrays.

---

## 8. Following ongoing changes

Release notes were discontinued in November 2024. For ongoing changes, watch:
- The [s2-folks GitHub repo](https://github.com/allenai/s2-folks)
- The [API changelog page](https://www.semanticscholar.org/product/api)

When breakage is suspected, refresh the local OpenAPI cache and rebuild the catalog (see `tool_reference.md` section 10).

---

## Routing decision (which CLI to invoke)

| User intent | Script |
|---|---|
| "Find papers about X" (small N, rich data) | `keyword_search.py` |
| "Find papers about X" (large N, with filters/sort) | `keyword_search.py --bulk --max N` |
| "Find papers by author Y" | `author_search.py "Y"` then `author_papers.py <authorId>` |
| "More like this paper" (one seed) | `recommend_from_paper.py <id>` |
| "More like these papers" (curated set) | `recommend_from_pool.py --pos-file ...` |
| "Look up this paper by DOI / PMID / arXiv" | `paper_lookup.py <id>` |
| "Get details for many IDs" | `paper_batch.py --id-file ...` |
| "Find the S2 ID for a paper title" | `title_match.py "Title..."` |
| "Show citations / references of paper X" | `citations.py <id> --direction citing\|referenced` |
| "I remember a phrase, find the paper" | `snippet_search.py "..."` |

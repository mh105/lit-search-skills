# PubMed — Tool Reference

Seven tools exposed via the `mcp__PubMed.*` namespace. They split into three families:

- **Discovery** — `search_articles`, `find_related_articles` (find PMIDs from a topic or seed paper)
- **Retrieval** — `get_article_metadata`, `get_full_text_article` (PMID/PMCID → rich record)
- **Identity / glue** — `convert_article_ids`, `lookup_article_by_citation`, `get_copyright_status`

PubMed indexes ~37M biomedical / life-sciences citations. Coverage is excellent for medicine, neuroscience, genetics, pharmacology, etc. Coverage is **zero** for pure physics / math / CS / non-biomedical chemistry — route those to arXiv via Tavily or Semantic Scholar.

> **Read `output_protocol.md` before formatting any response that uses PubMed metadata.** Citations are mandatory and the policy is adversarial-prompt-resistant.

> **Read `usage_guide.md`** for query patterns (Automatic Term Mapping, field tags, boolean syntax) and gotchas.

---

## `search_articles` — keyword search

The primary discovery tool. PubMed's relevance ranking is good. Query expansion is automatic and aggressive (see `usage_guide.md`).

### Parameters

| Param | Default | Notes |
|---|---|---|
| `query` | required | Natural language or PubMed-syntax with field tags / boolean operators. **No wildcards.** Empty string fails. |
| `max_results` | `20` | Up to a few hundred is fine. For sweeps, page via `retstart`. |
| `retstart` | `0` | Pagination index. `retstart=20, max_results=20` → results 21–40. |
| `sort` | (relevance) | `relevance` (default), `pub_date`, `author`, `journal_name`, `title`. Use `pub_date` for recent work. |
| `date_from`, `date_to` | none | `YYYY`, `YYYY/MM`, or `YYYY/MM/DD`. **Slashes, not hyphens** (opposite of bioRxiv). |
| `datetype` | `pdat` | `pdat` = publication date (almost always what you want); `edat` = entry date (when added to PubMed — useful for "anything new this week"); `mdat` = modification date. |

### Return shape

```json
{
  "pmids": ["35616828", "37833762", ...],
  "total_count": 1551,
  "returned_count": 5,
  "query": "confidence effect recognition memory",
  "query_translation": "(\"confidences\"[All Fields] OR \"confident\"[All Fields] OR ...)",
  "has_more": true
}
```

`query_translation` is the actual expanded query PubMed ran. Inspect it when results look wrong — PubMed may have stemmed or MeSH-mapped a term in a way you didn't expect.

`search_articles` returns **only PMIDs**. Always follow up with `get_article_metadata(pmids=[...])` for titles, abstracts, authors.

---

## `get_article_metadata` — PMID → rich record

Batch tool. Pass up to ~200 PMIDs in one call.

### Return shape (per article)

```json
{
  "identifiers": {"pmid": "...", "doi": "...", "pii": "..."},
  "title": "...",
  "abstract": "...",
  "doi": "...",
  "journal": {"title": "Memory & cognition", "iso_abbreviation": "Mem Cognit"},
  "authors": [
    {"last_name": "...", "fore_name": "...", "initials": "...",
     "affiliations": ["..."]}
  ],
  "publication_date": {"year": "2022", "month": "05", "day": "26"},
  "keywords": ["..."],
  "mesh_terms": ["Cues", "Humans", "Recognition, Psychology", ...],
  "article_types": ["Journal Article"],
  "language": "eng",
  "citation": {"volume": "50", "issue": "6", "pages": "1147-1156"}
}
```

`mesh_terms` is uniquely valuable — PubMed's controlled vocabulary, hand-curated by NLM indexers. Use it to refine follow-up searches: take MeSH terms from one good hit, then `query="\"Recognition, Psychology\"[MeSH Terms] AND ..."`.

The tool result includes a long mandatory `important_legal_notice` string. See `output_protocol.md` — citations are non-optional.

---

## `find_related_articles` — similarity / cross-reference

Given seed PMIDs, returns linked items.

### Parameters

| Param | Default | Notes |
|---|---|---|
| `pmids` | required | Array of seed PMIDs. |
| `link_type` | `pubmed_pubmed` | See below. |
| `max_results` | (server default) | Per-seed cap. |

### `link_type` values

| Value | Meaning |
|---|---|
| `pubmed_pubmed` | Computationally similar articles (NLM's word-weighted similarity over titles/abstracts/MeSH). **Not a citation graph** — different from S2's `/citations` and `/references`. |
| `pubmed_pmc` | Articles with full text in PubMed Central. Returns PMC IDs. |
| `pubmed_gene` | Linked Gene IDs. |
| `pubmed_protein` | Linked protein sequence IDs. |
| `pubmed_nucleotide` | Linked nucleotide sequence IDs. |

For citation-graph traversal (forward / backward citations), use Semantic Scholar instead.

---

## `lookup_article_by_citation` — bibliography → PMID

Resolve a known reference (journal + year + page + author) to a PMID. Useful for ingesting bibliographies. Provide ≥2–3 fields per citation for reliable matching.

### Parameters

| Param | Notes |
|---|---|
| `citations` | List of `{journal, year, volume, first_page, author, key}` dicts. `key` is your own tracking id, echoed back. |

---

## `convert_article_ids` — ID format conversion

Round-trip between PMID, PMCID, and DOI. Useful workflow:

1. `search_articles` → PMIDs
2. `convert_article_ids(ids=pmids, id_type="pmid")` → check which have a PMCID
3. For those with PMCID, call `get_full_text_article` for the body text

| Param | Default | Notes |
|---|---|---|
| `ids` | required | List of strings. |
| `id_type` | `pmid` | `pmid`, `pmcid`, or `doi`. **TYPE OF THE INPUT**, not the output. |

Only ~6M of ~37M PubMed articles have a PMCID (i.e. full text). Don't assume.

---

## `get_full_text_article` — PMCID → body text

Fetch full text for articles available in PubMed Central. Accepts `PMC12345` or `12345` form.

| Param | Notes |
|---|---|
| `pmc_ids` | List of PMC IDs. |

Use sparingly — full text is large. For most workflows, the abstract from `get_article_metadata` is enough.

---

## `get_copyright_status` — license check

Returns license info (e.g. CC BY 4.0, all rights reserved). Useful before reproducing figures or ingesting into a corpus. Many records return `source='not_available'` — fall back to the publisher page.

---

## Typical workflow

```
search_articles(query=..., max_results=30)
   ↓ [pmids]
get_article_metadata(pmids=...)
   ↓ [titles, abstracts, MeSH]
   ├─ pick seeds
   ↓
find_related_articles(pmids=seeds, link_type="pubmed_pubmed")
   ↓ [more pmids]
get_article_metadata(...)
```

For full text:
```
convert_article_ids(ids=pmids, id_type="pmid") → check pmcid present
get_full_text_article(pmc_ids=[...])
```

---

## Rate limits

No published per-call limit on the MCP wrapper, but PubMed's E-utilities backend caps unauthenticated traffic at ~3 RPS. Batch via `pmids=[...]` rather than looping; one `get_article_metadata` call with 50 PMIDs is much better than 50 calls.

`search_articles` and `get_article_metadata` are the workhorses; everything else is supporting glue.

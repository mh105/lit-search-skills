# PubMed — Usage Guide

PubMed's query language is its own dialect — well-documented but full of small gotchas that bite if you treat it like a generic web search. This guide covers the three behaviors you must internalize, a recipe book for common patterns, and the gotchas worth knowing before they cost you.

## Table of contents

1. The big three behaviors (Automatic Term Mapping, field tags, boolean operators)
2. Recipe book (worked queries)
3. What does NOT work
4. Iterating on noisy queries
5. Coverage gaps
6. Date-filter footguns
7. Author-name disambiguation

---

## 1. The big three behaviors to know

### 1a. Automatic Term Mapping (ATM) expands every untagged word

A bare query like `confidence effect recognition memory` is silently rewritten by PubMed to:

```
("confidences"[All Fields] OR "confident"[All Fields] OR "confidently"[All Fields]
 OR "self concept"[MeSH Terms] OR ("self"[All Fields] AND "concept"[All Fields])
 OR "self concept"[All Fields] OR "confidence"[All Fields])
AND ("effect"[All Fields] OR "effecting"[All Fields] OR "effective"[All Fields] OR ...)
AND ("recognition, psychology"[MeSH Terms] OR ("recognition"[All Fields]
 AND "psychology"[All Fields]) OR "psychology recognition"[All Fields]
 OR ("recognition"[All Fields] AND "memory"[All Fields])
 OR "recognition memory"[All Fields])
```

Mostly helpful (pulls in MeSH-mapped synonyms), occasionally wrong (mapping "confidence" to `self concept[MeSH]` is a stretch). Always inspect `query_translation` in the response when a hit count surprises you.

To **disable expansion**, wrap a term in quotes:

```
"confidence" AND "recognition memory"     # only literal forms
```

To **disable MeSH mapping but keep stemming**, append a field tag like `[All Fields]` or `[Title]`.

### 1b. Field tags scope a term to one part of the record

| Tag | Searches |
|---|---|
| `[Title]` | Title only |
| `[Title/Abstract]` | Title or abstract |
| `[Author]` | Author name (`Smith J[Author]`) |
| `[Affiliation]` | Author affiliation |
| `[Journal]` | Journal name (`Nature[Journal]`) |
| `[MeSH Terms]` | Controlled vocabulary (`"Recognition, Psychology"[MeSH Terms]`) |
| `[Publication Type]` | E.g. `Clinical Trial[Publication Type]`, `Review[Publication Type]` |
| `[Language]` | `english[Language]` |
| `[orgn]` | Organism (`mouse[orgn]`) |
| `[All Fields]` | Bypass MeSH mapping but keep word stemming |
| `[PMID]` | Lookup by ID |
| `[DOI]` | Lookup by DOI |

For author searches, `Smith J[Author]` (last name + initials) is canonical. `John Smith[Author]` works but is less reliable.

### 1c. Boolean operators must be UPPERCASE

`AND`, `OR`, `NOT`. Lowercase `and`/`or` are treated as keywords, not operators. Group with parentheses:

```
("recognition memory"[Title/Abstract] AND confidence[Title/Abstract])
AND (fMRI[Title/Abstract] OR EEG[Title/Abstract])
```

---

## 2. Recipe book

### Find a specific paper by title fragment

```
"memory conformity"[Title] AND "high-confidence"[Title]
```

Title-only search bypasses ATM expansion and is fast. If you only have a few exact words, this beats fuzzy keyword search.

### Find a known author's recent work

```
query: "Friston KJ"[Author]
sort: pub_date
date_from: 2024
```

For common surnames, add affiliation or co-author:

```
"Smith J"[Author] AND "Stanford"[Affiliation]
```

### Topic + recency

```
query: "recognition memory"[Title/Abstract] AND confidence[Title/Abstract]
sort: pub_date
date_from: 2023
max_results: 50
```

### Reviews / meta-analyses only

```
"recognition memory"[Title/Abstract] AND
(Review[Publication Type] OR Meta-Analysis[Publication Type] OR
 "Systematic Review"[Publication Type])
```

### Clinical trials only

```
asthma[Title/Abstract] AND "Clinical Trial"[Publication Type]
```

### Restrict to humans, exclude animals

```
"recognition memory"[Title/Abstract] AND humans[MeSH Terms] NOT animals[MeSH Terms]
```

For a softer filter, just add `humans[MeSH Terms]` without the NOT clause.

### Exact-phrase + MeSH combo (recommended for narrow queries)

```
"posterior alpha"[Title/Abstract] AND
("Magnetoencephalography"[MeSH Terms] OR "Electroencephalography"[MeSH Terms])
AND "source localization"[Title/Abstract]
```

Quoted phrases for the topic, MeSH terms for the modality — gives precision without sacrificing the coverage MeSH provides.

### Find anything entered to PubMed in the last 7 days

```
query: "recognition memory"[Title/Abstract]
datetype: edat
date_from: 2026/04/28
date_to: 2026/05/05
```

Note `edat` (entry date), not `pdat` (pub date). Useful for catching just-indexed papers regardless of when they came out.

---

## 3. What does NOT work

- **Wildcards (`*`)** — PubMed used to support these via E-utilities; the MCP wrapper rejects them.
- **Empty query string** — errors out.
- **Lowercase boolean operators** — `cancer and immunotherapy` searches for papers containing the literal word "and".
- **Proximity operators (NEAR, ADJ)** — PubMed doesn't have these. Use quotes for exact phrases instead.

---

## 4. Iterating on noisy queries

When a query returns way too many hits:

1. Inspect `query_translation` in the response.
2. Identify the term that expanded into a long OR-list of synonyms.
3. Pin it: replace `confidence` with `"confidence"` (literal) or `confidence[Title/Abstract]` (no MeSH mapping).
4. Add a tighter MeSH term from a good hit's `mesh_terms` array.

When a query returns too few:

1. Drop quotes / field tags one at a time and re-run.
2. Check spelling — PubMed does NOT spell-correct.
3. Try the OR of plausible synonyms explicitly.

PubMed's `query_translation` field is a uniquely useful debugging tool no other engine in this skill exposes. When PubMed disagrees with Consensus or Semantic Scholar on hit counts, the translation is usually the explanation.

---

## 5. Coverage gaps

The tool descriptions state these explicitly. Skipping listed scopes saves a wasted call:

- Physics, astrophysics, applied math → arXiv (via S2 or Tavily)
- Pure CS / AI / ML → arXiv
- Pure chemistry (non-biomedical) → ACS / SciFinder
- Engineering (non-biomedical) → IEEE Xplore
- Social sciences, economics, non-clinical psychology → other databases (PsyArxiv for psychology preprints)

For neuroscience-adjacent ML / computational papers (e.g. SVM-based EEG classifiers, deep learning for neuroimaging), PubMed coverage is real but patchy. Cross-search with Semantic Scholar or Tavily.

---

## 6. Date-filter footguns

- `datetype="pdat"` (default) = publication date in print. For online-first journals, this can lag actual availability by months.
- `datetype="edat"` = entry date in PubMed. The right choice for "find me anything indexed since last week" workflows.
- `date_from` / `date_to` accept `YYYY`, `YYYY/MM`, or `YYYY/MM/DD`. **Slashes, not hyphens.** `2024-01-15` will fail or be silently misinterpreted.

---

## 7. Author-name disambiguation is on the user

PubMed has no author-ID system equivalent to Semantic Scholar's `authorId`. "Smith J" matches thousands of distinct researchers. For unambiguous author work, prefer Semantic Scholar's `/author/search` followed by `/author/{id}/papers`. PubMed author search is best treated as a coarse filter, refined with affiliation or co-author constraints.

---

## 8. Other tool-specific gotchas

### `find_related_articles` is similarity, not citation

`find_related_articles(link_type="pubmed_pubmed")` returns *similar* articles via NLM's word-weighted similarity, **not citations**. Don't describe results as "papers that cite this one." For citation graphs, use Semantic Scholar.

`find_related_articles(link_type="pubmed_pmc")` only returns PMC IDs (full text). It is not a similarity tool — it's "does this paper have full text in PMC?"

### `find_related_articles` ignores `max_results`

The MCP tool accepts a `max_results` parameter, but the underlying ELink endpoint does not honor it — every call returns the *full* related-PMID list (often >1000 entries). Trim client-side or, in the lit-search skill, route the call through a haiku subagent (see `Mode: Associate` → "PubMed similarity sub-workflow" in SKILL.md).

### `lookup_article_by_citation` returns swapped `pmid` / `key` fields

When the response shape comes back, the resolved PMID lands in the `key` field and the `key` you submitted lands in `pmid` — the field names are inverted relative to what the schema implies. Always read the resolved PMID from `result.key`, not `result.pmid`. Example:

```python
# Submitted: [{journal: "Nature", year: 2015, ..., key: "test1"}]
# Returned:  [{journal: "Nature", year: "2015", ..., pmid: "test1", key: "26017442"}]
#                                                   ^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^
#                                                   user's key here  resolved PMID here
```

### PMCID coverage is sparse

- ~37M PMID records.
- ~6M have PMCID (full text in PubMed Central).
- Most older / non-NIH-funded / commercial-publisher papers do not.

`get_full_text_article` will silently return nothing if you pass a PMID-mapped PMCID that doesn't exist. Always run `convert_article_ids` first to verify a PMCID is present before calling full-text retrieval.

### Rate-limit symptoms

The MCP wrapper does not enforce a per-call cap, but the underlying NCBI E-utilities backend rate-limits at ~3 RPS for unauthenticated traffic. Symptoms of being throttled: occasional 5xx responses or empty `returned_count` with a non-zero `total_count`.

Mitigation: batch IDs whenever possible. One call with `pmids=[50 IDs]` is much better than 50 sequential calls.

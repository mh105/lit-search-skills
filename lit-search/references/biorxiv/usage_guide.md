# bioRxiv — Usage Guide

bioRxiv is a **secondary engine** in this skill. The MCP surface looks discovery-oriented but `search_preprints` filters by date and category only — no keyword field, no abstract search, no title search. Treat bioRxiv as a **DOI-resolution + provenance + fresh-feed** engine, not as a topic-search engine.

This guide explains how to use bioRxiv productively given that constraint, including the in-house keyword-filter pattern and its failure modes.

---

## Mental model

bioRxiv has three productive roles:

1. **DOI lookup** — given a bioRxiv DOI from another engine, return the rich record (full abstract, all authors, license, PDF URL, published version).
2. **Fresh feed** — "what was submitted to bioRxiv in the last N days in neuroscience?" Answerable, often valuable, but not topic-targeted.
3. **Provenance tracking** — "did this preprint get published?", "what NIH-funded preprints landed last month?" Unique capabilities, none replicated elsewhere.

Topic-driven discovery has to come from outside (S2, Tavily, PubMed), then bioRxiv fills in detail.

---

## Workflow A — keyword search that *includes* bioRxiv

User wants papers (including preprints) on a topic.

```
1. Semantic Scholar keyword_search          # primary discovery
   -> S2 indexes bioRxiv DOIs natively
   -> returns paperId, externalIds.DOI, sometimes openAccessPdf
2. Filter results to those with externalIds.DOI starting "10.1101/"
3. For each bioRxiv DOI: get_preprint(doi)  # rich record
   -> full abstract, license, pdf_url, published_doi
```

Alternative if S2 misses something:

```
1. tavily_search(query=..., include_domains=["biorxiv.org", "medrxiv.org"])
2. Extract DOIs from URL paths
3. get_preprint(doi) for each
```

---

## Workflow B — fresh feed for a category

User wants to track a field over time (the "Latest" mode in SKILL.md).

```
search_preprints(
  category="neuroscience",
  recent_days=30,
  limit=100,
)
-> recent preprints, ranked newest-first
-> scan abstract_preview (~200 chars per result) for relevance
-> for promising hits: get_preprint(doi) for full abstracts
```

There's no comparable feed in S2 or PubMed at this granularity.

---

## Workflow C — preprint-to-publication tracking

Per-paper:
```
get_preprint(doi=<biorxiv-doi>)
-> response.published_doi
   - "NA" / null   -> not yet peer-reviewed
   - "10.1038/..." -> published; resolve via PubMed or DOI
```

Cohort:
```
search_published_preprints(
  date_from="2024-01-01", date_to="2024-12-31",
  publisher="10.1038",   # Nature
  limit=100,
)
```

Neither workflow has an equivalent in any other engine.

---

## Workflow D — funder tracking

```
search_by_funder(
  funder_ror_id="021nxhr62",   # NIH
  date_from="2025-04-10",      # earliest funder metadata
  date_to="2026-05-05",
  category="neuroscience",
  limit=100,
)
```

Limitation: funder metadata only exists for preprints submitted on/after 2025-04-10.

---

## Workflow E — emulating keyword search via the LLM filter

The Claude bioRxiv tutorial shows prompts like *"Find all neuroscience preprints posted in the last 30 days related to Alzheimer's disease."* There is **no server-side keyword endpoint** — the under-the-hood pipeline is:

```
search_preprints(category="neuroscience", recent_days=30, limit=100)
  -> server returns ~30 most recent neuroscience preprints (any topic)
  -> Claude scans title + abstract_preview in-context for "Alzheimer",
     "AD", "tau", "amyloid", etc.
  -> Claude presents the matching subset
```

This works *acceptably* for high-frequency topics in densely-submitted categories (Alzheimer's in neuroscience, COVID-19 in medRxiv). It works *poorly* for niche topics.

### Pagination behavior — important caveat

The schema advertises `limit ∈ [1, 100]`. **In practice the API returns ~30 results per call regardless of `limit`.** Verified empirically: `limit=100, recent_days=90, category="neuroscience"` returned 30 records; `cursor=100` and `cursor=500` returned different non-overlapping batches of 30 each.

The `total` field is reported as `0` even when results exist — likely a misreporting bug. There is no way to precompute how many pages to fetch.

### Exhaustive-fetch loop

```python
cursor = 0
all_results = []
while True:
    resp = search_preprints(
        category=..., recent_days=..., limit=100, cursor=cursor,
    )
    if not resp["results"]:
        break
    all_results.extend(resp["results"])
    cursor += 30   # observed page size, not the schema-advertised 100
```

Stop condition: empty `results`. Do **not** rely on `total` or `count`.

### Cost intuition

- bioRxiv submission volume in neuroscience ≈ 30–50 preprints/day.
- 30-day window in `category="neuroscience"` → 900–1,500 records.
- Exhaustive fetch → **30–50 paginated calls per query.**
- Each call returns ~30 records with truncated `abstract_preview` (~200 chars).

For routine "what's new this month" round-ups, **don't default to exhaustive**. Either:

1. Cap pagination at 3–5 pages (~90–150 results) and tell the user the cap.
2. Tighten the date window (`recent_days=7` instead of 30).
3. Route to S2 first (`keyword_search.py --year-min=<recent>`), then enrich the bioRxiv DOIs via `get_preprint(doi)`.

Default exhaustive only when the user explicitly asks for "all" / "every" / "comprehensive" coverage of recent preprints in a field.

### Failure modes

1. **Silent recall ceiling.** Past the pagination cap, hits are invisible to the keyword filter.
2. **Silent precision floor.** `abstract_preview` is truncated; topic mentions in methods/results/discussion are missed. The fix (`get_preprint(doi)` for full abstracts) costs one MCP call per paper.
3. **Vocabulary mismatch.** Bag-of-words matching on "Alzheimer" misses "AD", "amyloid pathology", "neurodegenerative tauopathy". Claude must expand synonyms manually before scanning.

### When to use this pattern

- The user wants a "what's new this month in <field>" round-up rather than exhaustive topic search.
- The topic is high-frequency in the chosen category.
- A coverage gap is acceptable.

### When to reject this pattern

- The user says "find all" / "comprehensive" / "every paper" — recall matters, this pattern silently undercovers.
- The topic is niche or has many synonyms.
- The user's field doesn't map to one bioRxiv category (pure psychology, statistical methods, computational-neuro methods).

In those cases, route to S2's keyword search (S2 indexes bioRxiv natively) or to Tavily with `include_domains=["biorxiv.org", "medrxiv.org", "psyarxiv.com"]`. Use `get_preprint(doi)` only to enrich DOIs.

---

## Field routing — what bioRxiv covers, what it doesn't

| Field | Best category | Notes |
|---|---|---|
| Neuroscience (broad) | `neuroscience` | Single dense bucket. Use as primary. |
| Systems / computational neuro | `neuroscience` + `systems biology` | Methods may also drop into `bioinformatics`/`biophysics`. |
| Cognitive science (humans) | `neuroscience` | No dedicated category. Cog-sci-on-humans lands here. |
| Cognitive science (animals) | `animal behavior and cognition` | Comparative cognition, decision-making in non-humans. |
| Psychology | (none — limited) | bioRxiv has no psychology category. **Route to PsyArxiv** instead. |
| Statistical signal processing (methods) | (mismatch) | Pure methods → arXiv `stat.ME` / `eess.SP` / `q-bio.NC`. Route to S2. |
| Statistical signal processing (applied) | `bioinformatics` / `biophysics` | EEG/MEG with bio applications can land here, sparse vs arXiv. |
| EEG / MEG / fMRI methods | `neuroscience` + `bioinformatics` | Mixed: implementation → bioinformatics; cog-application → neuroscience. |
| Confidence / metacognition / recognition memory | `neuroscience` + PsyArxiv | Split; sweep both. |

**Practical default for the user's field mix** (statistical signal processing, neuroscience, psychology, cognitive science): browse bioRxiv with `category="neuroscience"` and `category="animal behavior and cognition"`; treat psychology as PsyArxiv-via-OSF; treat statistical methods as arXiv-via-S2.

---

## Workflow F — full-text retrieval

```
get_preprint(doi=...)
-> response.pdf_url   # direct PDF, no auth, no rate limits
-> pass to tavily_extract or PDF fetcher
```

bioRxiv PDFs are CC-licensed in most cases. PMCID-based PubMed full text is restricted to ~6M articles; bioRxiv full text is universal across all preprints.

---

## Output / disclosure rules

bioRxiv preprints are **not peer-reviewed**. When summarising results, always disclose this — usually as a parenthetical after the venue:

> Smith et al. (2024, *bioRxiv preprint, not peer-reviewed*) report that ...

If the preprint has a published version (`published_doi != "NA"`), prefer linking to the peer-reviewed version and note it was originally a preprint.

---

## What NOT to do

- ❌ `search_preprints(query="confidence recognition memory")` — there is no `query` parameter; the call fails validation.
- ❌ Treat `search_preprints` as topic search and apologise that "no results were found" when the recent feed happens to miss the topic.
- ❌ Pass a non-bioRxiv DOI (e.g. `10.1038/...`) to `get_preprint` — it returns an error.
- ❌ Cite a preprint without disclosing that it isn't peer-reviewed.
- ❌ Use bioRxiv's `find_related_articles`-style features — they don't exist. Route to S2 for similarity.

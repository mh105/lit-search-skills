# Consensus — Tool Reference

Two Codex tools: `mcp__codex_apps__consensus._search` and `mcp__codex_apps__consensus._fetch`. Consensus is a meta-search engine layered over **Semantic Scholar + PubMed + Scopus + ArXiv** (~200M peer-reviewed papers). It's the one engine in this skill that crosses biomedical and physical-science boundaries in a single call.

> **Read `usage_guide.md` first.** Two higher-level skills (`consensus-literature-review`, `consensus-grant-finder`) wrap Consensus into curated multi-search workflows. When the user's intent matches lit-review or NIH-grant-scoping, invoke that skill instead of calling this tool directly.

---

## When to call this tool directly

- Quick "what does the literature say on X" with a curated top-10 list and full abstracts.
- Cross-checking a Semantic Scholar / PubMed result set against an alternative ranker.
- Evidence-based questions ("does X cause Y?", "what's the evidence for Z?") — Consensus's `medical_mode` is built for this.
- Queries that straddle bio + physics / CS / methods (e.g. "deep learning for fMRI source reconstruction") — pulls from arXiv too.

## When to route elsewhere

- Citation graphs → Semantic Scholar (`citations.py`).
- MeSH-controlled search → PubMed.
- Full text → PubMed PMC or S2 `openAccessPdf`.
- Pagination beyond 10 results → S2's `/paper/search/bulk`. Consensus free-tier hard cap is 10; Pro is 20.
- Complex multi-search workflows (lit reviews, grant scoping) → the wrapper skills above.

---

## `_search`

### Parameters

| Param | Default | Notes |
|---|---|---|
| `query` | required | Natural language. The Codex connector accepts only this field. To request filters, include supported tokens in the query text, e.g. `year:2020-2026`, `study:rct`, `study:meta-analysis`, `study:systematic-review`, `human:true`. |

### Return shape

The tool returns JSON with `papers` and `top_papers`. Each result includes title, authors, year, citation count, journal, URL, abstract, study type/takeaway when available, and DOI when available. Before citing any result, call `_fetch` with the result id.

```
[N] [Paper Title](consensus.app/papers/details/<hash>/?utm_source=chatgpt)
   (Author1 et al., Year, Citations, Journal, DOI when present)
   Full abstract text (typically 1-3 paragraphs).
```

The response may end with Consensus's own trailer text (citation instructions and/or a sign-up/upgrade footer, when provided) — server-appended boilerplate, not paper data.

Each result carries: title, Consensus URL (opaque hash in the URL), authors, publication year, citation count, journal name, full abstract, and often DOI. It does not carry PMID, Semantic Scholar paperId, fields-of-study, PDF URL, or publisher URL.

## `_fetch`

`_fetch(id="<hash>")` is required before citing a search result. In Codex search results, use the opaque hash in the Consensus URL if there is no separate `id` field in the payload. `_fetch` returns the canonical Consensus paper URL plus metadata such as authors, year, journal, citation count, and DOI when available.

To bridge a Consensus hit into another engine: search the title in Semantic Scholar (`title_match.py`) or PubMed (`"Title fragment"[Title]`). Title-match is reliable at ≥7 distinct words.

---

## Plan tiers

| Tier | Results per call | Extra metadata |
|---|---|---|
| Unauthenticated | ~3 | none |
| Free | 10 | none |
| Pro | 20 | study design, key takeaways |

Detect tier from the response: language like "Found 19 papers, showing top 10" tells you the cap. Surface this to the user when sparse results may reflect a plan limit, not a literature gap.

---

## Pagination

There is none. Free-tier returns top 10; Pro returns top 20. For broader sweeps, route to S2's `/paper/search/bulk` or PubMed's paginated `search_articles`.

---

## Rate limits

Hit aggressively in testing — back-to-back calls returned `Rate limit exceeded. Please wait a moment before searching again.`

Practical guidance:
- **At most 3 calls in a 30-second window.** Server-stated.
- The wrapper skills (`consensus-literature-review`, `consensus-grant-finder`) enforce stricter 1 query/second sequential pacing; follow that when delegating.
- If a 429 comes back, wait ~30s and retry.
- For multi-query workflows, prefer Semantic Scholar (~1 RPS, well-behaved with retry) and use Consensus for the one or two highest-value cross-checks.

---

## Coverage overlap with other engines

| Engine | Overlap with Consensus | Why use Consensus instead |
|---|---|---|
| Semantic Scholar | High — S2 is a Consensus source DB | Different ranking; pre-filtered for "evidence" framing; bundled abstract; medical_mode quality filter |
| PubMed | High for biomedical | Consensus also pulls Scopus + arXiv; one query covers cross-domain |
| Tavily | Low — Tavily searches web; Consensus searches papers | Use Consensus for paper hits, Tavily for grey literature / non-paper sources |
| bioRxiv | None directly — Consensus's source set excludes preprints unless `exclude_preprints` is left off | Consensus does include preprints by default but doesn't expose bioRxiv-specific filters |

In the biomedical neuroscience domain, Consensus and S2 typically return overlapping top hits. Consensus's unique value is (a) curated single-call top-10 with full abstracts inline, (b) `medical_mode` for clinical questions, (c) cross-domain queries that need arXiv too.

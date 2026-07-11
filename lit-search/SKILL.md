---
name: lit-search
description: >
  Multi-engine academic literature search with adaptive routing. Use whenever the user asks 
  to find papers, look up references, search for related work, look up specific papers
  by title/DOI/ID, find work by a named author, find the latest preprints in a field, surface
  non-paper material (press releases, clinical trial reports, lab pages) on a research topic,
  or find papers similar/related to one or more seed papers ("more like this paper"),
  or check whether a paper or claim is reliable — retracted, corrected, disputed, or well-supported.
---

# Literature Search

Adaptive multi-engine search for academic literature. The skill picks one of six modes based on what the user is actually trying to do, runs the appropriate engine(s), and returns results in a format that suits the mode.

## Runtime setup

The `scripts` and `references` folders are under the same directory containing this file.

Python example scripts (Semantic Scholar, PsyArxiv) run through a shared venv at `scripts/.venv/`. **Always invoke them as `scripts/.venv/bin/python scripts/<engine>/examples/<script>.py …`** — the bare `python` interpreter on this machine does not have `requests` installed and will `ModuleNotFoundError`. If the venv is missing (fresh clone), recreate it with:

```bash
python3 -m venv scripts/.venv
scripts/.venv/bin/pip install -r scripts/requirements.txt
```

Credentials (`S2_API_KEY`, `OSF_TOKEN`) are read from the shell environment — `.env` files are also supported but the env-var path is the default. See `scripts/<engine>/.env.example` for which variables each engine needs.

### MCP engine tool names — discover at runtime, never hardcode

The MCP tool names written throughout this skill (`mcp__codex_apps__consensus._search`, `mcp__PubMed.search_articles`, `mcp__bioRxiv.search_preprints`, `mcp__codex_apps__scite._search_literature`, and the `mcp__tavily.*` family) are **illustrative names for this Codex setup**. The registered names are **host-dependent**: other environments expose the same servers under different prefixes or opaque IDs (e.g. `mcp__<uuid>__search`), so a literal call to a hardcoded name can fail with "tool not found."

**Before the first MCP call in a session, resolve the real tool name at runtime** — do not assume the illustrative name resolves. Discover it by capability keyword (e.g. via `ToolSearch` or the host's tool-discovery mechanism), then call whatever name it returns. Treat every `mcp__…` string below as "the tool that does X," not as a literal identifier. The Python-script engines (Semantic Scholar, PsyArxiv) are unaffected — they run through the venv, not MCP.

## When to use

The skill triggers on any of these intents:

- "Find papers about X" / "what does the literature say on X"
- "Look up this paper by DOI / title / arXiv ID"
- "Find papers by author Y"
- "Tell me the latest preprints on X in the last N weeks"
- "What's online about X" (non-paper sources, press, trials, lab pages)
- "More like this paper" / "find papers similar to <DOI/title>" / "related work to these papers"
- "Is this paper retracted / reliable / safe to cite?" / "how contested is this claim?" / "which work on X is well-supported vs. disputed?"
- "Implementation of X on GitHub"

It does **not** trigger on:

- "Write me a literature review on X" / "lit review on X" → invoke `consensus-literature-review`.
- "Find NIH grants for my research idea" → invoke `consensus-grant-finder`.
- "Run deep research on X" → use the `notebooklm` skill or a dedicated deep-research skill.

## Mode selection — decision tree

Apply in order. Stop at the first match.

```
1. Did the user say "literature review" or "lit review" explicitly?
   → invoke `consensus-literature-review` skill. Do NOT proceed in this skill.

2. Did the user ask about NIH funding / grants / NOSIs / institutes?
   → invoke `consensus-grant-finder` skill. Do NOT proceed in this skill.

3. Did the user supply ONE OR MORE SEED PAPERS and ask for similar / related work?
   Phrasing like "more like this paper", "find papers similar to <DOI/PMID/arXiv/title>",
   "related work to these <N> papers", "expand my reading list from these seeds",
   "what else is like <paper>". The seeds may be DOIs, PMIDs, arXiv IDs, S2 hashes,
   CorpusIds, or titles the user wants resolved first.
   → MODE: Associate  (Semantic Scholar recommendations + optional PubMed related)

4. Is the user asking about LATEST PREPRINTS specifically?
   Phrasing like "latest preprints on X", "what's new in <field> this month",
   "preprints in the last N weeks/days/months"
   → MODE: Latest  (bioRxiv + PsyArxiv with subagent filter)

5. Is the user asking whether a paper or claim is RELIABLE, or how CONTESTED it is?
   Phrasing like "is this paper retracted / reliable / safe to cite", "has <paper> been
   corrected or flagged", "how disputed is <claim>", "find the contested vs. well-supported
   work on X". The subject may be specific paper(s) (DOI/PMID/title) or a topic/claim.
   → MODE: Vet  (Scite only)

6. Is the user looking for a SPECIFIC PAPER OR AUTHOR they have in mind?
   Phrasing like "the X paper by Y", "the 2023 Friston paper on active inference",
   "find papers by Karl Friston since 2024", named-paper / named-author queries
   → MODE: Precise  (PubMed + Tavily(Google Scholar))

7. Is the user looking for NON-PAPER WEB MATERIAL on a topic?
   Phrasing like "what's online about X", "press / news / trial registries",
   "lab pages / company X's research / FDA submission for Y"
   → MODE: AI  (Tavily, broad or domain-restricted)

8. DEFAULT — broad topic-driven discovery.
   Phrasing like "find papers on X", "what does the literature say on X",
   contextual discussions where the user wants to ground a claim
   → MODE: Explore  (Consensus MCP direct + Semantic Scholar cross-check)
```

The default is **Explore**. The other five are entered only when the user's phrasing matches their specific cue.

## GitHub code search (orthogonal)

Code-implementation queries ("implementation of X on GitHub", "code for paper Y") are not part of the six modes — they go through `gh search`:

```bash
gh search repos "<topic>" --language=python --sort=stars
gh search code "<algorithm-name>" --filename=*.py
```

This sometimes runs alongside Explore (find a paper, then find the code) but doesn't share the engine selection logic.

**Caution — over-constrained `gh search` returns an empty result, not an error.** Stacking filters (e.g. a multi-word phrase *and* `--language=python` *and* `--sort=stars`) can legitimately match zero repos and print nothing at all. An empty result here is **not** a failure or an auth problem — it means "no repo matched all constraints." Loosen the query (drop `--language`, shorten the phrase) and retry before concluding the search is broken.

---

## Modes

### Mode: Explore (default)

For broad topic-driven discovery in contextual discussions where the user wants to ground a claim or get a feel for the literature.

**Primary engine**: `mcp__codex_apps__consensus._search` (direct call), followed by `mcp__codex_apps__consensus._fetch` for any result you cite.

**Supplementary engine**: Semantic Scholar (`scripts/.venv/bin/python scripts/semantic-scholar/examples/keyword_search.py`) — catches papers Consensus may miss. Run when the topic is in S2's strong domains (citation graphs, niche methods, very recent work) or when Consensus returns thin results.

**Workflow**:

1. Call `mcp__codex_apps__consensus._search` with just the `query` parameter. The Codex connector does not expose separate filter parameters; if the user explicitly named criteria, encode supported filters in the query text as tokens such as `year:2020-2026`, `study:rct`, `study:meta-analysis`, `study:systematic-review`, or `human:true` (see `references/consensus/usage_guide.md`).
2. If results are thin (<5) or the topic is methods-heavy, run an S2 cross-check:
   ```bash
   scripts/.venv/bin/python scripts/semantic-scholar/examples/keyword_search.py "<reformulated keyword query>"
   ```
   Reformulate the query for keyword density (S2 rewards keyword soup; Consensus rewards natural language).
3. Deduplicate cross-engine results by DOI when present, by title (case-insensitive, whitespace-normalized) otherwise.
4. Before citing any Consensus result, call `mcp__codex_apps__consensus._fetch(id=<hash>)`. The `id` is the opaque hash in the result URL when the search payload does not expose a separate `id`.
5. Present results inline as a conversational summary with citations.

**Output**:

- Apply the Consensus citation protocol (`references/consensus/output_protocol.md`): inline `[N]` cites, exact consensus.app URLs verbatim with whatever `utm_source` the tool returned intact, and the mandatory footer/instructions when the tool result provides one.
- For S2-only finds, use a separate `[S2-N]` block linked via DOI.
- See `references/consensus/output_protocol.md` for the cross-engine merge pattern.

### Mode: Precise

For when the user has a specific paper in mind, names an author, or describes papers from a research conversation. The user trusts canonical-engine relevance ranking and wants the top results without aggressive synthesis.

**Engines**:

- **PubMed** via `mcp__PubMed.search_articles` → `mcp__PubMed.get_article_metadata`. Use for biomedical queries, named MeSH-mappable topics, author searches with affiliation, clinical work.
- **Google Scholar via Tavily** with `include_domains=["scholar.google.com"]`. Use for citation-count cross-checks, exact-title lookups (`exact_match="true"`), or coverage Tavily extracts well from Scholar's HTML (Friston 2023 active inference, etc.).
  - Caution — Do not use Scholar profile URLs as bibliography entries. Prefer PubMed, S2, DOI, or publisher URLs for clean paper metadata. If Tavily returns a Scholar profile page, extract only the citation count/title row as auxiliary metadata.


**Workflow**:

1. Pick the engine that matches the query: clinical/biomedical/MeSH → PubMed; author + topic + year → Tavily(Scholar); both → run in parallel.
2. **Trust the server-side relevance ranking.** Take the first 10–20 results. Do not re-sort.
3. For PubMed, follow `search_articles` with `get_article_metadata(pmids=[top 20])` to enrich.
4. Surface the top hits with full metadata — title, authors, year, venue, DOI/PMID, abstract.

**Output**:

- For PubMed-sourced papers: apply `references/pubmed/output_protocol.md` — open/close with attribution to PubMed, every cited paper hyperlinked via DOI.
- For Tavily(Scholar) hits: include the Scholar URL as the link, surface citation count when the snippet preserves it.
- Cross-engine merge into a single numbered bibliography is fine here (both engines link via DOI or stable URLs).

### Mode: Latest

For "what came out on bioRxiv / PsyArxiv in the last N days/weeks/months on X." Used when the user explicitly wants bleeding-edge preprints, accepting that these are not peer-reviewed.

**Engines**:

- **bioRxiv** via `mcp__bioRxiv.search_preprints` (biology / neuroscience).
- **PsyArxiv** via `scripts/.venv/bin/python scripts/psyarxiv/examples/recent_preprints.py` (psychology).

Both engines have **no native keyword search** (bioRxiv has none at all; PsyArxiv has substring filters but not full-text). The Latest workflow pulls a category- or date-windowed feed and filters in-house.

**Workflow**:

1. Detect domain from query language:
   - Biology / clinical / neuroscience-mechanism → bioRxiv (`category="neuroscience"` or relevant).
   - Psychology / cognitive science / methods → PsyArxiv.
   - Ambiguous (cognitive neuroscience, computational psychiatry) → both.
2. Pull date-windowed feeds:
   ```bash
   # bioRxiv
   mcp__bioRxiv.search_preprints(category="neuroscience", recent_days=14, limit=100)
   # iterate cursor += 30 (observed page size, see references/biorxiv/usage_guide.md)
   
   # PsyArxiv
   scripts/.venv/bin/python scripts/psyarxiv/examples/recent_preprints.py --days 14 --limit 100
   ```
   Default cap: 3–5 pages (~90–150 records per engine). Exhaustive sweeps only when the user explicitly asks for "all" / "every" / "comprehensive."
   **Note — bioRxiv `search_preprints` reports `"total":0` even when results are present.** The `total` field in its response envelope is not populated; it is a known API quirk, **not** an error and **not** an empty-result signal. Judge success by the returned `results`/`count`, and paginate by `cursor` (+ observed page size), never by `total`.
3. **Spawn a cheap subagent to filter for relevance** (this is the cost-saving step):
   ```
   multi_agent_v1.spawn_agent({
     message: "Given these N preprints (titles + abstract previews), return
               the subset relevant to '<user topic>' with synonym expansion
               (<X synonyms>). Return JSON list of {id, doi, title, score 1-5}.
               Do not edit files."
   })
   ```
   The subagent does the reading; only the filtered list returns to this agent's context.
4. For top hits in the filtered list, follow up with `get_preprint(doi)` (bioRxiv) or `preprint_lookup.py` (PsyArxiv) to enrich abstracts.
5. Deduplicate cross-engine by DOI; within each engine, dedup on versioned id (`fu6de_v1` vs `fu6de_v2` are distinct records, keep the latest).

**Output**:

- Sorted newest-first.
- Each entry: title, authors (first + et al.), date, DOI/preprint URL, abstract preview, brief relevance note.
- **Always disclose** "preprint, not peer-reviewed" parenthetically. If `published_doi` is set, link to the published version too.

### Mode: AI

For non-paper material on a research topic — lab pages, press releases, clinical trial registries, FDA submissions, conference programmes, blog posts from researchers, news coverage of papers. Tavily's web index covers what other engines don't.

**Engines**:

- `mcp__tavily.tavily_search` — primary discovery (broad or domain-restricted).
- `mcp__tavily.tavily_extract` — pull full content from specific URLs.
- `mcp__tavily.tavily_map` — list every URL on a site without bodies (cheap; ideal for "find every paper PDF on this lab's website").
- `mcp__tavily.tavily_crawl` — crawl-and-extract from a base URL with natural-language `instructions=` for filtering.

**Workflow**:

1. Decide the scope:
   - **Broad web** — let Tavily rank generically. Apply default `exclude_domains` for noise (`researchgate.net`, `wikipedia.org`, `youtube.com`, `twitter.com`, `medium.com`).
   - **Domain-restricted** — pick a subdomain allowlist from `references/tavily/usage_guide.md` (section 6) based on the field. E.g., systems neuroscience → `["jneurosci.org", "neuron.cell.com", "elifesciences.org", "biorxiv.org", "janelia.org", "alleninstitute.org"]`.
2. Use `search_depth="advanced"` and `max_results=15-20` when domain-restricted (push for recall since the allowlist already restricts the candidate pool).
3. For longer pages where the snippet is thin, follow with **`tavily_extract(urls=[...], query=<original_query>)`**. The `query` parameter is **mandatory** in this skill — it tells Tavily to rerank/trim chunks by relevance. Without it, a single page extract can return 60+ KB of full-page markdown and spill to disk.
4. For "what's on this site?" without bodies, use `tavily_map(url=..., max_depth=1, limit=50)` first — cheap URL-only scan — then run `tavily_extract` on the URLs that look promising.
5. For systematic harvesting from a single site (e.g., a lab's full publication list), use `tavily_crawl` with `instructions="..."`.

**Output**:

- Free-form synthesis with provenance — every claim links back to the URL.
- Distinguish paper hits from non-paper hits: papers get `(Authors, Year, Venue)`; non-paper hits get `(Source, Type — press release / lab page / trial registry)`.
- Note when material is preliminary or non-peer-reviewed.

### Mode: Associate

For "more like this paper" — the user supplies one or more seed papers and wants similar / related work.

**Primary engine**: Semantic Scholar recommendations API via the wrapper scripts.

- Single seed → `scripts/.venv/bin/python scripts/semantic-scholar/examples/recommend_from_paper.py <id>` (`GET /recommendations/v1/papers/forpaper/{id}`).
- Multiple seeds (with optional negatives to push results away from off-topic neighbors) → `scripts/.venv/bin/python scripts/semantic-scholar/examples/recommend_from_pool.py --pos ... --neg ...` (`POST /recommendations/v1/papers/`).

**Supplementary engine for biomedical seeds**: PubMed `find_related_articles` (`mcp__PubMed.find_related_articles`). Different similarity model than S2 (MeSH + abstract word-weighting vs. S2's embedding similarity), so it surfaces complementary hits. Use it as a cross-check whenever the seed has a PMID. **Always wrap this call in a subagent** — see "PubMed similarity sub-workflow" below — because the endpoint ignores `max_results` and returns the full PMID list (1000+ entries is normal), which would flood the main context.

See `references/semantic-scholar/tool_reference.md` §8 for the response envelope (no pagination — `--limit` is a single-shot cap, max 500) and `scripts/semantic-scholar/README.md` for the routing table.

**Workflow**:

1. **Resolve seeds to S2 paper IDs.** Any S2-accepted ID format is fine for both endpoints (`DOI:...`, `PMID:...`, `ARXIV:...`, `CorpusId:N`, or the 40-char S2 hash). If the user only gave you a title, resolve it first:
   ```bash
   scripts/.venv/bin/python scripts/semantic-scholar/examples/title_match.py "<title>"
   ```
2. **Pick the endpoint by seed count:**
   - Exactly one seed → `recommend_from_paper.py <id>`. By default this **merges two complementary routes**: the `from=recent` pool (papers published in ~the last 60 days *from today*) plus a single-seed **pool** query (co-citation-based, tighter to the seed's subtopic). Switch to `--from all-cs` (a pure CS-pool query, no merge) only when the topic is clearly computer science.
   - Two or more seeds → `recommend_from_pool.py`. Pass each seed as `--pos <id>` (repeatable) or via `--pos-file <path>` (one ID per line). If the user has flagged off-topic papers to push away from, pass them as `--neg <id>` / `--neg-file`.
   ```bash
   # single seed
   scripts/.venv/bin/python scripts/semantic-scholar/examples/recommend_from_paper.py DOI:10.1038/nature14066 --limit 50
   
   # multi-seed pool
   scripts/.venv/bin/python scripts/semantic-scholar/examples/recommend_from_pool.py \
     --pos-file seeds.txt --neg-file off_topic.txt --limit 50
   ```
3. **Set `--limit` realistically.** Each endpoint returns its full list in one response (no pagination); for a single seed `--limit` applies **per route** and the deduped union is returned (so the count can exceed `--limit`). Default `--limit 50` is usually plenty; raise toward 500 only when the user wants a wide sweep, lower (~20–30) when they want a tight reading-list addition.
4. **Filter by user-stated constraints in-house.** The recommendations endpoint does not accept `year` / `venue` / `fieldsOfStudy` filters server-side, so apply any year cutoff, venue filter, or minimum citation count after the response returns.
5. **Re-rank toward the user's intent if needed.** S2's recommender is topic-similarity-driven; if the user explicitly wants high-citation canonical work or recent-only work, sort by `citationCount` or `year` before presenting.
6. **Disclose the seeds in the output.** Always show which paper(s) the recommendations were generated from, so the user can sanity-check direction.

**Output**:

- Lead with a one-line "Recommendations seeded from: <Title>, <Year>" (or a list of titles for multi-seed).
- Numbered list of recommendations with title, authors (first + et al.), year, venue, citation count, DOI link.
- For each recommendation, include a 1-line note on *why* it relates (shared method, same author, follow-up, etc.) when the abstract makes it obvious — otherwise omit rather than guess.
- Note "preprint, not peer-reviewed" parenthetically for any arXiv/bioRxiv/medRxiv hits returned in the recommendation set.

#### PubMed similarity sub-workflow (biomedical seeds only)

`mcp__PubMed.find_related_articles` is similarity-based (MeSH + word-weighted abstract overlap), not citation-based. Two important quirks:

- The `max_results` parameter is **ignored** by the underlying ELink API — every call returns the full related-PMID list, often >1000 entries.
- Pulling the full list into the main agent's context burns tokens fast. Always offload to a cheap subagent.

Pattern:

```
multi_agent_v1.spawn_agent({
  message: "
    Seed PMID: <pmid>
    Topic phrase: <one-sentence description of what's interesting about the seed>
    Step 1: call mcp__PubMed.find_related_articles(pmids=['<pmid>'], link_type='pubmed_pubmed').
    Step 2: take the first 100 PMIDs (they're already ordered by similarity score).
    Step 3: call mcp__PubMed.get_article_metadata(pmids=[those 100]).
    Step 4: rank/filter by topic relevance to '<topic phrase>'. Drop anything off-topic.
    Step 5: return JSON list of {pmid, doi, title, year, journal, score 1-5, why}
            for the top 15-20 hits.
    Do not return any other PMIDs or full abstracts. Do not edit files.
  "
})
```

Only the trimmed JSON re-enters this skill's context. Merge those PMIDs into the S2 recommendation list before output, deduplicating by DOI when present.

### Mode: Vet

For reliability and consensus checks — the one thing the other modes do not do. Two questions it answers: (1) *Is this specific paper safe to cite?* (retracted / corrected / expression of concern / erratum), and (2) *On this topic or claim, what is well-supported versus contested?*

**Engine**: `mcp__codex_apps__scite._search_literature` — **Scite only. Do not fall back to or merge with any other engine in this mode.**

**Read this payload note before using — it shapes the whole workflow.** Access is via a Stanford→EBSCO institutional integration (resolver URLs are normal). In Codex, `search_literature` can return rich fields including `authors`, `abstract`, `year`, `journal`, `tally`, Smart Citation `citations`, `fulltextExcerpts`, `access`, and `retraction_notices`, but availability varies by paper and access rights. Always inspect the actual response before citing any counts or snippets. What reliably works:

- **Server-side filters** on Smart Citation / editorial-notice data: `has_retraction`, `has_correction`, `has_concern`, `has_erratum`, `has_tally`, `supporting_from/to`, `contrasting_from/to`, `mentioning_from/to`, `citing_publications_from/to`.
- **The `RETRACTED` / `RETRACTED ARTICLE` prefix baked into the indexed `title`.**

So Vet can both **select** papers by their citation/notice profile and, when fields are present, report the returned tally/snippet evidence. **Never invent tally counts or citation-sentiment numbers**; if a field is absent, say it was not returned and rely on filters plus report links instead.

**Workflow — sub-flow A: reliability check on specific paper(s).**

1. Resolve each subject to a DOI (titles are accepted, but DOIs are exact — prefer them).
2. Fetch metadata: `search_literature(dois=[...])` with no `term`. A `RETRACTED` / `RETRACTED ARTICLE` prefix in the returned title is a definitive positive signal.
3. Probe each editorial-notice type by re-querying the DOI *with the matching filter* — the filter runs server-side, so a hit means the flag is set and an empty result means it is not:
   ```
   search_literature(dois=[doi], has_retraction=true)   # non-empty → retracted
   search_literature(dois=[doi], has_correction=true)   # non-empty → has a correction
   search_literature(dois=[doi], has_concern=true)      # non-empty → expression of concern
   search_literature(dois=[doi], has_erratum=true)      # non-empty → has an erratum
   ```
   Batch multiple DOIs per call where possible; run the four notice probes in parallel.
   **Gotcha — notice-absent surfaces as an error, not a clean empty list (verified):** on this integration, a DOI+notice probe for a notice the paper does *not* carry frequently returns an **HTTP 500** (and sometimes an empty result carrying a *"not present in Scite's index"* message) rather than a clean empty list. **If the plain fetch in step 2 returned the paper, treat a 500 (or an empty result) on its notice probe as "notice absent" — not as a tool failure and not as an un-indexed paper.** Only report a paper as un-indexed if step 2 itself returned nothing. Because the probe can 500, do not batch a DOI's four notice probes so tightly that one 500 aborts the others, and lean on the two signals that are reliable here: the `RETRACTED` / `RETRACTED ARTICLE` title prefix from step 2, and the `term`-based retraction sweep (sub-flow B step 3).
4. Report each paper's status per notice type, with links.

**Workflow — sub-flow B: consensus / controversy map on a topic or claim.**

1. Turn the topic into a specific technical `term`. Boolean/phrase/proximity syntax is supported (`"exact phrase"`, `AND`/`OR`/`NOT`, `"a b"~5`); the index spans all fields, so broad terms return cross-discipline noise.
2. Run the same term twice to split the field:
   ```
   search_literature(term="<topic>", contrasting_from=5, limit=15)   # contested / disputed
   search_literature(term="<topic>", supporting_from=25, limit=15)   # well-supported
   ```
   Tune thresholds to the field's citation volume — raise `supporting_from` for large literatures, lower `contrasting_from` (min 1) for niche ones.
3. Optionally surface any retracted work still circulating: `search_literature(term="<topic>", has_retraction=true, limit=10)`.
4. Present the two lists side by side; a paper appearing only in the contested list is a caution flag, one in the supported list with no notices is safer footing.

**Output**:

- Banner label `VET`.
- **Sub-flow A**: a short status line per paper — e.g. `⚠️ RETRACTED` / `⚠ Expression of concern` / `Correction on file` / `No editorial notices found` — each linking to its Scite report (the visual supporting/contrasting/mentioning breakdown) and to the paper:
  - Scite report: `https://scite.ai/reports/{doi}`
  - Paper: `https://doi.org/{doi}`
- **Sub-flow B**: two labelled lists — "Well-supported (≥N supporting citations)" and "Contested (≥M contrasting citations)" — each entry `title` + returned tally when present + Scite report link + `doi.org` link.
- **State the payload caveat once**: use returned Scite tallies/snippets only when present; otherwise results are selected by Scite's Smart Citation / editorial-notice filters and the actual counts/citation statements live on the linked Scite report page. Do not fabricate numbers.
- Vet is a reliability gate, not a synthesis — it does not summarize the science or draw conclusions. For that, use Explore.

**Out of scope for Vet** (needs the gated `evidence:*:mcp` entitlements, not enabled on this license): Scite's regulatory/clinical databases — clinical trials, FAERS/MAUDE adverse events, MHRA alerts, 510(k) clearances, drugs, patents, grants — all return an entitlement error. If those are ever enabled they warrant their own mode; they are not part of Vet.

---

## Cross-engine workflow

### Deduplication

When results from multiple engines hit the same response:

1. **DOI when populated** is the primary key. Most engines return DOIs (S2 `externalIds.DOI`, PubMed `article.identifiers.doi`, bioRxiv top-level `doi`, PsyArxiv `attributes.doi` or `links.preprint_doi`).
2. **Title (case-insensitive, whitespace-normalized)** when DOI is missing.
3. **Within PsyArxiv only**, also dedup on the versioned id (`fu6de_v1` vs `fu6de_v2` are intentionally distinct — keep the latest).
4. **Consensus stays separate** — its URLs use opaque hashes, not DOIs, and its citation protocol forbids merging into a DOI-keyed bibliography. See `references/consensus/output_protocol.md`.

### Result presentation

#### Mandatory mode banner (always first)

**Every lit-search response MUST begin with a fenced code block announcing the mode.** This is the first thing the user sees, before any prose, citations, or lists. No exceptions — even a single-paper lookup gets a banner.

Use exactly this format (a plain fenced code block, no language tag — renders as a monospace box in Codex):

```
┌─────────────────────────────────────────────────┐
│  LIT-SEARCH MODE: <MODE_NAME>                   │
│  Engines: <engine1> + <engine2>                 │
│  Trigger: <one-line reason this mode was picked>│
└─────────────────────────────────────────────────┘
```

Concrete examples:

```
┌─────────────────────────────────────────────────┐
│  LIT-SEARCH MODE: EXPLORE  (default)            │
│  Engines: Consensus + Semantic Scholar          │
│  Trigger: broad topic-discovery query           │
└─────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────┐
│  LIT-SEARCH MODE: ASSOCIATE                     │
│  Engines: Semantic Scholar recommendations      │
│  Trigger: seed paper(s) supplied — "more like"  │
└─────────────────────────────────────────────────┘
```

Mode names are always one of: `EXPLORE`, `PRECISE`, `LATEST`, `AI`, `ASSOCIATE`, `VET` (uppercase). Pad the right side of each line with spaces so the box characters line up; the box should look square in monospace. Keep the box ≤ 53 chars wide so it doesn't wrap on narrow terminals.

After the banner, leave one blank line, then proceed with the mode-specific output.

#### Per-mode output style (after the banner)

Output style is **mode-dependent** — there is no single template:

| Mode | Banner label | Output style |
|---|---|---|
| Explore | `EXPLORE  (default)` | Conversational synthesis with inline `[N]` cites + Consensus footer |
| Precise | `PRECISE` | Top-N enumerated list with full metadata + DOI links |
| Latest | `LATEST` | Newest-first list with preprint disclosures |
| AI | `AI` | Free-form synthesis with URL provenance |
| Associate | `ASSOCIATE` | Numbered recommendation list, headed by the seed paper(s) used |
| Vet | `VET` | Reliability status per paper, or supported-vs-contested lists, with Scite report links |

Each mode has its own quality signals — see the per-mode workflow above.

### Common quality signals

- **Citation count**: high = established work; less meaningful for papers <6 months old.
- **Venue tier**: ACL/EMNLP/NeurIPS/ICML/Nature/Science/Cell > field-specific journals > workshops > arXiv-only.
- **Cross-engine corroboration**: a paper that appears in 2+ engines is higher-confidence than a single-engine hit.
- **Code availability**: papers with code are more verifiable. Surface this when present.
- **Recency vs canonical**: prefer recent for "latest" intents, prefer canonical (high-citation, high-tier) for "what does the literature say."

---

## Engine quick-reference

```
Semantic Scholar  scripts/.venv/bin/python scripts/semantic-scholar/...    references/semantic-scholar/
PsyArxiv          scripts/.venv/bin/python scripts/psyarxiv/...            references/psyarxiv/
PubMed            (MCP only)                                               references/pubmed/
bioRxiv           (MCP only)                                               references/biorxiv/
Consensus         (MCP only)                                               references/consensus/
Tavily            (MCP only)                                               references/tavily/
Scite             (MCP only)                                               references/scite/
```

The two Python-script engines share a single venv at `scripts/.venv/`. Re-create with `python3 -m venv scripts/.venv && scripts/.venv/bin/pip install -r scripts/requirements.txt` if missing.

Per-engine reference docs follow a uniform structure:

- `tool_reference.md` — what tools / parameters / response shapes are available.
- `usage_guide.md` — when to use, gotchas, recipes, defaults.
- `output_protocol.md` — formatting requirements (only for Consensus and PubMed, which have mandatory rules).

When uncertain about a parameter on any engine, open the `tool_reference.md` for that engine first. When uncertain about *whether* to use an engine for a given query, check the `usage_guide.md`.

For Semantic Scholar, structured parameter lookups are fastest via the SQLite catalog: `sqlite3 references/semantic-scholar/data/endpoints.db "..."`.

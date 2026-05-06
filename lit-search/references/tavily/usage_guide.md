# Tavily — Usage Guide

This guide covers four interrelated concerns:

1. Query phrasing (what works for Tavily's web index)
2. Source targeting via `include_domains` (the most powerful lever)
3. Default parameter sets for neuroscience workflows
4. Worked examples and anti-patterns

For the parameter surface of each tool, see `tool_reference.md`.

## Table of contents

1. Natural-language vs keyword-dense phrasing
2. Quoted phrases and `exact_match`
3. What survives Tavily's snippet extraction
4. Search-depth selection
5. Source targeting: per-domain patterns
6. Domain allowlists for neuroscience
7. Default parameter sets
8. Topic-area subdomain hints
9. Date-range conventions
10. Worked examples
11. Anti-patterns

---

## 1. Natural-language vs keyword-dense phrasing

Semantic Scholar's `/paper/search` rewards **keyword density** — short, content-word queries score best:

```
S2:      "hippocampal replay sharp-wave ripple consolidation"
```

Tavily rewards **natural-language phrasing** that mirrors how people *write* about a topic on the web — full questions or noun phrases:

```
Tavily:  "how does hippocampal replay during sharp-wave ripples support memory consolidation"
```

Why: Tavily's index is web-content snippets, written in prose, not abstract-style keyword soup. Snippet-matching favours queries that look like sentences other people have written.

### Practical rule

- **Same query for both engines** → mediocre on both.
- **Reformulate at the engine boundary** → better recall on each.

If orchestrating across S2 and Tavily, plan for two query forms per research question.

---

## 2. Quoted phrases and `exact_match`

Two ways to enforce verbatim matching:

1. **Quoted phrases inside `query`**:
   ```
   query='"sharp-wave ripple" replay hippocampus'
   ```
   Quoted segments must appear verbatim; unquoted words are flexible.

2. **`exact_match=true` parameter** — applies the constraint to the entire query *and* its quoted substrings. Stricter, lower recall, higher precision.

| Use case | Choice |
|---|---|
| Exact paper title lookup | `exact_match=true` with the title quoted |
| Topic search with a key technical term | Quote just the term, leave the rest unquoted |
| Broad discovery | No quotes, no `exact_match` — let the ranker work |

---

## 3. What survives Tavily's snippet extraction

Tavily returns ~300–500 char snippets per result. Things that reliably show up:

- **Paper titles** (when the page is a journal landing page or preprint)
- **Author lists** (especially first/last author)
- **Year** (in parens or as `Published 2024`)
- **Abstracts**, often the first sentence or two
- **Citation counts** when the source page exposes them (Scholar, S2)
- **DOIs** when present in the page header

What tends to *not* survive:

- Body-text claims (snippets are usually intro/abstract material)
- Equations and figures
- Reference lists
- Anything behind tabs/accordions on the page

**Implication**: treat Tavily snippets as **discovery + metadata**, not as evidence. To support a claim from a paper, follow up with `tavily_extract` (or read the PDF directly).

---

## 4. Search-depth selection

| Depth | Use when |
|---|---|
| `ultra-fast` | You're sure of the title and just need the URL. Latency-sensitive lookups. |
| `fast` | Generic web facts. Rarely the right call for lit search. |
| `basic` | Default; cheap; fine for sanity checks. |
| `advanced` | **Default for lit search.** Better recall, surfaces deeper results past the first page. |

When in doubt, `advanced` for paper hunting and `basic` for everything else.

---

## 5. Source targeting: per-domain patterns

`include_domains` is the lever that turns a generic web search into an indirect query against specific sources. The general shape:

```python
tavily_search(
  query="...",
  include_domains=["target-domain.tld", ...],
  search_depth="advanced",
  max_results=15,
)
```

Bump `search_depth` to `advanced` and `max_results` to 10–20 when targeting one domain — the allowlist already restricts the candidate pool, so push for recall.

### Google Scholar (`scholar.google.com`)

```
include_domains=["scholar.google.com"]
```

The big one. Tavily is currently the only path to Scholar without a direct scraper.

**What works:**
- **Exact title lookups** with `exact_match=true` — Scholar's title-keyed pages are stable URLs, snippet usually contains citation count.
- **Author + year + topic** — *"Friston 2023 active inference"* tends to surface the author's profile or paper page.
- **Citation-count discovery** — Scholar shows `Cited by N` inline; Tavily preserves it. Useful when S2's `citationCount` lags.

**What doesn't:**
- **Broad topical sweeps** — Scholar's HTML doesn't expose enough structure for Tavily to rank well.
- **Forward citation traversal** — Scholar's *"Cited by"* links are JS-rendered; Tavily can't follow them.
- **Filter combinations** — Scholar's URL params for filters aren't stable. Bake the year into the query string instead.

**Tactic**: use Scholar-via-Tavily for **citation-count sanity-checks** and **finding the canonical paper page** for a known title. Don't use it for discovery.

### PubMed (`pubmed.ncbi.nlm.nih.gov`)

```
include_domains=["pubmed.ncbi.nlm.nih.gov"]
```

PubMed's HTML is structured and Tavily extracts cleanly — abstract, authors, MeSH terms, DOI, PMID all show up.

**What works:**
- Clinical / biomedical queries — PubMed's coverage is much stronger than S2 here.
- Finding the PMID for a paper you know by title.
- Pulling abstracts when the journal landing page is paywalled but PubMed has the abstract.

**What doesn't:**
- Preprints — PubMed indexes published versions only.
- Very recent papers — MEDLINE indexing lag is days to weeks.

**Tactic**: use PubMed-via-Tavily as a **cross-check on Semantic Scholar** for clinical neuro queries. If S2 returns thin results, repeat with `include_domains=["pubmed.ncbi.nlm.nih.gov"]`.

### bioRxiv / medRxiv (`biorxiv.org`, `medrxiv.org`)

```
include_domains=["biorxiv.org", "medrxiv.org"]
```

There's a dedicated bioRxiv MCP (`mcp__claude_ai_bioRxiv__*`) which should be preferred for DOI lookup and category browsing. Tavily targeting bioRxiv is the **fallback** when you want a single search across bioRxiv *and* other preprint mirrors at once (e.g., bioRxiv + arXiv + lab pages in one call).

### arXiv (`arxiv.org`)

```
include_domains=["arxiv.org"]
```

arXiv abstract pages are clean and Tavily extracts well. Useful for computational neuroscience, NeuroAI, and theory papers that often live on arXiv before (or instead of) bioRxiv.

Pair with bioRxiv when sweeping a NeuroAI topic: `include_domains=["arxiv.org", "biorxiv.org"]`.

### PsyArxiv (`psyarxiv.com`)

```
include_domains=["psyarxiv.com"]
```

Use as the **full-text-search fallback** for psychology preprints when the OSF API's substring filters don't cover the query. The dedicated `scripts/psyarxiv/` pathway has stronger structured access (date, subject, contributors) but no full-text search.

### Lab homepages

Two-step pattern when the lab domain is unknown:

1. `tavily_search(query="Karl Friston lab homepage", max_results=3)` to discover the domain.
2. Re-run with `include_domains` set, or follow with `tavily_crawl` for systematic harvesting.

```
tavily_crawl(
  url="https://lab.example.edu/",
  instructions="only follow links to publication pages or paper PDFs",
  max_depth=2,
  limit=30,
)
```

### Conferences and workshops

```
include_domains=[
  "proceedings.neurips.cc",
  "openreview.net",
  "proceedings.mlr.press",
]
```

For full programme harvesting, `tavily_crawl` with `instructions="follow links to individual paper pages or PDFs only"`.

---

## 6. Domain allowlists for neuroscience

### `NEURO_PUBLISHERS` — peer-reviewed journals

```python
NEURO_PUBLISHERS = [
    # Glamour
    "nature.com", "science.org", "cell.com",
    # Neuro-specific
    "jneurosci.org",          # Journal of Neuroscience
    "neuron.cell.com",        # Neuron
    "elifesciences.org",      # eLife
    "plos.org",               # PLoS Biology / Comp Bio / ONE
    "frontiersin.org",        # Frontiers in Neuroscience / Neural Circuits
    "academic.oup.com",       # Cerebral Cortex, Brain
    "journals.physiology.org",# J Neurophysiol
    "link.springer.com",      # Springer family
    "onlinelibrary.wiley.com",# Wiley family
    "sciencedirect.com",      # Elsevier (NeuroImage, Neuropsychologia)
]
```

### `NEURO_PREPRINTS` — preprint servers

```python
NEURO_PREPRINTS = [
    "biorxiv.org", "medrxiv.org",
    "arxiv.org",              # NeuroAI / theory
    "psyarxiv.com",           # Psychology preprints
    "osf.io",                 # OSF preprints
]
```

### `NEURO_INDEXES` — abstract indexes / metadata

```python
NEURO_INDEXES = [
    "pubmed.ncbi.nlm.nih.gov",
    "scholar.google.com",
    "europepmc.org",          # PMC Europe — full-text + abstracts, OA-friendly
]
```

### `NEURO_FUNDERS_AND_INSTITUTES`

```python
NEURO_FUNDERS_AND_INSTITUTES = [
    "nih.gov",                # NIH RePORTER, grant abstracts
    "alleninstitute.org", "janelia.org",
    "humanbrainproject.eu", "ebrains.eu",
]
```

### `NEURO_NOISE` — typical exclude list

```python
NEURO_NOISE = [
    "researchgate.net",       # paywalled / login-walled / SEO-spammy
    "academia.edu",
    "wikipedia.org",
    "youtube.com",
    "twitter.com", "x.com",
    "reddit.com",
    "medium.com",
]
```

Apply selectively — sometimes ResearchGate is the only place a preprint lives.

---

## 7. Default parameter sets

### `DEFAULT_PAPER_SEARCH` — small-N relevance search

For "find me ~15 strong hits on this topic":

```python
DEFAULT_PAPER_SEARCH = dict(
    search_depth="advanced",
    max_results=15,
    include_domains=NEURO_PUBLISHERS + NEURO_PREPRINTS + NEURO_INDEXES,
    exclude_domains=NEURO_NOISE,
    include_raw_content=False,
)
```

### `LEAN_PAPER_SEARCH` — fast sanity check

```python
LEAN_PAPER_SEARCH = dict(
    search_depth="basic",
    max_results=5,
    exclude_domains=NEURO_NOISE,
)
```

### `RECENT_NEURO` — recent activity sweep

```python
RECENT_NEURO = dict(
    search_depth="advanced",
    max_results=20,
    time_range="year",
    include_domains=NEURO_PREPRINTS + NEURO_PUBLISHERS,
    exclude_domains=NEURO_NOISE,
)
```

### `SCHOLAR_PROXY` — citation-count check via Scholar

```python
SCHOLAR_PROXY = dict(
    search_depth="advanced",
    max_results=10,
    include_domains=["scholar.google.com"],
    exact_match=True,    # combine with quoted title in query
)
```

### `PUBMED_CLINICAL` — clinical / biomedical neuro

```python
PUBMED_CLINICAL = dict(
    search_depth="advanced",
    max_results=20,
    include_domains=["pubmed.ncbi.nlm.nih.gov", "europepmc.org"],
    exclude_domains=NEURO_NOISE,
)
```

### `LAB_HARVEST` — extract all papers from a lab homepage

```python
LAB_HARVEST = dict(
    instructions="only follow links to publication pages, paper PDFs, or preprint URLs",
    max_depth=2,
    max_breadth=20,
    limit=50,
    extract_depth="basic",
    allow_external=True,
)
```

---

## 8. Topic-area subdomain hints

### Systems / circuit neuroscience

```
["jneurosci.org", "neuron.cell.com", "elifesciences.org", "nature.com",
 "biorxiv.org", "janelia.org", "alleninstitute.org"]
```

### Computational neuroscience / NeuroAI

```
["arxiv.org", "biorxiv.org", "elifesciences.org", "plos.org",
 "proceedings.neurips.cc", "openreview.net", "proceedings.mlr.press"]
```

### Cognitive neuroscience / fMRI

```
["sciencedirect.com",         # NeuroImage
 "academic.oup.com",           # Cerebral Cortex
 "jneurosci.org",
 "nature.com",                 # Nature Human Behaviour
 "elifesciences.org",
 "biorxiv.org"]
```

### Clinical / neurology / psychiatry

```
["pubmed.ncbi.nlm.nih.gov", "thelancet.com", "nejm.org",
 "academic.oup.com",           # Brain
 "nature.com",                 # Nature Medicine
 "jamanetwork.com", "bmj.com"]
```

### Molecular / cellular neuroscience

```
["cell.com", "nature.com", "elifesciences.org", "embopress.org",
 "pubmed.ncbi.nlm.nih.gov", "biorxiv.org", "embo.org"]
```

### Cognitive psychology / behavioural

```
["psyarxiv.com", "apa.org", "sciencedirect.com",
 "nature.com",                 # Nature Human Behaviour
 "academic.oup.com", "tandfonline.com"]
```

---

## 9. Date-range conventions

- `time_range="year"` for "what's recent" — fast, but filters by *crawl* date.
- `start_date`/`end_date` for explicit ranges — also crawl-date.
- For **publication-year** filtering, bake the year into the query string and post-filter the results. Tavily has no API for publication date.

When users ask for "papers from 2023–2025" on a topic:

```
query="<topic> 2023 OR 2024 OR 2025"   # OR is ignored; year tokens still help
```

Then drop hits whose snippet doesn't mention an in-range year.

---

## 10. Worked examples

### Specific paper by title

```
tavily_search(
  query='"Predictive coding under the free-energy principle"',
  exact_match=True,
  max_results=5,
)
```

### Topical sweep over the last year

```
tavily_search(
  query="hippocampal replay during awake rest memory consolidation",
  search_depth="advanced",
  time_range="year",
  max_results=15,
  exclude_domains=["wikipedia.org", "researchgate.net"],
)
```

### Cross-source comparison (Scholar + PubMed)

```
tavily_search(query=Q, include_domains=["scholar.google.com"], search_depth="advanced", max_results=15)
tavily_search(query=Q, include_domains=["pubmed.ncbi.nlm.nih.gov"], search_depth="advanced", max_results=15)
```

### Multi-hop research question

```
tavily_research(
  input=(
    "Survey the leading hypotheses for the role of astrocyte calcium "
    "signalling in NREM sleep regulation. Include key papers from 2022 "
    "onward, the experimental techniques used (genetic Ca2+ indicators, "
    "two-photon imaging, optogenetics), and the main points of disagreement."
  ),
  model="pro",
)
```

### Lab publication harvest

```
# Step 1: discover lab domain
tavily_search(query="Friston lab UCL homepage", max_results=3)

# Step 2: crawl
tavily_crawl(
  url="https://www.fil.ion.ucl.ac.uk/~karl/",
  instructions="only follow links to publication or paper pages",
  max_depth=2,
  limit=50,
)
```

---

## 11. Anti-patterns

- **Stop-word soup**: `"papers about X"` — "papers" and "about" displace signal. Just write the topic.
- **Boolean operators**: Tavily ignores `AND` / `OR` / `NOT`. Use `include_domains` / `exclude_domains` and quoted phrases instead.
- **Wildcards**: not supported.
- **Filter-laden queries on Scholar-via-Tavily**: don't try to encode Scholar's URL filter params into the query — bake constraints into prose: *"... 2023 to 2025 ..."*.
- **Re-using the S2 query verbatim**: covered in section 1.

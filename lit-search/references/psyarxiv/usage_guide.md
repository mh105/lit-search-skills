# PsyArxiv — Usage Guide

This page covers three concerns:

1. **Search strategy** — how to do keyword discovery without a full-text endpoint.
2. **Subjects taxonomy** — the bepress hierarchy and the cached JSON.
3. **Gotchas** — empirical edge cases to avoid.

For the API surface (auth, filters, response shapes), see `tool_reference.md`. For the cached subjects taxonomy, see `data/psyarxiv_subjects.json`.

## Table of contents

1. The "no full-text search" constraint
2. The synonym fan-out heuristic
3. When to query `description` vs `title`
4. When to combine with date / subject filters
5. The "recent preprints" composite pattern
6. Subjects taxonomy
7. Gotchas and edge cases

---

## 1. The "no full-text search" constraint

The OSF Preprints endpoint has **no full-text search**. Sending `filter[q]=working memory` returns:

```
HTTP 400 — "'q' is not a valid field for this endpoint."
```

This is structurally similar to bioRxiv (which also has no keyword search exposed via its public API) and structurally different from Semantic Scholar / PubMed / Tavily.

What is available for keyword discovery:

1. `filter[title]` — phrase-ordered substring on the paper title.
2. `filter[description]` — substring on the abstract.
3. `filter[tags]` — substring on the free-text author-supplied tag list.

These are AND-combined within a single request. To OR across terms or fields you must fan out and deduplicate client-side.

---

## 2. The synonym fan-out heuristic

For any topic-driven query, expand the user's term into 3–5 synonyms before issuing requests. Each synonym becomes one request; results merge by `id`.

```
user query: "working memory"
fan-out:
  filter[title]=working memory
  filter[title]=short-term memory
  filter[title]=WM capacity
  filter[title]=verbal STM
```

`examples/search_preprints.py --any 'working memory,short-term memory,WM capacity'` implements exactly this pattern.

For psychology, expect heavy synonym variance:

| Topic | Likely synonyms |
|---|---|
| Working memory | short-term memory, STM, WM capacity, verbal STM, visuospatial STM |
| Cognitive control | executive function, EF, top-down attention, inhibitory control |
| Reward | reinforcement, value learning, incentive |
| Replication | reproducibility, robustness, registered report |
| Mental health | depression, anxiety, mood disorder, internalizing, psychopathology |

---

## 3. When to query `description` vs `title`

| Field | Profile |
|---|---|
| `title` | **Precision-leaning.** Authors put the most discriminative term in the title, but many papers use a less canonical synonym. Lower recall. |
| `description` | **Recall-leaning.** Abstracts mention more synonyms but also more incidental terms. Lower precision. |

**Default to `title` first** for topic discovery. Fall back to `description` only if `title` returns < ~10 results, or if the user explicitly wants exhaustive recall.

---

## 4. When to combine with date / subject filters

Always pair a keyword query with `filter[date_published][gte]` for "recent" intents. Without a date floor, you'll get the all-time corpus (58k+ records) and pagination becomes the bottleneck.

Pair with `filter[subjects]=<text>` to restrict to a sub-discipline. The subject taxonomy has 234 leaf entries (see section 6); pick the most specific match. Note that subject filtering uses substring match on the taxonomy text, so `filter[subjects]=Cognitive` matches Cognitive Psychology, Cognitive Neuroscience, Cognitive Science, Social Cognition, etc.

### When to fall back to other engines

If the user wants full-text search over psychology preprints, **route to Tavily with `include_domains=["psyarxiv.com"]`** instead of using this pathway. The OSF API is best for:

- Newest-first feeds (`sort=-date_published`)
- Date-bounded sweeps with subject/tag constraints
- Single-paper metadata + contributor lookup
- Subject taxonomy enumeration

It is poor for:

- Open-ended "find papers about X" without strong signal in the title

---

## 5. The "recent preprints" composite pattern

PsyArxiv's strongest role in this skill is as the **psychology counterpart to bioRxiv**. The composite query for "recent psych preprints on X":

```
1. search_preprints.py --title <term> --date-from <floor> --limit 50
2. search_preprints.py --description <term> --date-from <floor> --limit 50
3. merge by id, drop duplicates
4. sort by date_published descending
```

This pattern feeds the Latest mode in `SKILL.md` alongside bioRxiv.

---

## 6. Subjects taxonomy

PsyArxiv inherits the bepress Digital Commons taxonomy under the "Social and Behavioral Sciences" umbrella. The provider-scoped enumeration returns 234 subject leaves.

Refresh the local cache any time with:

```bash
python3 scripts/psyarxiv/examples/list_subjects.py \
  --dump references/psyarxiv/data/psyarxiv_subjects.json
```

### Cache file format

`data/psyarxiv_subjects.json` is a flat array; each entry:

```json
{
  "id": "5b4e7427c6983001430b6c98",
  "text": "Aging",
  "taxonomy_name": "bepress",
  "parent_id": "5b4e7426c6983001430b6c1d"
}
```

`parent_id` lets you reconstruct the hierarchy if needed; many leaves are two or three levels deep.

### Querying with subjects

`filter[subjects]` accepts either form interchangeably:

```
filter[subjects]=Aging                       → 272 hits
filter[subjects]=5b4e7427c6983001430b6c98    → 272 hits  (same)
```

The text form is a substring match. So `filter[subjects]=Cognitive` matches *all* of: Cognitive Psychology, Cognitive Neuroscience, Cognitive Science, Social Cognition, etc. For tight selectivity, prefer the UUID form looked up from the cache.

### Hot subjects for this skill's user

Likely-relevant subject leaves for a neuroscience + psychology + cognitive science + signal-processing user:

| Subject text | Use case |
|---|---|
| Cognitive Psychology | Top-level cognitive psych |
| Cognitive Neuroscience | Brain-cognition mechanisms |
| Behavioral Neurobiology | Animal/circuit-level cognition |
| Memory | Memory-specific |
| Attention | Attention-specific |
| Learning | Learning/skill acquisition |
| Quantitative Methods | Methods/stats psych |
| Psychometrics | Psychometric methodology |
| Computational Neuroscience | Modeling/computational |
| Neurosciences | Generic neuroscience catch-all |
| Developmental Psychology | Across lifespan dev |
| Aging | Aging-specific |
| Clinical Psychology | Clinical applications |
| Neuropsychology | Lesion/clinical neuro |

The full 234-row enumeration is in the JSON cache; grep for any term not listed above.

### Composing subject + keyword

Subjects narrow the candidate pool *before* keyword substring matches:

```bash
python3 scripts/psyarxiv/examples/search_preprints.py \
  --subject "Cognitive Neuroscience" \
  --title "memory" \
  --date-from 2026-01-01 \
  --limit 50
```

Returns Cognitive Neuroscience preprints with "memory" in the title from 2026 forward, sorted newest first.

---

## 7. Gotchas and edge cases

Empirically discovered against the live API on 2026-05-05.

### `page[size]` silently caps at 100

```
page[size]=10    → 10 rows
page[size]=100   → 100 rows
page[size]=200   → 100 rows  (silently capped, no warning)
page[size]=1000  → 100 rows  (silently capped)
```

Always paginate via `links.next` for >100 results.

### `filter[title]` is phrase-ordered

```
filter[title]=working memory   → 668 hits
filter[title]=memory working   → 0 hits
```

Word order matters. The default is a literal-phrase icontains. Use `filter[title][contains]=` or `[icontains]=` for token-level substring, but the recall ceiling is the same — there is no tokenized inverted index behind this filter.

### `sort=date_created` returns HTTP 502

Server-side bug. Use `sort=-date_published` or `sort=-date_modified` for chronological feeds.

### `embed=contributors` on the list endpoint returns links only

The same `embed=contributors` on the **detail** endpoint inlines data correctly. For list sweeps, do not embed contributors — pick interesting rows and call `/preprints/{id}/contributors/` for those. `examples/preprint_lookup.py` already follows this pattern.

### `X-OSF-Version` header is not echoed

Even when sending `?version=2.20`, the server does not return any `X-OSF-Version` response header. The version is reported in the body's `meta.version`. Don't write code that depends on a header for version detection.

### `abstract` is not a valid filter field

Use `filter[description]` for abstract substring matching. The OSF data model calls the abstract field `description`.

### Versioned IDs (`<id>_v<N>`)

A bare preprint id (`fu6de`) resolves to the latest version. Versioned IDs (`fu6de_v1`, `fu6de_v2`) resolve to specific versions. Detail and contributors endpoints accept both forms; list responses return versioned IDs in the `data[*].id` field even when the parent has only one version (`v1`).

When deduplicating across multiple queries, dedup on the versioned id; the same paper at v1 and v2 are distinct records (different DOIs, different content snapshots).

### `doi` is null until OSF mints it

New preprints have `doi: null` in their attribute payload — the DOI is minted asynchronously after acceptance. Use `links.preprint_doi` instead; that field is populated as soon as the DOI is reserved (often before `doi` is filled).

### `total` in `links.meta` is reliable

`links.meta.total` reports the count for the current filter combo, accurately, across all pages. (Compare to bioRxiv MCP, which misreports `total: 0`.) This makes pre-pagination cost estimation cheap — fetch one row to learn the size before deciding how aggressively to paginate.

### Provider scope must always be set

Without `filter[provider]=psyarxiv`, the endpoint returns all OSF preprint providers. There are ~30, including EngrXiv, EarthArxiv, SocArxiv, and many field-specific ones. The default behavior is union, not "OSF-only psych."

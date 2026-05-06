# Semantic Scholar — Tool Reference

The Semantic Scholar (S2) pathway has both a Python client (`scripts/semantic-scholar/s2_client.py`) and CLI examples (`scripts/semantic-scholar/examples/`). This reference covers the API surface they wrap.

> **Read `usage_guide.md`** for neuroscience defaults, recipe templates, and gotchas. The on-disk **endpoints catalog** (`data/endpoints.db`, regenerable via `data/build_endpoints_db.py`) holds 16 endpoints and 47 filter values for fast structured lookup — query patterns at the bottom of this file.

## Table of contents

1. Base URLs
2. Authentication
3. Rate limits
4. Paper ID formats
5. Search query syntax (relevance vs. bulk)
6. Filter values (`fieldsOfStudy`, `publicationTypes`, `year`, `venue`, etc.)
7. The `fields` parameter (sparse fieldsets, dot notation)
8. Response envelopes (offset / token / edge / batch)
9. Status codes worth handling
10. Querying `endpoints.db`

---

## 1. Base URLs

| API | Base URL |
|---|---|
| Graph (papers, authors, snippets) | `https://api.semanticscholar.org/graph/v1` |
| Recommendations | `https://api.semanticscholar.org/recommendations/v1` |
| Datasets | `https://api.semanticscholar.org/datasets/v1` (not used in this skill) |

## 2. Authentication

Header: `x-api-key: <your-key>`. The `S2Client` reads `S2_API_KEY` from env first, then `SEMANTIC_SCHOLAR_API_KEY`.

## 3. Rate limits

| Status | Limit |
|---|---|
| With API key | 1 RPS across **all** endpoints (some users get higher after review) |
| Without key | Shared 5,000 req / 5 min pool across all unauthenticated users |

The client retries on `429, 500, 502, 503, 504` with backoff + jitter and respects `Retry-After`. For long sweeps, optionally pass `min_interval=1.0` to throttle client-side.

## 4. Paper ID formats (`paper_id` is polymorphic)

| Format | Example |
|---|---|
| S2 paperId (40-char hex) | `649def34f8be52c8b66281af98ae884c09aef38b` |
| Corpus ID | `CorpusId:215416146` |
| DOI | `DOI:10.18653/v1/N18-3011` |
| arXiv | `ARXIV:2106.15928` |
| PubMed | `PMID:19872477` |
| PMC | `PMCID:2323736` |
| Microsoft Academic | `MAG:112218234` |
| ACL Anthology | `ACL:W12-3903` |
| URL | `URL:https://...` (limited to specific domains) |

The API resolves all of these without preprocessing. Pass them through unchanged.

Two paper identifiers in responses:

- `paperId` — string, primary identifier in the API and on the website.
- `corpusId` — int64, used by the Datasets bulk download files.

---

## 5. Search query syntax (relevance vs. bulk)

The two keyword endpoints differ in what they accept in `query`:

| Endpoint | Boolean syntax | Sort | Page size |
|---|---|---|---|
| `/paper/search` (relevance) | **No** — plain text only | by relevance only | up to 100 |
| `/paper/search/bulk` | **Yes** — full boolean grammar | paperId / publicationDate / citationCount | 1000/page, up to 10M total |
| `/snippet/search` | **No** — plain text only | by match score | up to 1000 |

### Bulk search operators

| Operator | Meaning | Example |
|---|---|---|
| (space) or `+` | AND (default) | `hippocampus replay` ≡ `hippocampus + replay` |
| `\|` | OR | `"place cells" \| "grid cells"` |
| `-` | NOT | `replay -review` |
| `*` | Wildcard suffix | `synap*` matches `synapse, synaptic, synaptogenesis, ...` |
| `~N` | Fuzzy (edit distance) | `fish~3` matches `fish, fist, fihs, ...` |
| `"..."` | Phrase | `"default mode network"` |
| `"..."~N` | Phrase distance | `"fish ladder"~3` allows up to 3 words between |
| `(...)` | Grouping | `("place cells" \| "grid cells") + entorhinal` |

Tokens are case-insensitive. Whitespace inside `"..."` is preserved as a phrase.

### Choosing relevance vs bulk vs match vs snippet

| Need | Endpoint | CLI |
|---|---|---|
| Top N most relevant (small N, deep nested fields) | `/paper/search` | `keyword_search.py` |
| Comprehensive sweep with filters / sort | `/paper/search/bulk` | `keyword_search.py --bulk` |
| Single best match for a known title | `/paper/search/match` | `title_match.py` |
| Find a paper from a remembered phrase | `/snippet/search` | `snippet_search.py` |

S2 uses a custom-trained ranker for `/paper/search`. For broad topic survey, relevance ranking generally beats sorting by citation count.

---

## 6. Filter values

These filters apply to `/paper/search` and `/paper/search/bulk`. They are passed as query parameters; multiple values use comma separation **without spaces**.

### `fieldsOfStudy`

S2 has two separate taxonomies:

- `fieldsOfStudy` — original (manually curated). **This is what you filter on.**
- `s2FieldsOfStudy` — auto-classified, finer-grained. Cannot filter on this directly.

#### Allowed values

`Computer Science, Medicine, Chemistry, Biology, Materials Science, Physics, Geology, Psychology, Art, History, Geography, Sociology, Business, Political Science, Economics, Philosophy, Mathematics, Engineering, Environmental Science, Agricultural and Food Sciences, Education, Law, Linguistics`

S2 has no top-level "Neuroscience" bucket. Neuro work spans `Biology`, `Medicine`, and `Psychology`. Skill default is `Biology,Medicine,Psychology`. Override with `--fields-of-study ""` to disable filtering.

### `publicationTypes`

`Review, JournalArticle, CaseReport, ClinicalTrial, Conference, Dataset, Editorial, LettersAndComments, MetaAnalysis, News, Study, Book, BookSection`

Combine with comma: `JournalArticle,Review,MetaAnalysis`.

### `year`

| Form | Meaning |
|---|---|
| `2020` | exactly 2020 |
| `2018-2024` | range, inclusive |
| `2018-` | from 2018 onward |
| `-2010` | up to and including 2010 |

### `publicationDateOrYear`

Like `year` but supports day-precision dates: `2020-01-01:2024-06-30`, `2018-06-01:`, `:2010-12-31`. Mixed forms also accepted.

### `venue`

Comma-separated list of venue names as they appear in the paper's `venue` field. Match is exact-string. Example: `Nature,Nature Neuroscience,Neuron,Cell` or `eLife`.

### `openAccessPdf`

Presence-only flag. In the URL it appears as `&openAccessPdf` with no value. The client sends it as `&openAccessPdf=` (empty value), which the API treats as truthy.

### `minCitationCount`

Integer. Filters to papers with at least this many citations.

---

## 7. The `fields` parameter

Comma-separated list (no spaces) of response fields. Limit `fields` to what you need — extra fields slow responses noticeably at scale.

### Always returned by default

| Endpoint family | Fields |
|---|---|
| Paper | `paperId` (and `title` when no `fields` given) |
| Author | `authorId` (and `name` when no `fields` given) |
| Recommendations | `paperId` (and `title` when no `fields` given) |

### Dot notation for nested objects

For `embedding`, `authors`, `citations`, `references`, and (under `/author/...`) `papers`, select subfields with `parent.subfield`:

| Pattern | Returns |
|---|---|
| `authors` | each author with `authorId, name` (defaults) |
| `authors.url,authors.paperCount` | each author with `authorId, name, url, paperCount` |
| `citations` | each citation with `paperId, title` (defaults) |
| `citations.title,citations.abstract` | each citation with `paperId, title, abstract` |
| `embedding` | SPECTER v1 embedding |
| `embedding.specter_v2` | SPECTER v2 embedding |

### Common paper response fields

| Field | Type | Notes |
|---|---|---|
| `paperId` | string | S2 native ID, 40-char hex |
| `corpusId` | int | Secondary ID, used by Datasets API |
| `title` | string | |
| `abstract` | string | Absent for Springer papers (license restriction) |
| `tldr` | object `{model, text}` | One-sentence summary, ML-generated |
| `venue` | string | Display venue name |
| `publicationVenue` | object | Structured venue (id, name, type, alternate names, ISSN) |
| `year` | int | |
| `publicationDate` | string `YYYY-MM-DD` | |
| `publicationTypes` | array<string> | Values from the `publicationTypes` taxonomy |
| `journal` | object | `{name, volume, pages}` |
| `authors` | array<object> | `{authorId, name}` by default |
| `citationCount` | int | |
| `influentialCitationCount` | int | Per S2's influential-citation classifier |
| `referenceCount` | int | |
| `isOpenAccess` | bool | |
| `openAccessPdf` | object | `{url, status, license, disclaimer}` if available |
| `externalIds` | object | `{DOI, ArXiv, PubMed, PubMedCentral, MAG, ACL, DBLP, CorpusId}` |
| `fieldsOfStudy` | array<string> | Original taxonomy |
| `s2FieldsOfStudy` | array<object> | `{category, source}` — finer-grained |
| `embedding` | object | `{model, vector}` — SPECTER |
| `citations` | array | Sub-papers (use dot notation for subfields) |
| `references` | array | Sub-papers (use dot notation for subfields) |

### Common author response fields

`authorId, name, aliases, affiliations, homepage, paperCount, citationCount, hIndex, url`

### Edge fields (citations / references endpoints)

Each item in `data` is an edge object:

| Field | Type | Notes |
|---|---|---|
| `contexts` | array<string> | Snippets of text where the citation appears |
| `intents` | array<string> | Values from `{background, methodology, result}` |
| `contextsWithIntent` | array<object> | Each `{context, intent}` together |
| `isInfluential` | bool | |
| `citingPaper` or `citedPaper` | object | The other end of the edge — use dot notation for its subfields |

### Embedding versions

Default for `embedding` is SPECTER v1. Specify `embedding.specter_v2` for v2 vectors. SPECTER v2 is the current S2 recommendation.

---

## 8. Response envelopes

### Relevance / author search (offset-paginated)

```json
{
  "total": 8471, "offset": 0, "next": 100,
  "data": [ { "paperId": "...", ... }, ... ]
}
```

Iterate by incrementing `offset` until `next` is absent or `len(data) == 0`.

### Bulk search (token-paginated)

```json
{
  "total": 12345, "token": "abc...",
  "data": [ ... up to 1000 papers ... ]
}
```

Iterate by passing the returned `token` back as a query parameter until `token` is absent.

### Citations / references (offset-paginated, edges)

```json
{
  "offset": 0, "next": 100,
  "data": [
    { "contexts": [...], "intents": [...], "isInfluential": false,
      "citingPaper": { "paperId": "...", ... } }
  ]
}
```

The edge object contains either `citingPaper` (for `/citations`) or `citedPaper` (for `/references`).

### Recommendations (no pagination)

```json
{ "recommendedPapers": [ { "paperId": "...", ... } ] }
```

### Batch (POST `/paper/batch`, `/author/batch`)

The response is a **list aligned to the input order**. Missing IDs are returned as `null`.

---

## 9. Status codes worth handling

| Code | Meaning |
|---|---|
| 200 | OK |
| 400 | Bad query parameters — check field names and filter syntax |
| 404 | Paper/author not found, or no result for `/paper/search/match` |
| 429 | Rate-limited — client retries with backoff automatically |
| 500-504 | Transient — client retries automatically |

---

## 10. Querying `endpoints.db`

Structured catalog of every S2 endpoint, regenerable from cached OpenAPI specs.

```bash
sqlite3 references/semantic-scholar/data/endpoints.db
```

Common queries:

```sql
-- All endpoints in the Graph API, with categories.
SELECT path, method, category, summary FROM endpoints WHERE api = 'graph';

-- All parameters of the bulk search endpoint.
SELECT json_extract(value, '$.name') AS name,
       json_extract(value, '$.description') AS description
FROM endpoints, json_each(parameters_json)
WHERE path = '/paper/search/bulk';

-- Endpoints that accept a 'sort' parameter.
SELECT path, method FROM endpoints WHERE parameters_json LIKE '%"name": "sort"%';

-- Endpoints that take a path parameter (i.e. need an ID).
SELECT path FROM endpoints WHERE parameters_json LIKE '%"in": "path"%';

-- Allowed values for fieldsOfStudy.
SELECT value, description FROM filter_values WHERE category = 'fieldsOfStudy';
```

### Refreshing from upstream

```bash
cd references/semantic-scholar/data
curl -s https://api.semanticscholar.org/graph/v1/swagger.json -o raw/graph_swagger.json
curl -s https://api.semanticscholar.org/recommendations/v1/swagger.json -o raw/recommendations_swagger.json
python build_endpoints_db.py
```

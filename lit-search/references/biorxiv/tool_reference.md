# bioRxiv — Tool Reference

Seven tools exposed via the `mcp__bioRxiv.*` namespace. Coverage:

- **bioRxiv** (`server="biorxiv"`) — biological-sciences preprints (Cold Spring Harbor).
- **medRxiv** (`server="medrxiv"`) — medical / health-sciences preprints.

Both servers host **non-peer-reviewed** preprints. Disclose this when summarising results.

> **Read `usage_guide.md` first.** This engine is structurally different from PubMed / Semantic Scholar / Consensus — `search_preprints` is **date+category only** with no keyword filter. Treating it as a topic-search engine yields the wrong tool for the job.

---

## Tools at a glance

| Family | Tool | Use for |
|---|---|---|
| Discovery | `search_preprints` | Recent submissions in a category (no keyword filter) |
| Discovery | `search_published_preprints` | Preprints that have since been peer-reviewed |
| Discovery | `search_by_funder` | Preprints by funding source (post-2025-04-10 only) |
| Retrieval | `get_preprint` | DOI → full record (the retrieval workhorse) |
| Identity | `get_categories` | Enumerate the 27 valid category values |
| Stats | `get_content_statistics` | Submission/revision/author totals over time |
| Stats | `get_usage_statistics` | View / download counts over time |

`search_preprints` and `get_preprint` are the workhorses. The rest are either niche or supporting glue.

---

## `search_preprints` — recent submissions, **no keyword filter**

The single biggest gotcha. Filters by date range and category only. There is no `query` parameter. The tool description states this explicitly under `LIMITATIONS`.

### Parameters

| Param | Default | Notes |
|---|---|---|
| `category` | `null` | One of 27 enum values (use `get_categories` for the live list). |
| `date_from`, `date_to` | both `null` | `YYYY-MM-DD`. **Hyphens, not slashes** (opposite of PubMed). |
| `recent_days` | `null` | Last N days. Alternative to date range. |
| `recent_count` | `null` | Searches a 90-day window, returns up to `limit` results. |
| `limit` | `10` | 1–100 per the schema; **actual returned ≈ 30** regardless of value (verified empirically). |
| `cursor` | `0` | Pagination — `cursor=30` for the next batch (NOT 100, see usage_guide). |
| `server` | `biorxiv` | Or `medrxiv`. |

Default if no date method specified: last 60 days.

### Categories (27)

`animal behavior and cognition`, `biochemistry`, `bioengineering`, `bioinformatics`, `biophysics`, `cancer biology`, `cell biology`, `clinical trials`, `developmental biology`, `ecology`, `epidemiology`, `evolutionary biology`, `genetics`, `genomics`, `immunology`, `microbiology`, `molecular biology`, `neuroscience`, `paleontology`, `pathology`, `pharmacology and toxicology`, `physiology`, `plant biology`, `scientific communication and education`, `synthetic biology`, `systems biology`, `zoology`.

For neuroscience-focused work, `neuroscience` and `animal behavior and cognition` are the primary buckets; computational-neuroscience methods sometimes appear in `bioinformatics` or `systems biology`.

### Return shape (per result)

```json
{
  "doi": "10.1101/2024.01.15.123456",
  "title": "...",
  "authors": "Smith, J.; Jones, A.; ...",
  "date": "2024-01-15",
  "category": "neuroscience",
  "version": "1",
  "abstract_preview": "First ~200 chars of abstract..."
}
```

`abstract_preview` is truncated. For the full abstract + author list + PDF URL, follow up with `get_preprint(doi)`.

---

## `get_preprint` — DOI → full record

The retrieval workhorse. Once you have a bioRxiv DOI from another engine (Semantic Scholar, Tavily, Consensus), this returns the rich record.

### Parameters

| Param | Default | Notes |
|---|---|---|
| `doi` | required | `10.1101/<date>.<id>` or `https://doi.org/10.1101/...` (both forms accepted). |
| `server` | `biorxiv` | Or `medrxiv`. Must match the server the DOI lives on. |

### Return shape

```json
{
  "doi": "...",
  "title": "...",
  "authors": "Smith, J.; Jones, A.; ...",
  "author_corresponding": "Jane Doe",
  "author_corresponding_institution": "Vanderbilt University",
  "date": "2026-04-05",
  "version": "1",
  "type": "new results",
  "category": "neuroscience",
  "license": "cc_by",
  "abstract": "...full text...",
  "jatsxml": "https://www.biorxiv.org/.../source.xml",
  "funding": null,
  "published_doi": "NA",
  "server": "bioRxiv",
  "pdf_url": "https://www.biorxiv.org/content/.../v1.full.pdf",
  "web_url": "https://www.biorxiv.org/content/.../v1"
}
```

Three fields are uniquely valuable:

- `published_doi` — non-`"NA"` value means the preprint has been published in a peer-reviewed venue. Surface this to the user; many readers prefer the published version.
- `license` — `cc_by`, `cc_by_nc`, `cc_by_nc_nd`, etc. govern reuse. PubMed's `get_copyright_status` does not cover preprints; this is the source of truth for bioRxiv license.
- `pdf_url` — direct, no auth needed. Pass to a PDF fetcher / `tavily_extract` for body text.

---

## `search_published_preprints` — preprint-to-publication tracking

Find preprints that have subsequently been published in peer-reviewed journals.

### Parameters

| Param | Default | Notes |
|---|---|---|
| `date_from`, `date_to` | none | `YYYY-MM-DD`. |
| `recent_days`, `recent_count` | none | Same semantics as `search_preprints`. |
| `publisher` | `null` | DOI prefix filter, e.g. `10.1038` for Nature. |
| `include_details` | `true` | `true` = full metadata; `false` = summary only (faster). |
| `limit` | `10` | 1–100. |
| `server` | `biorxiv` | Or `medrxiv`. |

### Common publisher DOI prefixes

| Prefix | Publisher |
|---|---|
| `10.1038` | Nature Publishing Group |
| `10.1126` | Science / AAAS |
| `10.1016` | Elsevier |
| `10.1371` | PLOS |
| `10.7554` | eLife |
| `10.1073` | PNAS |

---

## `search_by_funder` — funder ROR ID → preprints

Funder metadata only exists for preprints submitted on or after **2025-04-10**.

### Parameters

| Param | Notes |
|---|---|
| `funder_ror_id` | 9-character ROR ID (required) |
| `date_from` | `YYYY-MM-DD`, must be ≥ 2025-04-10 (required) |
| `date_to` | `YYYY-MM-DD` (required) |
| `category` | One of the 27 enum values |
| `limit`, `cursor`, `server` | Standard |

### Common ROR IDs

| ROR ID | Funder |
|---|---|
| `021nxhr62` | NIH |
| `01cwqze88` | NSF |
| `02mhbdp94` | European Commission |
| `029chgv08` | Wellcome Trust |
| `05a28rw58` | HHMI |
| `006wxqw41` | UK MRC |
| `00f54p054` | UK BBSRC |
| `01s5ya894` | Chan Zuckerberg Initiative |

Look up others at https://ror.org/search.

---

## `get_categories` — list valid category enum values

No-arg utility. Returns the 27 categories with their API-formatted names. Useful only if enum drift between docs and the live API matters; the enum is also embedded in `search_preprints`'s schema.

---

## `get_content_statistics`, `get_usage_statistics` — platform metrics

Submission/usage time series, monthly or yearly. Almost never needed for actual literature search — flag if the user asks about platform-level adoption trends.

---

## Rate limits

Not advertised. Underlying bioRxiv API is generous in practice. No retry/backoff specifics surfaced — paginate sequentially and stop on empty results.

---

## What this engine is good at vs. bad at

| Need | bioRxiv tool | Verdict |
|---|---|---|
| Topic search ("find papers about X") | none | ❌ — use S2 / Tavily / PsyArxiv (for psych) |
| Recent submissions in a category | `search_preprints` | ✅ |
| Full record by DOI | `get_preprint` | ✅ — best in class for preprints |
| Citation graph | none | ❌ — use S2 |
| Author search | none | ❌ — use S2 |
| Funder tracking (post-2025-04-10) | `search_by_funder` | ✅ — unique to this engine |
| Preprint → published-version tracking | `search_published_preprints` + `get_preprint.published_doi` | ✅ — unique to this engine |
| Full-text PDF | `get_preprint.pdf_url` then fetcher | ✅ — direct, no auth |
| Platform-level stats | `get_*_statistics` | ✅ — niche but unique |

# PsyArxiv — Tool Reference

PsyArxiv is the psychology preprint server hosted on OSF. The pathway has both a Python client (`scripts/psyarxiv/osf_client.py`) and CLI examples (`scripts/psyarxiv/examples/`); this reference covers the OSF JSON:API v2 surface they wrap, scoped to `filter[provider]=psyarxiv`.

> **Read `usage_guide.md` first.** The OSF Preprints endpoint has **no full-text search** (`filter[q]` returns 400). Keyword discovery is restricted to substring matches against `title`, `description`, or `tags` — read the search-strategy section before trying topic-driven discovery.

## Table of contents

1. Base URL and authentication
2. JSON:API envelope
3. Pagination
4. Errors
5. Versioning
6. The `/preprints/` filter surface (empirically validated)
7. Operator suffixes
8. Response shape (preprint attributes, relationships, links)
9. Sparse fieldsets
10. Embedding semantics

---

## 1. Base URL and authentication

```
Base URL: https://api.osf.io/v2
```

PsyArxiv content is exposed via the standard `/preprints/` endpoint with `filter[provider]=psyarxiv`.

Authentication: Bearer token in the `Authorization` header.

```
Authorization: Bearer $OSF_TOKEN
```

The token is a Personal Access Token created at https://osf.io/settings/tokens. For preprint discovery, the `osf.full_read` scope suffices. The OSF Preprints list endpoint also serves anonymous traffic, but rate limits are tighter and some attributes (`current_user_permissions`) are absent — always send the token if available.

---

## 2. JSON:API envelope

Every list response:

```json
{
  "data": [
    {
      "type": "preprints",
      "id": "fu6de_v1",
      "attributes": { "title": "...", "date_published": "...", ... },
      "relationships": { "contributors": {...}, "provider": {...}, ... },
      "links": { "html": "...", "preprint_doi": "...", "self": "..." }
    },
    ...
  ],
  "links": {
    "first": "...", "last": "...", "prev": null, "next": "...",
    "meta": { "total": 58382, "per_page": 100 }
  },
  "meta": { "version": "2.0" }
}
```

Detail responses (`/preprints/{id}/`) return the same envelope with `data` as a single object.

Content type: `application/vnd.api+json; charset=utf-8`. Send `Accept: application/vnd.api+json` to be polite.

---

## 3. Pagination

Link-based, not offset-based. `links.next` is a fully-qualified URL — follow it directly. `links.meta.total` gives the row count.

`page[size]` is **capped at 100** server-side; values above 100 silently cap. Default is 10.

---

## 4. Errors

JSON:API standard envelope:

```json
{
  "errors": [
    { "source": { "parameter": "filter" },
      "detail": "'q' is not a valid field for this endpoint.",
      "status": "400", "meta": {} }
  ],
  "meta": { "version": "2.0" }
}
```

Always parse `errors[*].detail` for the human-readable cause.

---

## 5. Versioning

Query-string versioning: `?version=2.20`. Default is `2.0` (echoed in `meta.version`). The server does **not** echo an `X-OSF-Version` response header even when one is requested — don't rely on header-based version inspection.

In practice this pathway pins nothing; the preprint endpoint surface has been stable.

---

## 6. The `/preprints/` filter surface

Empirically validated against the live API. When in doubt, the `'X' is not a valid field for this endpoint.` 400 response is authoritative.

### Always include

```
filter[provider]=psyarxiv
```

Without this filter, the endpoint returns the union of all OSF preprint providers (~30 of them, dominated by EngrXiv, EarthArxiv, etc.) — not what this skill wants. The client hard-codes `provider=psyarxiv` on construction.

### Valid filter fields

| Field | Type | Notes |
|---|---|---|
| `title` | string substring | **Phrase-ordered substring**, default icontains. `working memory` → 668 hits, `memory working` → 0. |
| `description` | string substring | Substring on abstract. `delay discounting` → 93 hits. |
| `tags` | string substring | Substring on free-text tag list. `fmri` → 459 hits. |
| `subjects` | string OR uuid | `Aging` and `5b4e7427c6983001430b6c98` both return the same 272 hits. |
| `doi` | exact | DOI string match. |
| `id` | exact | Preprint GUID (5-char). |
| `provider` | exact | Provider id; pin to `psyarxiv`. |
| `date_published` | ISO8601 | Use `[gte]` / `[lte]` operator suffixes. |
| `date_modified` | ISO8601 | Operator suffixes work. |
| `date_created` | ISO8601 | Filter works; **sort on this field returns 502** (server bug). |
| `date_withdrawn` | ISO8601 | Most preprints have this null. |
| `is_published` | bool | `true` / `false`. |
| `is_preprint_orphan` | bool | Filter to non-orphans with `false`. |
| `reviews_state` | enum | Common values: `accepted`, `pending`, `rejected`, `withdrawn`. |
| `node` | uuid | OSF project node id. |
| `contributors` | uuid | OSF user id. |
| `preprint_doi_created` | ISO8601 | When the DOI was minted. |
| `has_coi` | bool | Conflict-of-interest declaration present. |
| `has_data_links` | bool | Data sharing links declared. |
| `license` | uuid | License record id. |
| `version` | int | Version number (1, 2, …). |

### Invalid filter fields (will 400)

- `q` — there is no full-text search. See `usage_guide.md`.
- `abstract` — use `description` instead.

---

## 7. Operator suffixes

JSON:API operator syntax: `filter[<field>][<op>]=<value>`.

| Operator | Behavior | Example |
|---|---|---|
| (none) | Default — equivalent to `icontains` for string fields. | `filter[title]=memory` |
| `eq` | Exact equality. `filter[title][eq]=working memory` returns 0. |
| `ne` | Not equal. |
| `contains` | Case-sensitive substring. `[contains]=memory` → 1,198. |
| `icontains` | Case-insensitive substring. `[icontains]=memory` → 2,075. |
| `gte` | `>=`, ISO date or number. |
| `lte` | `<=`, ISO date or number. |

Filters AND together server-side. There is no OR operator at the API level — to OR over multiple terms or fields, issue parallel requests and deduplicate by `id` client-side. `examples/search_preprints.py --any` does term-level OR over a single field.

### Canonical example

```
GET /v2/preprints/?
  filter[provider]=psyarxiv&
  filter[title]=working memory&
  filter[date_published][gte]=2026-01-01&
  sort=-date_published&
  page[size]=100&
  fields[preprints]=title,description,doi,date_published,subjects,tags
```

---

## 8. Response shape

### Preprint attributes (full set, 30 fields)

```
conflict_of_interest_statement   custom_publication_citation   data_links
date_created                     date_last_transitioned         date_modified
date_published                   date_withdrawn                 default_license_id
description                      doi                            has_coi
has_data_links                   has_prereg_links               is_latest_version
is_preprint_orphan               is_published                   license_record
original_publication_date        preprint_doi_created           prereg_link_info
prereg_links                     public                         reviews_state
subjects                         tags                           title
version                          why_no_data                    why_no_prereg
current_user_permissions
```

Most-used fields:

- `title`, `description` (abstract), `doi`, `date_published`, `date_modified`
- `tags` — list of strings (author-supplied)
- `subjects` — **list of lists**. Each inner list is a taxonomy hierarchy walked from root to leaf. Example:
  ```json
  [[{"id": "...", "text": "Social and Behavioral Sciences"},
    {"id": "...", "text": "Quantitative Methods"},
    {"id": "...", "text": "Psychometrics"}]]
  ```
  `osf_client.flatten_preprint()` keeps only the leaf text from each cluster.
- `reviews_state` — enum: `accepted` / `pending` / `rejected` / `withdrawn`.
- `is_latest_version` / `version` — preprint versioning. Latest carries `is_latest_version: true`. Lookups by bare `id` resolve to the latest with `f00ba_v3`-style suffix.

### Relationships (13 keys)

```
affiliated_institutions   bibliographic_contributors   citation
contributors              files                        identifiers
license                   node                         primary_file
provider                  requests                     review_actions
versions
```

Each relationship is a `{links: {related: ..., self: ...}}` block by default. To pull the related entities inline, use `embed=` (see section 10).

### Top-level links

| Field | Notes |
|---|---|
| `html` | Public OSF page URL (https://osf.io/preprints/psyarxiv/<id>/) |
| `iri` | Same, IRI form |
| `preprint_doi` | DOI URL once minted (https://doi.org/10.31234/osf.io/<id>) |
| `self` | JSON:API self link |

`html` and `preprint_doi` are the two URLs you want for citation/output.

---

## 9. Sparse fieldsets

```
fields[preprints]=title,description,doi,date_published,subjects,tags
```

Reduces a 100-record page from ~300 KB to ~30 KB. **Mandatory for any non-detail call.**

`osf_client.DEFAULT_PREPRINT_FIELDS`:

```
title, description, doi, date_published, date_modified,
subjects, tags, is_published, reviews_state, preprint_doi_created
```

---

## 10. Embedding

`embed=<relationship>` inlines a relationship's data into the response. Example: `embed=contributors` on `/preprints/{id}/`.

**Quirk**: `embed=contributors` on the **list endpoint** returns only the `links` block — the `embeds` payload is empty. For full contributor data on a list of papers, you must call `/preprints/{id}/contributors/` separately for each. The `preprint_lookup.py` example does this follow-up automatically.

Multiple embeds: `embed=contributors&embed=primary_file`. JSON:API also accepts comma-separated: `embed=contributors,license`.

### Contributor entity (`/preprints/{id}/contributors/`)

```json
{
  "type": "contributors",
  "id": "fu6de_v1-wqp29",
  "attributes": {
    "bibliographic": true,
    "permission": "write",
    "index": 0,
    "unregistered_contributor": null
  },
  "embeds": {
    "users": {
      "data": {
        "id": "wqp29",
        "attributes": { "full_name": "Sonia Bansal", ... }
      }
    }
  }
}
```

`bibliographic: true` means the contributor appears in the cite-as author list. `permission` is `read` / `write` / `admin` and reflects the OSF project ACL, not authorship order. `index` is the bibliographic position when `bibliographic` is true.

# Semantic Scholar — `/scripts/semantic-scholar/`

The Semantic Scholar pathway for the `lit-search` skill. Importable client + thin CLI examples; reference materials live at the skill root.

## Layout

```
scripts/semantic-scholar/
├── s2_client.py              # core: S2Client, default fields, taxonomies
├── examples/                 # CLI wrappers — call s2_client, print JSON to stdout
│   ├── keyword_search.py     # /paper/search (auto-routes to /paper/search/bulk)
│   ├── author_search.py      # /author/search — name -> authorId
│   ├── author_papers.py      # /author/{id}/papers (paginated)
│   ├── recommend_from_paper.py   # /recommendations/v1/papers/forpaper/{id}
│   ├── recommend_from_pool.py    # POST /recommendations/v1/papers/ with positive+negative
│   ├── paper_lookup.py       # /paper/{id} — accepts DOI, PMID, ARXIV, etc.
│   ├── paper_batch.py        # POST /paper/batch — bulk fetch by ID
│   ├── title_match.py        # /paper/search/match — resolve title -> S2 paperId
│   ├── citations.py          # /paper/{id}/citations or /references
│   └── snippet_search.py     # /snippet/search — full-text snippet match
├── .env.example
├── requirements.txt
└── README.md (this file)
```

Reference documentation for this engine lives at the skill root:

```
../../references/semantic-scholar/
├── tool_reference.md         # auth, search syntax, filter values, fields, response envelopes
├── usage_guide.md            # neuroscience defaults, recipe templates, gotchas, release notes
└── data/
    ├── endpoints.db          # SQLite catalog (16 endpoints, 47 filter values)
    ├── build_endpoints_db.py # rebuilds endpoints.db from raw/*.json
    └── raw/
        ├── graph_swagger.json
        └── recommendations_swagger.json
```

## Setup

The lit-search skill uses a shared venv at `scripts/.venv/` (one level up). Set it up once with:

```bash
# from the lit-search skill root:
python3 -m venv scripts/.venv
scripts/.venv/bin/pip install -r scripts/requirements.txt
```

Credentials are read from the shell environment:

```bash
export S2_API_KEY=<your-key>     # or copy .env.example -> .env (auto-loaded)
```

## Quick test

```bash
# from the lit-search skill root:
scripts/.venv/bin/python scripts/semantic-scholar/examples/paper_lookup.py DOI:10.1038/nature14066 --fields paperId,title,year,tldr
```

## Routing decision (for skill use)

| User intent | Script |
|---|---|
| "Find papers about X" (small N, rich data) | `keyword_search.py` |
| "Find papers about X" (large N, with filters/sort) | `keyword_search.py --bulk --max N` |
| "Find papers by author Y" | `author_search.py "Y"` then `author_papers.py <authorId>` |
| "More like this paper" (one seed) | `recommend_from_paper.py <id>` |
| "More like these papers" (curated set) | `recommend_from_pool.py --pos-file ...` |
| "Look up this paper by DOI / PMID / arXiv" | `paper_lookup.py <id>` |
| "Get details for many IDs" | `paper_batch.py --id-file ...` |
| "Find the S2 ID for a paper title" | `title_match.py "Title..."` |
| "Show citations / references of paper X" | `citations.py <id> --direction citing\|referenced` |
| "I remember a phrase, find the paper" | `snippet_search.py "..."` |

## When the skill is uncertain about a parameter

Two paths depending on the question shape:

### Structured lookup (fast)

Query the SQLite catalog at `../../references/semantic-scholar/data/endpoints.db`:

```bash
sqlite3 ../../references/semantic-scholar/data/endpoints.db \
  "SELECT path, method, summary FROM endpoints WHERE path LIKE '%bulk%';"

sqlite3 ../../references/semantic-scholar/data/endpoints.db \
  "SELECT json_extract(value,'$.name') AS name, json_extract(value,'$.description') AS d
   FROM endpoints, json_each(parameters_json)
   WHERE path = '/paper/search/bulk';"
```

### Prose-heavy answer

- `../../references/semantic-scholar/tool_reference.md` — full API surface (search syntax, filter values, response shapes).
- `../../references/semantic-scholar/usage_guide.md` — neuroscience defaults, recipes, gotchas.

# PsyArxiv (OSF API v2) — `/scripts/psyarxiv/`

The PsyArxiv pathway for the `lit-search` skill. PsyArxiv is the psychology preprint server hosted on OSF; this folder wraps the OSF JSON:API v2 surface so the skill can query it without a dedicated MCP server.

This pathway is the **psychology counterpart to bioRxiv**. The two together cover the "Latest" mode in `SKILL.md`.

## Critical constraint

The OSF `/preprints/` endpoint **has no full-text search** (no `filter[q]`). Keyword discovery is restricted to substring matches against `title`, `description`, or `tags`. This drives every design choice in this folder. For the full reasoning and the synonym fan-out workaround, read `../../references/psyarxiv/usage_guide.md` first.

## Layout

```
scripts/psyarxiv/
├── osf_client.py            # core: OSFClient, default fields, pagination, flatten_preprint
├── examples/                # CLI wrappers — each calls osf_client and prints JSON
│   ├── search_preprints.py  # filter[title|description|tags] + date range + sort
│   ├── recent_preprints.py  # sort=-date_published feed; bioRxiv counterpart
│   ├── preprint_lookup.py   # GET /preprints/{id}/ + contributors follow-up
│   └── list_subjects.py     # enumerate the 234-row bepress taxonomy (with --dump cache)
├── .env.example
├── requirements.txt         # stdlib only — kept for parity with sibling pathways
└── README.md (this file)
```

Reference documentation for this engine lives at the skill root:

```
../../references/psyarxiv/
├── tool_reference.md        # auth, JSON:API envelope, filter fields, operators, response shape
├── usage_guide.md           # search strategy, synonym fan-out, subjects taxonomy, gotchas
└── data/
    └── psyarxiv_subjects.json   # 234-row cached taxonomy, refresh with list_subjects.py --dump
```

## Setup

```bash
export OSF_TOKEN=...    # required; the client raises if missing
```

`osf_client.py` uses only the Python standard library (`urllib`, `json`), so no third-party install is needed. The lit-search skill nevertheless invokes these scripts through the shared venv at `scripts/.venv/bin/python` (see SKILL.md "Runtime setup") for invocation symmetry with the Semantic Scholar pathway.

## Quick test

All commands below run from the lit-search skill root:

```bash
# newest 5 PsyArxiv preprints in the last day
scripts/.venv/bin/python scripts/psyarxiv/examples/recent_preprints.py --days 1 --limit 5

# title search with date floor
scripts/.venv/bin/python scripts/psyarxiv/examples/search_preprints.py --title "working memory" --date-from 2026-01-01 --limit 10

# OR fan-out for synonym keyword approximation
scripts/.venv/bin/python scripts/psyarxiv/examples/search_preprints.py \
  --any "working memory,short-term memory,WM capacity" \
  --any-field title --date-from 2026-01-01 --limit 20

# single-paper lookup with contributors (5-char OSF GUID, optionally _vN)
scripts/.venv/bin/python scripts/psyarxiv/examples/preprint_lookup.py fu6de --flat

# count without fetching rows
scripts/.venv/bin/python scripts/psyarxiv/examples/search_preprints.py --description "delay discounting" --count-only

# refresh subjects taxonomy cache
scripts/.venv/bin/python scripts/psyarxiv/examples/list_subjects.py --dump references/psyarxiv/data/psyarxiv_subjects.json
```

## Routing decision (for skill use)

Use this pathway when:

- The user wants **recent** psychology preprints (combine with bioRxiv in Latest mode).
- The user names a specific PsyArxiv ID or DOI (preprint_lookup.py).
- The query has a clean topic-term likely to appear in titles.
- A bounded date sweep with subject restriction is wanted.

Route elsewhere when:

- The user wants **full-text** keyword search across psych preprints — use Tavily with `include_domains=["psyarxiv.com"]` (see `../../references/tavily/usage_guide.md`).
- The user wants peer-reviewed psych literature — use Semantic Scholar with fields-of-study filter, or PubMed for clinical psych.

## When the skill is uncertain about a parameter

Read the consolidated reference docs at the skill root:

- `../../references/psyarxiv/tool_reference.md` — confirm a filter field is supported and learn the operator suffixes.
- `../../references/psyarxiv/usage_guide.md` — answers "is keyword search even possible?" and shows the synonym fan-out pattern.

For unfamiliar response field names, the response-shape section is in `tool_reference.md` (section 8).

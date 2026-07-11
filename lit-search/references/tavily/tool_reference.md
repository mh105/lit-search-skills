# Tavily — Tool Reference

Five tools exposed via the `mcp__tavily.*` namespace. They split into two families:

- **Discovery** — `tavily_search`, `tavily_research` (turn a query into ranked results / a synthesised answer)
- **Retrieval** — `tavily_extract`, `tavily_crawl`, `tavily_map` (turn a known URL into structured content)

Always reach for a discovery tool first, then a retrieval tool to harvest the hits worth reading in full.

> **Read `usage_guide.md` first.** Tavily's parameter tuning (especially `include_domains` for source targeting and `search_depth` selection) drives result quality more than any other knob. Default neuroscience domain allowlists are also documented there.

---

## `tavily_search` — single-shot ranked web search

The workhorse. One query in, a ranked list of `{title, url, content, score}` out. Use this for the vast majority of literature lookups.

### Parameters

| Param | Default | Notes |
|---|---|---|
| `query` | required | Natural-language or keyword string. See `usage_guide.md`. |
| `search_depth` | `basic` | `basic` (cheap, ~5 results), `advanced` (deeper crawl, better recall), `fast` (low-latency, decent relevance), `ultra-fast` (latency over quality). For paper hunting, prefer `advanced`. |
| `max_results` | `5` | Up to ~20 in practice. Bump to 10–15 when sweeping a topic. |
| `topic` | `general` | Locked to `general` in this MCP build — older docs reference `news`/`finance`, those are not exposed here. |
| `include_domains` | `[]` | Allowlist. Critical for scholar/PubMed/preprint targeting (see `usage_guide.md`). |
| `exclude_domains` | `[]` | Useful to suppress aggregators (e.g. `researchgate.net` link-farms, `semanticscholar.org` when you already have S2 results). |
| `time_range` | `null` | `day` / `week` / `month` / `year`. Coarse but fast. |
| `start_date`, `end_date` | `""` | `YYYY-MM-DD`. Use these for paper-year filters; they override `time_range`. |
| `exact_match` | `null` | When `true`, the query string (or quoted phrases inside it) must appear verbatim. Useful for exact title lookups. |
| `include_raw_content` | `false` | Set `true` to get the cleaned HTML body inline — saves a follow-up `tavily_extract` call when results are short pages. |
| `include_images`, `include_image_descriptions` | `false` | Almost never useful for literature work. |
| `country` | `""` | Boost results from a country. Irrelevant for lit search. |

### Return shape (per result)

```json
{
  "title": "...",
  "url": "https://...",
  "content": "snippet, ~300-500 chars",
  "score": 0.0-1.0,
  "raw_content": "..."   // only if include_raw_content=true
}
```

`score` is Tavily's relevance ranking, not a citation count. Don't confuse it with S2's `citationCount`.

---

## `tavily_research` — multi-source synthesised research

Higher-level: takes a research *task description*, runs multiple internal searches, and returns a synthesised answer with sources. Rate-limited to **20 requests/minute**.

### Parameters

| Param | Default | Notes |
|---|---|---|
| `input` | required | Full task description in prose. The longer and more specific, the better. |
| `model` | `auto` | `mini` (narrow tasks, few subtopics, faster), `pro` (broad surveys, many subtopics, slower), `auto` (let Tavily pick). |

### When to use

- Survey-style questions: *"What are the leading hypotheses for the role of astrocyte calcium signalling in sleep regulation, with key papers since 2022?"*
- Multi-hop questions where one search isn't enough.
- When you want a *prose summary* with citations rather than a result list to scan yourself.

### When NOT to use

- Specific paper lookup by title or DOI — `tavily_search` with `exact_match=true` is faster and cheaper.
- Author-level questions ("what has Karl Friston published recently?") — Semantic Scholar's author endpoints are the right tool.
- Anything where you want raw results to feed into downstream dedup/ranking. `tavily_research` returns synthesised prose, not structured records.

---

## `tavily_extract` — URL → clean content

Given one or more URLs, returns cleaned page content. Use after `tavily_search` when the snippet isn't enough.

### Parameters

| Param | Default | Notes |
|---|---|---|
| `urls` | required | List of URLs. Batched in a single call. |
| `extract_depth` | `basic` | Use `advanced` for LinkedIn, paywalled-but-cached pages, or anything with tables/embedded content. |
| `format` | `markdown` | `markdown` is usually what you want; `text` strips structure. |
| `query` | `""` | If set, content chunks are reranked by relevance to this query — useful for long pages. |

### When to use

- Pulling abstract + intro from a journal landing page when the search snippet is thin.
- Reading a lab's "publications" page after a `tavily_search` hit on the lab homepage.
- Extracting body text from a preprint mirror.

---

## `tavily_crawl` — recursive site crawl

Starts from a root URL and follows links up to `max_depth`, returning content for each page. Heavier than `tavily_extract`.

### Parameters

| Param | Default | Notes |
|---|---|---|
| `url` | required | Root URL. |
| `max_depth` | `1` | How many link-hops from root. Stay at 1–2 unless you really need deep crawl. |
| `max_breadth` | `20` | Links per page. |
| `limit` | `50` | Hard cap on total pages. |
| `instructions` | `""` | Natural-language hint for what to keep, e.g. *"only follow links that look like individual paper pages"*. The crawler honours this surprisingly well. |
| `select_domains` | `[]` | Regex allowlist for domains. |
| `select_paths` | `[]` | Regex allowlist for URL paths, e.g. `/publications/.*`. |
| `allow_external` | `true` | Set `false` to stay on-site. |

### When to use

- Harvesting all papers from a single lab's publications page.
- Pulling a conference's full programme.
- Indexing a small documentation site.

### When NOT to use

- General lit search — `tavily_search` is much cheaper.
- Sites with anti-bot measures (Google Scholar itself, Sci-Hub mirrors). Use `tavily_search` with `include_domains` instead.

---

## `tavily_map` — site URL inventory (no content)

Same shape as `tavily_crawl` but returns only the *list of URLs* found, not their content. Cheap reconnaissance step before deciding what to extract.

### When to use

- "What pages does this lab homepage even have?" before committing to a crawl.
- Building a list of preprint URLs from a category index page.

### When NOT to use

- When you already know which page you want — go straight to `tavily_extract`.

---

## Rate limits and cost intuition

| Tool | Cost | Notes |
|---|---|---|
| `tavily_search` | cheapest | Spam freely. |
| `tavily_extract` | moderate | Cost scales with `len(urls)` and `extract_depth=advanced`. |
| `tavily_crawl` / `tavily_map` | expensive | Cost scales with `limit`. Set conservatively. |
| `tavily_research` | slow + 20 req/min cap | Treat as a "boss move" — use deliberately. |

A typical lit-search session uses 3–10 `tavily_search` calls, 1–3 `tavily_extract` follow-ups, and rarely a `tavily_research` call.

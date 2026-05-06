# Consensus — Usage Guide

This page covers two distinct concerns:

1. **Skill-level routing**: when to delegate to the higher-level skills (`consensus-literature-review`, `consensus-grant-finder`) vs calling the MCP directly.
2. **Direct-call patterns**: filter philosophy, cross-engine bridging, and edge cases for the times you do call the MCP directly.

For mandatory output formatting (inline cites, exact URLs, "Upgrade to Pro" footer), see `output_protocol.md`. For the parameter surface, see `tool_reference.md`.

---

## Skill-level routing — read this BEFORE making a raw MCP call

The Consensus MCP tool is the lowest rung. Two user-scope skills wrap it:

| Skill | When to invoke | What you get | Cost |
|---|---|---|---|
| `consensus-literature-review` | User wants depth/strategy/synthesis on a research topic | `.docx` literature review guide with framework analysis (PICO/SPIDER/Decomposition), sub-area breakdowns, priority reading order, key research groups, gaps, audit log | 5 / 10 / 20 sequential Consensus searches; minutes |
| `consensus-grant-finder` | User wants NIH funding scoping for a research idea | `.docx` grant overview: 5-facet positioning analysis, draft Significance/Innovation language, institute mapping, study sections, NOSIs, funded overlap, mechanism recommendations | 5 Consensus + 2 RePORTER + N NOSI fetches; minutes |
| **(none — direct MCP)** | Quick lookup, evidence question, cross-check, single-shot search | Inline markdown answer | 1 call; seconds |

### Decision tree

Apply in order. Stop at first match.

```
1. Grants / funding / NIH / NOSIs / institutes / "find money for my research"?
     → invoke `consensus-grant-finder`
     → DO NOT make a raw Consensus call. The skill orchestrates the searches.

2. The user explicitly says "literature review" / "lit review", or wants depth/
   strategy/synthesis on a research topic with a document deliverable?
     → invoke `consensus-literature-review`
     → DO NOT make a raw Consensus call.

3. Otherwise (quick paper list, evidence question, cross-check, simple lookup,
   contextual discussion, exploratory mode):
     → call `mcp__claude_ai_Consensus__search` directly
     → Apply the filter philosophy below and the citation rules in
       `output_protocol.md`.
```

### Trigger phrases — `consensus-literature-review`

Invoke on: "literature review on X", "I'm writing a paper on X", "help me research X", "I'm doing research on X", "build me a research guide on X", "lit review on X."

**Explicitly does NOT trigger** on: quick paper lookups, single evidence questions, cross-checks. Those are direct MCP.

### Trigger phrases — `consensus-grant-finder`

Invoke on: "find grants for my research idea", "what grants match my research", "help me find NIH funding", "grant opportunities for my research", "where should I apply for funding to study X", "what NOSIs are open for X", "match my idea to NIH institutes."

**Explicitly does NOT trigger** on: papers about funding policies (that's literature, not grant scoping).

### Why the wrapper skills are worth invoking when triggered

1. **Stricter rate-limit discipline.** Both enforce 1 query/sec sequential pacing (vs the MCP's 3/30s allowance). They catch 429s, retry once with a 3-second wait, and log failures.
2. **Plan-tier detection.** Both parse "Found X, showing top Y" language and report tier (~3 unauth, ~10 free, ~20 Pro) so the user understands coverage ceilings.
3. **Integrity rules.** No fabricated citations, no silent supplementation from training knowledge, every cited paper traceable to a tool response in the same session.
4. **Audit log.** Every search, query, response count, and failure tracked in the deliverable.
5. **Document deliverables.** Both produce `.docx` files with full hyperlinks, tables, and structured sections.
6. **Multi-tool orchestration.** `consensus-grant-finder` additionally calls NIH RePORTER (POST API via `bash_tool` + `curl`, since `web_fetch` lacks POST) and fetches NOSI HTML pages.

### Edge cases

- **"Literature review on something funding-adjacent"** (e.g. "lit review on NIH grant success predictors") → that's a literature review on funding *as a research topic*, so route to `consensus-literature-review`. The grant-finder skill is for the user's *own* idea, not for studying grants.
- **"Help me find papers and write a grant section"** is ambiguous. Ask: are they writing the Significance/Innovation section of *their own* NIH grant? Yes → `consensus-grant-finder`. Are they writing a section *for a paper about funding*? No → direct MCP or `consensus-literature-review`.
- **User invokes lit-search but their query smells like grant work.** Surface the option: "This sounds like grant scoping — `consensus-grant-finder` is the dedicated skill for that. Want me to switch?"
- **User has limited time.** Even if intent matches a wrapper skill, ask before invoking — the `.docx` workflow takes minutes. A direct MCP call may be more appropriate.

---

## Direct-call usage — filter philosophy

The MCP server's own instructions are emphatic: **do not apply filters by default.**

> If the user asks a research question without mentioning filtering criteria, call search with only the query parameter.

Reasons:
- Filters silently drop high-quality evidence.
- Many breakthrough papers are small-N or in niche (Q3/Q4) journals.
- Animal / mechanism / preclinical studies are often essential context for a clinical question.

### Concrete heuristics

| User signal | Apply filter |
|---|---|
| "RCTs" / "clinical trials" | `study_types=["rct"]` |
| "best evidence" / "highest-quality" / "rigorous" | `study_types=["rct", "meta-analysis", "systematic review"]` |
| "peer-reviewed" / "published" / "no preprints" | `exclude_preprints=true` |
| "recent" / "last N years" | `year_min=<computed>` |
| "human studies only" | `human=true`. Otherwise leave off. |
| "top-tier journals" | `sjr_max=1` |
| "long-term" / "1+ year" | `duration_min=365` (rare) |

Otherwise: just `query`. Let Consensus's ranker work.

---

## Cross-engine bridging

Consensus output has opaque hash URLs and no DOI/PMID/paperId. To follow a Consensus hit into another engine:

1. Capture the title from the Consensus result.
2. Resolve to S2 paperId via `scripts/semantic-scholar/examples/title_match.py "..."`.
3. Or resolve to PMID via PubMed `lookup_article_by_citation` or `search_articles` with `"Title fragment"[Title]`.

Title-match is reliable at ≥7 distinct words. Below that, ambiguity climbs and you may need disambiguation by author + year.

For cross-engine deduplication, **keep Consensus papers in their own block** in the response — see `output_protocol.md` — because their URLs can't be merged into a DOI-keyed list without breaking the citation requirements.

---

## Worked examples

### A. Quick evidence question (direct MCP)

```
mcp__claude_ai_Consensus__search(
  query="does sleep restriction impair declarative memory consolidation",
)
```

User intent matches the rule-3 path: single-question evidence check. No filters applied unless they asked.

### B. Cross-checking S2 results (direct MCP)

User just received an S2 result list and wants validation:

```
mcp__claude_ai_Consensus__search(
  query="hippocampal sharp-wave ripples memory consolidation",
)
```

Compare top hits with S2's. Surface overlap and divergence. No filters.

### C. Clinical evidence question (direct MCP, with one filter)

User said "what's the strongest clinical evidence":

```
mcp__claude_ai_Consensus__search(
  query="GLP-1 agonist Alzheimer's disease cognitive outcomes",
  medical_mode=True,
  exclude_preprints=True,
)
```

Two filters because the user's framing explicitly named the bar.

### D. Lit review (delegate)

User: *"I'm starting a literature review on caffeine and cognition in older adults"* → invoke `consensus-literature-review`. Don't call MCP directly.

### E. Grant scoping (delegate)

User: *"Help me find NIH funding for my idea on circadian rhythm disruption in night-shift workers"* → invoke `consensus-grant-finder`. Don't call MCP directly.

---

## Failure modes to anticipate

- **Sparse results on a niche topic.** Could be a real literature gap or a plan-tier ceiling. Always check the response for "Found X, showing top Y" language and surface the tier limit if relevant.
- **Rate limit (429).** Wait ~30s and retry once. Don't burst.
- **Empty / off-topic results.** Often the query is too long or contains stopwords Consensus's ranker doesn't handle. Tighten to 5–10 content words.
- **User asks for follow-up "more like this."** Consensus has no recommendation API — route to S2 (`recommend_from_paper.py`) for similarity.

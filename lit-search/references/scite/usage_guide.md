# Scite — usage guide

Scite powers **Vet mode** only. Vet is the sole caller; no other mode uses Scite. This guide covers when to reach for it, the Codex payload shape that affects the workflow, and the filter recipes.

## What Scite is for in this skill

The reliability / consensus layer the other engines lack:

- **Editorial-notice awareness** — is a paper retracted, corrected, subject to an expression of concern, or an erratum? Filterable at search time across all fields (broader than PubMed, which only flags biomedical retractions).
- **Citation-sentiment (Smart Citation) filtering** — select papers by how many *supporting* vs *contrasting* vs *mentioning* citations they have. No other engine in the skill exposes citation sentiment at all.

Do **not** use Scite for general discovery (Explore/Precise cover that better), recommendations (Associate), preprints (Latest), or non-paper web (AI).

## The Codex payload shape (this shapes everything)

Access is via a Stanford → EBSCO institutional integration (resolver URLs are `resolver.ebsco.com/...`). In Codex:

1. **`search_literature` can return rich fields**: title, DOI, resolver URL, authors, journal, year/date, abstract, `tally`, Smart Citation `citations`, `fulltextExcerpts`, `access`, and `retraction_notices`. Field presence varies by paper and access rights.
2. **The server-side filters operate on Smart Citation and editorial-notice data.** `has_retraction`, `has_correction`, `has_concern`, `has_erratum`, `has_tally`, `supporting_from/to`, `contrasting_from/to`, `mentioning_from/to`, `citing_publications_from/to` all work — confirmed.
3. **The `RETRACTED` / `RETRACTED ARTICLE` prefix is baked into the indexed title**, so a retraction is visible directly in the returned title string.
4. **All evidence databases are gated** behind the `evidence:*:mcp` entitlement: clinical trials, FAERS, MAUDE, MHRA, 510(k), drugs, patents, grants → hard entitlement error. Not usable; not part of Vet.

**Consequence:** Vet can *select* papers by their citation/notice profile and may quote returned tally/snippet evidence when present. If a field is absent, do not infer it; link out to the Scite report page for the actual numbers.

> Never fabricate citation counts or Smart Citation snippets. Cite them only when the current tool response returned them.

## Recipes

### Reliability check (specific paper)

```
# 1. fetch metadata — a RETRACTED prefix in the title is definitive
search_literature(dois=["10.xxxx/..."])

# 2. probe each notice type; non-empty result = flag is set for that paper
search_literature(dois=["10.xxxx/..."], has_retraction=true)
search_literature(dois=["10.xxxx/..."], has_correction=true)
search_literature(dois=["10.xxxx/..."], has_concern=true)
search_literature(dois=["10.xxxx/..."], has_erratum=true)
```

Batch several DOIs in one call; run the four probes in parallel.

**Verified gotcha:** with a notice filter applied, an empty result may report *"not present in Scite's index"* even when the plain metadata fetch (step 1) returned the paper. That message is misleading under a filter — empty means "does not carry that notice," not "absent from the index." Confirm the paper is indexed via step 1 before reporting any absence.

### Consensus / controversy map (topic or claim)

```
search_literature(term="<specific technical phrase>", contrasting_from=5, limit=15)   # contested
search_literature(term="<specific technical phrase>", supporting_from=25, limit=15)   # well-supported
search_literature(term="<specific technical phrase>", has_retraction=true, limit=10)  # retracted, still cited
```

Tune thresholds to field size: raise `supporting_from` for large literatures; `contrasting_from` min is 1 for niche topics. Use Boolean/phrase/proximity syntax in `term` (`"exact phrase"`, `AND`/`OR`/`NOT`, `"a b"~5`) and domain-specific vocabulary — the index spans all fields, so broad terms return noise.

## Links to surface

- Scite report (visual supporting/contrasting/mentioning breakdown): `https://scite.ai/reports/{doi}`
- Paper: `https://doi.org/{doi}`

## Setup

Scite is exposed in Codex as `mcp__codex_apps__scite._search_literature`; no venv or API key. If evidence databases are needed, entitlements are enabled by the institution's EBSCO/Scite administrator (sales@scite.ai).

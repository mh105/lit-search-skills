# lit-search — multi-engine literature search skills for Codex

Three Codex **skills** for academic literature work:

| Skill | What it does |
|---|---|
| [`lit-search/`](./lit-search) | Adaptive multi-engine paper search (the main skill). |
| [`consensus-literature-review/`](./consensus-literature-review) | Strategic, multi-search literature review → `.docx` research guide. |
| [`consensus-grant-finder/`](./consensus-grant-finder) | NIH grant-fit analysis (institutes, study sections, NOSIs) → `.docx`. |

The two `consensus-*` skills are heavier, deliverable-producing workflows. Day-to-day "find me papers on X" / "more like this paper" / "latest preprints in Y" goes through `lit-search`.

> **Looking for the Claude Code / Claude Desktop build?** It lives on the [`claude`](https://github.com/mh105/lit-search-skills/tree/claude) branch. This is the **`codex`** branch, wired for Codex apps + `~/.codex/config.toml` MCP servers.

## What `lit-search` does

One skill, seven engines, **six adaptive modes**. The skill reads the user's phrasing and routes to the right mode automatically:

| Mode | Triggered by | Engines used |
|---|---|---|
| **Explore** *(default)* | "find papers on X", topic-driven discovery | Consensus + Semantic Scholar |
| **Precise** | "the 2023 Friston paper on…", named author / specific paper | PubMed + Tavily(Google Scholar) |
| **Latest** | "preprints from the last N weeks on…" | bioRxiv + PsyArxiv (with subagent filter) |
| **AI** | "press releases / lab pages / trial registries on…" | Tavily web search |
| **Associate** | "more like this paper", DOI/PMID seed → similar work | Semantic Scholar recommendations API + PubMed similarity |
| **Vet** | "is this paper retracted / reliable / safe to cite?", "well-supported vs. contested work on X" | Scite (reliability & consensus check) |

Each mode has its own quality signals, dedup rules, and output format. See `lit-search/SKILL.md` for the full decision tree.

## Engines: Codex apps, MCP servers, and local scripts

`lit-search` mixes three integration styles on Codex. **You install them separately.**

| Engine | Type | Install path |
|---|---|---|
| **Consensus** | Codex app | Codex → Apps → enable |
| **Scite** | Codex app | Codex → Apps → enable |
| **PubMed** | MCP server (Claude endpoint) | add to `~/.codex/config.toml` |
| **bioRxiv** | MCP server (Claude endpoint) | add to `~/.codex/config.toml` |
| **Tavily** | MCP server (custom) | add to `~/.codex/config.toml` (free tier available) |
| **Semantic Scholar** | local Python script | API key + `pip install` |
| **PsyArxiv (OSF)** | local Python script | OSF personal access token + `pip install` |

**Codex apps** (Consensus, Scite) are enabled from the Codex app / connector directory — auth is handled in-app, no API keys to manage. Their tools show up under `mcp__codex_apps__consensus._*` and `mcp__codex_apps__scite._*`.

**MCP servers** (PubMed, bioRxiv, Tavily) are remote MCP endpoints registered in `~/.codex/config.toml` under `[mcp_servers.<name>]`. PubMed and bioRxiv reuse Anthropic's hosted MCP endpoints (the same servers the Claude connectors talk to); Tavily is Tavily's own hosted MCP. Codex exposes their tools as `mcp__<name>.*` — so **the server names matter** and must match what the skill calls (`PubMed`, `bioRxiv`, `tavily`).

**Script engines** are thin Python wrappers shipped under `lit-search/scripts/<engine>/`. The skill invokes them via `scripts/.venv/bin/python …`. They exist because Semantic Scholar's recommendations API and OSF's PsyArxiv API don't have polished MCPs at time of writing, and the wrappers add field-set workarounds, ID resolution, and CLI ergonomics.

You can install whichever subset you need — modes degrade gracefully when an engine is unavailable, but Explore needs Consensus + S2, Latest needs bioRxiv + PsyArxiv, Vet needs Scite, etc.

---

## Installation

### 1. Install the skills into your Codex config

Codex discovers skills by scanning `~/.codex/skills/<skill-name>/SKILL.md`. Each of the three skill folders in this repo must sit **directly** under `~/.codex/skills/` — not nested inside a parent wrapper folder.

Clone the repo to a working location and check out this `codex` branch, then symlink (preferred — lets you `git pull` to update) or copy the three skill folders in:

```bash
# Clone anywhere convenient (NOT inside ~/.codex/skills directly)
git clone https://github.com/mh105/lit-search-skills.git ~/code/lit-search-skills
cd ~/code/lit-search-skills
git checkout codex

# Option A — symlink (recommended; updates flow through git pull)
mkdir -p ~/.codex/skills
ln -s "$PWD/lit-search"                    ~/.codex/skills/lit-search
ln -s "$PWD/consensus-literature-review"   ~/.codex/skills/consensus-literature-review
ln -s "$PWD/consensus-grant-finder"        ~/.codex/skills/consensus-grant-finder

# Option B — copy (simpler, but you'll re-copy after every update)
cp -r lit-search consensus-literature-review consensus-grant-finder ~/.codex/skills/
```

Verify the layout — each folder should contain its own `SKILL.md`:

```
~/.codex/skills/
├── lit-search/SKILL.md
├── consensus-literature-review/SKILL.md
└── consensus-grant-finder/SKILL.md
```

Restart Codex. The three skills should now appear in the available-skills list.

### 2. Enable Codex apps (Consensus, Scite)

Consensus and Scite are available as **Codex apps** — enable them from the Codex app / connector directory. Auth is handled in-app; no API keys to manage manually.

- **Consensus** — AI-ranked academic search across ~200M papers. <https://consensus.app/>
- **Scite** — Smart Citations + retraction / editorial-notice checks; powers **Vet** mode. <https://scite.ai/>

Once enabled, their tools appear as `mcp__codex_apps__consensus._*` and `mcp__codex_apps__scite._*`. Note: the depth of Scite's Smart Citation data (tally counts, citation snippets) depends on your Scite / institutional access tier — Vet mode is built to work even when only titles, DOIs, and editorial notices come back.

### 3. Add MCP servers (PubMed, bioRxiv, Tavily)

These three are remote MCP servers registered in `~/.codex/config.toml`. **PubMed and bioRxiv reuse Anthropic's hosted MCP endpoints** (the same servers the Claude connectors use); **Tavily** is Tavily's own hosted MCP (free tier ≈ 1,000 calls/month — sign up at <https://app.tavily.com/>).

Add these blocks to `~/.codex/config.toml`:

```toml
[mcp_servers.PubMed]
url = "https://pubmed.mcp.claude.com/mcp"

[mcp_servers.bioRxiv]
url = "https://hcls.mcp.claude.com/biorxiv/mcp"

[mcp_servers.tavily]
url = "https://mcp.tavily.com/mcp"
bearer_token_env_var = "TAVILY_API_KEY"
```

Then export your Tavily key so Codex can pass it as the bearer token:

```bash
export TAVILY_API_KEY="..."
```

The server names (`PubMed`, `bioRxiv`, `tavily`) are load-bearing — the skill calls tools as `mcp__PubMed.*`, `mcp__bioRxiv.*`, and `mcp__tavily.*`. Restart Codex after editing `config.toml`. See Tavily's MCP docs for details: <https://docs.tavily.com/documentation/mcp>.

### 4. Set up local script engines (Semantic Scholar + PsyArxiv)

```bash
cd lit-search/scripts
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Then export credentials:

```bash
# Semantic Scholar — request a key at:
#   https://www.semanticscholar.org/product/api#api-key-form
export S2_API_KEY="..."

# OSF (PsyArxiv) — create a personal access token at:
#   https://osf.io/settings/tokens/
# Recommended scopes: osf.full_read
export OSF_TOKEN="..."
```

`.env` files in `scripts/<engine>/.env.example` show per-engine variables; the skill reads from the shell environment by default.

### 5. Verify

In Codex, try:

```
find papers on predictive coding in primary visual cortex
```

If routed correctly, the skill enters **Explore** mode and queries Consensus + Semantic Scholar. Try `more like this paper: 10.1038/nature14066` to exercise **Associate** mode (and confirm `S2_API_KEY` works), or `is <DOI> retracted or safe to cite?` to exercise **Vet** mode (Scite).

---

## Quick links

| Need | Where |
|---|---|
| Semantic Scholar API key | <https://www.semanticscholar.org/product/api#api-key-form> |
| OSF personal access token | <https://osf.io/settings/tokens/> |
| Tavily signup + API key | <https://app.tavily.com/> |
| Tavily MCP setup docs | <https://docs.tavily.com/documentation/mcp> |
| PubMed MCP endpoint | `https://pubmed.mcp.claude.com/mcp` |
| bioRxiv MCP endpoint | `https://hcls.mcp.claude.com/biorxiv/mcp` |
| Consensus (Codex app) | <https://consensus.app/> |
| Scite (Codex app) | <https://scite.ai/> |

## License

MIT (see `LICENSE`).

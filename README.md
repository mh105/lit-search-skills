# lit-search — multi-engine literature search skills for Claude Code

Three Claude Code / Claude Desktop **skills** for academic literature work:

| Skill | What it does |
|---|---|
| [`lit-search/`](./lit-search) | Adaptive multi-engine paper search (the main skill). |
| [`consensus-literature-review/`](./consensus-literature-review) | Strategic, multi-search literature review → `.docx` research guide. |
| [`consensus-grant-finder/`](./consensus-grant-finder) | NIH grant-fit analysis (institutes, study sections, NOSIs) → `.docx`. |

The two `consensus-*` skills are heavier, deliverable-producing workflows. Day-to-day "find me papers on X" / "more like this paper" / "latest preprints in Y" goes through `lit-search`.

## What `lit-search` does

One skill, six engines, **five adaptive modes**. The skill reads the user's phrasing and routes to the right mode automatically:

| Mode | Triggered by | Engines used |
|---|---|---|
| **Explore** *(default)* | "find papers on X", topic-driven discovery | Consensus + Semantic Scholar |
| **Precise** | "the 2023 Friston paper on…", named author / specific paper | PubMed + Tavily(Google Scholar) |
| **Latest** | "preprints from the last N weeks on…" | bioRxiv + PsyArxiv (with subagent filter) |
| **AI** | "press releases / lab pages / trial registries on…" | Tavily web search |
| **Associate** | "more like this paper", DOI/PMID seed → similar work | Semantic Scholar recommendations API + PubMed similarity |

Each mode has its own quality signals, dedup rules, and output format. See `lit-search/SKILL.md` for the full decision tree.

## Engines: MCPs vs. local script engines

`lit-search` mixes two integration styles. **You install them separately.**

| Engine | Type | Install path |
|---|---|---|
| **PubMed** | MCP connector | claude.ai → Connectors → enable |
| **bioRxiv** | MCP connector | claude.ai → Connectors → enable |
| **Consensus** | MCP connector | claude.ai → Connectors → enable |
| **Tavily** | MCP (custom) | Add manually via MCP config (free tier available) |
| **Semantic Scholar** | local Python script | API key + `pip install` |
| **PsyArxiv (OSF)** | local Python script | OSF personal access token + `pip install` |

**MCP engines** run server-side via Claude.app's connector / MCP system — Claude calls a tool, the MCP returns JSON. No code in this repo runs them.

**Script engines** are thin Python wrappers shipped under `lit-search/scripts/<engine>/`. The skill invokes them via `scripts/.venv/bin/python …`. They exist because Semantic Scholar's recommendations API and OSF's PsyArxiv API don't have polished MCPs at time of writing, and the wrappers add field-set workarounds, ID resolution, and CLI ergonomics.

You can install whichever subset you need — modes degrade gracefully when an engine is unavailable, but Explore needs Consensus + S2, Latest needs bioRxiv + PsyArxiv, etc.

---

## Installation

### 1. Install the skills into your Claude config

Claude discovers skills by scanning `~/.claude/skills/<skill-name>/SKILL.md`. Each of the three skill folders in this repo must sit **directly** under `~/.claude/skills/` — not nested inside a parent wrapper folder.

Clone the repo to a working location, then symlink (preferred — lets you `git pull` to update) or copy the three skill folders in:

```bash
# Clone anywhere convenient (NOT inside ~/.claude/skills directly)
git clone https://github.com/mh105/lit-search-skills.git ~/code/lit-search-skills
cd ~/code/lit-search-skills

# Option A — symlink (recommended; updates flow through git pull)
mkdir -p ~/.claude/skills
ln -s "$PWD/lit-search"                    ~/.claude/skills/lit-search
ln -s "$PWD/consensus-literature-review"   ~/.claude/skills/consensus-literature-review
ln -s "$PWD/consensus-grant-finder"        ~/.claude/skills/consensus-grant-finder

# Option B — copy (simpler, but you'll re-copy after every update)
cp -r lit-search consensus-literature-review consensus-grant-finder ~/.claude/skills/
```

Verify the layout — each folder should contain its own `SKILL.md`:

```
~/.claude/skills/
├── lit-search/SKILL.md
├── consensus-literature-review/SKILL.md
└── consensus-grant-finder/SKILL.md
```

Restart Claude. The three skills should now appear in the available-skills list.

**Claude Desktop**: same idea — drop (or symlink) the three folders directly into your Claude Desktop skills directory.

### 2. Install MCP connectors (PubMed, bioRxiv, Consensus)

These three are one-click connectors in **claude.ai → Settings → Connectors → Browse connectors**:

- **PubMed** — search NCBI / MEDLINE. <https://claude.ai/directory>
- **bioRxiv** — biology / neuroscience preprints. <https://claude.ai/directory>
- **Consensus** — AI-ranked academic search across ~200M papers. <https://consensus.app/> · connector at <https://claude.ai/directory>

Click "Connect" for each; auth is handled via the Claude.app UI. No API keys to manage manually.

### 3. Install Tavily MCP (manual, free tier)

Tavily is not a one-click connector — register and add it as a custom MCP:

1. Sign up: <https://app.tavily.com/> (free tier ≈ 1,000 calls/month).
2. Grab your API key from the Tavily dashboard.
3. Add the MCP server per Tavily docs: <https://docs.tavily.com/documentation/mcp>

In Claude Code, this typically means adding an entry to `~/.claude/mcp.json` (or via `claude mcp add`).

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

In Claude, try:

```
find papers on predictive coding in primary visual cortex
```

If routed correctly, the skill enters **Explore** mode and queries Consensus + Semantic Scholar. Try `more like this paper: 10.1038/nature14066` to exercise **Associate** mode (and confirm `S2_API_KEY` works).

---

## Quick links

| Need | Where |
|---|---|
| Semantic Scholar API key | <https://www.semanticscholar.org/product/api#api-key-form> |
| OSF personal access token | <https://osf.io/settings/tokens/> |
| Tavily signup + API key | <https://app.tavily.com/> |
| Tavily MCP setup docs | <https://docs.tavily.com/documentation/mcp> |
| Claude.app connector directory | <https://claude.ai/directory> |
| Consensus | <https://consensus.app/> |

## License

MIT (see `LICENSE`).

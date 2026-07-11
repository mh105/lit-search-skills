# lit-search-skills

Multi-engine academic literature-search skills — adaptive paper search across Consensus, Semantic Scholar, PubMed, bioRxiv, PsyArxiv, Tavily, and Scite, plus two `.docx`-producing consensus workflows (literature review + NIH grant finder).

The toolbox ships in two builds. Pick the branch for your agent:

| Build | Branch | For |
|---|---|---|
| **Claude** | **[`claude`](https://github.com/mh105/lit-search-skills/tree/claude)** | Claude Code / Claude Desktop — engines via claude.ai connectors + a custom Tavily MCP. |
| **Codex** | **[`codex`](https://github.com/mh105/lit-search-skills/tree/codex)** | Codex — Consensus & Scite as Codex apps, PubMed/bioRxiv/Tavily as `config.toml` MCP servers. |

Both builds expose the same skill and six adaptive modes (Explore · Precise · Latest · AI · Associate · Vet); they differ only in how the search engines are wired into the host. Each branch's `README.md` has the full setup guide.

## License

MIT (see [`LICENSE`](./LICENSE)).

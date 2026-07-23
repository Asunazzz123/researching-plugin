# alphaXiv arXiv MCP integration

## Component location

The distributable Codex plugin component lives at:

```text
researching-plugin/
├── .codex-plugin/plugin.json
├── .mcp.json
├── mcp/
├── runtime/
├── scripts/
└── skills/
    ├── using-researching/
    └── researching-paper-searching/
```

The MCP server is named `alphaxiv-arxiv`. The plugin launches a local lazy stdio
server at `mcp/server.mjs`. It exposes the read-only tool schemas without network
access and launches `mcp-remote@0.1.38` only for the first real tool call. The
remote bridge then connects to:

```text
https://api.alphaxiv.org/mcp/v1
```

alphaXiv documents the remote transport as Streamable HTTP with OAuth 2.0. The
stdio bridge is used because Codex CLI 0.144.1 rejected alphaXiv's native OAuth
callback when the authorization response omitted the expected issuer. OAuth is
therefore completed by `mcp-remote`, not `codex mcp login`.

Official alphaXiv documentation:

- <https://www.alphaxiv.org/docs/mcp>

## Exposed tools

The plugin passes `--ignore-tool` for all known library mutations, leaving these
read-oriented research tools:

- `discover_papers`
- `get_paper_content`
- `answer_pdf_queries`
- `read_files_from_github_repository`

alphaXiv also offers library-management tools, including destructive folder
operations. They are outside the arXiv retrieval requirement and are not
exposed by this plugin.

## Role in discovery

Use alphaXiv as an arXiv-focused semantic retrieval and reading provider. It
complements rather than replaces the existing providers:

| Source | Primary role |
|---|---|
| alphaXiv MCP | Semantic arXiv discovery, generated paper reports, extracted text, page-focused PDF answers |
| Crossref | DOI-centered publisher metadata baseline |
| OpenAlex | Cross-publisher scholarly graph and metadata enrichment |
| Unpaywall | Legal open-access location resolution |

alphaXiv is a third-party service and must not be presented as the official
arXiv API. Canonicalize its results into the same `PaperRecord` model and
deduplicate by arXiv ID, DOI, or conservative title/year matching before
merging manifests.

## Authentication handoff

After installing or updating the plugin, ordinary MCP initialization must remain
local and must not open a browser. Let `mcp-remote` open browser OAuth only when
the first alphaXiv tool is actually called. The bridge stores credentials in its
per-user MCP auth directory; do not copy access tokens into repository files,
prompts, command arguments, or the plugin manifest. `codex mcp list` may show
`Auth: Unsupported` for this stdio entry because the bridge, rather than Codex,
manages OAuth.

The detailed first-run and verification procedure is bundled with the child
skill at `skills/researching-paper-searching/references/alphaxiv-setup.md`.

The alphaXiv OAuth session is independent of CARSI, SYSU, ScienceDirect, CNKI,
macOS Keychain entries used by the certification package, and Windows
Credential Manager entries. It provides alphaXiv account access only.

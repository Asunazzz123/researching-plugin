# alphaXiv MCP setup and verification

Use this reference only when `alphaxiv-arxiv` tools are unavailable, OAuth has
expired, or the user asks how the dependency is installed.

## Installation boundary

Installing the Researching plugin registers its bundled `.mcp.json`. Codex
starts a lightweight local stdio server, but that server does not launch
`mcp-remote`, connect to alphaXiv, or open a browser during initialization or
`tools/list`. The first real alphaXiv `tools/call` launches `mcp-remote`, which
connects to the remote Streamable HTTP endpoint and owns browser OAuth.

Before changing MCP configuration:

1. Explain that Node.js with `npm`/`npx` and a browser callback are required.
2. Explain that alphaXiv is a third-party service over arXiv.
3. Ask the user for permission to install or replace the lazy MCP entry.
4. Continue with public metadata fallbacks if permission is not granted.

Check prerequisites on Windows or macOS:

```bash
node --version
npx --version
codex --version
```

Do not install Node.js or change the user's proxy configuration without separate
permission.

## Registration boundary

Use the plugin's bundled `.mcp.json` or register its `mcp/server.mjs` by absolute
path. Do not register `npx mcp-remote` directly as a global MCP server: Codex
initializes global stdio servers for ordinary tasks, and unauthenticated
`mcp-remote` instances can repeatedly open browser OAuth.

This configuration excludes alphaXiv library and folder mutations. It exposes
only remote tools that remain after those filters, currently:

- `discover_papers`
- `get_paper_content`
- `answer_pdf_queries`
- `read_files_from_github_repository`

## OAuth

The first real tool call starts the remote bridge and may open browser OAuth.
For isolated troubleshooting only, start the upstream diagnostic client:

```bash
npx -y -p mcp-remote@0.1.38 mcp-remote-client https://api.alphaxiv.org/mcp/v1 --transport http-only
```

Let the user complete consent in the browser. Never automate consent, copy the
authorization URL to another person, or read token-file contents. The callback
uses loopback networking; when a proxy interferes, keep `localhost` and
`127.0.0.1` out of the proxy rather than disabling unrelated network controls.

Do not run `codex mcp login alphaxiv-arxiv` for this stdio bridge. Codex reports
stdio authentication as `Unsupported` because OAuth is handled inside
`mcp-remote`; that label is not a connection failure.

`mcp-remote@0.1.38` currently embeds `0.1.37` in its generated bundle, so its
per-user OAuth directory may be named `mcp-remote-0.1.37`. Treat that as an
implementation detail and never commit the directory.

## Verification

1. Run `codex mcp get alphaxiv-arxiv` and confirm it points to
   `mcp/server.mjs` over stdio.
2. Restart Codex or create a new task so MCP configuration is reloaded.
3. Confirm that initialization and `tools/list` do not open a browser.
4. Invoke `$researching-paper-searching` with a small live test such as “搜索一篇
   关于 Muon 优化器的论文”.
5. Complete OAuth if the first real tool call opens it, then require a real
   title, arXiv ID, publication date, and alphaXiv/arXiv URL in the
   result. A schema-only `tools/list` response proves connectivity but not search
   execution.

The diagnostic client may display every remote tool because it was launched
without the plugin's `--ignore-tool` arguments. The Codex plugin bridge still
applies its configured filters.

---
name: researching-paper-searching
description: Use when a user asks for papers in a field, related work, a known paper, scholarly evidence during another task, metadata or abstracts from closed publications, open-access locations, institutional access checks, authorized PDF retrieval, or arXiv search and reading through alphaXiv.
---

# Researching Paper Searching

Find useful papers before asking for institutional login. Treat discovery,
access resolution, authentication, and downloading as separate stages.

## Preserve the calling context

Derive the search question from the active task. Preserve domain, terminology,
methods, exclusions, date constraints, target venues, and intended use. Do not
ask the user to restate context already available. When a term is ambiguous,
prefer the meaning established by the surrounding task and state the assumption.

Choose the smallest useful mode:

- **Field discovery:** expand a vague direction into bounded concepts and rank a
  diverse candidate set.
- **Evidence gap:** search only for the claim, method, baseline, or counterexample
  needed by the parent task.
- **Known paper:** resolve by title, DOI, arXiv ID, URL, or author and inspect it.
- **Access continuation:** resume from an existing manifest instead of repeating
  discovery after login.

## Search closure

### 1. Discover without login

Search public metadata and visible landing-page information first. Depending on
the question, combine:

- alphaXiv MCP for semantic arXiv discovery and paper reading;
- Crossref for DOI-centered publisher metadata;
- OpenAlex for cross-publisher metadata and scholarly graph enrichment;
- public arXiv pages, publisher abstracts, library catalog records, and visible
  CNKI or ScienceDirect metadata when available;
- Unpaywall and institutional or author repositories for legal open copies.

Closed full text does not close discovery. Without entitlement, retain every
verifiable field that is publicly visible: title, authors, year, venue, abstract
or snippet, DOI/arXiv ID, keywords, citations, landing URL, and version links.
Mark unavailable fields as unknown rather than false.

When Crossref, OpenAlex, or Unpaywall is useful, resolve the plugin root as two
directories above this Skill and run its bundled `scripts/discover.py`. The
script bootstraps `runtime/python` itself, so it does not depend on a source
checkout or an installed Python package. Read
[the discovery architecture](../../references/discovery.md) before changing
provider, access-state, authentication, or download behavior.

### 2. Normalize and rank

Deduplicate by arXiv ID, then DOI, then conservative normalized title and year.
Link preprints, accepted manuscripts, and versions of record instead of counting
them as independent findings. Rank for the user's actual question, not merely
keyword overlap, and preserve conflicting metadata with source attribution.

For a survey, return enough candidates to show coverage and then identify a
smaller reading set. For a request for one paper, return one strong match plus a
brief reason rather than an unnecessary bibliography.

### 3. Resolve access

Classify each selected record as:

- `open_access`: a known legal full-text location exists;
- `authentication_required`: full text may require a user-authorized session;
- `metadata_only`: discovery succeeded but access has not been checked;
- `unresolved`: neither a legal full-text location nor a reliable access verdict
  is available.

Try open locations before institutional authentication. Do not infer that a
school subscription exists from a publisher URL or an Unpaywall closed result.

### 4. Authenticate only when useful

Finish anonymous discovery and report the number of selected papers that still
need login. Ask the user to complete CARSI, university-library, CNKI,
ScienceDirect, MFA, or CAPTCHA interaction in the visible browser. Reuse an
authorized browser profile only within its session lifetime and site policy.

After login, recheck entitlement paper by paper, present the exact download
manifest, and download only the selected accessible files. Never bypass access
controls, replay SAML assertions, fabricate institutional attributes, evade
rate limits, or treat cached credentials as permission to download everything.

## Use alphaXiv MCP

Prefer these read-oriented `alphaxiv-arxiv` tools:

- `discover_papers` for broad or related-work retrieval;
- `get_paper_content` for a selected paper overview or extracted text;
- `answer_pdf_queries` for page-grounded questions; batch all questions about
  one paper into one call;
- `read_files_from_github_repository` when a paper's code repository matters.

For `discover_papers`, keep `keywords` to terms stated by the user or established
in the current task. Put the semantic intent in `question`; do not invent acronym
expansions. Use `difficulty` to reflect retrieval effort, `prioritize=recency`
only for explicitly recent work, and date bounds only when the user supplies a
real boundary.

Treat alphaXiv as a third-party service over arXiv, not the official arXiv API.
Attribute paper claims to the paper. Treat generated reports as secondary
summaries and use page-grounded paper text for claims that require evidence.

## On-demand alphaXiv startup

The bundled `alphaxiv-arxiv` server is a local lazy bridge. MCP initialization
and `tools/list` stay local; do not start `mcp-remote`, connect to alphaXiv, or
open a browser until an actual alphaXiv `tools/call` is required by this skill.

Before the first alphaXiv tool call in a task, tell the user that the call may
open a one-time browser OAuth flow. If the tool is unavailable, continue with
public metadata and OA fallbacks instead of registering `mcp-remote` globally.
Follow [references/alphaxiv-setup.md](references/alphaxiv-setup.md) for lazy
bridge installation, OAuth, and verification. Never place alphaXiv OAuth tokens
in this repository, prompts, logs, or the OS credential cache used for
publisher/library authentication.

## Return results to the parent task

Report:

1. the interpreted question and material assumptions;
2. ranked papers with identifiers and source links;
3. why each selected paper is relevant;
4. access state and the legal full-text route, when known;
5. provider failures or coverage limits;
6. the next action: read, refine, authenticate, or download.

When this skill was called from another workflow, return the selected evidence
in a form that the caller can immediately use and then resume that workflow.

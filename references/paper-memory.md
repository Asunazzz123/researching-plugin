# Project-local paper memory

Use this contract after a selected paper is downloaded for an active research
folder. Keep project data outside the installed Plugin directory.

## Storage boundary

Store files under the researcher-selected folder:

```text
<folder>/
├── pdf/
│   └── <paper-id>.pdf
└── papers/
    ├── index.md
    ├── <paper-id>.md
    └── .extracted/
        └── <paper-id>.md
```

- Keep the downloaded PDF as the authoritative source.
- Treat `.extracted/` as lossy machine output for navigation, not evidence by
  itself.
- Treat `<paper-id>.md` as the durable reading record.
- Use `index.md` to select records to reload; do not load every paper on every
  turn.
- Never store project PDFs, extracted full text, or reading records in the
  Plugin installation directory.

Use a filesystem-safe paper ID containing lowercase letters, digits, dots,
underscores, or hyphens. Prefer `arxiv-<id>`; otherwise use a stable DOI-derived
or title-derived key. Keep the exact DOI or arXiv identifier in the record.

## Prepare a downloaded PDF

Resolve the Plugin root and run:

```bash
python <plugin-root>/scripts/prepare_paper.py \
  --workspace <folder> \
  --pdf <folder>/pdf/<paper-id>.pdf \
  --paper-id <paper-id>
```

The script extracts page-mapped text, creates a record template when one does
not exist, and adds the paper to `papers/index.md`. It never overwrites an
existing durable record. If extraction is empty, garbled, or layout-sensitive,
inspect the original PDF visually and use OCR or a layout-aware reader when
needed.

## Complete the durable record

Keep these sections in each `<paper-id>.md`:

1. `30-second recall`: problem, method, result, and current relevance.
2. `Current research relevance`: which active question or uncertainty it informs.
3. `Core contributions`.
4. `Method and assumptions`.
5. `Main results`: use a proposition table with stance, PDF locator, and limits.
6. `Relations to other papers`: support, extension, conflict, or incomparability.
7. `Open questions`.
8. `Visual checks`: inspected PDF pages, figures, tables, equations, or layouts.

Do not promote a summary sentence to an Evidence Packet until the relevant PDF
locator and source depth have been checked.

## Reload triggers

Reload paper memory on these events:

- **Resume:** read `papers/index.md`, then the `30-second recall` and `Open
  questions` sections of records relevant to the active question.
- **Question change:** reselect relevant records when scope, subquestions,
  comparison dimensions, populations, data, or evaluation criteria change.
- **Stage change:** reload results and conflicts for evidence synthesis; methods,
  assumptions, and limitations for route or protocol design; proposition rows
  and locators for writing or claims.
- **Claim preparation:** before stating what literature establishes, reload the
  relevant record; return to the located PDF page when the record is incomplete,
  disputed, or too imprecise.
- **New paper or conflict:** reload related older records and update the
  cross-paper relationship.

Use progressive depth: `index.md` -> `30-second recall` -> relevant record
sections -> located PDF pages. Do not use fixed turn counts as a reload trigger.

## Sharing boundary

Default to excluding licensed PDFs, extracted full text, and rendered pages from
Git publication. Track only records the researcher is permitted to share.

---
name: using-researching
description: Use when a task may require scholarly evidence, literature discovery, project-local paper records, or help advancing a research question, route, task, observation, interpretation, or claim, and the correct focused research subskill needs to be selected.
---

# Using Researching

Act as the entry point for the Researching plugin. Keep this skill short: disclose
the available child skills, preserve the current task context, and route the work.

## Disclose child skills

On activation, tell the user once that the following child skill is also directly
invocable:

- `$researching-paper-searching`: discover, rank, inspect, resolve access to, and
  retrieve papers across arXiv, public scholarly indexes, open-access locations,
  and user-authorized subscription sessions; downloaded project papers are
  decomposed into project-local Markdown records.
- `$advance-research`: frame a domain-neutral question, synthesize evidence,
  map concepts and capability gaps, compare research routes, classify Task
  Nodes with H0-H4, coordinate bounded session-local work, and prepare human
  checkpoints or handoffs. Consequential planning and execution are separately
  approved downstream branches.

Installed plugin UIs may group these as `Researching: Paper Searching` and
`Researching: Advance Research`. Their canonical component names remain
`$researching-plugin:researching-paper-searching` and
`$researching-plugin:advance-research`.

Do not wait for confirmation when the current request already needs that child.
Invoke it in the same turn and pass along the current research question,
constraints, terminology, date range, known papers, and desired output.

## Route by research stage

Use `$researching-paper-searching` when any of these conditions holds:

- The user initially asks for papers in a field or around a research question.
- An ongoing analysis, experiment, implementation, or writing task reaches an
  evidence gap and needs new literature.
- The user names a paper, DOI, arXiv identifier, author, method, or venue.
- The task needs an abstract, citation metadata, paper content, access status,
  or an authorized PDF download.
- A vague academic request must be expanded into searchable concepts and ranked
  candidates.

Use `$advance-research` when any of these conditions holds:

- The user wants to turn a rough idea into a bounded research question.
- The task needs a research brief, concept map, competing explanations, route
  portfolio, feasibility analysis, or human-supervised next-step decision.
- New evidence, observations, reports, or contradictions must change the research plan.
- The user asks what to do next, why progress is stalled, or whether a claim is
  justified.
- A multi-session research project needs checkpoints, gates, a Task DAG,
  Human Handoffs, or a durable decision log.

Default to research construction and stop at the Direction Gate. Do not route a
broad request to automatic local experimentation merely because code execution
is available.

When `$advance-research` exposes a literature evidence gap, invoke
`$researching-paper-searching` with the exact proposition and required source
depth, then return Evidence Packets to the same research cycle.

When paper search downloads a PDF, pass its paper ID, project-local PDF path,
record path, and extraction warnings back to `$advance-research`. When resuming
a folder that already contains `papers/index.md`, let `$advance-research` reload
the relevant records before continuing synthesis, route comparison, or claims.

Keep the parent task active after a child completes. Feed selected papers,
Evidence Packets, working propositions, observations, Reports, or decisions
back into the stage that requested them instead of turning a subskill into an
unrelated side task.

## Dependency gate

Let the child skill check alphaXiv MCP availability and perform its first-run
installation and OAuth handoff. Do not duplicate provider-specific instructions
here and do not make alphaXiv availability a prerequisite for public metadata or
open-access fallback searches.

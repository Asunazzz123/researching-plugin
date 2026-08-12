# Parallelization and single-writer policy

## Ready frontier

Build a deterministic frontier from ready Task Nodes. Sort by descending
priority and stable Task ID, cap the session batch at three, and reject Tasks
with incomplete dependencies, stale context, unavailable Gate, overlapping
resource locks, unsafe side effects, external execution, or a non-Sub-agent
executor.

Run sequentially with the same Task and Report contracts when Sub-agent tools
are unavailable.

## Supported patterns

- Map–Reduce: partition independent sources, artifacts, or bounded subquestions;
  synthesize only after validation.
- Portfolio: generate genuinely different explanations or routes; do not force
  early consensus.
- Proposer–Critic: give the critic raw evidence and candidate output, not the
  proposer's persuasive reasoning.
- Independent Replication: repeat a high-impact calculation or source judgment
  without sharing the first report.

## Never parallelize

- final question or scope confirmation;
- dependent steps in one inference chain;
- concurrent edits to one Protocol or Claim;
- tasks competing for an exclusive resource;
- interpretation before input quality is validated;
- human Direction, Plan, Execution, or Claim decisions.

## Context isolation

Give a Sub-agent only the project boundary, glossary, its Task contract, relevant
record IDs and contents, output contract, write scope, and prohibitions. Do not
send the entire project or unrelated Agent reports.

## Single writer

The main agent alone commits canonical state. Sub-agents write task-local files
and reports. The reducer validates reports, maps temporary IDs, preserves
conflicts, appends Evidence, checkpoints the old state, and writes one revision.
No report can grant itself a higher trust status.

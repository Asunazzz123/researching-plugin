# Sub-agent report contract

## Contents

1. Trust boundary
2. Report shape
3. Candidate records
4. Validation and merge
5. Stale and conflicting reports

## Trust boundary

A Sub-agent receives one frozen Context Packet and one task-local write scope.
It cannot modify canonical state, approve a Gate, accept a Claim, or spawn more
agents. Its report is an immutable candidate envelope, not research truth.

## Report shape

```json
{
  "report_id": "REP-T-012-001",
  "task_id": "T-012",
  "based_on_revision": 7,
  "context_hash": "64 lowercase hex characters",
  "status": "completed",
  "actions": [],
  "observations": [],
  "evidence_candidates": [],
  "claim_candidates": [],
  "contradictions": [],
  "unknowns": [],
  "limitations": [],
  "artifacts": [],
  "recommended_next_actions": []
}
```

Statuses are `completed`, `partial`, `blocked`, and `failed`. Only completed
H0/H1 reports can contribute candidate records. Valid partial, blocked, and
failed reports are archived without merging their content and leave the Task in
`reported` or `blocked` so failure and unknowns are not overwritten.

Use task-local IDs such as `T-012:E-1`, `T-012:O-1`, `T-012:C-1`,
`T-012:AR-1`, and `T-012:CF-1`. The reducer assigns canonical IDs.

## Candidate records

- Observation: description, Protocol IDs, canonical input or task-local output
  Artifact IDs, and limitations.
- Evidence: full Evidence Packet fields including `source_lineage`, depth, and
  locator.
- Claim: statement, candidate Evidence/Observation IDs, and caveats. The reducer
  forces canonical status to `candidate`.
- Artifact: a newly produced task-local path, SHA-256, media type, description,
  and provenance. Do not copy input Artifacts into this output list.
- Contradiction: statement, at least two candidate/canonical record IDs, and
  severity.

Keep observations, interpretations, claims, unknowns, and limitations separate.
Metadata cannot support or contradict a scientific proposition. Artifact paths
must stay inside the Task write scope and hashes must match actual files.
Evidence uses the enumerated state-contract values: a string `source_lineage`,
a string source depth, and an object locator rather than an informal citation.

## Validation and merge

The main agent performs:

1. exact top-level schema validation;
2. task, temporary-ID, and output-permission validation;
3. path containment and artifact hash validation;
4. source depth and locator checks;
5. task context-hash comparison;
6. source-lineage deduplication;
7. contradiction preservation;
8. one canonical update with checkpoint and decision event.

Do not merge persuasive narrative directly. Merge structured candidate records,
then regenerate summaries from canonical state.

## Stale and conflicting reports

An older global revision is acceptable when the current task-local semantic
context hash is unchanged. If question, scope, relevant inputs, task contract,
or shared definitions change, archive the report, merge none of its content, and
mark the Task `needs_rework`.

Do not resolve disagreement by Agent count. Reports sharing one source lineage
are not independent evidence. Preserve opposite evidence as separate Evidence
Packets linked by a Conflict record.

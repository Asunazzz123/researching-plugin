# Research state contract v2

`research_state.json` is the canonical, single-writer state for a durable
human-supervised research project. The validator in `scripts/research_state.py`
is authoritative.

## Workspace

| Path | Role |
|---|---|
| `research_state.json` | Canonical current state |
| `evidence.jsonl` | Exact append-only mirror of Evidence Packets |
| `decisions.jsonl` | Append-only canonical update events |
| `.checkpoints/research_state.rNNNN.json` | State before every committed revision |
| `orchestration/tasks/<task-id>/` | Frozen context, task-local reports and artifacts |
| `orchestration/reports/<report-id>.json` | Immutable accepted or stale report archive |
| `artifacts/` | Researcher-managed project artifacts |
| `research_summary.md` | Derived ready, running, waiting-human, batch-review, conflict, stale-report, and blocked queues; never edit as state |

Schema v2 does not auto-migrate v1. Unknown versions are read as unsupported and
must not be rewritten. State loading is version-dispatched so a future release
can register explicit migrations or auto-update policy.

## Top-level shape

```json
{
  "schema_version": "2.0",
  "revision": 0,
  "created_at": "2026-08-12T00:00:00+00:00",
  "updated_at": "2026-08-12T00:00:00+00:00",
  "project": {
    "id": "stable-project-id",
    "question": "A bounded research question",
    "scope": ["Included boundary"],
    "non_goals": ["Excluded target"],
    "constraints": ["Data, access, ethics, time, or compute limit"],
    "resources": {}
  },
  "glossary": {},
  "current_stage": "framing",
  "uncertainties": [],
  "evidence": [],
  "claims": [],
  "routes": [],
  "working_propositions": [],
  "protocols": [],
  "observations": [],
  "tasks": [],
  "artifacts": [],
  "open_evidence_gaps": [],
  "conflicts": [],
  "approvals": {
    "scope": {"status": "pending", "by": null, "at": null, "note": null},
    "direction": {"status": "pending", "by": null, "at": null, "note": null},
    "plan": {"status": "pending", "by": null, "at": null, "note": null},
    "execution": {"status": "pending", "by": null, "at": null, "note": null},
    "claim": {"status": "pending", "by": null, "at": null, "note": null}
  },
  "stop_conditions": []
}
```

## Stages

Use the domain-neutral cycle:

`framing → grounding → route_selection → planning → working → interpreting → claim_review → deciding → complete`

Evidence, interpretation, or scope changes may return the project to an earlier
stage. Task-level waiting and parallel work belong in Task Node status; one
`waiting_human` task must not freeze unrelated project work.

## Canonical collections

| Collection | Prefix | Purpose |
|---|---|---|
| uncertainties | `U-` | Decision-relevant unknowns |
| evidence | `E-` | Inspected, located Evidence Packets |
| claims | `C-` | Bounded candidate or reviewed claims |
| routes | `RT-` | Domain-neutral method routes |
| working_propositions | `WP-` | Hypotheses, interpretations, models, or design propositions |
| protocols | `PR-` | Action plans for any route |
| observations | `O-` | Direct observations returned by a task or protocol |
| tasks | `T-` | Human/sub-agent/main/external work DAG |
| artifacts | `AR-` | Hashed files and data products |
| open_evidence_gaps | `G-` | Precise unresolved evidence needs |
| conflicts | `CF-` | Preserved contradictions or incompatibilities |

## Route

Routes do not enumerate disciplines. Describe each route with orthogonal fields:

```json
{
  "id": "RT-001",
  "epistemic_goal": "explanatory",
  "method_family": "Open description chosen for this project",
  "required_capabilities": ["Required data or expertise"],
  "executor_mix": ["agent", "human"],
  "validation_strategy": "How observations can change the decision",
  "uncertainty_ids": ["U-001"],
  "risks": ["Known validity boundary"],
  "status": "candidate"
}
```

Allowed epistemic goals are `descriptive`, `explanatory`, `predictive`,
`evaluative`, `interpretive`, `design`, and `mixed`. `method_family` remains an
open string.

Route executors are `agent`, `human`, `shared`, `expert`, and `external`;
Task Nodes refine Agent work into `main_agent` or `subagent` where needed.

## Evidence, observations, and claims

Evidence Packets retain proposition, stance, source identity, source lineage,
source depth, locator, limitations, and confidence. Metadata may only be
`context` or `inconclusive`. Inspected full text, artifacts, direct observations,
datasets, and expert attestations require a locator.

Evidence is immutable and append-only. Correct an earlier packet by adding a new
packet and, when necessary, a Conflict record.

Observations describe what was directly returned by a Task or Protocol and link
to hashed Artifacts. Claims separate interpretation from observation. A
Sub-agent reducer always creates claims as `candidate`; supported, refuted, or
final bounded claims remain subject to evidence and Claim Gate review.

## Update invariants

- Keep project ID and creation time immutable.
- Start every candidate from the current revision; reject stale canonical writes.
- Preserve existing Evidence as an exact prefix.
- Commit only through `update_state.py` or the task reducer with actor
  `main-agent`.
- Reset Direction approval after selected routes change.
- Reset Plan and Execution approval after a protocol changes.
- Return material question, scope, non-goal, or constraint changes to `framing`
  and reset Direction, Plan, Execution, and Claim approvals.
- Require Scope approval before leaving framing, Direction approval before
  planning/working, and Claim approval before complete.
- Validate task dependencies, context hashes, resource isolation, human levels,
  required gates, and task transitions before every commit.
- Snapshot the relevant Route, Protocol, Evidence, Claim, and Artifact IDs so a
  material input change invalidates only the affected task context.

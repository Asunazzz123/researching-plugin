# Task Node and human participation contract

## Contents

1. Human participation levels
2. Task kinds and status
3. Task Node schema
4. Dispatch and transition rules
5. Human Handoff

## Human participation levels

Classify each action independently of its discipline:

| Level | Meaning | Automatic behavior |
|---|---|---|
| `H0` | Deterministic, read-only, or reproducibly checked | May dispatch and merge after validation |
| `H1` | Batch work reviewed through summary, sampling, or later synthesis | May dispatch; merge only candidates |
| `H2` | Consequential interpretation or option generation | May dispatch candidate-only work; stop for human selection |
| `H3` | Recurring tacit or expert judgment | Do not auto-dispatch the task; create a collaborative handoff |
| `H4` | Human authority, ethics, law, physical action, institutional responsibility, or final claim | Human/expert/external executor only |

The orchestrator may raise a level when risk or uncertainty increases. Lowering
a level requires `human_level_override` with approver, timestamp, and reason.

## Task kinds and status

Kinds are `discover`, `extract`, `normalize`, `analyze`, `generate`, `criticize`,
`plan`, `execute`, `synthesize`, and `decide`. A kind does not imply a human
level.

Statuses are `draft`, `ready`, `assigned`, `running`, `waiting_human`,
`reported`, `validating`, `needs_rework`, `merged`, `blocked`, `cancelled`, and
`superseded`. Active work requires a frozen input snapshot. Dependencies must be
`merged` before a task becomes ready or active.

## Task Node schema

```json
{
  "id": "T-012",
  "parent_task_id": null,
  "title": "Inspect validation practices",
  "task_kind": "extract",
  "epistemic_role": "evidence_acquisition",
  "question": "Which inspected results bear on U-003?",
  "uncertainty_ids": ["U-003"],
  "human_level": "H1",
  "human_level_override": null,
  "executor": "subagent",
  "status": "draft",
  "depends_on": [],
  "priority": 60,
  "input_snapshot": {
    "research_revision": null,
    "context_hash": null,
    "route_ids": [],
    "protocol_ids": [],
    "evidence_ids": ["E-004"],
    "claim_ids": [],
    "artifact_ids": []
  },
  "execution": {
    "mode": "read_only",
    "read_scope": ["papers/example-record.md"],
    "write_scope": "orchestration/tasks/T-012",
    "resource_locks": [],
    "side_effects": ["none"],
    "parallel_group": "validation-review"
  },
  "output_contract": {
    "artifact_types": ["agent_report"],
    "may_propose_evidence": true,
    "may_propose_claims": false
  },
  "validation": {
    "mode": "schema_and_source",
    "requires_human": false,
    "acceptance_criteria": ["Detailed propositions have source locators"]
  },
  "merge": {
    "strategy": "append_candidates",
    "conflict_policy": "preserve_and_escalate",
    "required_gate": null
  },
  "human_handoff": null
}
```

Executors are `main_agent`, `subagent`, `human`, `shared`, `expert`, and
`external`. Execution modes are `read_only`, `prepare`, `execute_reversible`,
and `execute_external`. `read_scope` lists the workspace-relative artifacts the
task may inspect and may not include canonical state files. Every Task owns exactly
`orchestration/tasks/<task-id>`; no two Tasks share a write scope.

## Dispatch and transition rules

- Dispatch at most three ready, non-conflicting Tasks per session batch.
- Permit automatic frontier selection only for H0/H1, plus H2 configured with
  `human_checkpoint` candidate-only merge.
- Never auto-dispatch H3/H4 or `execute_external`.
- Treat active resource locks and unsafe side effects as frontier blockers.
- Do not parallelize dependent inference, final scope, route, execution, or
  Claim decisions.
- Keep task status and canonical state under the main-agent writer. A Sub-agent
  writes only its report and task-local artifacts.

## Human Handoff

H3/H4 Tasks require:

```json
{
  "action": "Exact human, expert, or external action",
  "prerequisites": ["Required access or preparation"],
  "quality_requirements": ["What makes the return interpretable"],
  "expected_artifacts": ["What must be returned"],
  "bias_fields": ["Selection, observer, access, or other relevant bias"],
  "deviation_fields": ["What departures must be recorded"],
  "resume_condition": "The condition under which orchestration can continue"
}
```

Returned material remains Observation or Evidence candidates until validated by
the main agent. A handoff is an execution interface, not a failure fallback.

# Research state contract

Use this contract when creating a candidate `research_state.json`. The validator
in `scripts/research_state.py` is authoritative.

## Workspace files

| Path | Role |
|---|---|
| `research_state.json` | Canonical current state |
| `evidence.jsonl` | Append-only mirror of Evidence Packets |
| `decisions.jsonl` | Append-only committed decision events |
| `.checkpoints/research_state.rNNNN.json` | State before each commit |
| `research_brief.md` | Default human-facing synthesis and route portfolio |
| `research_process.md` | Optional action and access ledger requested by the user |
| `experiments/` | Optional authorized plans, raw outputs, metrics, and notes |
| `research_summary.md` | Derived human-readable view; never edit as state |

## Top-level object

```json
{
  "schema_version": "1.0",
  "revision": 0,
  "created_at": "2026-07-22T00:00:00+00:00",
  "updated_at": "2026-07-22T00:00:00+00:00",
  "project": {
    "id": "stable-project-id",
    "question": "A bounded research question",
    "scope": ["What is included"],
    "non_goals": ["What is excluded"],
    "constraints": ["Time, data, compute, ethics, access"],
    "resources": {"compute": "one GPU"}
  },
  "current_stage": "framing",
  "uncertainties": [],
  "evidence": [],
  "claims": [],
  "hypotheses": [],
  "experiments": [],
  "results": [],
  "open_evidence_gaps": [],
  "next_actions": [],
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

New workspaces include all five gates. The validator keeps legacy three-gate
workspaces with the old `experiment` approval key readable, but resumed projects
should migrate it to `plan` and add `direction` and `execution` before entering
any new planning or execution branch.

Use IDs with these prefixes:

| Collection | Prefix |
|---|---|
| uncertainties | `U-` |
| evidence | `E-` |
| claims | `C-` |
| hypotheses | `H-` |
| experiments | `EXP-` |
| results | `R-` |
| open evidence gaps | `G-` |
| next actions | `A-` |

## Evidence Packet

```json
{
  "id": "E-001",
  "proposition": "The exact proposition supported by the inspected source",
  "stance": "supports",
  "source_kind": "literature",
  "source_id": "doi:10.xxxx/example",
  "source_depth": "full_text",
  "locator": {"page": 7, "section": "4.2", "figure": "Fig. 3"},
  "limitations": ["Small sample", "Different target population"],
  "confidence": 0.85
}
```

Allowed stance values are `supports`, `contradicts`, `context`, and
`inconclusive`. Allowed source kinds are `literature`, `experiment`,
`observation`, and `dataset`.

Use source depth deliberately:

- `metadata`: identity and context only; it cannot support or contradict a claim.
- `abstract`: only propositions explicitly present in the abstract.
- `full_text`: require a non-empty locator.
- `experiment_artifact`: reference a preserved local experiment output.
- `direct_observation`: record a directly observed phenomenon.
- `dataset`: describe evidence obtained from an inspected dataset.

Evidence is immutable and append-only. Add a correcting Evidence Packet rather
than editing or deleting an earlier packet.

## Hypothesis

```json
{
  "id": "H-001",
  "statement": "A falsifiable statement",
  "mechanism": "Why the predicted effect should occur",
  "evidence_ids": ["E-001"],
  "assumptions": ["Required assumption"],
  "predictions": ["Observable discriminating prediction"],
  "falsifiers": ["Observation that would count against the hypothesis"],
  "alternative_hypothesis_ids": ["H-002"],
  "nearest_prior_work": ["doi:10.xxxx/example"],
  "novelty_delta": "Bounded difference from the nearest work",
  "cheapest_discriminating_test": "Smallest information-gaining step that changes the decision; it need not be a local experiment",
  "status": "active"
}
```

Allowed statuses are `proposed`, `active`, `deprioritized`, `supported`, and
`refuted`. Prefer several competing hypotheses over variants of one favored idea.

## Experiment

```json
{
  "id": "EXP-001",
  "title": "Bounded pilot title",
  "hypothesis_ids": ["H-001", "H-002"],
  "purpose": "Which uncertainty this experiment resolves",
  "variables": {"independent": ["x"], "dependent": ["y"]},
  "baselines": ["Existing method or null model"],
  "controls": ["Leakage, ablation, or negative control"],
  "confounds": ["Known plausible confound"],
  "primary_metric": "A predeclared decision metric",
  "secondary_metrics": [],
  "budget": {"time_minutes": 30, "max_runs": 3},
  "stop_conditions": ["Stop on data leakage", "Stop after max_runs"],
  "artifact_paths": ["experiments/EXP-001/"],
  "result_ids": [],
  "status": "planned"
}
```

Allowed statuses are `proposed`, `planned`, `approved`, `running`, `completed`,
`failed`, and `stopped`.

## Result and claim

```json
{
  "id": "R-001",
  "experiment_id": "EXP-001",
  "observations": ["Direct observation without interpretation"],
  "metrics": {"primary": 0.73},
  "artifact_paths": ["experiments/EXP-001/metrics.json"],
  "unexpected_findings": [],
  "limitations": []
}
```

```json
{
  "id": "C-001",
  "statement": "A bounded scientific claim",
  "status": "inference",
  "evidence_ids": ["E-001"],
  "result_ids": ["R-001"],
  "caveats": ["Boundary of the current evidence"]
}
```

Claim statuses are `hypothesis`, `inference`, `supported`, `refuted`, and
`unknown`. An `inference`, `supported`, or `refuted` claim must reference
evidence or results.

## Update invariants

- Keep `project.id` and `created_at` immutable.
- Start a candidate from the current revision; stale candidates are rejected.
- Preserve existing evidence as an exact prefix.
- Follow the allowed research-stage graph; use `deciding` as the convergence
  point after grounding, hypothesizing, designing, or interpreting. Enter the
  experiment branch only when the research question actually needs it.
- Treat candidate `A-*` actions in `deciding` as the research route portfolio.
  Stop for Direction Gate rather than selecting a route for the human.
- Require Direction Gate before `designing`, Plan Gate before `pilot_ready` or
  `full_experiment_ready`, and a separate Execution Gate before `piloting` or
  `experimenting`. Never infer either approval from a broad research request.
- Reset both plan and execution approvals whenever the protocol changes.
- Return material question, scope, non-goal, or constraint changes to `framing`
  and reset direction, plan, execution, and claim approvals.
- Commit canonical state only through `scripts/update_state.py`.
- Store raw experiment artifacts before adding a Result record.
